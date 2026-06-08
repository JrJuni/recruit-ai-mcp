from __future__ import annotations

import os
from typing import Any


class MongoDBClient:
    """MongoDB Atlas client. pymongo is imported lazily (cold-start guard)."""

    def __init__(self, *, uri: str | None = None, database: str = "deal_intel") -> None:
        self._uri = uri or os.environ.get("MONGODB_URI")
        self._database_name = database
        self._client: Any = None
        self._db: Any = None

    def _get_db(self) -> Any:
        if self._db is None:
            if not self._uri:
                raise RuntimeError(
                    "MONGODB_URI not set. "
                    "Add MONGODB_URI=mongodb+srv://... to .env (see .env.example)."
                )
            from pymongo import MongoClient
            self._client = MongoClient(self._uri)
            self._db = self._client[self._database_name]
        return self._db

    def ping(self) -> dict:
        if not self._uri:
            return {
                "status": "missing_uri",
                "fix": "Set MONGODB_URI in .env (see .env.example)",
            }
        try:
            db = self._get_db()
            db.command("ping")
            return {"status": "ok", "database": self._database_name}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    # --- deals collection ---

    def upsert_deal(self, deal: dict) -> None:
        db = self._get_db()
        db.deals.replace_one({"deal_id": deal["deal_id"]}, deal, upsert=True)

    def get_deal(self, deal_id: str) -> dict | None:
        db = self._get_db()
        return db.deals.find_one({"deal_id": deal_id}, {"_id": 0})

    def list_deals(self, *, stage: str | None = None, limit: int = 50) -> list[dict]:
        db = self._get_db()
        query: dict = {}
        if stage:
            query["deal_stage"] = stage
        cursor = db.deals.find(query, {"_id": 0, "meetings.raw_notes": 0}).sort(
            "updated_at", -1
        ).limit(limit)
        return list(cursor)
