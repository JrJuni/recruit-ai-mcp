from __future__ import annotations

import pytest

from deal_intel.storage.mongodb import MongoDBClient
from deal_intel.storage.recruiting_collections import (
    CANDIDATES,
    INTERACTIONS,
    RECOMMENDATION_RUNS,
    recruiting_id_field,
    recruiting_safe_projection,
)


class FakeReplaceResult:
    def __init__(self, *, upserted_id: str | None = None, matched_count: int = 0) -> None:
        self.upserted_id = upserted_id
        self.matched_count = matched_count


class FakeCursor:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def sort(self, sort_spec):
        for key, direction in reversed(sort_spec):
            self.rows.sort(key=lambda row: row.get(key) or "", reverse=direction < 0)
        return self

    def limit(self, limit: int):
        self.rows = self.rows[:limit]
        return self

    def __iter__(self):
        return iter(self.rows)


class FakeCollection:
    def __init__(self, id_field: str) -> None:
        self.id_field = id_field
        self.rows: dict[str, dict] = {}
        self.last_replace_filter: dict | None = None
        self.last_find_projection: dict | None = None

    def replace_one(self, query: dict, record: dict, *, upsert: bool):
        self.last_replace_filter = query
        key = str(query[self.id_field])
        existed = key in self.rows
        self.rows[key] = dict(record)
        return FakeReplaceResult(upserted_id=None if existed else key, matched_count=int(existed))

    def find_one(self, query: dict, projection: dict):
        self.last_find_projection = projection
        key = str(query[self.id_field])
        row = self.rows.get(key)
        return _apply_projection(row, projection) if row else None

    def find(self, query: dict, projection: dict):
        self.last_find_projection = projection
        rows = [
            _apply_projection(row, projection)
            for row in self.rows.values()
            if all(row.get(key) == value for key, value in query.items())
        ]
        return FakeCursor(rows)


class FakeRecruitingDB:
    def __init__(self) -> None:
        self.candidates = FakeCollection(recruiting_id_field(CANDIDATES))
        self.interactions = FakeCollection(recruiting_id_field(INTERACTIONS))
        self.recommendation_runs = FakeCollection(recruiting_id_field(RECOMMENDATION_RUNS))

    def __getitem__(self, name: str):
        return getattr(self, name)


def _client_with_fake_db() -> tuple[MongoDBClient, FakeRecruitingDB]:
    db = FakeRecruitingDB()
    client = MongoDBClient(uri="mongodb://example.invalid")
    client._db = db
    return client, db


def _apply_projection(row: dict | None, projection: dict) -> dict | None:
    if row is None:
        return None
    result = dict(row)
    for key, enabled in projection.items():
        if enabled == 0:
            result.pop(key, None)
    return result


def test_recruiting_safe_projection_excludes_interaction_raw_content_by_default() -> None:
    assert recruiting_safe_projection(INTERACTIONS) == {"_id": 0, "raw_content": 0}
    assert recruiting_safe_projection(INTERACTIONS, include_raw=True) == {"_id": 0}


def test_upsert_and_get_candidate_use_recruiting_collection_contract() -> None:
    client, db = _client_with_fake_db()

    created = client.upsert_candidate(
        {
            "_id": "internal",
            "candidate_id": "cand-1",
            "name": "Avery Chen",
            "updated_at": "2026-06-22T00:00:00+00:00",
        }
    )
    candidate = client.get_candidate("cand-1")

    assert created is True
    assert db.candidates.last_replace_filter == {"candidate_id": "cand-1"}
    assert db.candidates.last_find_projection == {"_id": 0}
    assert candidate == {
        "candidate_id": "cand-1",
        "name": "Avery Chen",
        "updated_at": "2026-06-22T00:00:00+00:00",
    }


def test_list_recruiting_records_applies_query_limit_sort_and_safe_projection() -> None:
    client, db = _client_with_fake_db()
    db.candidates.rows = {
        "cand-old": {
            "_id": "internal-old",
            "candidate_id": "cand-old",
            "name": "Old",
            "seniority": "staff",
            "updated_at": "2026-06-20",
        },
        "cand-new": {
            "_id": "internal-new",
            "candidate_id": "cand-new",
            "name": "New",
            "seniority": "staff",
            "updated_at": "2026-06-22",
        },
    }

    rows = client.list_candidates(query={"seniority": "staff"}, limit=1)

    assert rows == [
        {
            "candidate_id": "cand-new",
            "name": "New",
            "seniority": "staff",
            "updated_at": "2026-06-22",
        }
    ]


def test_recruiting_interaction_read_path_hides_raw_content_unless_requested() -> None:
    client, _db = _client_with_fake_db()
    client.append_recruiting_interaction(
        {
            "interaction_id": "int-1",
            "subject_type": "candidate",
            "subject_id": "cand-1",
            "interaction_type": "candidate_screen",
            "summary": "Strong Python background.",
            "raw_content": "Full private screen transcript.",
        }
    )

    safe = client.get_recruiting_record(INTERACTIONS, "int-1")
    raw = client.get_recruiting_record(INTERACTIONS, "int-1", include_raw=True)

    assert "raw_content" not in safe
    assert raw["raw_content"] == "Full private screen transcript."


def test_save_recommendation_run_uses_recommendation_run_id() -> None:
    client, db = _client_with_fake_db()

    saved = client.save_recommendation_run(
        {
            "recommendation_run_id": "run-1",
            "mode": "position_to_candidates",
            "anchor_type": "position",
            "anchor_id": "pos-1",
        }
    )

    assert saved is True
    assert db.recommendation_runs.last_replace_filter == {
        "recommendation_run_id": "run-1"
    }


def test_upsert_recruiting_record_requires_collection_id_field() -> None:
    client, _db = _client_with_fake_db()

    with pytest.raises(ValueError, match="candidate_id"):
        client.upsert_recruiting_record(CANDIDATES, {"name": "Missing ID"})
