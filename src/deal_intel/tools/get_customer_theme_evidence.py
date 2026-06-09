from __future__ import annotations

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.schema.customer_theme_insights import (
    VALID_DIMENSION_FILTERS,
    VALID_STAGE_FILTERS,
    build_customer_theme_evidence,
    validate_evidence_inputs,
)
from deal_intel.schema.customer_themes import THEME_TAXONOMY
from deal_intel.storage.mongodb import MongoDBClient


def handle(
    mongo: MongoDBClient,
    *,
    theme_key: str,
    dimension: str = "all",
    stage: str = "active",
    industry: str | None = None,
    limit: int = 10,
    min_importance: int = 1,
) -> dict:
    """Return curated customer-theme evidence without raw meeting notes."""
    try:
        validate_evidence_inputs(
            theme_key=theme_key,
            dimension=dimension,
            stage=stage,
            limit=limit,
            min_importance=min_importance,
        )
    except ValueError as exc:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=str(exc),
            hint={
                "valid_theme_keys": sorted(THEME_TAXONOMY),
                "valid_dimensions": sorted(VALID_DIMENSION_FILTERS),
                "valid_stages": sorted(VALID_STAGE_FILTERS),
            },
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

    result = build_customer_theme_evidence(
        deals,
        theme_key=theme_key,
        dimension=dimension,
        stage=stage,
        industry=industry,
        limit=limit,
        min_importance=min_importance,
    )
    return {"ok": True, **result}
