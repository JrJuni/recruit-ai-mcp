from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.product_context import (
    embedding_readiness_status,
    product_context_refs,
    render_product_context_prompt_block,
    retrieve_product_context,
)
from deal_intel.providers.llm import LLMProvider
from deal_intel.schema.interactions import scoring_interactions
from deal_intel.storage.mongodb import MongoDBClient
from deal_intel.usage import (
    build_llm_usage_metadata,
    normalize_usage,
    provider_model_from_config,
)

_SYSTEM = "You are a senior B2B sales strategist. Be direct, specific, and actionable."
_CACHE_TTL_SECONDS = 600
_CACHE_MAX_ENTRIES = 128
_ANALYZE_CACHE: dict[str, dict] = {}
_ANALYZE_CACHE_LOCK = RLock()

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
        return {
            "ok": True,
            "result_count": 0,
            "results": [],
            "warnings": [
                {
                    "code": "product_context_embedding_not_installed",
                    "message": "Product context was skipped because embeddings are not installed.",
                }
            ],
            "embedding_status": embedding_readiness_status(embedding_provider),
            "product_context_status": {
                "state": "embedding_unavailable",
                "message": "Product context retrieval requires embeddings.",
            },
        }
    product_cfg = cfg.get("product_context") if isinstance(cfg, dict) else None
    if isinstance(product_cfg, dict) and product_cfg.get("enabled") is False:
        return {
            "ok": True,
            "result_count": 0,
            "results": [],
            "warnings": [],
            "embedding_status": embedding_readiness_status(embedding_provider),
            "product_context_status": {
                "state": "disabled",
                "message": "Product context is disabled in config.",
            },
        }
    embedding_status = embedding_readiness_status(embedding_provider)
    if embedding_status["state"] != "ready":
        return {
            "ok": True,
            "result_count": 0,
            "results": [],
            "warnings": [
                {
                    "code": "product_context_embedding_not_ready",
                    "message": (
                        "Product context was skipped because the local embedding "
                        "model is not ready yet."
                    ),
                    "embedding_status": embedding_status,
                }
            ],
            "embedding_status": embedding_status,
            "product_context_status": {
                "state": "embedding_loading"
                if embedding_status["state"] in {"loading", "not_started"}
                else "embedding_failed",
                "message": "Product context retrieval is not ready.",
            },
        }
    query = _product_context_query(deal, interactions)
    if not query:
        return {
            "ok": True,
            "result_count": 0,
            "results": [],
            "warnings": [],
            "embedding_status": embedding_status,
            "product_context_status": {
                "state": "no_query",
                "message": "No deal text was available for product-context retrieval.",
            },
        }
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


def clear_analysis_cache() -> None:
    with _ANALYZE_CACHE_LOCK:
        _ANALYZE_CACHE.clear()


def _analysis_cache_key(
    *,
    deal_id: str,
    prompt: str,
    product_context_references: list[dict],
    llm_provider: str,
    llm_model: str,
) -> str:
    payload = {
        "version": 1,
        "deal_id": deal_id,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "prompt": prompt,
        "product_context_refs": product_context_references,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _cache_get(cache_key: str) -> tuple[dict | None, float]:
    now = time.monotonic()
    with _ANALYZE_CACHE_LOCK:
        entry = _ANALYZE_CACHE.get(cache_key)
        if not entry:
            return None, 0.0
        age = now - float(entry.get("created_monotonic") or 0.0)
        if age > _CACHE_TTL_SECONDS:
            _ANALYZE_CACHE.pop(cache_key, None)
            return None, 0.0
        return deepcopy(entry), age


def _cache_set(cache_key: str, entry: dict) -> None:
    with _ANALYZE_CACHE_LOCK:
        _ANALYZE_CACHE[cache_key] = deepcopy(entry)
        if len(_ANALYZE_CACHE) <= _CACHE_MAX_ENTRIES:
            return
        oldest_key = min(
            _ANALYZE_CACHE,
            key=lambda key: float(
                _ANALYZE_CACHE[key].get("created_monotonic") or 0.0
            ),
        )
        _ANALYZE_CACHE.pop(oldest_key, None)


def _usage_summary(llm_usage: dict) -> dict:
    return {
        "calls": llm_usage["calls"],
        "totals": llm_usage["totals"],
        "estimated_cost_usd": llm_usage["estimated_cost_usd"],
        "cost_basis": llm_usage["cost_basis"],
    }


def _zero_usage_summary(cfg: dict) -> dict:
    llm_usage = build_llm_usage_metadata(
        cfg,
        source_tool="analyze_deal",
        calls=[],
    )
    return _usage_summary(llm_usage)


def _persist_strategy(
    *,
    mongo: MongoDBClient,
    deal: dict,
    analysis: str,
    llm_usage: dict,
    product_context_references: list[dict],
) -> tuple[bool, dict | None]:
    deal["bd_strategy"] = analysis
    deal["bd_strategy_usage"] = llm_usage
    deal["bd_strategy_product_context_refs"] = product_context_references
    deal["updated_at"] = datetime.now(UTC).isoformat()
    try:
        mongo.upsert_deal(deal)
    except Exception as exc:
        return False, {
            "code": "bd_strategy_persist_failed",
            "message": str(exc),
        }
    return True, None


def _base_result(
    *,
    deal_id: str,
    analysis: str,
    product_context_references: list[dict],
    product_context_payload: dict,
    warnings: list[dict],
    persist_strategy: bool,
    storage_written: bool,
    cache_hit: bool,
    force: bool,
    usage: dict,
    usage_summary: dict,
) -> dict:
    return {
        "ok": True,
        "deal_id": deal_id,
        "analysis": analysis,
        "persist_strategy": persist_strategy,
        "storage_written": storage_written,
        "cache_hit": cache_hit,
        "force": force,
        "product_context_used": bool(product_context_references),
        "product_context_ref_count": len(product_context_references),
        "product_context_refs": product_context_references,
        "product_context_status": product_context_payload.get(
            "product_context_status"
        ),
        "embedding_status": product_context_payload.get("embedding_status"),
        "warnings": warnings,
        "usage": usage,
        "usage_summary": usage_summary,
    }


def handle(
    mongo: MongoDBClient,
    llm: LLMProvider,
    cfg: dict,
    embedding_provider=None,
    *,
    deal_id: str,
    persist_strategy: bool = False,
    confirmed_by_user: bool = False,
    force: bool = False,
) -> dict:
    if persist_strategy and not confirmed_by_user:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=(
                "persist_strategy=true requires confirmed_by_user=true so "
                "analyze_deal does not write bd_strategy accidentally"
            ),
            retryable=False,
        )

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
    llm_provider_name, llm_model_name = provider_model_from_config(cfg)
    cache_key = _analysis_cache_key(
        deal_id=deal_id,
        prompt=prompt,
        product_context_references=product_context_references,
        llm_provider=llm_provider_name,
        llm_model=llm_model_name,
    )

    if not force:
        cached, cache_age_seconds = _cache_get(cache_key)
        if cached is not None:
            warnings = deepcopy(cached.get("warnings") or [])
            storage_written = False
            if persist_strategy:
                storage_written, persist_warning = _persist_strategy(
                    mongo=mongo,
                    deal=deal,
                    analysis=str(cached["analysis"]),
                    llm_usage=deepcopy(cached["llm_usage"]),
                    product_context_references=deepcopy(
                        cached["product_context_refs"]
                    ),
                )
                if persist_warning is not None:
                    warnings.append(persist_warning)
            result = _base_result(
                deal_id=deal_id,
                analysis=str(cached["analysis"]),
                product_context_references=deepcopy(
                    cached["product_context_refs"]
                ),
                product_context_payload=product_context_payload,
                warnings=warnings,
                persist_strategy=persist_strategy,
                storage_written=storage_written,
                cache_hit=True,
                force=force,
                usage=normalize_usage({}),
                usage_summary=_zero_usage_summary(cfg),
            )
            result["cache_age_seconds"] = round(cache_age_seconds, 3)
            result["cooldown_seconds"] = _CACHE_TTL_SECONDS
            return result

    try:
        resp = llm.chat_once(system=_SYSTEM, user=prompt, max_tokens=2048)
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.LLM_ERROR,
            stage=Stage.ANALYSIS,
            message=str(exc),
            retryable=False,
        ) from exc

    llm_usage = build_llm_usage_metadata(
        cfg,
        source_tool="analyze_deal",
        calls=[{"operation": "generate_bd_strategy", "usage": resp.usage}],
    )
    storage_written = False
    warnings = deepcopy(product_context_warnings)
    if persist_strategy:
        storage_written, persist_warning = _persist_strategy(
            mongo=mongo,
            deal=deal,
            analysis=resp.text,
            llm_usage=llm_usage,
            product_context_references=product_context_references,
        )
        if persist_warning is not None:
            warnings.append(persist_warning)

    _cache_set(
        cache_key,
        {
            "created_monotonic": time.monotonic(),
            "analysis": resp.text,
            "product_context_refs": product_context_references,
            "warnings": product_context_warnings,
            "usage": resp.usage,
            "llm_usage": llm_usage,
        },
    )

    return _base_result(
        deal_id=deal_id,
        analysis=resp.text,
        product_context_references=product_context_references,
        product_context_payload=product_context_payload,
        warnings=warnings,
        persist_strategy=persist_strategy,
        storage_written=storage_written,
        cache_hit=False,
        force=force,
        usage=resp.usage,
        usage_summary=_usage_summary(llm_usage),
    )
