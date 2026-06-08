from __future__ import annotations

from datetime import UTC, datetime

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.schema.meddpicc import VALID_STAGES, compute_meddpicc_latest
from deal_intel.storage.mongodb import MongoDBClient


def handle(
    mongo: MongoDBClient,
    cfg: dict,
    *,
    deal_id: str,
    new_stage: str,
) -> dict:
    if new_stage not in VALID_STAGES:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=f"stage {new_stage!r} is not valid",
            hint={"valid_stages": sorted(VALID_STAGES)},
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

    old_stage = deal.get("deal_stage", "discovery")
    now = datetime.now(UTC).isoformat()

    deal["deal_stage"] = new_stage
    deal["updated_at"] = now
    deal.setdefault("stage_history", []).append({
        "stage": new_stage,
        "entered_at": now,
    })

    # Recompute meddpicc_latest with the new stage so gap classification
    # reflects the updated stage context (e.g., won → gaps cleared).
    if deal.get("meetings"):
        meddpicc_cfg = cfg.get("meddpicc", {})
        deal["meddpicc_latest"] = compute_meddpicc_latest(
            deal["meetings"],
            weights=meddpicc_cfg.get("weights", {}),
            gap_threshold=int(meddpicc_cfg.get("gap_threshold", 2)),
            deal_stage=new_stage,
        )

    try:
        mongo.upsert_deal(deal)
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=str(exc),
            retryable=True,
        ) from exc

    # Compute days spent in previous stage from stage_history.
    history = deal.get("stage_history", [])
    days_in_prev: float | None = None
    if len(history) >= 2:
        prev_entry = history[-2]
        try:
            from datetime import datetime as _dt
            prev_ts = _dt.fromisoformat(prev_entry["entered_at"])
            curr_ts = _dt.fromisoformat(now)
            days_in_prev = round((curr_ts - prev_ts).total_seconds() / 86400, 1)
        except Exception:
            pass

    # Check stuck threshold for the NEW stage using configurable values.
    pipeline_cfg = cfg.get("pipeline", {})
    stuck_by_stage = pipeline_cfg.get("stuck_threshold_days_by_stage", {})
    stuck_default = int(pipeline_cfg.get("stuck_threshold_days", 14))
    threshold = int(stuck_by_stage.get(new_stage, stuck_default))

    return {
        "ok": True,
        "deal_id": deal_id,
        "old_stage": old_stage,
        "new_stage": new_stage,
        "days_in_previous_stage": days_in_prev,
        "stuck_threshold_days": threshold,
    }
