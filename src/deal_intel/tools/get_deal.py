from __future__ import annotations

from deal_intel.storage.mongodb import MongoDBClient


def handle(mongo: MongoDBClient, *, deal_id: str) -> dict:
    deal = mongo.get_deal(deal_id)
    if deal is None:
        return {"ok": False, "error_code": "NOT_FOUND", "message": f"deal_id {deal_id!r} not found"}
    return {"ok": True, "deal": deal}
