from __future__ import annotations

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.storage.mongodb import MongoDBClient
from deal_intel.tools.get_deal import raw_deal_payload


def handle(
    mongo: MongoDBClient,
    *,
    deal_id: str,
    confirmed_by_user: bool = False,
    reason: str = "",
    include_raw_content: bool = False,
) -> dict:
    normalized_reason = str(reason or "").strip()
    if not confirmed_by_user:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message="get_deal_raw requires confirmed_by_user=true",
            retryable=False,
        )
    if not normalized_reason:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message="get_deal_raw requires a non-empty reason",
            retryable=False,
        )
    if not include_raw_content:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message="get_deal_raw requires include_raw_content=true",
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
    result = {
        "ok": True,
        "deal": raw_deal_payload(deal),
        "raw_access": {
            "confirmed_by_user": True,
            "reason": normalized_reason,
            "include_raw_content": True,
            "embeddings_excluded": True,
        },
    }
    if deal.get("archived") is True:
        result["warnings"] = ["deal_archived"]
        result["archive"] = {
            "archived_at": deal.get("archived_at"),
            "archived_reason": deal.get("archived_reason"),
        }
    return result
