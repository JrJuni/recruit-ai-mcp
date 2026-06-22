from __future__ import annotations

import re
from dataclasses import dataclass

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.storage.mongodb import MongoDBClient
from deal_intel.tools.sample_dataset import (
    DATASET_RECRUITING_PIPELINE,
    DATASET_WEEKLY_PIPELINE,
    SUPPORTED_DATASETS,
    recruiting_sample_ids,
    sample_batch_id,
)

_DATABASE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_RESERVED_DATABASES = frozenset({"admin", "config", "local"})


@dataclass(frozen=True)
class DemoDatabaseSelection:
    primary_database: str
    demo_database: str


def resolve_demo_database(
    cfg: dict,
    *,
    demo_database: str | None = None,
) -> DemoDatabaseSelection:
    mongodb_cfg = cfg.get("mongodb", {})
    primary = str(mongodb_cfg.get("database") or "recruit_ai").strip()
    demo = str(
        demo_database
        or mongodb_cfg.get("demo_database")
        or "recruit_ai_demo"
    ).strip()
    _validate_database_name(primary, field_name="mongodb.database")
    _validate_database_name(demo, field_name="demo_database")
    if demo == primary:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message="demo_database must be different from the primary database",
            hint={
                "primary_database": primary,
                "recommended_demo_database": f"{primary}_demo",
            },
            retryable=False,
        )
    return DemoDatabaseSelection(primary_database=primary, demo_database=demo)


def validate_dataset(dataset: str) -> str:
    cleaned = (dataset or "").strip() or DATASET_WEEKLY_PIPELINE
    if cleaned not in SUPPORTED_DATASETS:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=f"dataset {cleaned!r} is not supported",
            hint={"supported_datasets": sorted(SUPPORTED_DATASETS)},
            retryable=False,
        )
    return cleaned


def require_confirmation(*, confirmed_by_user: bool, action: str) -> None:
    if not confirmed_by_user:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=f"{action} requires explicit user confirmation",
            hint={"required": "confirmed_by_user=true"},
            retryable=False,
        )


def sample_query(dataset: str = DATASET_WEEKLY_PIPELINE) -> dict:
    return {"is_sample": True, "sample_batch_id": sample_batch_id(dataset)}


def is_recruiting_sample_dataset(dataset: str) -> bool:
    return dataset == DATASET_RECRUITING_PIPELINE


def recruiting_sample_record_ids(records: dict[str, list[dict]]) -> dict[str, list[str]]:
    return recruiting_sample_ids(records)


def count_recruiting_sample_records(
    mongo: MongoDBClient,
    records: dict[str, list[dict]],
) -> int:
    ids_by_collection = recruiting_sample_record_ids(records)
    if hasattr(mongo, "count_recruiting_records_by_ids"):
        return int(mongo.count_recruiting_records_by_ids(ids_by_collection))
    return sum(
        1
        for collection, ids in ids_by_collection.items()
        for record_id in ids
        if mongo.get_recruiting_record(collection, record_id) is not None
    )


def upsert_recruiting_sample_records(
    mongo: MongoDBClient,
    records: dict[str, list[dict]],
) -> int:
    if hasattr(mongo, "upsert_recruiting_records"):
        return int(mongo.upsert_recruiting_records(records))
    count = 0
    for collection, rows in records.items():
        for row in rows:
            mongo.upsert_recruiting_record(collection, row)
            count += 1
    return count


def delete_recruiting_sample_records(
    mongo: MongoDBClient,
    records: dict[str, list[dict]],
) -> int:
    ids_by_collection = recruiting_sample_record_ids(records)
    if hasattr(mongo, "delete_recruiting_records_by_ids"):
        return int(mongo.delete_recruiting_records_by_ids(ids_by_collection))
    deleted = 0
    for collection, ids in ids_by_collection.items():
        for record_id in ids:
            if mongo.delete_recruiting_record(collection, record_id):
                deleted += 1
    return deleted


def validate_demo_client(
    mongo: MongoDBClient,
    selection: DemoDatabaseSelection,
) -> None:
    actual = getattr(mongo, "database_name", None)
    if actual != selection.demo_database:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message="sample data tools must use the resolved demo database client",
            hint={
                "expected_demo_database": selection.demo_database,
                "actual_database": actual,
            },
            retryable=False,
        )


def _validate_database_name(value: str, *, field_name: str) -> None:
    if not value or not _DATABASE_RE.fullmatch(value):
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=f"{field_name} must be 1-64 chars: letters, numbers, _ or -",
            retryable=False,
        )
    if value in _RESERVED_DATABASES:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=f"{field_name} uses a reserved MongoDB database name",
            hint={"reserved": sorted(_RESERVED_DATABASES)},
            retryable=False,
        )
