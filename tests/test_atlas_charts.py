from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

import pytest

import deal_intel.reports.atlas_charts as atlas_charts
from deal_intel.reports.atlas_charts import (
    ATLAS_SOURCE_CHART_READY,
    load_customer_themes_dashboard_spec,
    load_pipeline_trend_dashboard_spec,
    load_weekly_pipeline_dashboard_spec,
    render_chart_pipeline,
    render_customer_themes_dashboard_spec,
    render_dashboard_spec,
    render_pipeline_trend_dashboard_spec,
    render_weekly_pipeline_dashboard_spec,
)

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_CHART_IDS = {
    "pipeline_kpis",
    "stage_breakdown",
    "health_bands",
    "attention_deals",
    "qualification_gap_distribution",
    "meddpicc_gap_distribution",
}
TREND_CHART_IDS = {
    "trend_kpis",
    "trend_delta_bars",
}
CUSTOMER_THEME_CHART_IDS = {
    "theme_overview",
    "decision_criteria_by_stage",
    "pain_by_industry",
    "pain_by_industry_tag",
    "theme_evidence_drilldown",
}


def test_weekly_pipeline_dashboard_spec_is_versioned_and_complete() -> None:
    spec = load_weekly_pipeline_dashboard_spec()

    assert spec["dashboard_title"] == "Weekly Pipeline Review"
    assert spec["version"] == 1
    assert spec["database"] == "deal_intel"
    assert spec["collection"] == "deals"
    assert {chart["id"] for chart in spec["charts"]} == REQUIRED_CHART_IDS
    assert all(isinstance(chart["pipeline"], list) for chart in spec["charts"])
    assert all(chart["pipeline"] for chart in spec["charts"])


def test_pipeline_trend_dashboard_spec_is_versioned_and_complete() -> None:
    spec = load_pipeline_trend_dashboard_spec()

    assert spec["dashboard_title"] == "Pipeline Trend Review"
    assert spec["version"] == 1
    assert spec["database"] == "deal_intel"
    assert spec["collection"] == "analytics_snapshots"
    assert {chart["id"] for chart in spec["charts"]} == TREND_CHART_IDS
    assert all(isinstance(chart["pipeline"], list) for chart in spec["charts"])
    assert all(chart["pipeline"] for chart in spec["charts"])


def test_customer_themes_dashboard_spec_is_versioned_and_complete() -> None:
    spec = load_customer_themes_dashboard_spec()

    assert spec["dashboard_title"] == "Customer Themes Review"
    assert spec["version"] == 1
    assert spec["database"] == "deal_intel"
    assert spec["collection"] == "deals"
    assert {chart["id"] for chart in spec["charts"]} == CUSTOMER_THEME_CHART_IDS
    assert all(isinstance(chart["pipeline"], list) for chart in spec["charts"])
    assert all(chart["pipeline"] for chart in spec["charts"])


def test_chart_ready_dashboard_specs_are_versioned_and_complete() -> None:
    weekly = load_weekly_pipeline_dashboard_spec(source=ATLAS_SOURCE_CHART_READY)
    trend = load_pipeline_trend_dashboard_spec(source=ATLAS_SOURCE_CHART_READY)
    themes = load_customer_themes_dashboard_spec(source=ATLAS_SOURCE_CHART_READY)

    assert weekly["source_mode"] == "chart_ready"
    assert weekly["collection"] == "dashboard_weekly_pipeline"
    assert {chart["id"] for chart in weekly["charts"]} == REQUIRED_CHART_IDS

    assert trend["source_mode"] == "chart_ready"
    assert trend["collection"] == "dashboard_pipeline_trend"
    assert {chart["id"] for chart in trend["charts"]} == TREND_CHART_IDS

    assert themes["source_mode"] == "chart_ready"
    assert themes["collection"] == "dashboard_customer_themes"
    assert {chart["id"] for chart in themes["charts"]} == CUSTOMER_THEME_CHART_IDS


def test_packaged_dashboard_specs_match_repo_specs() -> None:
    for file_name in (
        "weekly_pipeline_review.v1.json",
        "pipeline_trend.v1.json",
        "customer_themes.v1.json",
    ):
        packaged = (
            resources.files("deal_intel.resources")
            .joinpath("atlas", "charts", file_name)
            .read_text(encoding="utf-8")
        )
        repo = (ROOT / "atlas" / "charts" / file_name).read_text(encoding="utf-8")

        assert packaged == repo


def test_packaged_chart_ready_dashboard_specs_match_repo_specs() -> None:
    for file_name in (
        "weekly_pipeline_review.v1.json",
        "pipeline_trend.v1.json",
        "customer_themes.v1.json",
    ):
        packaged = (
            resources.files("deal_intel.resources")
            .joinpath("atlas", "chart_ready", file_name)
            .read_text(encoding="utf-8")
        )
        repo = (ROOT / "atlas" / "chart_ready" / file_name).read_text(
            encoding="utf-8"
        )

        assert packaged == repo


def test_dashboard_specs_fall_back_to_packaged_resources(monkeypatch, tmp_path) -> None:
    monkeypatch.setitem(
        atlas_charts.DASHBOARD_SPECS,
        atlas_charts.WEEKLY_PIPELINE_DASHBOARD,
        tmp_path / "missing-weekly.json",
    )

    spec = load_weekly_pipeline_dashboard_spec()

    assert spec["dashboard_title"] == "Weekly Pipeline Review"
    assert {chart["id"] for chart in spec["charts"]} == REQUIRED_CHART_IDS


def test_chart_ready_dashboard_specs_fall_back_to_packaged_resources(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setitem(
        atlas_charts.CHART_READY_DASHBOARD_SPECS,
        atlas_charts.WEEKLY_PIPELINE_DASHBOARD,
        tmp_path / "missing-weekly-chart-ready.json",
    )

    spec = load_weekly_pipeline_dashboard_spec(source=ATLAS_SOURCE_CHART_READY)

    assert spec["collection"] == "dashboard_weekly_pipeline"
    assert {chart["id"] for chart in spec["charts"]} == REQUIRED_CHART_IDS


def test_weekly_pipeline_dashboard_render_replaces_config_tokens() -> None:
    rendered = render_weekly_pipeline_dashboard_spec(
        {
            "reporting": {"timezone": "Asia/Seoul"},
            "metrics": {
                "health_bands": {"healthy_min": 75, "watch_min": 45},
                "overdue": {"grace_days": 2},
            },
            "pipeline": {
                "stuck_threshold_days": 99,
                "stuck_threshold_days_by_stage": {
                    "discovery": 3,
                    "qualification": 4,
                    "proposal": 5,
                    "negotiation": 6,
                },
            },
        },
        as_of="2026-06-09",
    )

    payload = json.dumps(rendered, ensure_ascii=False)
    assert "{{" not in payload
    assert rendered["parameters"] == {
        "as_of_datetime": "2026-06-09T00:00:00Z",
        "healthy_min": 75.0,
        "watch_min": 45.0,
        "overdue_grace_days": 2,
        "stuck_days": {
            "discovery": 3,
            "qualification": 4,
            "proposal": 5,
            "negotiation": 6,
        },
    }
    assert rendered["rendered_parameters"]["healthy_min"] == 75.0
    payload = json.dumps(rendered, ensure_ascii=False)
    assert "$qualification_latest.health_pct" in payload
    assert "$qualification_latest.filled_count" in payload
    assert "$qualification_latest.gaps" in payload
    assert "$meddpicc_latest.health_pct" in payload
    assert "$meddpicc_latest.gaps" in payload


def test_chart_ready_weekly_pipeline_render_uses_materialized_collection() -> None:
    rendered = render_weekly_pipeline_dashboard_spec(
        {"reporting": {"timezone": "Asia/Seoul"}},
        as_of="2026-06-09",
        source=ATLAS_SOURCE_CHART_READY,
    )

    payload = json.dumps(rendered, ensure_ascii=False)
    assert "{{" not in payload
    assert rendered["collection"] == "dashboard_weekly_pipeline"
    assert rendered["parameters"]["as_of"] == "2026-06-09"
    assert "$qualification_latest" not in payload
    assert "$meddpicc_latest" not in payload


def test_pipeline_trend_dashboard_render_replaces_window_tokens() -> None:
    rendered = render_pipeline_trend_dashboard_spec(
        {"reporting": {"timezone": "Asia/Seoul"}},
        as_of="2026-06-10",
        lookback_days=14,
    )

    payload = json.dumps(rendered, ensure_ascii=False)
    assert "{{" not in payload
    assert rendered["parameters"] == {
        "start_date": "2026-05-27",
        "end_date": "2026-06-10",
        "lookback_days": 14,
    }
    assert rendered["rendered_parameters"]["start_date"] == "2026-05-27"
    assert rendered["rendered_parameters"]["as_of_date"] == "2026-06-10"
    assert rendered["rendered_parameters"]["lookback_days"] == 14


def test_chart_ready_trend_render_uses_materialized_collection() -> None:
    rendered = render_pipeline_trend_dashboard_spec(
        {"reporting": {"timezone": "Asia/Seoul"}},
        as_of="2026-06-10",
        lookback_days=7,
        source=ATLAS_SOURCE_CHART_READY,
    )

    payload = json.dumps(rendered, ensure_ascii=False)
    assert "{{" not in payload
    assert rendered["collection"] == "dashboard_pipeline_trend"
    assert rendered["parameters"]["window_start"] == "2026-06-03"
    assert rendered["parameters"]["window_end"] == "2026-06-10"


def test_customer_themes_dashboard_render_has_no_placeholders() -> None:
    rendered = render_customer_themes_dashboard_spec(
        {"reporting": {"timezone": "Asia/Seoul"}},
        as_of="2026-06-10",
    )

    payload = json.dumps(rendered, ensure_ascii=False)
    assert "{{" not in payload
    assert rendered["rendered_parameters"]["as_of_date"] == "2026-06-10"


def test_chart_ready_customer_themes_render_uses_materialized_collection() -> None:
    rendered = render_customer_themes_dashboard_spec(
        {"reporting": {"timezone": "Asia/Seoul"}},
        as_of="2026-06-10",
        source=ATLAS_SOURCE_CHART_READY,
    )

    payload = json.dumps(rendered, ensure_ascii=False)
    assert "{{" not in payload
    assert rendered["collection"] == "dashboard_customer_themes"
    assert rendered["parameters"]["as_of"] == "2026-06-10"
    assert "$customer_themes" not in payload


def test_chart_pipeline_rendering_returns_single_pipeline_and_rejects_unknown_id() -> None:
    pipeline = render_chart_pipeline(
        "pipeline_kpis",
        {},
        as_of="2026-06-09",
    )

    assert isinstance(pipeline, list)
    assert pipeline[0]["$match"]["archived"] == {"$ne": True}
    assert pipeline[1]["$addFields"]["_as_of"]["$dateFromString"]["dateString"] == (
        "2026-06-09T00:00:00Z"
    )
    with pytest.raises(ValueError, match="chart_id"):
        render_chart_pipeline("not-a-chart", {}, as_of="2026-06-09")


def test_chart_ready_chart_pipeline_rendering_returns_short_pipeline() -> None:
    pipeline = render_chart_pipeline(
        "pipeline_kpis",
        {},
        as_of="2026-06-09",
        source=ATLAS_SOURCE_CHART_READY,
    )

    assert len(pipeline) == 2
    assert pipeline[0]["$match"] == {
        "dashboard_id": "weekly_pipeline_review",
        "chart_id": "pipeline_kpis",
        "schema_version": 1,
        "as_of": "2026-06-09",
    }
    assert pipeline[-1]["$project"]["open_pipeline_value_amount"] == 1


def test_chart_pipeline_rendering_supports_trend_dashboard() -> None:
    pipeline = render_chart_pipeline(
        "trend_kpis",
        {},
        dashboard="pipeline_trend",
        as_of="2026-06-10",
        lookback_days=7,
    )

    assert pipeline[0]["$match"]["as_of"] == {
        "$gte": "2026-06-03",
        "$lte": "2026-06-10",
    }
    assert pipeline[-1]["$project"]["window_start"] == {"$literal": "2026-06-03"}
    assert pipeline[-1]["$project"]["lookback_days"] == {"$literal": 7}


def test_chart_ready_pipeline_rendering_supports_trend_dashboard() -> None:
    pipeline = render_chart_pipeline(
        "trend_delta_bars",
        {},
        dashboard="pipeline_trend",
        as_of="2026-06-10",
        lookback_days=7,
        source=ATLAS_SOURCE_CHART_READY,
    )

    assert pipeline[0]["$match"] == {
        "dashboard_id": "pipeline_trend",
        "chart_id": "trend_delta_bars",
        "schema_version": 1,
        "window_start": "2026-06-03",
        "window_end": "2026-06-10",
        "lookback_days": 7,
    }


def test_chart_pipeline_rendering_supports_customer_themes_dashboard() -> None:
    pipeline = render_chart_pipeline(
        "theme_overview",
        {},
        dashboard="customer_themes",
        as_of="2026-06-10",
    )

    assert pipeline[0]["$match"]["archived"] == {"$ne": True}
    assert pipeline[0]["$match"]["deal_stage"] == {"$nin": ["won", "lost"]}
    assert pipeline[-1]["$project"]["theme_key"] == "$_id"


def test_chart_ready_pipeline_rendering_supports_customer_themes_dashboard() -> None:
    pipeline = render_chart_pipeline(
        "theme_overview",
        {},
        dashboard="customer_themes",
        as_of="2026-06-10",
        source=ATLAS_SOURCE_CHART_READY,
    )

    assert pipeline[0]["$match"] == {
        "dashboard_id": "customer_themes",
        "chart_id": "theme_overview",
        "schema_version": 1,
        "as_of": "2026-06-10",
    }
    assert pipeline[-1]["$project"]["deal_count"] == 1


def test_customer_theme_evidence_chart_projects_source_labels() -> None:
    pipeline = render_chart_pipeline(
        "theme_evidence_drilldown",
        {},
        dashboard="customer_themes",
        as_of="2026-06-10",
    )

    payload = json.dumps(pipeline, ensure_ascii=False)
    assert "_theme_source_label" in payload
    assert "Email thread" in payload
    assert "User interview" in payload
    project_stage = next(stage["$project"] for stage in pipeline if "$project" in stage)
    assert project_stage["source_label"] == "$_theme_source_label"
    assert project_stage["interaction_type"] == "$_theme_interaction_type"


def test_customer_theme_industry_tag_chart_unwinds_tags() -> None:
    pipeline = render_chart_pipeline(
        "pain_by_industry_tag",
        {},
        dashboard="customer_themes",
        as_of="2026-06-10",
    )

    payload = json.dumps(pipeline, ensure_ascii=False)
    assert "$industry_tags" in payload
    assert {"$unwind": "$_industry_tags_for_chart"} in pipeline
    project_stage = next(
        stage["$project"]
        for stage in pipeline
        if "$project" in stage and "industry_tag" in stage["$project"]
    )
    assert project_stage["industry_tag"] == {
        "$ifNull": ["$_id.industry_tag", "unknown"]
    }


def test_weekly_pipeline_chart_pipelines_exclude_archived_deals_first() -> None:
    rendered = render_weekly_pipeline_dashboard_spec({}, as_of="2026-06-09")

    for chart in rendered["charts"]:
        assert chart["pipeline"][0] == {"$match": {"archived": {"$ne": True}}}


def test_atlas_chart_pipelines_do_not_touch_sensitive_fields() -> None:
    rendered = render_weekly_pipeline_dashboard_spec({}, as_of="2026-06-09")
    trend_rendered = render_pipeline_trend_dashboard_spec({}, as_of="2026-06-10")
    theme_rendered = render_customer_themes_dashboard_spec({}, as_of="2026-06-10")
    chart_ready_rendered = [
        render_dashboard_spec(
            "weekly_pipeline_review",
            {},
            as_of="2026-06-09",
            source=ATLAS_SOURCE_CHART_READY,
        ),
        render_dashboard_spec(
            "pipeline_trend",
            {},
            as_of="2026-06-10",
            source=ATLAS_SOURCE_CHART_READY,
        ),
        render_dashboard_spec(
            "customer_themes",
            {},
            as_of="2026-06-10",
            source=ATLAS_SOURCE_CHART_READY,
        ),
    ]

    payload = json.dumps(
        [rendered, trend_rendered, theme_rendered, *chart_ready_rendered],
        ensure_ascii=False,
    )
    assert "raw_notes" not in payload
    assert "contacts" not in payload
    assert "summary_embedding" not in payload
