from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

from typer.testing import CliRunner

from deal_intel import _context
from deal_intel.cli import _audit_deal_review_quality, _contains_sensitive_result_key, app
from scripts.validate_recruiting_smoke import EXPECTED_CONTRACT

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
    def __init__(self, deals: list[dict], snapshots: list[dict] | None = None) -> None:
        self.deals = deepcopy(deals)
        self.snapshots = deepcopy(snapshots or [])
        self.read_count = 0
        self.write_count = 0

    def list_deals_for_metrics(self) -> list[dict]:
        self.read_count += 1
        return deepcopy(self.deals)

    def list_analytics_snapshots(
        self,
        *,
        start_date: str,
        end_date: str,
        stage: str | None = None,
        industry: str | None = None,
    ) -> list[dict]:
        self.read_count += 1
        return [
            deepcopy(snapshot)
            for snapshot in self.snapshots
            if start_date <= str(snapshot.get("as_of") or "") <= end_date
            and (stage is None or snapshot.get("deal_stage") == stage)
            and (industry is None or snapshot.get("industry") == industry)
        ]

    def upsert_deal(self, deal: dict) -> None:
        self.write_count += 1
        raise AssertionError("smoke-deal-review must be read-only")


def _deal(
    deal_id: str,
    *,
    company: str,
    stage: str = "proposal",
    health_pct: float = 86.5,
    filled_count: int = 7,
    actual_close_date: str | None = None,
    close_reason: str | None = None,
) -> dict:
    scores = {
        dim: {"score": 4.5, "trend": None}
        for dim in MEDDPICC_DIMS[:filled_count]
    }
    return {
        "deal_id": deal_id,
        "company": company,
        "industry": "IT",
        "deal_stage": stage,
        "deal_size_amount": 72_000_000,
        "deal_size_status": "quoted",
        "expected_close_date": "2026-06-30",
        "expected_close_date_source": "user_provided",
        "stage_history": [
            {"stage": stage, "entered_at": "2026-06-01T00:00:00+00:00"}
        ],
        "actual_close_date": actual_close_date,
        "close_reason": close_reason,
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
        "customer_themes": [
            {
                "theme_key": "compliance_security",
                "label": "규제·보안·컴플라이언스",
                "dimension": "decision_criteria",
                "evidence": "audit log export is mandatory",
                "importance": 5,
                "meeting_id": "m1",
                "meeting_date": "2026-06-01",
            }
        ],
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


def test_smoke_deal_review_audit_text_outputs_quality_summary(monkeypatch) -> None:
    mongo = FakeMongo(
        [
            _deal("deal-1", company="Alpha Labs"),
            _deal("deal-2", company="Beta Works", filled_count=2),
        ]
    )
    monkeypatch.setattr(_context, "mongo", lambda: mongo)
    monkeypatch.setattr(_context, "config", lambda: {})

    result = CliRunner().invoke(
        app,
        ["smoke-deal-review-audit", "--as-of", "2026-06-10", "--limit", "10"],
    )

    assert result.exit_code == 0
    assert "Deal Review Audit (as_of=2026-06-10, reviewed=2)" in result.output
    assert "Sensitive field check: passed" in result.output
    assert "Quality rules: passed" in result.output
    assert "Alert levels:" in result.output
    assert "Uncertainty:" in result.output
    assert "Top review targets:" in result.output
    assert "raw_notes" not in result.output
    assert "secret raw note" not in result.output
    assert "contacts" not in result.output
    assert "summary_embedding" not in result.output
    assert mongo.write_count == 0


def test_smoke_deal_review_audit_json_filters_and_counts(monkeypatch) -> None:
    mongo = FakeMongo(
        [
            _deal("deal-1", company="Alpha Labs", stage="proposal"),
            _deal("deal-2", company="Beta Works", stage="discovery"),
            _deal(
                "deal-3",
                company="Closed Lost",
                stage="lost",
                actual_close_date="2026-06-05",
                close_reason="No budget",
            ),
        ]
    )
    monkeypatch.setattr(_context, "mongo", lambda: mongo)
    monkeypatch.setattr(_context, "config", lambda: {})

    result = CliRunner().invoke(
        app,
        [
            "smoke-deal-review-audit",
            "--stage",
            "proposal",
            "--as-of",
            "2026-06-10",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["filters"]["stage"] == "proposal"
    assert payload["summary"]["reviewed_count"] == 1
    assert payload["summary"]["quality_issue_count"] == 0
    assert payload["deals"][0]["deal_id"] == "deal-1"
    encoded = json.dumps(payload, ensure_ascii=False)
    assert "raw_notes" not in encoded
    assert "contacts" not in encoded
    assert "summary_embedding" not in encoded
    assert mongo.write_count == 0


def test_smoke_deal_review_audit_invalid_stage_fails_before_storage(monkeypatch) -> None:
    mongo = FakeMongo([_deal("deal-1", company="Alpha Labs")])
    monkeypatch.setattr(_context, "mongo", lambda: mongo)
    monkeypatch.setattr(_context, "config", lambda: {})

    result = CliRunner().invoke(
        app,
        ["smoke-deal-review-audit", "--stage", "bad-stage", "--as-of", "2026-06-10"],
    )

    assert result.exit_code == 1
    assert "Smoke failed: INVALID_INPUT (preflight)" in result.output
    assert mongo.read_count == 0
    assert mongo.write_count == 0


def test_deal_review_audit_quality_rules_detect_broken_review_payload() -> None:
    review = {
        "deal_stage": "proposal",
        "health_interpretation": {
            "health_band": "healthy",
            "evidence_coverage_pct": 25.0,
            "review_band": "verified_healthy",
            "alert_level": "none",
            "uncertainty_level": "low",
        },
        "warnings": [],
        "missing_information": [],
        "confirmed_risks": [
            {"risk_id": "forecast:rough_estimate", "severity": "watch"}
        ],
        "recommended_questions": ["이 딜의 수주 확률은 80%인가요?"],
        "recommended_actions": ["review_forecast_basis"],
    }

    issue_ids = {
        issue["issue_id"] for issue in _audit_deal_review_quality(review)
    }

    assert "missing_win_probability_suppression" in issue_ids
    assert "overconfidence_warning_missing" in issue_ids
    assert "verified_healthy_with_low_coverage" in issue_ids
    assert "risk_rows_without_attention_level" in issue_ids
    assert "percent_estimate_in_guidance" in issue_ids


def test_deal_review_audit_quality_rules_require_closed_gap_reporting() -> None:
    review = {
        "deal_stage": "lost",
        "health_interpretation": {
            "health_band": "unassessed",
            "evidence_coverage_pct": 0.0,
            "review_band": "insufficient_evidence",
            "alert_level": "info",
            "uncertainty_level": "high",
        },
        "warnings": ["win_probability_suppressed", "insufficient_evidence"],
        "missing_information": [],
        "confirmed_risks": [],
        "recommended_questions": [],
        "recommended_actions": [],
    }

    issue_ids = {
        issue["issue_id"] for issue in _audit_deal_review_quality(review)
    }

    assert "closed_actual_close_gap_not_reported" in issue_ids
    assert "lost_close_reason_gap_not_reported" in issue_ids


def test_deal_review_audit_accepts_structured_uncertainty_reasons() -> None:
    review = {
        "deal_stage": "proposal",
        "review_version": "v2",
        "assessment": {},
        "health_interpretation": {
            "health_band": "healthy",
            "evidence_coverage_pct": 35.0,
            "review_band": "promising_but_unproven",
            "alert_level": "watch",
            "uncertainty_level": "high",
        },
        "warnings": ["win_probability_suppressed", "overconfidence_warning"],
        "missing_information": [],
        "uncertainty_reasons": [
            {
                "reason_id": "low_qualification_coverage",
                "field": "qualification",
                "severity": "high",
                "reason": "Only a small portion of evidence is known.",
            }
        ],
        "confirmed_risks": [],
        "recommended_questions": [],
        "recommended_actions": [],
        "data_quality": {"is_confirmed_complete": False},
    }

    issue_ids = {
        issue["issue_id"] for issue in _audit_deal_review_quality(review)
    }

    assert "high_uncertainty_without_gap_or_warning" not in issue_ids


def test_deal_review_audit_allows_terminal_risks_without_next_actions() -> None:
    review = {
        "deal_stage": "lost",
        "review_version": "v2",
        "assessment": {},
        "health_interpretation": {
            "health_band": "watch",
            "evidence_coverage_pct": 80.0,
            "review_band": "watch_with_evidence",
            "alert_level": "watch",
            "uncertainty_level": "medium",
        },
        "warnings": ["win_probability_suppressed", "confirmed_risk_present"],
        "missing_information": [],
        "confirmed_risks": [
            {"risk_id": "platform_fit", "severity": "watch"},
        ],
        "recommended_questions": [],
        "recommended_actions": [],
        "data_quality": {"is_confirmed_complete": True},
    }

    issue_ids = {
        issue["issue_id"] for issue in _audit_deal_review_quality(review)
    }

    assert "confirmed_risks_without_actions" not in issue_ids


def test_smoke_natural_questions_writes_pack(monkeypatch, tmp_path) -> None:
    mongo = FakeMongo(
        [
            _deal("deal-1", company="페이브릿지", stage="proposal"),
            _deal("deal-2", company="Beta Works", stage="discovery", filled_count=4),
            _deal("deal-3", company="Closed Lost", stage="lost"),
        ]
    )
    monkeypatch.setattr(_context, "mongo", lambda: mongo)
    monkeypatch.setattr(_context, "config", lambda: {})
    output_dir = tmp_path / "natural-pack"

    result = CliRunner().invoke(
        app,
        [
            "smoke-natural-questions",
            "--as-of",
            "2026-06-10",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Natural Question Smoke (as_of=2026-06-10, questions=12)" in result.output
    assert "OK: True" in result.output
    assert "Sensitive failures: none" in result.output
    assert (output_dir / "summary.md").exists()
    summary_markdown = (output_dir / "summary.md").read_text(encoding="utf-8")
    assert "## Source Evidence" in summary_markdown
    assert "Meeting" in summary_markdown
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["ok"] is True
    assert summary["question_count"] == 12
    assert summary["answerability_counts"] == {"derived": 6, "direct": 6}
    assert (output_dir / "q01_pipeline_health.json").exists()
    assert (output_dir / "q08_theme_evidence_drilldown.json").exists()
    assert (output_dir / "q09_interaction_source_evidence.json").exists()
    assert (output_dir / "q10_pipeline_trend.json").exists()
    assert (output_dir / "q11_deal_review_actionability.json").exists()
    assert (output_dir / "q12_interaction_source_coverage.json").exists()
    encoded = json.dumps(summary, ensure_ascii=False)
    assert "raw_notes" not in encoded
    assert "secret raw note" not in encoded
    assert "contacts" not in encoded
    assert "summary_embedding" not in encoded
    assert mongo.write_count == 0


def test_smoke_natural_questions_json_outputs_artifact_path(monkeypatch, tmp_path) -> None:
    mongo = FakeMongo([_deal("deal-1", company="페이브릿지")])
    monkeypatch.setattr(_context, "mongo", lambda: mongo)
    monkeypatch.setattr(_context, "config", lambda: {})
    output_dir = tmp_path / "natural-pack"

    result = CliRunner().invoke(
        app,
        [
            "smoke-natural-questions",
            "--as-of",
            "2026-06-10",
            "--output-dir",
            str(output_dir),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["output_dir"] == str(output_dir.resolve())
    assert [row["id"] for row in payload["questions"]][-1] == (
        "q12_interaction_source_coverage"
    )
    assert (output_dir / "summary.md").exists()
    assert mongo.write_count == 0


def test_smoke_natural_questions_recruiting_pack_writes_artifacts(
    monkeypatch,
    tmp_path,
) -> None:
    mongo = FakeMongo([_deal("deal-1", company="페이브릿지")])
    monkeypatch.setattr(_context, "mongo", lambda: mongo)
    monkeypatch.setattr(_context, "config", lambda: {})
    output_dir = tmp_path / "recruiting-natural-pack"

    result = CliRunner().invoke(
        app,
        [
            "smoke-natural-questions",
            "--pack",
            "recruiting",
            "--as-of",
            "2026-06-22",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Natural Question Smoke (as_of=2026-06-22, questions=13)" in result.output
    assert "OK: True" in result.output
    assert "candidates=9, open_positions=2, submissions=4" in result.output
    assert "open_positions=2, shortlists=2, risk_reviews=2" in result.output
    assert (output_dir / "summary.md").exists()
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["ok"] is True
    assert summary["pack"] == "recruiting"
    assert summary["question_count"] == 13
    assert summary["answerability_counts"] == {"derived": 9, "direct": 4}
    validator = Path(__file__).resolve().parents[1] / "scripts" / (
        "validate_recruiting_smoke.py"
    )
    contract = subprocess.run(
        [sys.executable, str(validator), str(output_dir / "summary.json")],
        check=True,
        capture_output=True,
        text=True,
    )
    contract_payload = json.loads(contract.stdout)
    assert contract_payload["contract"] == EXPECTED_CONTRACT
    assert (output_dir / "rq01_recruiting_pipeline_metrics.json").exists()
    assert (output_dir / "rq02_candidates_for_northstar_backend.json").exists()
    assert (output_dir / "rq03_positions_for_avery.json").exists()
    position_recommendations = json.loads(
        (output_dir / "rq02_candidates_for_northstar_backend.json").read_text(
            encoding="utf-8"
        )
    )
    top_candidate = position_recommendations["run"]["results"][0]
    assert top_candidate["target_id"] == "cand_avery_chen"
    assert {
        (row["feedback_id"], row["dimension"])
        for row in top_candidate["feedback_adjustments"]
    } == {
        ("fb_avery_northstar_advance", "domain_fit"),
        ("fb_avery_northstar_advance", "client_preference_fit"),
    }
    candidate_recommendations = json.loads(
        (output_dir / "rq03_positions_for_avery.json").read_text(encoding="utf-8")
    )
    assert candidate_recommendations["summary"] == {
        "candidate_id": "cand_avery_chen",
        "position_status": "open",
        "available_position_count": 2,
        "excluded_position_count": 1,
        "excluded_position_ids": ["pos_northstar_data_manager"],
    }
    assert {
        row["target_id"] for row in candidate_recommendations["run"]["results"]
    } == {"pos_northstar_backend_lead", "pos_orbitpay_payments_lead"}
    assert "pos_northstar_data_manager" not in {
        row["target_id"] for row in candidate_recommendations["run"]["results"]
    }
    assert (output_dir / "rq08_local_recruiting_data_safety.json").exists()
    assert (output_dir / "rq09_recruiting_intake_coverage.json").exists()
    assert (output_dir / "rq10_recruiting_report_preview.json").exists()
    assert (output_dir / "rq11_local_recruiting_persistence.json").exists()
    assert (output_dir / "rq12_recommendation_guardrails.json").exists()
    guardrails = json.loads(
        (output_dir / "rq12_recommendation_guardrails.json").read_text(
            encoding="utf-8"
        )
    )
    assert guardrails["summary"] == {
        "guardrail_candidate_count": 5,
        "ranking_guardrails_passed": True,
    }
    assert {
        row["guardrail_candidate_id"] for row in guardrails["guardrails"]
    } == {
        "cand_nora_weiss",
        "cand_jordan_lee",
        "cand_iris_kim",
        "cand_eli_brooks",
        "cand_sam_taylor",
    }
    guardrail_by_candidate = {
        row["guardrail_candidate_id"]: row for row in guardrails["guardrails"]
    }
    nora_guardrail = guardrail_by_candidate["cand_nora_weiss"]
    assert nora_guardrail["guardrail_dimension_scores"]["availability_fit"] == 2
    assert nora_guardrail["guardrail_dimension_scores"]["location_fit"] == 1
    assert nora_guardrail["guardrail_dimension_scores"]["risk"] == 5
    assert "Confirm work authorization or sponsorship feasibility." in (
        nora_guardrail["guardrail_next_questions"]
    )
    assert "Confirm whether timing fits the search plan." in (
        nora_guardrail["guardrail_next_questions"]
    )
    jordan_guardrail = guardrail_by_candidate["cand_jordan_lee"]
    assert jordan_guardrail["guardrail_dimension_scores"]["skill_fit"] == 2
    assert "Confirm required skill: Python" in (
        jordan_guardrail["guardrail_next_questions"]
    )
    assert "Confirm required skill: data platforms" in (
        jordan_guardrail["guardrail_next_questions"]
    )
    eli_guardrail = guardrail_by_candidate["cand_eli_brooks"]
    assert eli_guardrail["guardrail_dimension_scores"]["client_preference_fit"] == 1
    assert "Confirm whether candidate is open to an IC mandate." in (
        eli_guardrail["guardrail_next_questions"]
    )
    assert (output_dir / "rq13_client_shortlist_readiness.json").exists()
    shortlist = json.loads(
        (output_dir / "rq13_client_shortlist_readiness.json").read_text(
            encoding="utf-8"
        )
    )
    assert shortlist["summary"] == {
        "open_position_count": 2,
        "positions_with_shortlist": 2,
        "positions_with_review_risks": 2,
        "positions_with_next_questions": 2,
    }
    assert [row["top_candidate_id"] for row in shortlist["shortlists"]] == [
        "cand_avery_chen",
        "cand_mateo_rivera",
    ]
    encoded = json.dumps(summary, ensure_ascii=False)
    assert "raw_content" not in encoded
    assert "contacts" not in encoded
    assert "summary_embedding" not in encoded
    assert mongo.write_count == 0


def test_smoke_natural_questions_recruiting_pack_json(monkeypatch, tmp_path) -> None:
    def fail_context() -> None:
        raise AssertionError("recruiting pack should not require runtime storage config")

    monkeypatch.setattr(_context, "mongo", fail_context)
    monkeypatch.setattr(_context, "config", fail_context)
    output_dir = tmp_path / "recruiting-natural-pack"

    result = CliRunner().invoke(
        app,
        [
            "smoke-natural-questions",
            "--pack",
            "recruiting",
            "--as-of",
            "2026-06-22",
            "--output-dir",
            str(output_dir),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["pack"] == "recruiting"
    assert payload["output_dir"] == str(output_dir.resolve())
    assert [row["id"] for row in payload["questions"]] == [
        "rq01_recruiting_pipeline_metrics",
        "rq02_candidates_for_northstar_backend",
        "rq03_positions_for_avery",
        "rq04_feedback_adjustment_signal",
        "rq05_active_submission_next_steps",
        "rq06_client_preference_learning",
        "rq07_candidate_risk_flags",
        "rq08_local_recruiting_data_safety",
        "rq09_recruiting_intake_coverage",
        "rq10_recruiting_report_preview",
        "rq11_local_recruiting_persistence",
        "rq12_recommendation_guardrails",
        "rq13_client_shortlist_readiness",
    ]


def test_smoke_natural_questions_default_output_dir_uses_user_home(
    monkeypatch,
    tmp_path,
) -> None:
    mongo = FakeMongo([_deal("deal-1", company="페이브릿지")])
    monkeypatch.setattr(_context, "mongo", lambda: mongo)
    monkeypatch.setattr(_context, "config", lambda: {})
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "smoke-natural-questions",
            "--as-of",
            "2026-06-10",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    output_dir = Path(payload["output_dir"])
    assert output_dir.parent == tmp_path / ".recruit-ai" / "smoke"
    assert output_dir.name.startswith("natural-question-pack-")
    assert (output_dir / "summary.md").exists()
    assert mongo.write_count == 0
