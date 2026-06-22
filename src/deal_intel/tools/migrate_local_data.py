from __future__ import annotations

from copy import deepcopy
from typing import Any

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.storage.local_personal import LocalPersonalStore

MIGRATION_TYPE = "local_personal_to_mongo"


def handle(
    *,
    source_store: LocalPersonalStore,
    target_mongo: Any,
    dry_run: bool = True,
    overwrite: bool = False,
    confirmed_by_user: bool = False,
) -> dict:
    """Migrate user-created local personal records into a Mongo-backed store.

    Bundled zero-config fixture records are intentionally not part of this
    path. The source store only exposes records from storage.local_data_dir.
    """

    if not dry_run and not confirmed_by_user:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message="migrate_local_data requires confirmed_by_user=true when dry_run=false",
            hint="Run a dry-run first, then retry with confirmed_by_user=true.",
        )

    deals = source_store.load_deals()
    recruiting_records = source_store.load_recruiting_records()
    audit_logs = source_store.load_delete_audit_logs()
    source_recruiting_count = _count_recruiting_records(recruiting_records)

    if dry_run and not deals and not source_recruiting_count:
        counts = _count_rows([], [])
        warnings = _build_warnings(
            source_deals=0,
            source_recruiting_records=0,
            delete_audit_log_count=len(audit_logs),
            skipped_existing=0,
        )
        warnings.append(
            {
                "code": "target_not_checked_no_source_records",
                "message": (
                    "Target MongoDB readiness was not checked because there "
                    "are no local personal records to migrate."
                ),
            }
        )
        return {
            "ok": True,
            "migration_type": MIGRATION_TYPE,
            "dry_run": dry_run,
            "storage_written": False,
            "source": {
                "dataset": "local_personal",
                "data_dir": str(source_store.data_dir),
                "deals_path": str(source_store.deals_path),
                "recruiting_path": str(source_store.recruiting_path),
                "deal_count": 0,
                "recruiting_record_count": 0,
                "delete_audit_log_count": len(audit_logs),
            },
            "target": {
                "storage_backend": "mongo",
                "database": getattr(target_mongo, "database_name", None),
                "readiness": "not_checked_no_source_records",
            },
            "options": {
                "overwrite": overwrite,
            },
            "counts": counts,
            "deals": [],
            "recruiting": [],
            "warnings": warnings,
        }

    target_ping = _safe_ping(target_mongo)
    if target_ping.get("status") != "ok":
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message="Target MongoDB storage is not ready for migration.",
            hint=target_ping,
        )

    rows = [_build_deal_row(target_mongo, deal, overwrite=overwrite) for deal in deals]
    recruiting_rows = _build_recruiting_rows(
        target_mongo,
        recruiting_records,
        overwrite=overwrite,
    )
    counts = _count_rows(rows, recruiting_rows)
    warnings = _build_warnings(
        source_deals=len(deals),
        source_recruiting_records=source_recruiting_count,
        delete_audit_log_count=len(audit_logs),
        skipped_existing=counts["would_skip_existing"],
    )

    migrated = 0
    overwritten = 0
    if not dry_run:
        for row, deal in zip(rows, deals, strict=True):
            if row["action"] not in {"create", "overwrite"}:
                continue
            _safe_upsert_deal(target_mongo, deal)
            if row["action"] == "overwrite":
                overwritten += 1
            else:
                migrated += 1
        records_by_key = _recruiting_records_by_key(recruiting_records)
        for row in recruiting_rows:
            if row["action"] not in {"create", "overwrite"}:
                continue
            _safe_upsert_recruiting_record(
                target_mongo,
                row["collection"],
                records_by_key[(row["collection"], row["record_id"])],
            )
            if row["action"] == "overwrite":
                overwritten += 1
            else:
                migrated += 1

    counts.update(
        {
            "migrated": migrated,
            "overwritten": overwritten,
            "skipped_existing": counts["would_skip_existing"] if not dry_run else 0,
        }
    )

    return {
        "ok": True,
        "migration_type": MIGRATION_TYPE,
        "dry_run": dry_run,
        "storage_written": (not dry_run and (migrated + overwritten) > 0),
        "source": {
            "dataset": "local_personal",
            "data_dir": str(source_store.data_dir),
            "deals_path": str(source_store.deals_path),
            "recruiting_path": str(source_store.recruiting_path),
            "deal_count": len(deals),
            "recruiting_record_count": source_recruiting_count,
            "delete_audit_log_count": len(audit_logs),
        },
        "target": {
            "storage_backend": "mongo",
            "database": getattr(target_mongo, "database_name", None),
        },
        "options": {
            "overwrite": overwrite,
        },
        "counts": counts,
        "deals": rows,
        "recruiting": recruiting_rows,
        "warnings": warnings,
    }


def _safe_ping(target_mongo: Any) -> dict:
    try:
        ping = target_mongo.ping()
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=f"Target MongoDB ping failed: {type(exc).__name__}: {exc}",
            retryable=True,
        ) from exc
    return ping if isinstance(ping, dict) else {"status": "error", "message": str(ping)}


def _build_deal_row(target_mongo: Any, deal: dict, *, overwrite: bool) -> dict:
    deal_id = str(deal.get("deal_id") or "").strip()
    company = str(deal.get("company") or "").strip()
    existing = _safe_get_deal(target_mongo, deal_id)
    if existing and overwrite:
        action = "overwrite"
        reason = "target_deal_exists_overwrite_enabled"
    elif existing:
        action = "skip_existing"
        reason = "target_deal_exists"
    else:
        action = "create"
        reason = "target_deal_missing"
    return {
        "record_type": "deal",
        "deal_id": deal_id,
        "record_id": deal_id,
        "company": company,
        "deal_stage": deal.get("deal_stage"),
        "action": action,
        "reason": reason,
    }


def _build_recruiting_rows(
    target_mongo: Any,
    records_by_collection: dict[str, list[dict]],
    *,
    overwrite: bool,
) -> list[dict]:
    rows: list[dict] = []
    for collection, records in records_by_collection.items():
        for record in records:
            record_id = _recruiting_record_id(collection, record)
            existing = _safe_get_recruiting_record(target_mongo, collection, record_id)
            if existing and overwrite:
                action = "overwrite"
                reason = "target_recruiting_record_exists_overwrite_enabled"
            elif existing:
                action = "skip_existing"
                reason = "target_recruiting_record_exists"
            else:
                action = "create"
                reason = "target_recruiting_record_missing"
            rows.append(
                {
                    "record_type": "recruiting",
                    "collection": collection,
                    "record_id": record_id,
                    "action": action,
                    "reason": reason,
                }
            )
    return rows


def _safe_get_deal(target_mongo: Any, deal_id: str) -> dict | None:
    try:
        return target_mongo.get_deal(deal_id)
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=f"Target MongoDB read failed for deal_id={deal_id}: {exc}",
            retryable=True,
        ) from exc


def _safe_get_recruiting_record(
    target_mongo: Any,
    collection: str,
    record_id: str,
) -> dict | None:
    try:
        return target_mongo.get_recruiting_record(collection, record_id)
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=(
                "Target MongoDB read failed for recruiting "
                f"{collection}/{record_id}: {exc}"
            ),
            retryable=True,
        ) from exc


def _safe_upsert_deal(target_mongo: Any, deal: dict) -> None:
    deal_id = str(deal.get("deal_id") or "").strip()
    try:
        target_mongo.upsert_deal(deepcopy(deal))
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=f"Target MongoDB write failed for deal_id={deal_id}: {exc}",
            retryable=True,
        ) from exc


def _safe_upsert_recruiting_record(
    target_mongo: Any,
    collection: str,
    record: dict,
) -> None:
    record_id = _recruiting_record_id(collection, record)
    try:
        target_mongo.upsert_recruiting_record(collection, deepcopy(record))
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=(
                "Target MongoDB write failed for recruiting "
                f"{collection}/{record_id}: {exc}"
            ),
            retryable=True,
        ) from exc


def _count_rows(deal_rows: list[dict], recruiting_rows: list[dict]) -> dict:
    rows = [*deal_rows, *recruiting_rows]
    would_create = sum(1 for row in rows if row["action"] == "create")
    would_overwrite = sum(1 for row in rows if row["action"] == "overwrite")
    would_skip_existing = sum(1 for row in rows if row["action"] == "skip_existing")
    return {
        "source_deals": len(deal_rows),
        "source_recruiting_records": len(recruiting_rows),
        "source_records": len(rows),
        "would_create": would_create,
        "would_overwrite": would_overwrite,
        "would_skip_existing": would_skip_existing,
        "would_write": would_create + would_overwrite,
    }


def _build_warnings(
    *,
    source_deals: int,
    source_recruiting_records: int,
    delete_audit_log_count: int,
    skipped_existing: int,
) -> list[dict]:
    warnings: list[dict] = []
    if source_deals == 0 and source_recruiting_records == 0:
        warnings.append(
            {
                "code": "no_local_personal_records",
                "message": "No user-created local personal records were found.",
            }
        )
    if delete_audit_log_count:
        warnings.append(
            {
                "code": "delete_audit_logs_not_migrated",
                "message": (
                    "Local delete audit logs stay in local_data_dir and are not "
                    "migrated to MongoDB in this command."
                ),
            }
        )
    if skipped_existing:
        warnings.append(
            {
                "code": "existing_records_skipped",
                "message": (
                    "One or more target MongoDB records already exist and will be "
                    "skipped unless overwrite is enabled."
                ),
            }
        )
    return warnings


def _count_recruiting_records(records_by_collection: dict[str, list[dict]]) -> int:
    return sum(len(records) for records in records_by_collection.values())


def _recruiting_records_by_key(
    records_by_collection: dict[str, list[dict]],
) -> dict[tuple[str, str], dict]:
    return {
        (collection, _recruiting_record_id(collection, record)): record
        for collection, records in records_by_collection.items()
        for record in records
    }


def _recruiting_record_id(collection: str, record: dict) -> str:
    from deal_intel.storage.recruiting_collections import recruiting_id_field

    id_field = recruiting_id_field(collection)
    return str(record.get(id_field) or "").strip()
