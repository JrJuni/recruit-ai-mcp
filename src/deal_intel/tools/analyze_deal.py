from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.product_context import (
    product_context_refs,
    render_product_context_prompt_block,
    retrieve_product_context,
)
from deal_intel.providers.llm import LLMProvider
from deal_intel.schema.interactions import scoring_interactions
from deal_intel.storage.mongodb import MongoDBClient
from deal_intel.usage import build_llm_usage_metadata

_SYSTEM = "You are a senior B2B sales strategist. Be direct, specific, and actionable."

_PROMPT = """\
Analyze this deal's MEDDPICC qualification status and provide a concrete BD strategy.

Deal: {company} | Stage: {stage} | Interactions: {interaction_count}
Industry: {industry} | Customer segment: {customer_segment}
{size_line}
{product_context_prompt}
MEDDPICC scores (avg across scoring-eligible interactions, 0=no data / 5=confirmed):
{meddpicc_summary}

Provide:

**1. Top 3 Gaps**
Which MEDDPICC dimensions are weakest, and why each gap is a deal risk.

**2. Next 3 Actions**
Specific, immediate steps to advance the deal (who to contact, what to ask, what to prepare).

**3. Win/Risk Assessment**
Probability estimate and the single biggest risk factor right now.

**4. GTM Positioning**
How to frame the value proposition for this specific prospect given their pain and metrics.\
"""

_DIMS = [
    "metrics", "economic_buyer", "decision_criteria",
    "decision_process", "identify_pain", "champion", "competition",
]


def _meddpicc_summary(interactions: list[dict]) -> str:
    scores: dict[str, list[int]] = defaultdict(list)
    for interaction in interactions:
        for k, v in (interaction.get("meddpicc") or {}).items():
            if isinstance(v, dict) and isinstance(v.get("score"), int):
                scores[k].append(v["score"])
    lines = []
    for d in _DIMS:
        if scores[d]:
            avg = sum(scores[d]) / len(scores[d])
            n = len(scores[d])
            lines.append(f"  {d}: {avg:.1f}/5 ({n} data point{'s' if n > 1 else ''})")
        else:
            lines.append(f"  {d}: no data")
    return "\n".join(lines)


def _product_context_query(deal: dict, interactions: list[dict]) -> str:
    parts = [
        str(deal.get("company") or ""),
        str(deal.get("industry") or ""),
        str(deal.get("customer_segment") or ""),
        str(deal.get("deal_stage") or ""),
    ]
    for theme in (deal.get("customer_themes") or [])[:8]:
        if not isinstance(theme, dict):
            continue
        parts.extend(
            [
                str(theme.get("label") or ""),
                str(theme.get("dimension") or ""),
                str(theme.get("evidence") or ""),
            ]
        )
    for interaction in interactions[-3:]:
        if not isinstance(interaction, dict):
            continue
        if interaction.get("summary"):
            parts.append(str(interaction["summary"]))
        for item in (interaction.get("meddpicc") or {}).values():
            if isinstance(item, dict) and item.get("evidence"):
                parts.append(str(item["evidence"]))
    return "\n".join(part.strip() for part in parts if part and part.strip())[:6000]


def _retrieve_product_context_for_strategy(
    *,
    cfg: dict,
    embedding_provider,
    deal: dict,
    interactions: list[dict],
) -> dict:
    if embedding_provider is None:
        return {"ok": True, "result_count": 0, "results": [], "warnings": []}
    product_cfg = cfg.get("product_context") if isinstance(cfg, dict) else None
    if isinstance(product_cfg, dict) and product_cfg.get("enabled") is False:
        return {"ok": True, "result_count": 0, "results": [], "warnings": []}
    query = _product_context_query(deal, interactions)
    if not query:
        return {"ok": True, "result_count": 0, "results": [], "warnings": []}
    try:
        payload = retrieve_product_context(
            cfg,
            embedding_provider=embedding_provider,
            query=query,
        )
    except Exception as exc:
        return {
            "ok": False,
            "result_count": 0,
            "results": [],
            "warnings": [
                {
                    "code": "product_context_retrieval_failed",
                    "message": str(exc),
                }
            ],
        }
    suppress_codes = {"product_context_index_empty_or_unembedded"}
    payload["warnings"] = [
        warning
        for warning in payload.get("warnings", [])
        if warning.get("code") not in suppress_codes
    ]
    return payload


def handle(
    mongo: MongoDBClient,
    llm: LLMProvider,
    cfg: dict,
    embedding_provider=None,
    *,
    deal_id: str,
) -> dict:
    deal = mongo.get_deal(deal_id)
    if deal is None:
        raise MCPError(
            error_code=ErrorCode.NOT_FOUND,
            stage=Stage.STORAGE,
            message=f"deal_id {deal_id!r} not found",
            retryable=False,
        )

    interactions = scoring_interactions(deal)
    product_context_payload = _retrieve_product_context_for_strategy(
        cfg=cfg,
        embedding_provider=embedding_provider,
        deal=deal,
        interactions=interactions,
    )
    product_context_prompt = render_product_context_prompt_block(
        product_context_payload
    )
    product_context_references = product_context_refs(product_context_payload)
    product_context_warnings = product_context_payload.get("warnings", [])
    currency = deal.get("deal_size_currency") or "KRW"
    size_line = (
        f"Deal size: {deal['deal_size_amount']:,} {currency}\n"
        if deal.get("deal_size_amount")
        else ""
    )
    prompt = _PROMPT.format(
        company=deal["company"],
        stage=deal.get("deal_stage", "unknown"),
        industry=deal.get("industry") or "unknown",
        customer_segment=deal.get("customer_segment") or "unknown",
        interaction_count=len(interactions),
        size_line=size_line,
        product_context_prompt=(
            f"{product_context_prompt}\n\n" if product_context_prompt else ""
        ),
        meddpicc_summary=_meddpicc_summary(interactions),
    )

    try:
        resp = llm.chat_once(system=_SYSTEM, user=prompt, max_tokens=2048)
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.LLM_ERROR,
            stage=Stage.ANALYSIS,
            message=str(exc),
            retryable=True,
        ) from exc

    llm_usage = build_llm_usage_metadata(
        cfg,
        source_tool="analyze_deal",
        calls=[{"operation": "generate_bd_strategy", "usage": resp.usage}],
    )
    deal["bd_strategy"] = resp.text
    deal["bd_strategy_usage"] = llm_usage
    deal["bd_strategy_product_context_refs"] = product_context_references
    deal["updated_at"] = datetime.now(UTC).isoformat()
    try:
        mongo.upsert_deal(deal)
    except Exception:
        pass  # analysis still returned even if save fails

    return {
        "ok": True,
        "deal_id": deal_id,
        "analysis": resp.text,
        "product_context_used": bool(product_context_references),
        "product_context_ref_count": len(product_context_references),
        "product_context_refs": product_context_references,
        "warnings": product_context_warnings,
        "usage": resp.usage,
        "usage_summary": {
            "calls": llm_usage["calls"],
            "totals": llm_usage["totals"],
            "estimated_cost_usd": llm_usage["estimated_cost_usd"],
            "cost_basis": llm_usage["cost_basis"],
        },
    }
