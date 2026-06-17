from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

WEEKLY_PIPELINE_COLLECTION = "dashboard_weekly_pipeline"
CUSTOMER_THEMES_COLLECTION = "dashboard_customer_themes"
PIPELINE_TREND_COLLECTION = "dashboard_pipeline_trend"

CHART_READY_COLLECTION_FILES = {
    WEEKLY_PIPELINE_COLLECTION: "dashboard_weekly_pipeline.v1.json",
    CUSTOMER_THEMES_COLLECTION: "dashboard_customer_themes.v1.json",
    PIPELINE_TREND_COLLECTION: "dashboard_pipeline_trend.v1.json",
}


def chart_ready_collections() -> tuple[str, ...]:
    """Return versioned chart-ready collection ids.

    These contracts are intentionally separate from `mongo_schema_collections()`.
    MDB-1 defines the target row shape only; MDB-2 will add the refresh/write
    path and decide when doctor/schema checks should require the collections.
    """

    return tuple(CHART_READY_COLLECTION_FILES)


def load_chart_ready_collection_spec(
    collection: str,
    *,
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Load a version-managed chart-ready collection contract."""

    if path is not None:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    file_name = _spec_filename(collection)
    resource = resources.files("deal_intel.resources").joinpath("mongo", file_name)
    return json.loads(resource.read_text(encoding="utf-8"))


def load_all_chart_ready_collection_specs() -> dict[str, dict[str, Any]]:
    """Load every chart-ready collection contract keyed by collection id."""

    return {
        collection: load_chart_ready_collection_spec(collection)
        for collection in chart_ready_collections()
    }


def chart_ready_collection_contract_summary(collection: str) -> dict[str, Any]:
    """Return a concise summary suitable for doctor/status output later."""

    spec = load_chart_ready_collection_spec(collection)
    return {
        "id": spec["id"],
        "version": spec["version"],
        "collection": spec["collection"],
        "dashboard_id": spec["dashboard_id"],
        "refresh_mode": spec["refresh_mode"],
        "source_collections": spec["source_collections"],
        "common_required_fields": spec["common_required_fields"],
        "row_types": sorted(spec["row_types"]),
    }


def _spec_filename(collection: str) -> str:
    try:
        return CHART_READY_COLLECTION_FILES[collection]
    except KeyError as exc:
        valid = ", ".join(chart_ready_collections())
        raise ValueError(
            f"unknown chart-ready collection {collection!r}; valid: {valid}"
        ) from exc
