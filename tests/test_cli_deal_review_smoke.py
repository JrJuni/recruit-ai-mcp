from __future__ import annotations

import json
from copy import deepcopy

from typer.testing import CliRunner

from deal_intel import _context
from deal_intel.cli import _contains_sensitive_result_key, app

MEDDPICC_DIMS = (
    "metrics",
    "economic_buyer",
    "decision_criteria",
    "decision_process",
    "identify_pain",
    "champion",
    "competition",
)


class FakeMongo:
    def __init__(self, deals: list[dict]) -> None:
        self.deals = deepcopy(deals)
        self.read_count = 0
        self.write_count = 0

    def list_deals_for_metrics(self) -> list[dict]:
        self.read_count += 1
        return deepcopy(self.deals)

    def upsert_deal(self, deal: dict) -> None:
        self.write_count += 1
        raise AssertionError("smoke-deal-review must be read-only")


def _deal(
    deal_id: str,
    *,
    company: str,
    health_pct: float = 86.5,
    filled_count: int = 7,
) -> dict:
    scores = {
        dim: {"score": 4.5, "trend": None}
        for dim in MEDDPICC_DIMS[:filled_count]
    }
    return {
        "deal_id": deal_id,
        "company": company,
        "industry": "IT",
        "deal_stage": "proposal",
        "deal_size_krw": 72_000_000,
        "deal_size_status": "quoted",
        "expected_close_date": "2026-06-30",
        "expected_close_date_source": "user_provided",
        "stage_history": [
            {"stage": "proposal", "entered_at": "2026-06-01T00:00:00+00:00"}
        ],
        "meddpicc_latest": {
            **scores,
            "filled_count": filled_count,
            "health_pct": health_pct,
            "gaps": [
                dim for dim in MEDDPICC_DIMS if dim not in scores
            ],
        },
        "meetings": [{"raw_notes": "secret raw note"}],
        "contacts": [{"name": "secret contact"}],
        "summary_embedding": [0.1, 0.2],
    }


def test_smoke_deal_review_text_outputs_human_summary(monkeypatch) -> None:
    mongo = FakeMongo([_deal("deal-1", company="페이브릿지")])
    monkeypatch.setattr(_context, "mongo", lambda: mongo)
    monkeypatch.setattr(_context, "config", lambda: {})

    result = CliRunner().invoke(
        app,
        ["smoke-deal-review", "--deal-id", "deal-1", "--as-of", "2026-06-10"],
    )

    assert result.exit_code == 0
    assert "Deal Review Smoke (as_of=2026-06-10, count=1)" in result.output
    assert "[페이브릿지] deal-1" in result.output
    assert "Band:" in result.output
    assert "Evidence coverage:" in result.output
    assert "Warnings: win_probability_suppressed" in result.output
    assert "Sensitive field check: passed" in result.output
    assert "raw_notes" not in result.output
    assert "secret raw note" not in result.output
    assert "contacts" not in result.output
    assert "summary_embedding" not in result.output
    assert mongo.write_count == 0


def test_smoke_deal_review_json_outputs_full_payload(monkeypatch) -> None:
    mongo = FakeMongo(
        [
            _deal("deal-1", company="Alpha Labs"),
            _deal("deal-2", company="Beta Works"),
        ]
    )
    monkeypatch.setattr(_context, "mongo", lambda: mongo)
    monkeypatch.setattr(_context, "config", lambda: {})

    result = CliRunner().invoke(
        app,
        [
            "smoke-deal-review",
            "--company",
            "alpha",
            "--as-of",
            "2026-06-10",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["count"] == 1
    assert payload["sensitive_field_check"]["ok"] is True
    assert payload["results"][0]["review"]["deal_id"] == "deal-1"
    encoded = json.dumps(payload, ensure_ascii=False)
    assert "raw_notes" not in encoded
    assert "secret raw note" not in encoded
    assert "contacts" not in encoded
    assert "summary_embedding" not in encoded
    assert mongo.write_count == 0


def test_smoke_deal_review_limit_selects_multiple_deals(monkeypatch) -> None:
    mongo = FakeMongo(
        [
            _deal("deal-1", company="Alpha Labs"),
            _deal("deal-2", company="Beta Works"),
            _deal("deal-3", company="Gamma Works"),
        ]
    )
    monkeypatch.setattr(_context, "mongo", lambda: mongo)
    monkeypatch.setattr(_context, "config", lambda: {})

    result = CliRunner().invoke(
        app,
        ["smoke-deal-review", "--limit", "2", "--as-of", "2026-06-10", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["count"] == 2
    assert [item["review"]["deal_id"] for item in payload["results"]] == [
        "deal-1",
        "deal-2",
    ]


def test_smoke_deal_review_not_found_returns_cli_error(monkeypatch) -> None:
    mongo = FakeMongo([_deal("deal-1", company="Alpha Labs")])
    monkeypatch.setattr(_context, "mongo", lambda: mongo)
    monkeypatch.setattr(_context, "config", lambda: {})

    result = CliRunner().invoke(
        app,
        ["smoke-deal-review", "--deal-id", "missing", "--as-of", "2026-06-10"],
    )

    assert result.exit_code == 1
    assert "Smoke failed: INVALID_INPUT (preflight)" in result.output
    assert "deal_id 'missing' not found" in result.output
    assert mongo.write_count == 0


def test_sensitive_key_detector_checks_keys_not_values() -> None:
    assert _contains_sensitive_result_key({"safe": "raw_notes"}) is False
    assert _contains_sensitive_result_key({"nested": [{"raw_notes": "secret"}]}) is True
