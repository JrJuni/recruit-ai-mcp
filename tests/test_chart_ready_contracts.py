from __future__ import annotations

import json

import pytest

from deal_intel.chart_ready_contracts import (
    CUSTOMER_THEMES_COLLECTION,
    PIPELINE_TREND_COLLECTION,
    WEEKLY_PIPELINE_COLLECTION,
    chart_ready_collection_contract_summary,
    chart_ready_collections,
    load_all_chart_ready_collection_specs,
    load_chart_ready_collection_spec,
)

SENSITIVE_TOKENS = (
    "raw_notes",
    "raw_content",
    "contacts",
    "summary_embedding",
    "product_context_raw",
    "embedding",
)


def test_chart_ready_collection_catalog_is_stable() -> None:
    assert chart_ready_collections() == (
        WEEKLY_PIPELINE_COLLECTION,
        CUSTOMER_THEMES_COLLECTION,
        PIPELINE_TREND_COLLECTION,
    )


def test_chart_ready_specs_have_common_identity_contract() -> None:
    specs = load_all_chart_ready_collection_specs()

    assert set(specs) == set(chart_ready_collections())
    for collection, spec in specs.items():
        assert spec["id"] == collection
        assert spec["collection"] == collection
        assert spec["database"] == "deal_intel"
        assert spec["version"] == 1
        assert spec["refresh_mode"] == "materialized_collection"
        assert spec["common_required_fields"]
        assert spec["identity_fields"]
        assert set(spec["identity_fields"]).issubset(spec["common_required_fields"])
        assert spec["row_types"]
        assert spec["indexes"][0]["unique"] is True


def test_chart_ready_specs_cover_existing_dashboard_chart_ids() -> None:
    weekly = load_chart_ready_collection_spec(WEEKLY_PIPELINE_COLLECTION)
    themes = load_chart_ready_collection_spec(CUSTOMER_THEMES_COLLECTION)
    trend = load_chart_ready_collection_spec(PIPELINE_TREND_COLLECTION)

    assert {row["chart_id"] for row in weekly["row_types"].values()} == {
        "pipeline_kpis",
        "stage_breakdown",
        "health_bands",
        "attention_deals",
        "qualification_gap_distribution",
    }
    assert {row["chart_id"] for row in themes["row_types"].values()} == {
        "theme_overview",
        "decision_criteria_by_stage",
        "pain_by_industry",
        "pain_by_industry_tag",
        "theme_evidence_drilldown",
    }
    assert {row["chart_id"] for row in trend["row_types"].values()} == {
        "trend_kpis",
        "trend_delta_bars",
    }


def test_chart_ready_specs_are_sensitive_field_safe() -> None:
    payload = json.dumps(load_all_chart_ready_collection_specs(), ensure_ascii=False)

    for token in SENSITIVE_TOKENS:
        assert token in payload
    for spec in load_all_chart_ready_collection_specs().values():
        row_payload = json.dumps(spec["row_types"], ensure_ascii=False)
        for token in SENSITIVE_TOKENS:
            assert token not in row_payload
        assert set(spec["sensitive_field_policy"]["exclude"]) >= set(SENSITIVE_TOKENS)


def test_chart_ready_summary_is_compact() -> None:
    summary = chart_ready_collection_contract_summary(WEEKLY_PIPELINE_COLLECTION)

    assert summary == {
        "id": "dashboard_weekly_pipeline",
        "version": 1,
        "collection": "dashboard_weekly_pipeline",
        "dashboard_id": "weekly_pipeline_review",
        "refresh_mode": "materialized_collection",
        "source_collections": ["deals"],
        "common_required_fields": [
            "dashboard_id",
            "chart_id",
            "row_type",
            "row_key",
            "as_of",
            "schema_version",
            "generated_at",
        ],
        "row_types": [
            "attention_deal",
            "health_band",
            "kpi",
            "qualification_gap",
            "stage",
        ],
    }


def test_unknown_chart_ready_collection_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown chart-ready collection"):
        load_chart_ready_collection_spec("not_a_dashboard")
