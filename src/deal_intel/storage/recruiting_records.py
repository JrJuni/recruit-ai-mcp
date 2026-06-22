from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from deal_intel.storage.recruiting_collections import recruiting_id_field


def normalize_recruiting_record(
    collection: str,
    record: Mapping[str, Any] | BaseModel,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Convert a recruiting model or mapping into a Mongo-safe replacement doc."""

    payload = _json_safe(record)
    if not isinstance(payload, dict):
        raise TypeError("recruiting record must be a mapping or Pydantic model")

    payload.pop("_id", None)
    id_field = recruiting_id_field(collection)
    record_id = payload.get(id_field)
    if not record_id:
        raise ValueError(f"{collection} record must include {id_field}")

    timestamp = _timestamp(now)
    if not payload.get("created_at"):
        payload["created_at"] = timestamp
    payload["updated_at"] = timestamp
    return payload


def _timestamp(now: datetime | None) -> str:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC).isoformat(timespec="seconds")


def _json_safe(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {str(key): _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value
