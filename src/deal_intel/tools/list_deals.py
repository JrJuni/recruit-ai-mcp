from __future__ import annotations

from deal_intel.storage.mongodb import MongoDBClient


def handle(mongo: MongoDBClient, *, stage: str | None, limit: int) -> dict:
    try:
        deals = mongo.list_deals(stage=stage, limit=limit)
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
    except Exception as exc:
        return {"ok": False, "error_code": "STORAGE_ERROR", "message": str(exc)}
