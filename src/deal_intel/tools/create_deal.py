from __future__ import annotations

import uuid
from datetime import UTC, datetime

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.storage.mongodb import MongoDBClient


def handle(
    mongo: MongoDBClient,
    *,
    company: str,
    industry: str | None,
    deal_size_krw: int | None,
    expected_close_date: str | None = None,
) -> dict:
    if not company or not company.strip():
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message="company must not be empty",
            retryable=False,
        )
    now = datetime.now(UTC).isoformat()
    deal = {
        "deal_id": str(uuid.uuid4()),
        "company": company.strip(),
        "industry": industry,
        "deal_size_krw": deal_size_krw,
        "contacts": [],
        "meetings": [],
        "meddpicc_latest": {},
        "stage_history": [{"stage": "discovery", "entered_at": now}],
        "deal_stage": "discovery",
        "expected_close_date": expected_close_date,
        "actual_close_date": None,
        "close_reason": None,
        "bd_strategy": "",
        "gtm_notes": "",
        "prospect_id": None,
        "created_at": now,
        "updated_at": now,
    }
    try:
        mongo.upsert_deal(deal)
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=str(exc),
            hint="Check MONGODB_URI and Atlas cluster status",
            retryable=True,
        ) from exc
    return {"ok": True, "deal_id": deal["deal_id"], "company": deal["company"]}
