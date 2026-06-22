from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from deal_intel.storage.local_sample_fixture import SENSITIVE_FIELD_NAMES
from deal_intel.storage.recruiting_collections import recruiting_collections, recruiting_id_field

DEFAULT_LOCAL_DATA_DIR = "~/.recruit-ai/local-data"
LOCAL_PERSONAL_DATASET = "local_personal"
LOCAL_PERSONAL_SCHEMA_VERSION = 1
LOCAL_PERSONAL_DEALS_FILE = "deals.json"
LOCAL_PERSONAL_RECRUITING_FILE = "recruiting.json"
LOCAL_PERSONAL_DELETE_AUDIT_FILE = "delete_audit_logs.json"
LOCAL_PERSONAL_EXPORT_DIR = "exports"


def resolve_local_data_dir(value: str | Path | None = None) -> Path:
    raw = str(value).strip() if value is not None else ""
    if not raw:
        raw = DEFAULT_LOCAL_DATA_DIR
    return Path(os.path.expandvars(raw)).expanduser()


class LocalPersonalStore:
    """Read/write helper for user-created local sample data.

    Bundled fixture data stays immutable. This store only reads records that a
    user created under storage.local_data_dir.
    """

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = resolve_local_data_dir(data_dir)

    @property
    def deals_path(self) -> Path:
        return self.data_dir / LOCAL_PERSONAL_DEALS_FILE

    @property
    def recruiting_path(self) -> Path:
        return self.data_dir / LOCAL_PERSONAL_RECRUITING_FILE

    @property
    def delete_audit_logs_path(self) -> Path:
        return self.data_dir / LOCAL_PERSONAL_DELETE_AUDIT_FILE

    def load_deals(self) -> list[dict]:
        if not self.deals_path.exists():
            return []
        try:
            payload = json.loads(self.deals_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid local personal deals JSON: {exc}") from exc
        deals = _extract_deals(payload)
        return [_strip_sensitive_fields(deal) for deal in deals]

    def save_deals(self, deals: list[dict]) -> None:
        safe_deals = [
            _strip_sensitive_fields(deal)
            for deal in _extract_deals({"deals": deals})
        ]
        payload = {
            "schema_version": LOCAL_PERSONAL_SCHEMA_VERSION,
            "dataset": LOCAL_PERSONAL_DATASET,
            "deals": safe_deals,
        }
        self.data_dir.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(self.deals_path, payload)

    def load_recruiting_records(self) -> dict[str, list[dict]]:
        if not self.recruiting_path.exists():
            return _empty_recruiting_payload()
        try:
            payload = json.loads(self.recruiting_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid local recruiting JSON: {exc}") from exc
        return _extract_recruiting_records(payload)

    def save_recruiting_records(self, records_by_collection: dict[str, list[dict]]) -> None:
        records = _extract_recruiting_records(records_by_collection)
        payload = {
            "schema_version": LOCAL_PERSONAL_SCHEMA_VERSION,
            "dataset": LOCAL_PERSONAL_DATASET,
            "records": records,
        }
        self.data_dir.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(self.recruiting_path, payload)

    def upsert_recruiting_record(self, collection: str, record: dict) -> bool:
        id_field = recruiting_id_field(collection)
        record_id = str(record.get(id_field) or "").strip()
        if not record_id:
            raise ValueError(f"local recruiting {collection} record must include {id_field}")
        records = self.load_recruiting_records()
        row = _strip_sensitive_fields(deepcopy(record))
        row.pop("raw_content", None)
        rows = records[collection]
        for index, existing in enumerate(rows):
            if str(existing.get(id_field) or "").strip() == record_id:
                rows[index] = row
                self.save_recruiting_records(records)
                return True
        rows.append(row)
        self.save_recruiting_records(records)
        return True

    def upsert_recruiting_records(self, records_by_collection: dict[str, list[dict]]) -> int:
        count = 0
        for collection, rows in _extract_recruiting_records(records_by_collection).items():
            for row in rows:
                self.upsert_recruiting_record(collection, row)
                count += 1
        return count

    def get_recruiting_record(self, collection: str, record_id: str) -> dict | None:
        id_field = recruiting_id_field(collection)
        for row in self.load_recruiting_records()[collection]:
            if str(row.get(id_field) or "").strip() == str(record_id or "").strip():
                return deepcopy(row)
        return None

    def list_recruiting_records(
        self,
        collection: str,
        *,
        query: dict[str, Any] | None = None,
        limit: int = 50,
    ) -> list[dict]:
        recruiting_id_field(collection)
        rows = [
            deepcopy(row)
            for row in self.load_recruiting_records()[collection]
            if _matches_query(row, query or {})
        ]
        rows.sort(key=_local_recruiting_sort_key, reverse=True)
        if limit > 0:
            rows = rows[:limit]
        return rows

    def count_recruiting_records_by_ids(self, ids_by_collection: dict[str, list[str]]) -> int:
        records = self.load_recruiting_records()
        count = 0
        for collection, ids in ids_by_collection.items():
            id_field = recruiting_id_field(collection)
            wanted = {str(item) for item in ids}
            count += sum(
                1
                for row in records[collection]
                if str(row.get(id_field) or "") in wanted
            )
        return count

    def delete_recruiting_record(self, collection: str, record_id: str) -> bool:
        return bool(self.delete_recruiting_records_by_ids({collection: [record_id]}))

    def delete_recruiting_records_by_ids(self, ids_by_collection: dict[str, list[str]]) -> int:
        records = self.load_recruiting_records()
        deleted_count = 0
        for collection, ids in ids_by_collection.items():
            id_field = recruiting_id_field(collection)
            wanted = {str(item) for item in ids}
            original = records[collection]
            kept = [
                row
                for row in original
                if str(row.get(id_field) or "") not in wanted
            ]
            deleted_count += len(original) - len(kept)
            records[collection] = kept
        if deleted_count:
            self.save_recruiting_records(records)
        return deleted_count

    def upsert_deal(self, deal: dict) -> None:
        deal_id = str(deal.get("deal_id") or "").strip()
        if not deal_id:
            raise ValueError("local personal deal must include deal_id")
        deals = self.load_deals()
        safe_deal = _strip_sensitive_fields(deepcopy(deal))
        for index, existing in enumerate(deals):
            if existing.get("deal_id") == deal_id:
                deals[index] = safe_deal
                self.save_deals(deals)
                return
        deals.append(safe_deal)
        self.save_deals(deals)

    def update_deal_fields(self, deal_id: str, fields: dict[str, Any]) -> bool:
        cleaned_deal_id = str(deal_id or "").strip()
        if not cleaned_deal_id:
            raise ValueError("deal_id is required for local personal update")
        deals = self.load_deals()
        for index, deal in enumerate(deals):
            if str(deal.get("deal_id") or "").strip() != cleaned_deal_id:
                continue
            updated = deepcopy(deal)
            for key, value in fields.items():
                updated[key] = deepcopy(value)
            deals[index] = updated
            self.save_deals(deals)
            return True
        return False

    def update_deal_interactions_and_snapshots(
        self,
        deal_id: str,
        *,
        interactions: list[dict],
        meddpicc_latest: dict,
        qualification_latest: dict,
        updated_at: str,
    ) -> bool:
        return self.update_deal_fields(
            deal_id,
            {
                "interactions": deepcopy(interactions),
                "meddpicc_latest": deepcopy(meddpicc_latest),
                "qualification_latest": deepcopy(qualification_latest),
                "updated_at": updated_at,
            },
        )

    def load_delete_audit_logs(self) -> list[dict]:
        if not self.delete_audit_logs_path.exists():
            return []
        try:
            payload = json.loads(
                self.delete_audit_logs_path.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid local delete audit log JSON: {exc}") from exc
        return _extract_audit_logs(payload)

    def insert_delete_audit_log(self, entry: dict) -> None:
        logs = self.load_delete_audit_logs()
        logs.append(_strip_sensitive_fields(deepcopy(entry)))
        self._save_delete_audit_logs(logs)

    def hard_delete_deal(self, deal_id: str) -> int:
        cleaned_deal_id = str(deal_id or "").strip()
        if not cleaned_deal_id:
            raise ValueError("deal_id is required for local hard delete")
        deals = self.load_deals()
        kept = [
            deal
            for deal in deals
            if str(deal.get("deal_id") or "").strip() != cleaned_deal_id
        ]
        deleted_count = len(deals) - len(kept)
        if deleted_count:
            self.save_deals(kept)
        return deleted_count

    def build_export_payload(self, *, generated_at: datetime | None = None) -> dict:
        now = generated_at or datetime.now(UTC)
        deals = self.load_deals()
        audit_logs = self.load_delete_audit_logs()
        return {
            "schema_version": LOCAL_PERSONAL_SCHEMA_VERSION,
            "dataset": LOCAL_PERSONAL_DATASET,
            "export_type": "local_personal_snapshot",
            "generated_at": now.astimezone(UTC).isoformat(),
            "data_dir": str(self.data_dir),
            "files": {
                "deals": str(self.deals_path),
                "recruiting": str(self.recruiting_path),
                "delete_audit_logs": str(self.delete_audit_logs_path),
            },
            "counts": {
                "deals": len(deals),
                "recruiting_records": sum(
                    len(rows) for rows in self.load_recruiting_records().values()
                ),
                "delete_audit_logs": len(audit_logs),
            },
            "deals": deals,
            "recruiting": self.load_recruiting_records(),
            "delete_audit_logs": audit_logs,
        }

    def export_data(
        self,
        *,
        output_path: str | Path | None = None,
        generated_at: datetime | None = None,
    ) -> dict:
        payload = self.build_export_payload(generated_at=generated_at)
        target = (
            Path(os.path.expandvars(str(output_path))).expanduser()
            if output_path is not None
            else self._default_export_path(generated_at=generated_at)
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(target, payload)
        return {
            "ok": True,
            "export_path": str(target),
            "data_dir": str(self.data_dir),
            "deal_count": payload["counts"]["deals"],
            "recruiting_record_count": payload["counts"]["recruiting_records"],
            "delete_audit_log_count": payload["counts"]["delete_audit_logs"],
        }

    def reset_deals(self, *, force: bool = False) -> dict:
        deals = self.load_deals()
        recruiting = self.load_recruiting_records()
        audit_logs = self.load_delete_audit_logs()
        payload = {
            "ok": True,
            "dry_run": not force,
            "data_dir": str(self.data_dir),
            "deals_path": str(self.deals_path),
            "recruiting_path": str(self.recruiting_path),
            "delete_audit_logs_path": str(self.delete_audit_logs_path),
            "would_delete_deal_count": len(deals),
            "would_delete_recruiting_record_count": sum(
                len(rows) for rows in recruiting.values()
            ),
            "preserved_delete_audit_log_count": len(audit_logs),
            "storage_written": False,
        }
        if not force:
            return payload
        self.save_deals([])
        self.save_recruiting_records(_empty_recruiting_payload())
        payload.update(
            {
                "deleted_deal_count": len(deals),
                "deleted_recruiting_record_count": sum(
                    len(rows) for rows in recruiting.values()
                ),
                "storage_written": True,
            }
        )
        return payload

    def summary(self) -> dict:
        deals = self.load_deals()
        return {
            "dataset": LOCAL_PERSONAL_DATASET,
            "schema_version": LOCAL_PERSONAL_SCHEMA_VERSION,
            "data_dir": str(self.data_dir),
            "deals_path": str(self.deals_path),
            "recruiting_path": str(self.recruiting_path),
            "delete_audit_logs_path": str(self.delete_audit_logs_path),
            "deal_count": len(deals),
            "recruiting_record_count": sum(
                len(rows) for rows in self.load_recruiting_records().values()
            ),
            "delete_audit_log_count": len(self.load_delete_audit_logs()),
        }

    def _save_delete_audit_logs(self, logs: list[dict]) -> None:
        payload = {
            "schema_version": LOCAL_PERSONAL_SCHEMA_VERSION,
            "dataset": LOCAL_PERSONAL_DATASET,
            "logs": [_strip_sensitive_fields(log) for log in _extract_audit_logs(logs)],
        }
        self.data_dir.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(self.delete_audit_logs_path, payload)

    def _default_export_path(self, *, generated_at: datetime | None = None) -> Path:
        now = generated_at or datetime.now(UTC)
        stamp = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        return self.data_dir / LOCAL_PERSONAL_EXPORT_DIR / f"local-data-{stamp}.json"


def _extract_deals(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        raw_deals = payload
    elif isinstance(payload, dict):
        raw_deals = payload.get("deals", [])
    else:
        raise ValueError("local personal deals file must be a list or mapping")
    if not isinstance(raw_deals, list):
        raise ValueError("local personal deals payload field 'deals' must be a list")

    deals: list[dict] = []
    seen: set[str] = set()
    for item in raw_deals:
        if not isinstance(item, dict):
            raise ValueError("local personal deal entries must be mappings")
        deal_id = str(item.get("deal_id") or "").strip()
        if not deal_id:
            raise ValueError("local personal deal entries must include deal_id")
        if deal_id in seen:
            raise ValueError(f"duplicate local personal deal_id: {deal_id}")
        seen.add(deal_id)
        deals.append(deepcopy(item))
    return deals


def _extract_audit_logs(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        raw_logs = payload
    elif isinstance(payload, dict):
        raw_logs = payload.get("logs", [])
    else:
        raise ValueError("local delete audit log file must be a list or mapping")
    if not isinstance(raw_logs, list):
        raise ValueError("local delete audit log payload field 'logs' must be a list")
    logs: list[dict] = []
    for item in raw_logs:
        if not isinstance(item, dict):
            raise ValueError("local delete audit log entries must be mappings")
        logs.append(deepcopy(item))
    return logs


def _empty_recruiting_payload() -> dict[str, list[dict]]:
    return {collection: [] for collection in recruiting_collections()}


def _extract_recruiting_records(payload: Any) -> dict[str, list[dict]]:
    raw_records = payload.get("records", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_records, dict):
        raise ValueError("local recruiting file must be a mapping")
    records = _empty_recruiting_payload()
    for collection, rows in raw_records.items():
        id_field = recruiting_id_field(collection)
        if not isinstance(rows, list):
            raise ValueError(f"local recruiting {collection} payload must be a list")
        seen: set[str] = set()
        cleaned_rows = []
        for item in rows:
            if not isinstance(item, dict):
                raise ValueError(f"local recruiting {collection} entries must be mappings")
            record_id = str(item.get(id_field) or "").strip()
            if not record_id:
                raise ValueError(
                    f"local recruiting {collection} entries must include {id_field}"
                )
            if record_id in seen:
                raise ValueError(f"duplicate local recruiting {id_field}: {record_id}")
            seen.add(record_id)
            row = _strip_sensitive_fields(deepcopy(item))
            row.pop("raw_content", None)
            cleaned_rows.append(row)
        records[collection] = cleaned_rows
    return records


def _matches_query(row: dict, query: dict[str, Any]) -> bool:
    for key, expected in query.items():
        if row.get(key) != expected:
            return False
    return True


def _local_recruiting_sort_key(row: dict) -> tuple[str, str, str]:
    return (
        str(row.get("updated_at") or row.get("created_at") or ""),
        str(row.get("occurred_at") or ""),
        json.dumps(row, sort_keys=True, default=str),
    )


def _write_json_atomic(path: Path, payload: dict) -> None:
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temp_path.replace(path)


def _strip_sensitive_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_sensitive_fields(item)
            for key, item in value.items()
            if key not in SENSITIVE_FIELD_NAMES
        }
    if isinstance(value, list):
        return [_strip_sensitive_fields(item) for item in value]
    return value
