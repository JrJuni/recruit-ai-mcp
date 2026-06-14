from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from deal_intel.errors import MCPError
from deal_intel.reports.data_export import build_data_export
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
