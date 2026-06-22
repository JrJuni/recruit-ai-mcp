from __future__ import annotations

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.storage.mongodb import MongoDBClient
from deal_intel.tools.sample_data import (
    count_recruiting_sample_records,
    delete_recruiting_sample_records,
    is_recruiting_sample_dataset,
    require_confirmation,
    resolve_demo_database,
    sample_query,
    validate_dataset,
    validate_demo_client,
)
from deal_intel.tools.sample_dataset import (
    build_sample_recruiting_records,
    recruiting_record_counts,
    recruiting_sample_preview,
    sample_batch_id,
)


def handle(
    mongo: MongoDBClient,
    cfg: dict,
    *,
    dataset: str = "weekly_pipeline_demo",
    demo_database: str | None = None,
    confirmed_by_user: bool = False,
    dry_run: bool = True,
) -> dict:
    dataset = validate_dataset(dataset)
    selection = resolve_demo_database(cfg, demo_database=demo_database)
    validate_demo_client(mongo, selection)
    sample_batch = sample_batch_id(dataset)
    if is_recruiting_sample_dataset(dataset):
        return _handle_delete_recruiting_sample_data(
            mongo=mongo,
            selection=selection,
            dataset=dataset,
            sample_batch=sample_batch,
            dry_run=dry_run,
            confirmed_by_user=confirmed_by_user,
        )

    try:
        existing_count = mongo.count_deals(sample_query(dataset))
        sample_deals = mongo.list_sample_deals(sample_batch)
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=str(exc),
            retryable=True,
        ) from exc

    base = {
        "ok": True,
        "dataset": dataset,
        "sample_batch_id": sample_batch,
        "primary_database": selection.primary_database,
        "demo_database": selection.demo_database,
        "dry_run": dry_run,
        "existing_count": existing_count,
        "sample_deals": sample_deals[:10],
    }
    if dry_run:
        return {
            **base,
            "would_delete_count": existing_count,
            "storage_written": False,
        }

    require_confirmation(
        confirmed_by_user=confirmed_by_user,
        action="delete_sample_data",
    )
    try:
        deleted_count = mongo.delete_sample_deals(sample_batch)
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=str(exc),
            retryable=True,
        ) from exc

    return {
        **base,
        "dry_run": False,
        "deleted_count": deleted_count,
        "storage_written": deleted_count > 0,
    }


def _handle_delete_recruiting_sample_data(
    *,
    mongo: MongoDBClient,
    selection,
    dataset: str,
    sample_batch: str,
    dry_run: bool,
    confirmed_by_user: bool,
) -> dict:
    records = build_sample_recruiting_records(loaded_at="")
    try:
        existing_count = count_recruiting_sample_records(mongo, records)
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=str(exc),
            retryable=True,
        ) from exc

    base = {
        "ok": True,
        "dataset": dataset,
        "sample_batch_id": sample_batch,
        "primary_database": selection.primary_database,
        "demo_database": selection.demo_database,
        "dry_run": dry_run,
        "existing_count": existing_count,
        "record_count": sum(recruiting_record_counts(records).values()),
        "record_counts": recruiting_record_counts(records),
        "sample_records": recruiting_sample_preview(records),
    }
    if dry_run:
        return {
            **base,
            "would_delete_count": existing_count,
            "storage_written": False,
        }

    require_confirmation(
        confirmed_by_user=confirmed_by_user,
        action="delete_sample_data",
    )
    try:
        deleted_count = delete_recruiting_sample_records(mongo, records)
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=str(exc),
            retryable=True,
        ) from exc

    return {
        **base,
        "dry_run": False,
        "deleted_count": deleted_count,
        "storage_written": deleted_count > 0,
    }
