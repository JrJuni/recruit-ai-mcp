from __future__ import annotations

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.storage.mongodb import MongoDBClient

_VALID_STAGES = frozenset({
    "discovery", "qualification", "proposal", "negotiation", "won", "lost", "stalled",
})


def handle(mongo: MongoDBClient, *, stage: str | None, limit: int) -> dict:
    if stage and stage not in _VALID_STAGES:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=f"stage {stage!r} is not valid",
            hint={"valid_stages": sorted(_VALID_STAGES)},
            retryable=False,
        )
    try:
        deals = mongo.list_deals(stage=stage, limit=limit)
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=str(exc),
            retryable=True,
        ) from exc

    summaries = [
        {
            "deal_id": d["deal_id"],
            "company": d["company"],
            "industry": d.get("industry"),
            "deal_stage": d.get("deal_stage", ""),
            "meeting_count": len(d.get("meetings", [])),
            "updated_at": d.get("updated_at", ""),
        }
        for d in deals
    ]
    return {"ok": True, "deals": summaries, "count": len(summaries)}
