from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from deal_intel.providers.llm import LLMProvider
from deal_intel.storage.mongodb import MongoDBClient

_SYSTEM = "You are a senior B2B sales strategist. Be direct, specific, and actionable."

_PROMPT = """\
Analyze this deal's MEDDPICC qualification status and provide a concrete BD strategy.

Deal: {company} | Stage: {stage} | Meetings: {meeting_count}
{size_line}
MEDDPICC scores (avg across all meetings, 0=no data / 5=confirmed):
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


def _meddpicc_summary(meetings: list[dict]) -> str:
    scores: dict[str, list[int]] = defaultdict(list)
    for m in meetings:
        for k, v in (m.get("meddpicc") or {}).items():
            if isinstance(v, dict) and isinstance(v.get("score"), int):
                scores[k].append(v["score"])
    lines = []
    for d in _DIMS:
        if scores[d]:
            avg = sum(scores[d]) / len(scores[d])
            lines.append(f"  {d}: {avg:.1f}/5 ({len(scores[d])} data point{'s' if len(scores[d])>1 else ''})")
        else:
            lines.append(f"  {d}: no data")
    return "\n".join(lines)


def handle(mongo: MongoDBClient, llm: LLMProvider, *, deal_id: str) -> dict:
    deal = mongo.get_deal(deal_id)
    if deal is None:
        return {"ok": False, "error_code": "NOT_FOUND", "message": f"deal_id {deal_id!r} not found"}

    meetings = deal.get("meetings", [])
    size_line = ""
    if deal.get("deal_size_krw"):
        size_line = f"Deal size: {deal['deal_size_krw']:,} KRW\n"

    prompt = _PROMPT.format(
        company=deal["company"],
        stage=deal.get("deal_stage", "unknown"),
        meeting_count=len(meetings),
        size_line=size_line,
        meddpicc_summary=_meddpicc_summary(meetings),
    )

    try:
        resp = llm.chat_once(system=_SYSTEM, user=prompt, max_tokens=2048)
    except Exception as exc:
        return {"ok": False, "error_code": "LLM_ERROR", "message": str(exc)}

    deal["bd_strategy"] = resp.text
    deal["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        mongo.upsert_deal(deal)
    except Exception:
        pass  # analysis result still returned even if save fails

    return {"ok": True, "deal_id": deal_id, "analysis": resp.text, "usage": resp.usage}
