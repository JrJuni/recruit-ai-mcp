from __future__ import annotations

from copy import deepcopy

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.storage.mongodb import MongoDBClient


def safe_deal_payload(deal: dict) -> dict:
    safe = deepcopy(deal)
    safe.pop("contacts", None)
    safe.pop("summary_embedding", None)
    for meeting in safe.get("meetings") or []:
        if isinstance(meeting, dict):
            meeting.pop("raw_notes", None)
    for interaction in safe.get("interactions") or []:
        if isinstance(interaction, dict):
            interaction.pop("raw_content", None)
    return safe


def raw_deal_payload(deal: dict) -> dict:
    raw = deepcopy(deal)
    raw.pop("summary_embedding", None)
    return raw


def handle(mongo: MongoDBClient, *, deal_id: str) -> dict:
    deal = mongo.get_deal(deal_id)
    if deal is None:
        raise MCPError(
            error_code=ErrorCode.NOT_FOUND,
            stage=Stage.STORAGE,
            message=f"deal_id {deal_id!r} not found",
            retryable=False,
        )
    result = {"ok": True, "deal": safe_deal_payload(deal)}
    if deal.get("archived") is True:
        result["warnings"] = ["deal_archived"]
        result["archive"] = {
            "archived_at": deal.get("archived_at"),
            "archived_reason": deal.get("archived_reason"),
        }
    return result
