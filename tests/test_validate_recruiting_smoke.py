from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.validate_recruiting_smoke import EXPECTED_CONTRACT, validate_payload

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_recruiting_smoke.py"
GUARDRAIL_DIMENSION_SCORES = {
    "skill_fit": 5,
    "domain_fit": 5,
    "seniority_fit": 5,
    "compensation_fit": 5,
    "location_fit": 5,
    "availability_fit": 5,
    "client_preference_fit": 1,
    "risk": 2,
}


def _payload(
    *,
    candidate_count: int = EXPECTED_CONTRACT["candidate_count"],
) -> dict:
    return {
        "ok": EXPECTED_CONTRACT["ok"],
        "question_count": EXPECTED_CONTRACT["question_count"],
        "questions": [
            {
                "id": "rq01_recruiting_pipeline_metrics",
                "payload": {"summary": {"candidate_count": candidate_count}},
            },
            {
                "id": "rq03_positions_for_avery",
                "payload": {
                    "summary": {
                        "available_position_count": EXPECTED_CONTRACT[
                            "candidate_position_available_count"
                        ],
                        "excluded_position_count": EXPECTED_CONTRACT[
                            "candidate_position_excluded_count"
                        ],
                    }
                },
            },
            {
                "id": "rq11_local_recruiting_persistence",
                "payload": {
                    "summary": {
                        "written_record_count": EXPECTED_CONTRACT[
                            "written_record_count"
                        ],
                        "reloaded_record_count": EXPECTED_CONTRACT[
                            "reloaded_record_count"
                        ],
                    }
                },
            },
            {
                "id": "rq12_recommendation_guardrails",
                "payload": {
                    "summary": {
                        "guardrail_candidate_count": EXPECTED_CONTRACT[
                            "guardrail_candidate_count"
                        ],
                        "guardrails_with_risk_flags": EXPECTED_CONTRACT[
                            "guardrails_with_risk_flags"
                        ],
                        "guardrails_with_next_questions": EXPECTED_CONTRACT[
                            "guardrails_with_next_questions"
                        ],
                    },
                    "guardrails": [
                        {
                            "guardrail_candidate_id": "cand_nora_weiss",
                            "guardrail_dimension_scores": dict(GUARDRAIL_DIMENSION_SCORES),
                            "guardrail_risk_flags": ["work_authorization_mismatch"],
                            "guardrail_next_questions": [
                                "Confirm work authorization or sponsorship feasibility."
                            ],
                        },
                        {
                            "guardrail_candidate_id": "cand_jordan_lee",
                            "guardrail_dimension_scores": dict(GUARDRAIL_DIMENSION_SCORES),
                            "guardrail_risk_flags": ["client_exclusion"],
                            "guardrail_next_questions": [
                                "Confirm required skill: Python"
                            ],
                        },
                        {
                            "guardrail_candidate_id": "cand_iris_kim",
                            "guardrail_dimension_scores": dict(GUARDRAIL_DIMENSION_SCORES),
                            "guardrail_risk_flags": ["review_match_risk"],
                            "guardrail_next_questions": [
                                "Improve evidence for seniority_fit."
                            ],
                        },
                        {
                            "guardrail_candidate_id": "cand_eli_brooks",
                            "guardrail_dimension_scores": dict(GUARDRAIL_DIMENSION_SCORES),
                            "guardrail_risk_flags": ["high_match_risk"],
                            "guardrail_next_questions": [
                                "Confirm whether candidate is open to an IC mandate."
                            ],
                        },
                        {
                            "guardrail_candidate_id": "cand_sam_taylor",
                            "guardrail_dimension_scores": dict(GUARDRAIL_DIMENSION_SCORES),
                            "guardrail_risk_flags": ["client_preference_conflict"],
                            "guardrail_next_questions": [
                                "Review client preference conflict before shortlisting."
                            ],
                        },
                        {
                            "guardrail_candidate_id": "cand_riley_morgan",
                            "guardrail_dimension_scores": dict(GUARDRAIL_DIMENSION_SCORES),
                            "guardrail_risk_flags": ["retention_risk"],
                            "guardrail_next_questions": [
                                "Confirm retention or counteroffer mitigation plan."
                            ],
                        },
                        {
                            "guardrail_candidate_id": "cand_casey_stone",
                            "guardrail_dimension_scores": dict(GUARDRAIL_DIMENSION_SCORES),
                            "guardrail_risk_flags": ["evidence_gap"],
                            "guardrail_next_questions": [
                                "Confirm source evidence before shortlisting."
                            ],
                        },
                    ],
                },
            },
            {
                "id": "rq13_client_shortlist_readiness",
                "payload": {
                    "summary": {
                        "open_position_count": EXPECTED_CONTRACT[
                            "open_position_count"
                        ],
                        "positions_with_shortlist": EXPECTED_CONTRACT[
                            "positions_with_shortlist"
                        ],
                        "positions_with_review_risks": EXPECTED_CONTRACT[
                            "positions_with_review_risks"
                        ],
                        "positions_with_next_questions": EXPECTED_CONTRACT[
                            "positions_with_next_questions"
                        ],
                    },
                    "shortlists": [
                        {
                            "position_id": "pos_northstar_backend_lead",
                            "candidates": [
                                {
                                    "candidate_id": "cand_avery_chen",
                                    "dimension_scores": dict(GUARDRAIL_DIMENSION_SCORES),
                                    "risk_flags": [],
                                    "next_questions": [],
                                },
                                {
                                    "candidate_id": "cand_jordan_lee",
                                    "dimension_scores": dict(GUARDRAIL_DIMENSION_SCORES),
                                    "risk_flags": [
                                        "missing production Python evidence"
                                    ],
                                    "next_questions": [
                                        "Confirm required skill: Python"
                                    ],
                                },
                                {
                                    "candidate_id": "cand_eli_brooks",
                                    "dimension_scores": dict(GUARDRAIL_DIMENSION_SCORES),
                                    "risk_flags": ["requires manager scope"],
                                    "next_questions": [
                                        "Confirm compensation flexibility."
                                    ],
                                },
                            ],
                        },
                        {
                            "position_id": "pos_orbitpay_payments_lead",
                            "candidates": [
                                {
                                    "candidate_id": "cand_mateo_rivera",
                                    "dimension_scores": dict(GUARDRAIL_DIMENSION_SCORES),
                                    "risk_flags": [],
                                    "next_questions": [
                                        "Confirm whether timing fits the search plan."
                                    ],
                                },
                                {
                                    "candidate_id": "cand_riley_morgan",
                                    "dimension_scores": dict(GUARDRAIL_DIMENSION_SCORES),
                                    "risk_flags": [
                                        "retention_risk"
                                    ],
                                    "next_questions": [
                                        "Confirm retention or counteroffer mitigation plan."
                                    ],
                                },
                                {
                                    "candidate_id": "cand_iris_kim",
                                    "dimension_scores": dict(GUARDRAIL_DIMENSION_SCORES),
                                    "risk_flags": [
                                        "needs senior mentorship for platform lead scope"
                                    ],
                                    "next_questions": [
                                        "Improve evidence for seniority_fit."
                                    ],
                                },
                            ],
                        },
                    ],
                },
            },
            {
                "id": "rq14_recommendation_run_review",
                "payload": {
                    "summary": {
                        "result_count": EXPECTED_CONTRACT[
                            "saved_run_result_count"
                        ],
                        "feedback_adjustment_row_count": EXPECTED_CONTRACT[
                            "saved_run_feedback_adjustment_row_count"
                        ],
                        "risk_row_count": EXPECTED_CONTRACT[
                            "saved_run_risk_row_count"
                        ],
                        "next_question_row_count": EXPECTED_CONTRACT[
                            "saved_run_next_question_row_count"
                        ],
                    }
                },
            },
            {
                "id": "rq15_workflow_trace_safety",
                "payload": {
                    "summary": {
                        "event_count": EXPECTED_CONTRACT["trace_event_count"],
                        "invalid_event_count": EXPECTED_CONTRACT[
                            "trace_invalid_event_count"
                        ],
                        "redacted_marker_count": EXPECTED_CONTRACT[
                            "trace_redacted_marker_count"
                        ],
                        "forbidden_value_present": EXPECTED_CONTRACT[
                            "trace_forbidden_value_present"
                        ],
                    }
                },
            },
            {
                "id": "rq16_recruiting_report_export",
                "payload": {
                    "summary": {
                        "artifact_count": EXPECTED_CONTRACT[
                            "report_export_artifact_count"
                        ],
                        "csv_exists": EXPECTED_CONTRACT[
                            "report_export_csv_exists"
                        ],
                        "markdown_exists": EXPECTED_CONTRACT[
                            "report_export_markdown_exists"
                        ],
                        "forbidden_term_present": EXPECTED_CONTRACT[
                            "report_export_forbidden_term_present"
                        ],
                    }
                },
            },
        ],
    }


def test_validate_recruiting_smoke_accepts_current_contract() -> None:
    assert validate_payload(_payload()) == EXPECTED_CONTRACT


def test_validate_recruiting_smoke_cli_fails_on_contract_mismatch(tmp_path) -> None:
    payload_path = tmp_path / "recruiting-natural-questions.json"
    mismatched_count = EXPECTED_CONTRACT["candidate_count"] - 1
    payload_path.write_text(
        json.dumps(_payload(candidate_count=mismatched_count)),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(payload_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Recruiting natural-question smoke contract mismatch" in result.stderr
    assert f"'candidate_count': {EXPECTED_CONTRACT['candidate_count']}" in result.stderr
    assert f"'candidate_count': {mismatched_count}" in result.stderr


def test_validate_recruiting_smoke_cli_names_missing_question(tmp_path) -> None:
    payload = _payload()
    payload["questions"] = [
        question
        for question in payload["questions"]
        if question["id"] != "rq12_recommendation_guardrails"
    ]
    payload_path = tmp_path / "recruiting-natural-questions.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(payload_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "missing required question ids" in result.stderr
    assert "rq12_recommendation_guardrails" in result.stderr


def test_validate_recruiting_smoke_cli_names_missing_summary_field(tmp_path) -> None:
    payload = _payload()
    persistence = next(
        question
        for question in payload["questions"]
        if question["id"] == "rq11_local_recruiting_persistence"
    )
    del persistence["payload"]["summary"]["reloaded_record_count"]
    payload_path = tmp_path / "recruiting-natural-questions.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(payload_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "rq11_local_recruiting_persistence summary" in result.stderr
    assert "reloaded_record_count" in result.stderr


def test_validate_recruiting_smoke_cli_fails_without_guardrail_evidence(tmp_path) -> None:
    payload = _payload()
    guardrails = next(
        question
        for question in payload["questions"]
        if question["id"] == "rq12_recommendation_guardrails"
    )
    for row in guardrails["payload"]["guardrails"][0:2]:
        row["guardrail_risk_flags"] = []
        row["guardrail_next_questions"] = []
    payload_path = tmp_path / "recruiting-natural-questions.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(payload_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Recruiting natural-question smoke contract mismatch" in result.stderr
    assert "'guardrail_risk_row_count': 5" in result.stderr
    assert "'guardrail_next_question_row_count': 5" in result.stderr


def test_validate_recruiting_smoke_cli_fails_without_guardrail_dimensions(tmp_path) -> None:
    payload = _payload()
    guardrails = next(
        question
        for question in payload["questions"]
        if question["id"] == "rq12_recommendation_guardrails"
    )
    del guardrails["payload"]["guardrails"][0]["guardrail_dimension_scores"]["risk"]
    payload_path = tmp_path / "recruiting-natural-questions.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(payload_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "guardrail_dimension_scores missing risk" in result.stderr


def test_validate_recruiting_smoke_cli_fails_without_shortlist_evidence(tmp_path) -> None:
    payload = _payload()
    shortlist = next(
        question
        for question in payload["questions"]
        if question["id"] == "rq13_client_shortlist_readiness"
    )
    for row in shortlist["payload"]["shortlists"][0]["candidates"]:
        row["risk_flags"] = []
        row["next_questions"] = []
    payload_path = tmp_path / "recruiting-natural-questions.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(payload_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Recruiting natural-question smoke contract mismatch" in result.stderr
    assert "'shortlist_risk_row_count': 4" in result.stderr
    assert "'shortlist_next_question_row_count': 5" in result.stderr


def test_validate_recruiting_smoke_cli_fails_without_shortlist_dimensions(tmp_path) -> None:
    payload = _payload()
    shortlist = next(
        question
        for question in payload["questions"]
        if question["id"] == "rq13_client_shortlist_readiness"
    )
    del shortlist["payload"]["shortlists"][0]["candidates"][0]["dimension_scores"][
        "skill_fit"
    ]
    payload_path = tmp_path / "recruiting-natural-questions.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(payload_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Recruiting smoke rq13 dimension_scores missing skill_fit" in result.stderr
