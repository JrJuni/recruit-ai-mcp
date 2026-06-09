from __future__ import annotations

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.schema.deal_gaps import MAX_LIMIT, PRIORITY_BANDS, build_deal_gaps_summary
from deal_intel.schema.metrics import (
    VALID_STAGES,
    HealthBandThresholds,
    PipelineTimingSettings,
    ReportingContext,
)
from deal_intel.storage.mongodb import MongoDBClient


def handle(
    mongo: MongoDBClient,
    cfg: dict,
    *,
    as_of: str | None = None,
    stage: str | None = None,
    industry: str | None = None,
    deal_id: str | None = None,
    min_priority: str = "medium",
    limit: int = 10,
) -> dict:
    if stage and stage not in VALID_STAGES:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=f"stage {stage!r} is not valid",
            hint={"valid_stages": sorted(VALID_STAGES)},
            retryable=False,
        )
    if min_priority not in PRIORITY_BANDS:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=f"min_priority {min_priority!r} is not valid",
            hint={"valid_priorities": list(PRIORITY_BANDS)},
            retryable=False,
        )
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > MAX_LIMIT:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=f"limit must be between 1 and {MAX_LIMIT}",
            hint={"min": 1, "max": MAX_LIMIT},
            retryable=False,
        )

    try:
        reporting = ReportingContext.from_config(cfg, as_of=as_of)
        health_thresholds = HealthBandThresholds.from_config(cfg)
        timing_settings = PipelineTimingSettings.from_config(cfg)
    except ValueError as exc:
        error_code = (
            ErrorCode.INVALID_INPUT
            if str(exc).startswith("as_of")
            else ErrorCode.CONFIG_ERROR
        )
        raise MCPError(
            error_code=error_code,
            stage=Stage.PREFLIGHT,
            message=str(exc),
            retryable=False,
        ) from exc

    try:
        deals = mongo.list_deals_for_metrics()
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=str(exc),
            retryable=True,
        ) from exc

    gaps = build_deal_gaps_summary(
        deals,
        as_of=reporting.as_of,
        health_thresholds=health_thresholds,
        timing_settings=timing_settings,
        stage=stage,
        industry=industry,
        deal_id=deal_id,
        min_priority=min_priority,
        limit=limit,
    )
    return {
        "ok": True,
        **reporting.to_dict(),
        **gaps,
    }
