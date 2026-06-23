from __future__ import annotations

import asyncio
import json
from copy import deepcopy

import pytest

from deal_intel import _context, mcp_server
from deal_intel.errors import ErrorCode, MCPError
from deal_intel.schema.recruiting import (
    CandidateProfile,
    ClientFeedback,
    Position,
    Submission,
)
from deal_intel.schema.recruiting_metrics import build_recruiting_pipeline_metrics
from deal_intel.storage.recruiting_collections import recruiting_id_field
from deal_intel.tool_surfaces import list_tool_surface_contracts
from deal_intel.tools import create_sample_data, delete_sample_data
from deal_intel.tools.sample_dataset import (
    DATASET_RECRUITING_PIPELINE,
    RECRUITING_SAMPLE_BATCH_ID,
    SAMPLE_BATCH_ID,
    build_sample_deals,
    build_sample_recruiting_records,
)


class FakeMongo:
    def __init__(self, *, database_name: str = "recruit_ai_demo") -> None:
        self.database_name = database_name
        self.deals: list[dict] = []
        self.recruiting: dict[str, dict[str, dict]] = {}
        self.upsert_calls = 0
        self.delete_calls = 0
        self.recruiting_upsert_calls = 0
        self.recruiting_delete_calls = 0

    def count_deals(self, query: dict) -> int:
        return len(_matching(self.deals, query))

    def upsert_deals(self, deals: list[dict]) -> int:
        self.upsert_calls += 1
        for deal in deepcopy(deals):
            self.deals = [item for item in self.deals if item["deal_id"] != deal["deal_id"]]
            self.deals.append(deal)
        return len(deals)

    def list_sample_deals(self, sample_batch_id: str) -> list[dict]:
        return [
            {
                "deal_id": deal["deal_id"],
                "company": deal["company"],
                "deal_stage": deal["deal_stage"],
            }
            for deal in self.deals
            if deal.get("is_sample") is True
            and deal.get("sample_batch_id") == sample_batch_id
        ]

    def delete_sample_deals(self, sample_batch_id: str) -> int:
        self.delete_calls += 1
        before = len(self.deals)
        self.deals = [
            deal
            for deal in self.deals
            if not (
                deal.get("is_sample") is True
                and deal.get("sample_batch_id") == sample_batch_id
            )
        ]
        return before - len(self.deals)

    def upsert_recruiting_record(self, collection: str, record: dict) -> bool:
        self.recruiting_upsert_calls += 1
        id_field = recruiting_id_field(collection)
        self.recruiting.setdefault(collection, {})[record[id_field]] = deepcopy(record)
        return True

    def upsert_recruiting_records(self, records_by_collection: dict[str, list[dict]]) -> int:
        count = 0
        for collection, rows in records_by_collection.items():
            for row in rows:
                self.upsert_recruiting_record(collection, row)
                count += 1
        return count

    def get_recruiting_record(self, collection: str, record_id: str) -> dict | None:
        row = self.recruiting.get(collection, {}).get(record_id)
        return deepcopy(row) if row is not None else None

    def count_recruiting_records_by_ids(self, ids_by_collection: dict[str, list[str]]) -> int:
        return sum(
            1
            for collection, ids in ids_by_collection.items()
            for record_id in ids
            if record_id in self.recruiting.get(collection, {})
        )

    def delete_recruiting_records_by_ids(self, ids_by_collection: dict[str, list[str]]) -> int:
        self.recruiting_delete_calls += 1
        deleted = 0
        for collection, ids in ids_by_collection.items():
            rows = self.recruiting.setdefault(collection, {})
            for record_id in ids:
                if record_id in rows:
                    del rows[record_id]
                    deleted += 1
        return deleted


def _cfg(**mongodb_overrides) -> dict:
    mongodb = {
        "database": "recruit_ai",
        "demo_database": "recruit_ai_demo",
    }
    mongodb.update(mongodb_overrides)
    return {"mongodb": mongodb}


def _matching(deals: list[dict], query: dict) -> list[dict]:
    return [
        deal
        for deal in deals
        if all(deal.get(key) == value for key, value in query.items())
    ]


def test_public_sample_dataset_excludes_sensitive_and_legacy_fields() -> None:
    deals = build_sample_deals(loaded_at="2026-06-15T00:00:00+00:00")
    serialized = json.dumps(deals, ensure_ascii=False).lower()

    assert len(deals) == 22
    assert all(deal["is_sample"] is True for deal in deals)
    assert {deal["sample_batch_id"] for deal in deals} == {SAMPLE_BATCH_ID}
    for forbidden in [
        "raw_notes",
        "raw_content",
        "summary_embedding",
        "contacts",
        "deal_size_krw",
        "deal_size_low_krw",
        "deal_size_high_krw",
        "deal_metadata_history",
        "mongodb+srv",
        "openai_api_key",
        "anthropic_api_key",
    ]:
        assert forbidden not in serialized


def test_recruiting_sample_dataset_is_model_safe_and_metric_ready() -> None:
    records = build_sample_recruiting_records(loaded_at="2026-06-22T00:00:00+00:00")
    serialized = json.dumps(records, ensure_ascii=False).lower()

    assert {collection: len(rows) for collection, rows in records.items()} == {
        "candidates": 13,
        "client_companies": 2,
        "positions": 3,
        "submissions": 4,
        "feedback": 4,
        "interactions": 7,
    }
    for row in records["candidates"]:
        CandidateProfile.model_validate(row)
    for row in records["positions"]:
        Position.model_validate(row)
    for row in records["submissions"]:
        Submission.model_validate(row)
    for row in records["feedback"]:
        ClientFeedback.model_validate(row)
    metrics = build_recruiting_pipeline_metrics(
        candidates=records["candidates"],
        positions=records["positions"],
        submissions=records["submissions"],
        feedback=records["feedback"],
    )

    assert metrics["summary"]["candidate_count"] == 13
    assert metrics["summary"]["open_position_count"] == 2
    assert metrics["summary"]["placed_count"] == 1
    for forbidden in [
        "mongodb+srv",
        "openai_api_key",
        "anthropic_api_key",
        "is_sample",
        "sample_batch_id",
    ]:
        assert forbidden not in serialized


def test_create_sample_data_dry_run_previews_without_writing() -> None:
    mongo = FakeMongo()

    result = create_sample_data.handle(
        mongo=mongo,
        cfg=_cfg(),
    )

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["storage_written"] is False
    assert result["primary_database"] == "recruit_ai"
    assert result["demo_database"] == "recruit_ai_demo"
    assert result["deal_count"] == 22
    assert len(result["preview"]) == 3
    assert mongo.upsert_calls == 0


def test_create_recruiting_sample_data_dry_run_previews_without_writing() -> None:
    mongo = FakeMongo()

    result = create_sample_data.handle(
        mongo=mongo,
        cfg=_cfg(),
        dataset=DATASET_RECRUITING_PIPELINE,
    )

    assert result["ok"] is True
    assert result["dataset"] == DATASET_RECRUITING_PIPELINE
    assert result["sample_batch_id"] == RECRUITING_SAMPLE_BATCH_ID
    assert result["dry_run"] is True
    assert result["storage_written"] is False
    assert result["record_count"] == 33
    assert result["record_counts"]["candidates"] == 13
    assert result["preview"]["positions"][0]["position_id"] == (
        "pos_northstar_backend_lead"
    )
    assert mongo.recruiting_upsert_calls == 0


def test_sample_data_rejects_primary_database_and_wrong_client() -> None:
    with pytest.raises(MCPError) as same_database:
        create_sample_data.handle(
            mongo=FakeMongo(database_name="recruit_ai"),
            cfg=_cfg(demo_database="recruit_ai"),
        )
    with pytest.raises(MCPError) as wrong_client:
        create_sample_data.handle(
            mongo=FakeMongo(database_name="recruit_ai"),
            cfg=_cfg(),
        )

    assert same_database.value.error_code == ErrorCode.INVALID_INPUT
    assert "different from the primary" in same_database.value.message
    assert wrong_client.value.error_code == ErrorCode.INVALID_INPUT
    assert wrong_client.value.hint["expected_demo_database"] == "recruit_ai_demo"


def test_create_sample_data_requires_confirmation_for_actual_write() -> None:
    mongo = FakeMongo()

    with pytest.raises(MCPError) as exc_info:
        create_sample_data.handle(
            mongo=mongo,
            cfg=_cfg(),
            dry_run=False,
        )

    assert exc_info.value.error_code == ErrorCode.INVALID_INPUT
    assert "confirmation" in exc_info.value.message
    assert mongo.upsert_calls == 0


def test_create_sample_data_writes_marked_demo_records() -> None:
    mongo = FakeMongo()

    result = create_sample_data.handle(
        mongo=mongo,
        cfg=_cfg(),
        dry_run=False,
        confirmed_by_user=True,
    )

    assert result["storage_written"] is True
    assert result["created_or_replaced_count"] == 22
    assert len(mongo.deals) == 22
    assert all(deal["is_sample"] is True for deal in mongo.deals)
    assert {deal["sample_batch_id"] for deal in mongo.deals} == {SAMPLE_BATCH_ID}
    assert mongo.delete_calls == 0


def test_create_recruiting_sample_data_writes_multi_collection_records() -> None:
    mongo = FakeMongo()

    result = create_sample_data.handle(
        mongo=mongo,
        cfg=_cfg(),
        dataset=DATASET_RECRUITING_PIPELINE,
        dry_run=False,
        confirmed_by_user=True,
    )

    assert result["storage_written"] is True
    assert result["created_or_replaced_count"] == 33
    assert len(mongo.recruiting["candidates"]) == 13
    assert len(mongo.recruiting["positions"]) == 3
    assert "cand_avery_chen" in mongo.recruiting["candidates"]
    assert "pos_northstar_backend_lead" in mongo.recruiting["positions"]
    assert mongo.recruiting_delete_calls == 0


def test_create_sample_data_blocks_existing_batch_without_overwrite() -> None:
    mongo = FakeMongo()
    create_sample_data.handle(
        mongo=mongo,
        cfg=_cfg(),
        dry_run=False,
        confirmed_by_user=True,
    )

    with pytest.raises(MCPError) as exc_info:
        create_sample_data.handle(
            mongo=mongo,
            cfg=_cfg(),
            dry_run=False,
            confirmed_by_user=True,
        )

    assert exc_info.value.error_code == ErrorCode.INVALID_INPUT
    assert exc_info.value.hint["fix"] == "Set overwrite=true to replace this sample batch."


def test_create_recruiting_sample_data_overwrite_replaces_known_ids() -> None:
    mongo = FakeMongo()
    create_sample_data.handle(
        mongo=mongo,
        cfg=_cfg(),
        dataset=DATASET_RECRUITING_PIPELINE,
        dry_run=False,
        confirmed_by_user=True,
    )

    with pytest.raises(MCPError) as exc_info:
        create_sample_data.handle(
            mongo=mongo,
            cfg=_cfg(),
            dataset=DATASET_RECRUITING_PIPELINE,
            dry_run=False,
            confirmed_by_user=True,
        )
    result = create_sample_data.handle(
        mongo=mongo,
        cfg=_cfg(),
        dataset=DATASET_RECRUITING_PIPELINE,
        dry_run=False,
        overwrite=True,
        confirmed_by_user=True,
    )

    assert exc_info.value.error_code == ErrorCode.INVALID_INPUT
    assert result["deleted_existing_count"] == 33
    assert result["created_or_replaced_count"] == 33
    assert result["record_counts"]["feedback"] == 4
    assert mongo.recruiting_delete_calls == 1


def test_create_sample_data_overwrite_replaces_existing_batch() -> None:
    mongo = FakeMongo()
    create_sample_data.handle(
        mongo=mongo,
        cfg=_cfg(),
        dry_run=False,
        confirmed_by_user=True,
    )

    result = create_sample_data.handle(
        mongo=mongo,
        cfg=_cfg(),
        dry_run=False,
        overwrite=True,
        confirmed_by_user=True,
    )

    assert result["deleted_existing_count"] == 22
    assert result["created_or_replaced_count"] == 22
    assert len(mongo.deals) == 22
    assert mongo.delete_calls == 1


def test_delete_sample_data_dry_run_and_actual_delete() -> None:
    mongo = FakeMongo()
    create_sample_data.handle(
        mongo=mongo,
        cfg=_cfg(),
        dry_run=False,
        confirmed_by_user=True,
    )

    dry_run = delete_sample_data.handle(mongo=mongo, cfg=_cfg())
    assert dry_run["dry_run"] is True
    assert dry_run["would_delete_count"] == 22
    assert dry_run["storage_written"] is False
    assert len(mongo.deals) == 22

    with pytest.raises(MCPError) as missing_confirmation:
        delete_sample_data.handle(mongo=mongo, cfg=_cfg(), dry_run=False)

    actual = delete_sample_data.handle(
        mongo=mongo,
        cfg=_cfg(),
        dry_run=False,
        confirmed_by_user=True,
    )

    assert missing_confirmation.value.error_code == ErrorCode.INVALID_INPUT
    assert actual["deleted_count"] == 22
    assert actual["storage_written"] is True
    assert mongo.deals == []


def test_delete_recruiting_sample_data_dry_run_and_actual_delete() -> None:
    mongo = FakeMongo()
    create_sample_data.handle(
        mongo=mongo,
        cfg=_cfg(),
        dataset=DATASET_RECRUITING_PIPELINE,
        dry_run=False,
        confirmed_by_user=True,
    )

    dry_run = delete_sample_data.handle(
        mongo=mongo,
        cfg=_cfg(),
        dataset=DATASET_RECRUITING_PIPELINE,
    )
    assert dry_run["dry_run"] is True
    assert dry_run["would_delete_count"] == 33
    assert dry_run["storage_written"] is False

    with pytest.raises(MCPError) as missing_confirmation:
        delete_sample_data.handle(
            mongo=mongo,
            cfg=_cfg(),
            dataset=DATASET_RECRUITING_PIPELINE,
            dry_run=False,
        )

    actual = delete_sample_data.handle(
        mongo=mongo,
        cfg=_cfg(),
        dataset=DATASET_RECRUITING_PIPELINE,
        dry_run=False,
        confirmed_by_user=True,
    )

    assert missing_confirmation.value.error_code == ErrorCode.INVALID_INPUT
    assert actual["deleted_count"] == 33
    assert actual["storage_written"] is True
    assert all(not rows for rows in mongo.recruiting.values())


def test_mcp_sample_data_wrappers_use_demo_database(monkeypatch) -> None:
    created_clients: list[FakeMongo] = []

    class FakeMongoFactory(FakeMongo):
        def __init__(self, *, database: str) -> None:
            super().__init__(database_name=database)
            created_clients.append(self)

    import deal_intel.storage.mongodb as mongodb_module

    monkeypatch.setattr(
        _context,
        "config",
        lambda: {**_cfg(), "tools": {"surface": "developer"}},
    )
    monkeypatch.setattr(mongodb_module, "MongoDBClient", FakeMongoFactory)

    result = mcp_server.create_sample_data()
    tools = asyncio.run(mcp_server.app.list_tools())
    names = sorted(tool.name for tool in tools)

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert created_clients[0].database_name == "recruit_ai_demo"
    assert len(names) == len(list_tool_surface_contracts())
    assert {"create_sample_data", "delete_sample_data"}.issubset(names)
