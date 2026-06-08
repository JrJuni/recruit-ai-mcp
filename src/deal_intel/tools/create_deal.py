from __future__ import annotations

import uuid
from datetime import datetime, timezone

from deal_intel.storage.mongodb import MongoDBClient


def handle(
    mongo: MongoDBClient,
    *,
    company: str,
    industry: str | None,
    deal_size_krw: int | None,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    deal = {
        "deal_id": str(uuid.uuid4()),
        "company": company,
        "industry": industry,
        "deal_size_krw": deal_size_krw,
        "contacts": [],
        "meetings": [],
        "deal_stage": "discovery",
        "close_reason": None,
        "bd_strategy": "",
        "gtm_notes": "",
        "prospect_id": None,
        "created_at": now,
        "updated_at": now,
    }
    try:
        mongo.upsert_deal(deal)
        return {"ok": True, "deal_id": deal["deal_id"], "company": company}
    except Exception as exc:
        return {"ok": False, "error_code": "STORAGE_ERROR", "message": str(exc)}
