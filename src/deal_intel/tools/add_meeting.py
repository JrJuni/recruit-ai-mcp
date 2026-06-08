from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from deal_intel.providers.llm import LLMProvider
from deal_intel.storage.mongodb import MongoDBClient

_SYSTEM = "You are a B2B sales expert specializing in MEDDPICC deal qualification."

_PROMPT = """\
Extract MEDDPICC qualification signals from the meeting notes below.

For each dimension present in the notes, return:
- score: 0-5  (0=absent, 1=weak mention, 3=moderate signal, 5=confirmed/strong)
- evidence: direct quote or close paraphrase from the notes

MEDDPICC dimensions:
- metrics: Quantifiable business impact, ROI, or success criteria
- economic_buyer: Decision-maker identity, authority level, and access
- decision_criteria: Formal or informal selection requirements
- decision_process: Procurement, approval, or timeline steps
- identify_pain: Core business problem, severity, and urgency
- champion: Internal advocate — name, position, commitment level
- competition: Competing vendors, alternatives, or status quo

Omit dimensions with no evidence. Return valid JSON only — no prose, no markdown fences.

Example output:
{{"metrics": {{"score": 3, "evidence": "CFO wants 20% cost reduction by Q3"}}, "identify_pain": {{"score": 4, "evidence": "Current system crashes weekly, costing ~$50k/mo"}}}}

Meeting notes:
{notes}\
"""


def handle(
    mongo: MongoDBClient,
    llm: LLMProvider,
    *,
    deal_id: str,
    date: str,
    raw_notes: str,
) -> dict:
    deal = mongo.get_deal(deal_id)
    if deal is None:
        return {"ok": False, "error_code": "NOT_FOUND", "message": f"deal_id {deal_id!r} not found"}

    try:
        resp = llm.chat_once(
            system=_SYSTEM,
            user=_PROMPT.format(notes=raw_notes),
            max_tokens=1024,
        )
        meddpicc_raw = json.loads(resp.text)
    except json.JSONDecodeError:
        meddpicc_raw = {}
    except Exception as exc:
        return {"ok": False, "error_code": "LLM_ERROR", "message": str(exc)}

    meeting = {
        "meeting_id": str(uuid.uuid4()),
        "date": date,
        "raw_notes": raw_notes,
        "summary": "",
        "meddpicc": meddpicc_raw,
    }
    deal.setdefault("meetings", []).append(meeting)
    deal["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        mongo.upsert_deal(deal)
    except Exception as exc:
        return {"ok": False, "error_code": "STORAGE_ERROR", "message": str(exc)}

    return {
        "ok": True,
        "meeting_id": meeting["meeting_id"],
        "meddpicc": meddpicc_raw,
        "usage": resp.usage,
    }
