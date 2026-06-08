from __future__ import annotations

from datetime import UTC, datetime

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.schema.meddpicc import VALID_STAGES
from deal_intel.storage.mongodb import MongoDBClient


def _days_in_current_stage(deal: dict) -> float | None:
    history = deal.get("stage_history")
    if not history:
        return None
    last = history[-1]
    try:
        entered = datetime.fromisoformat(last["entered_at"])
        now = datetime.now(UTC)
        return round((now - entered).total_seconds() / 86400, 1)
    except Exception:
        return None


def handle(mongo: MongoDBClient, cfg: dict, *, stage: str | None, limit: int) -> dict:
    if stage and stage not in VALID_STAGES:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=f"stage {stage!r} is not valid",
            hint={"valid_stages": sorted(VALID_STAGES)},
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

    pipeline_cfg = cfg.get("pipeline", {})
    stuck_by_stage = pipeline_cfg.get("stuck_threshold_days_by_stage", {})
    stuck_default = int(pipeline_cfg.get("stuck_threshold_days", 14))

    terminal_stages = {"won", "lost"}

    summaries = []
    for d in deals:
        current_stage = d.get("deal_stage", "")
        meddpicc_latest = d.get("meddpicc_latest") or {}
        days = _days_in_current_stage(d)
        threshold = int(stuck_by_stage.get(current_stage, stuck_default))
        is_stuck = (
            current_stage not in terminal_stages
            and threshold > 0
            and days is not None
            and days > threshold
        )
        summaries.append({
            "deal_id": d["deal_id"],
            "company": d["company"],
            "industry": d.get("industry"),
            "deal_stage": current_stage,
            "deal_size_krw": d.get("deal_size_krw"),
            "expected_close_date": d.get("expected_close_date"),
            "actual_close_date": d.get("actual_close_date"),
            "health_pct": meddpicc_latest.get("health_pct"),
            "filled_count": meddpicc_latest.get("filled_count"),
            "gaps": meddpicc_latest.get("gaps", []),
            "meeting_count": len(d.get("meetings", [])),
            "days_in_stage": days,
            "is_stuck": is_stuck,
            "updated_at": d.get("updated_at", ""),
        })

    # Sort: stuck deals first, then by health_pct desc within each group.
    summaries.sort(key=lambda x: (not x["is_stuck"], -(x["health_pct"] or 0)))

    return {"ok": True, "deals": summaries, "count": len(summaries)}
