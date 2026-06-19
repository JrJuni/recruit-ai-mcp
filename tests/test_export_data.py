from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest

from deal_intel.errors import ErrorCode, MCPError
from deal_intel.reports.data_export import build_data_export
from deal_intel.schema.qualification import compute_qualification_latest
from deal_intel.schema.qualification_framework import get_qualification_template
from deal_intel.tools import export_data


class FakeMetricsStore:
    def __init__(self, deals: list[dict]) -> None:
        self.deals = deals
        self.calls = 0

    def list_deals_for_metrics(self) -> list[dict]:
        self.calls += 1
        return self.deals


class ExplodingStore:
    def list_deals_for_metrics(self) -> list[dict]:
        raise AssertionError("storage should not be reached")


class StorageFailingStore:
    def __init__(self, message: str) -> None:
        self.message = message

    def list_deals_for_metrics(self) -> list[dict]:
        raise RuntimeError(self.message)


def _deal(
    deal_id: str,
    company: str,
    stage: str,
    *,
    amount: int = 1000,
    industry: str = "Software",
    health_pct: float = 80.0,
) -> dict:
    return {
        "deal_id": deal_id,
        "company": company,
        "industry": industry,
        "industry_tags": [industry],
        "customer_segment": "startup",
        "deal_stage": stage,
        "deal_size_amount": amount,
        "deal_size_currency": "KRW",
        "deal_size_status": "quoted",
        "expected_close_date": "2026-06-20",
        "actual_close_date": "2026-06-21" if stage in {"won", "lost"} else None,
        "close_reason": (
            "won reason"
            if stage == "won"
            else "lost reason"
            if stage == "lost"
            else None
        ),
        "created_at": "2026-06-01T00:00:00+00:00",
        "updated_at": "2026-06-10T00:00:00+00:00",
        "contacts": [{"name": "secret contact"}],
        "summary_embedding": [0.1, 0.2],
        "meetings": [{"date": "2026-06-05", "raw_notes": "do not export"}],
        "interactions": [
            {
                "interaction_id": f"{deal_id}-i1",
                "date": "2026-06-07",
                "interaction_type": "meeting",
                "source_confidence": "customer_stated",
                "raw_content": "do not export either",
            }
        ],
        "meddpicc_latest": {
            "filled_count": 7,
            "health_pct": health_pct,
            "gaps": ["competition"] if health_pct < 70 else [],
        },
        "customer_themes": [
            {
                "dimension": "identify_pain",
                "label": "Manual reporting",
                "evidence": "weekly report takes too long",
                "importance": 5,
            },
            {
                "dimension": "decision_criteria",
                "label": "Fast rollout",
                "evidence": "must launch this month",
                "importance": 4,
            },
        ],
    }


def _simple_b2b_latest(*, score: int = 1, stage: str = "proposal") -> dict:
    return compute_qualification_latest(
        [{"qualification": {"business_need": {"score": score}}}],
        framework=get_qualification_template("simple_b2b"),
        evidence_fields=("qualification",),
        deal_stage=stage,
    )


def test_build_data_export_open_deals_uses_safe_rows() -> None:
    result = build_data_export(
        [
            _deal("d1", "OpenCo", "proposal", health_pct=65.0),
            _deal("d2", "WonCo", "won"),
        ],
        dataset="open_deals",
        as_of=date(2026, 6, 10),
    )

    assert result["dataset"] == "open_deals"
    assert result["row_count"] == 1
    row = result["rows"][0]
    assert row["company"] == "OpenCo"
    assert row["primary_pain"].startswith("Manual reporting")
    serialized = str(result)
    assert "raw_notes" not in serialized
    assert "raw_content" not in serialized
    assert "secret contact" not in serialized
    assert "summary_embedding" not in serialized


def test_build_data_export_hubspot_deals_uses_import_columns_and_stage_mapping() -> None:
    stages = [
        "discovery",
        "qualification",
        "proposal",
        "negotiation",
        "stalled",
        "won",
        "lost",
    ]
    deals = [
        _deal(f"d-{stage}", f"{stage.title()}Co", stage)
        for stage in stages
    ]
    archived = _deal("d-archived", "ArchivedCo", "proposal")
    archived["archived"] = True

    result = build_data_export(
        [*deals, archived],
        dataset="hubspot_deals",
        as_of=date(2026, 6, 10),
    )

    assert result["columns"] == [
        "dealname",
        "pipeline",
        "dealstage",
        "amount",
        "closedate",
        "deal_currency_code",
        "description",
    ]
    assert result["row_count"] == len(stages)
    rows_by_name = {row["dealname"]: row for row in result["rows"]}
    assert rows_by_name["DiscoveryCo"]["dealstage"] == "appointmentscheduled"
    assert rows_by_name["QualificationCo"]["dealstage"] == "qualifiedtobuy"
    assert rows_by_name["ProposalCo"]["dealstage"] == "presentationscheduled"
    assert rows_by_name["NegotiationCo"]["dealstage"] == "contractsent"
    assert rows_by_name["StalledCo"]["dealstage"] == "qualifiedtobuy"
    assert rows_by_name["WonCo"]["dealstage"] == "closedwon"
    assert rows_by_name["LostCo"]["dealstage"] == "closedlost"
    assert rows_by_name["ProposalCo"]["pipeline"] == "default"
    assert rows_by_name["ProposalCo"]["closedate"] == "2026-06-20"
    assert rows_by_name["WonCo"]["closedate"] == "2026-06-21"
    assert "ArchivedCo" not in rows_by_name
    assert "hubspot_default_pipeline_mapping_review_required" in result["warnings"]
    assert "hubspot_stalled_stage_mapped_to_qualifiedtobuy" in result["warnings"]


def test_build_data_export_hubspot_deals_builds_capped_one_line_description() -> None:
    deal = _deal("d1", "DescCo", "proposal", health_pct=65.0)
    deal["customer_themes"][0]["evidence"] = "manual report " * 100

    result = build_data_export(
        [deal],
        dataset="hubspot_deals",
        as_of=date(2026, 6, 10),
    )

    description = result["rows"][0]["description"]
    assert len(description) <= 500
    assert "\n" not in description
    assert "deal_id=d1" in description
    assert "source_stage=proposal" in description
    assert "updated=2026-06-10" in description
    assert "health=watch (65.0%)" in description
    assert "primary_pain=Manual reporting" in description
    assert "primary_decision_criteria=Fast rollout" in description
    assert "top_gaps=competition" in description


def test_build_data_export_hubspot_deals_warns_for_duplicate_company_and_skip() -> None:
    missing_identity = {
        "deal_id": "",
        "company": "",
        "industry": "Software",
        "deal_stage": "proposal",
    }

    result = build_data_export(
        [
            _deal("d1", "DupCo", "proposal"),
            _deal("d2", "DupCo", "qualification"),
            missing_identity,
        ],
        dataset="hubspot_deals",
        as_of=date(2026, 6, 10),
    )

    assert result["row_count"] == 2
    assert "hubspot_multiple_deals_same_company_review_required" in result["warnings"]
    assert "hubspot_skipped_missing_dealname" in result["warnings"]


def test_build_data_export_hubspot_deals_uses_filters() -> None:
    result = build_data_export(
        [
            _deal("d1", "SoftwareCo", "proposal", industry="Software"),
            _deal("d2", "HealthCo", "proposal", industry="Healthcare"),
            _deal("d3", "DiscoveryCo", "discovery", industry="Software"),
        ],
        dataset="hubspot_deals",
        as_of=date(2026, 6, 10),
        stage="proposal",
        industry="Software",
    )

    assert result["row_count"] == 1
    assert result["rows"][0]["dealname"] == "SoftwareCo"
    assert result["filters"] == {"stage": "proposal", "industry": "Software"}


def test_build_data_export_uses_active_qualification_snapshot() -> None:
    deal = _deal("d1", "CustomCo", "proposal", health_pct=95.0)
    deal["qualification_latest"] = _simple_b2b_latest(score=1, stage="proposal")

    open_result = build_data_export(
        [deal],
        dataset="open_deals",
        as_of=date(2026, 6, 10),
    )
    all_result = build_data_export(
        [deal],
        dataset="all_deals",
        as_of=date(2026, 6, 10),
    )

    open_row = open_result["rows"][0]
    all_row = all_result["rows"][0]
    assert open_row["qualification_framework"] == "simple_b2b"
    assert open_row["health_pct"] == 6.7
    assert open_row["qualification_gaps"] == [
        "business_need",
        "buyer_owner",
        "next_step",
    ]
    assert open_row["meddpicc_gaps"] == []
    assert all_row["qualification_framework"] == "simple_b2b"
    assert all_row["health_pct"] == 6.7
    assert all_row["qualification_gaps"] == open_row["qualification_gaps"]


def test_export_data_writes_csv_and_preview(tmp_path: Path) -> None:
    store = FakeMetricsStore([
        _deal("d1", "OpenCo", "proposal"),
        _deal("d2", "LostCo", "lost"),
    ])

    result = export_data.handle(
        store,  # type: ignore[arg-type]
        {},
        dataset="all_deals",
        output_dir=str(tmp_path),
        as_of="2026-06-10",
    )

    assert result["ok"] is True
    assert result["dataset"] == "all_deals"
    assert result["row_count"] == 2
    assert result["artifacts"]["csv"]["encoding"] == "utf-8-sig"
    assert Path(result["csv_path"]).exists()
    assert store.calls == 1
    text = Path(result["csv_path"]).read_text(encoding="utf-8-sig")
    assert "raw_notes" not in text
    assert "raw_content" not in text
    assert "summary_embedding" not in text
    assert result["preview_rows"]


def test_export_data_hubspot_deals_writes_safe_csv_and_preview(tmp_path: Path) -> None:
    store = FakeMetricsStore([
        _deal("d1", "OpenCo", "proposal"),
        _deal("d2", "LostCo", "lost"),
    ])

    result = export_data.handle(
        store,  # type: ignore[arg-type]
        {},
        dataset="hubspot_deals",
        output_dir=str(tmp_path),
        as_of="2026-06-10",
    )

    assert result["ok"] is True
    assert result["dataset"] == "hubspot_deals"
    assert result["columns"] == [
        "dealname",
        "pipeline",
        "dealstage",
        "amount",
        "closedate",
        "deal_currency_code",
        "description",
    ]
    assert result["preview_rows"]
    text = Path(result["csv_path"]).read_text(encoding="utf-8-sig")
    assert "raw_notes" not in text
    assert "raw_content" not in text
    assert "summary_embedding" not in text
    assert "secret contact" not in text

    with Path(result["csv_path"]).open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["dealname"] for row in rows} == {"OpenCo", "LostCo"}
    assert rows[0]["description"]


def test_export_data_closed_deals_filters_terminal_rows(tmp_path: Path) -> None:
    store = FakeMetricsStore([
        _deal("d1", "OpenCo", "proposal"),
        _deal("d2", "LostCo", "lost"),
        _deal("d3", "WonCo", "won"),
    ])

    result = export_data.handle(
        store,  # type: ignore[arg-type]
        {},
        dataset="closed_deals",
        output_dir=str(tmp_path),
        as_of="2026-06-10",
    )

    assert result["row_count"] == 2
    assert {row["result"] for row in result["preview_rows"]} == {"lost", "won"}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"dataset": "missing"},
        {"dataset": "open_deals", "stage": "bad-stage"},
        {"dataset": "open_deals", "as_of": "bad-date"},
    ],
)
def test_export_data_rejects_invalid_inputs_before_storage(kwargs: dict) -> None:
    with pytest.raises(MCPError):
        export_data.handle(
            ExplodingStore(),  # type: ignore[arg-type]
            {},
            output_dir="reports",
            **kwargs,
        )


def test_export_data_invalid_dataset_hint_includes_hubspot_deals() -> None:
    with pytest.raises(MCPError) as exc_info:
        export_data.handle(
            ExplodingStore(),  # type: ignore[arg-type]
            {},
            dataset="missing",
            output_dir="reports",
        )

    assert "hubspot_deals" in exc_info.value.hint["valid_datasets"]


def test_export_data_storage_error_includes_actionable_secret_safe_hint(
    tmp_path: Path,
) -> None:
    secret_uri = "mongodb+srv://user:super-secret@example.mongodb.net"

    with pytest.raises(MCPError) as exc_info:
        export_data.handle(
            StorageFailingStore(f"MONGODB_URI is not set; attempted {secret_uri}"),  # type: ignore[arg-type]
            {},
            dataset="open_deals",
            output_dir=str(tmp_path),
            as_of="2026-06-10",
        )

    assert exc_info.value.error_code == ErrorCode.STORAGE_ERROR
    assert exc_info.value.stage == "storage"
    assert exc_info.value.retryable is True
    hint = exc_info.value.hint
    assert isinstance(hint, dict)
    assert hint["operation"] == "export_data.read_deals"
    assert hint["likely_issue"] == "missing_mongodb_uri"
    assert hint["diagnostic_command"] == "deal-intel config doctor"
    assert hint["next_actions"]
    serialized_hint = str(hint)
    assert "mongodb+srv" not in serialized_hint
    assert "super-secret" not in serialized_hint
