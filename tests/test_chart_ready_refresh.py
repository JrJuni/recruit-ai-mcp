from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime

from typer.testing import CliRunner

from deal_intel import _context
from deal_intel.chart_ready_refresh import (
    TARGET_WEEKLY_PIPELINE,
    build_customer_themes_chart_ready_rows,
    build_pipeline_trend_chart_ready_rows,
    build_weekly_pipeline_chart_ready_rows,
    refresh_chart_ready_collections,
)
from deal_intel.cli import app
from deal_intel.schema.metrics import ReportingContext

GENERATED_AT = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
CFG = {"reporting": {"timezone": "Asia/Seoul"}}


class FakeMongo:
    def __init__(
        self,
        *,
        deals: list[dict] | None = None,
        snapshots: list[dict] | None = None,
    ) -> None:
        self.deals = deepcopy(deals or _deals())
        self.snapshots = deepcopy(snapshots or _snapshots())
        self.writes: list[dict] = []

    def list_deals_for_metrics(self) -> list[dict]:
        return deepcopy(self.deals)

    def list_analytics_snapshots(
        self,
        *,
        start_date: str,
        end_date: str,
        stage: str | None = None,
        industry: str | None = None,
    ) -> list[dict]:
        return [
            deepcopy(snapshot)
            for snapshot in self.snapshots
            if start_date <= snapshot["as_of"] <= end_date
            and (stage is None or snapshot.get("deal_stage") == stage)
            and (industry is None or snapshot.get("industry") == industry)
        ]

    def replace_chart_ready_rows(
        self,
        *,
        collection: str,
        scope_filter: dict,
        rows: list[dict],
    ) -> dict:
        self.writes.append(
            {
                "collection": collection,
                "scope_filter": deepcopy(scope_filter),
                "rows": deepcopy(rows),
            }
        )
        return {
            "collection": collection,
            "matched_scope": scope_filter,
            "deleted_count": 2,
            "inserted_count": len(rows),
        }


class FakeFailingMongo:
    def list_deals_for_metrics(self) -> list[dict]:
        raise RuntimeError(
            "DNS operation timed out for mongodb+srv://user:secret@example.mongodb.net"
        )


def _reporting() -> ReportingContext:
    return ReportingContext.from_config(
        CFG,
        as_of="2026-06-10",
        generated_at=GENERATED_AT,
    )


def _deal(
    deal_id: str,
    *,
    company: str = "Alpha",
    stage: str = "proposal",
    industry: str = "SaaS",
    amount: int = 10_000_000,
    health_pct: float = 80,
    expected_close_date: str = "2026-06-30",
    gaps: list[str] | None = None,
    themes: list[dict] | None = None,
) -> dict:
    return {
        "deal_id": deal_id,
        "company": company,
        "industry": industry,
        "industry_tags": [industry],
        "deal_stage": stage,
        "deal_size_amount": amount,
        "deal_size_currency": "KRW",
        "deal_size_status": "quoted",
        "expected_close_date": expected_close_date,
        "stage_history": [
            {"stage": stage, "entered_at": "2026-06-01T00:00:00+00:00"}
        ],
        "customer_themes": themes if themes is not None else [_theme()],
        "meetings": [{"raw_notes": "do not leak"}],
        "interactions": [{"raw_content": "do not leak"}],
        "contacts": [{"name": "secret"}],
        "summary_embedding": [0.1, 0.2],
        "qualification_latest": {
            "framework_key": "meddpicc",
            "framework_display_name": "MEDDPICC",
            "health_pct": health_pct,
            "coverage_pct": 100,
            "quality_pct": health_pct,
            "filled_count": 6,
            "total_count": 7,
            "gaps": gaps if gaps is not None else ["champion"],
            "dimensions": {},
        },
        "meddpicc_latest": {
            "filled_count": 6,
            "health_pct": health_pct,
            "gaps": gaps if gaps is not None else ["champion"],
        },
    }


def _theme(
    *,
    theme_key: str = "compliance_security",
    dimension: str = "decision_criteria",
    evidence: str = "audit log is mandatory",
    importance: int = 5,
) -> dict:
    return {
        "theme_key": theme_key,
        "label": theme_key,
        "dimension": dimension,
        "evidence": evidence,
        "importance": importance,
        "interaction_type": "meeting",
        "source_confidence": "customer_stated",
        "interaction_date": "2026-06-02",
    }


def _deals() -> list[dict]:
    return [
        _deal(
            "deal-a",
            company="Alpha",
            stage="proposal",
            amount=100_000_000,
            themes=[
                _theme(),
                _theme(
                    theme_key="operational_efficiency",
                    dimension="identify_pain",
                    evidence="manual reporting takes too long",
                    importance=4,
                ),
            ],
        ),
        _deal(
            "deal-b",
            company="Beta",
            stage="negotiation",
            amount=50_000_000,
            health_pct=35,
            expected_close_date="2026-06-01",
            gaps=["champion", "competition"],
        ),
        _deal("deal-won", company="Won", stage="won", amount=20_000_000),
    ]


def _snapshots() -> list[dict]:
    return [
        {
            "event_id": "start-a",
            "deal_id": "deal-a",
            "as_of": "2026-06-03",
            "occurred_at": "2026-06-03T00:00:00+00:00",
            "deal_stage": "proposal",
            "deal_size_amount": 100_000_000,
            "deal_size_currency": "KRW",
            "health_pct": 70,
            "attention_reasons": [],
        },
        {
            "event_id": "end-a",
            "deal_id": "deal-a",
            "as_of": "2026-06-10",
            "occurred_at": "2026-06-10T00:00:00+00:00",
            "deal_stage": "negotiation",
            "deal_size_amount": 120_000_000,
            "deal_size_currency": "KRW",
            "health_pct": 80,
            "attention_reasons": ["overdue"],
        },
    ]


def test_weekly_pipeline_chart_ready_rows_are_safe_and_chart_friendly() -> None:
    rows, warnings = build_weekly_pipeline_chart_ready_rows(
        _deals(),
        cfg=CFG,
        reporting=_reporting(),
    )

    assert warnings
    assert {row["row_type"] for row in rows} >= {
        "kpi",
        "stage",
        "health_band",
        "attention_deal",
        "qualification_gap",
    }
    kpi = next(row for row in rows if row["row_type"] == "kpi")
    assert kpi["open_pipeline_value_amount"] == 150_000_000
    assert kpi["source_collections"] == ["deals"]
    assert kpi["schema_version"] == 1
    assert kpi["as_of"] == "2026-06-10"

    payload = json.dumps(rows, ensure_ascii=False)
    assert "raw_notes" not in payload
    assert "raw_content" not in payload
    assert "contacts" not in payload
    assert "summary_embedding" not in payload


def test_customer_themes_chart_ready_rows_cover_ranking_breakdown_and_evidence() -> None:
    rows, warnings = build_customer_themes_chart_ready_rows(
        _deals(),
        reporting=_reporting(),
    )

    assert warnings == []
    row_types = {row["row_type"] for row in rows}
    assert {
        "theme_overview",
        "decision_criteria_by_stage",
        "pain_by_industry",
        "pain_by_industry_tag",
        "theme_evidence",
    }.issubset(row_types)
    evidence = [row for row in rows if row["row_type"] == "theme_evidence"]
    assert evidence
    assert evidence[0]["source_label"]
    assert "audit log is mandatory" in {row["evidence"] for row in evidence}


def test_pipeline_trend_chart_ready_rows_include_kpi_and_delta_rows() -> None:
    rows, warnings = build_pipeline_trend_chart_ready_rows(
        _snapshots(),
        reporting=_reporting(),
        lookback_days=7,
    )

    assert warnings == []
    assert rows[0]["row_type"] == "trend_kpi"
    assert rows[0]["window_start"] == "2026-06-03"
    assert rows[0]["window_end"] == "2026-06-10"
    assert rows[0]["end_open_pipeline_value_amount"] == 120_000_000
    delta_metrics = {
        row["metric"] for row in rows if row["row_type"] == "trend_delta"
    }
    assert "open_pipeline_value_amount" in delta_metrics


def test_refresh_dry_run_does_not_write_and_apply_replaces_rows() -> None:
    mongo = FakeMongo()

    dry_run = refresh_chart_ready_collections(
        mongo,
        CFG,
        target=TARGET_WEEKLY_PIPELINE,
        as_of="2026-06-10",
        generated_at=GENERATED_AT,
    )

    assert dry_run["ok"] is True
    assert dry_run["dry_run"] is True
    assert dry_run["storage_written"] is False
    assert mongo.writes == []
    assert dry_run["targets"][0]["sample_rows"]

    applied = refresh_chart_ready_collections(
        mongo,
        CFG,
        target=TARGET_WEEKLY_PIPELINE,
        as_of="2026-06-10",
        generated_at=GENERATED_AT,
        apply=True,
    )

    assert applied["dry_run"] is False
    assert applied["storage_written"] is True
    assert mongo.writes[0]["collection"] == "dashboard_weekly_pipeline"
    assert mongo.writes[0]["scope_filter"] == {
        "dashboard_id": "weekly_pipeline_review",
        "as_of": "2026-06-10",
        "schema_version": 1,
    }
    assert applied["targets"][0]["write_result"]["inserted_count"] == len(
        mongo.writes[0]["rows"]
    )


def test_cli_refresh_chart_ready_dry_run(monkeypatch) -> None:
    monkeypatch.setattr(_context, "config", lambda: CFG)
    monkeypatch.setattr(_context, "mongo", lambda: FakeMongo())

    result = CliRunner().invoke(
        app,
        [
            "mongo",
            "refresh-chart-ready",
            "--target",
            "weekly_pipeline",
            "--as-of",
            "2026-06-10",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["targets"][0]["collection"] == "dashboard_weekly_pipeline"


def test_cli_refresh_chart_ready_accepts_explicit_dry_run(monkeypatch) -> None:
    monkeypatch.setattr(_context, "config", lambda: CFG)
    monkeypatch.setattr(_context, "mongo", lambda: FakeMongo())

    result = CliRunner().invoke(
        app,
        [
            "mongo",
            "refresh-chart-ready",
            "--target",
            "weekly_pipeline",
            "--as-of",
            "2026-06-10",
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["targets"][0]["collection"] == "dashboard_weekly_pipeline"


def test_cli_refresh_chart_ready_rejects_apply_with_dry_run(monkeypatch) -> None:
    monkeypatch.setattr(_context, "config", lambda: CFG)
    monkeypatch.setattr(_context, "mongo", lambda: FakeMongo())

    result = CliRunner().invoke(
        app,
        [
            "mongo",
            "refresh-chart-ready",
            "--target",
            "weekly_pipeline",
            "--as-of",
            "2026-06-10",
            "--apply",
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["dry_run"] is True
    assert "cannot be combined" in payload["error"]
    assert "remove --dry-run" in payload["hint"]


def test_cli_refresh_chart_ready_storage_error_includes_hint(monkeypatch) -> None:
    monkeypatch.setattr(_context, "config", lambda: CFG)
    monkeypatch.setattr(_context, "mongo", lambda: FakeFailingMongo())

    result = CliRunner().invoke(
        app,
        [
            "mongo",
            "refresh-chart-ready",
            "--target",
            "weekly_pipeline",
            "--as-of",
            "2026-06-10",
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["dry_run"] is True
    assert payload["hint"]["operation"] == "mongo.refresh_chart_ready"
    assert payload["hint"]["likely_issue"] == "dns_or_network"
    assert payload["hint"]["diagnostic_command"] == "recruit-ai config doctor"
    assert "secret" not in json.dumps(payload["hint"])
