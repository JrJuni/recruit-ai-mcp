from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.validate_recruiting_smoke import EXPECTED_CONTRACT, validate_payload

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_recruiting_smoke.py"


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
                            "guardrail_risk_flags": ["work_authorization_mismatch"],
                            "guardrail_next_questions": [
                                "Confirm work authorization or sponsorship feasibility."
                            ],
                        },
                        {
                            "guardrail_candidate_id": "cand_jordan_lee",
                            "guardrail_risk_flags": ["client_exclusion"],
                            "guardrail_next_questions": [
                                "Confirm required skill: Python"
                            ],
                        },
                        {
                            "guardrail_candidate_id": "cand_iris_kim",
                            "guardrail_risk_flags": ["review_match_risk"],
                            "guardrail_next_questions": [
                                "Improve evidence for seniority_fit."
                            ],
                        },
                        {
                            "guardrail_candidate_id": "cand_eli_brooks",
                            "guardrail_risk_flags": ["high_match_risk"],
                            "guardrail_next_questions": [
                                "Confirm whether candidate is open to an IC mandate."
                            ],
                        },
                        {
                            "guardrail_candidate_id": "cand_sam_taylor",
                            "guardrail_risk_flags": ["client_preference_conflict"],
                            "guardrail_next_questions": [
                                "Review client preference conflict before shortlisting."
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
                                    "risk_flags": [],
                                    "next_questions": [],
                                },
                                {
                                    "candidate_id": "cand_jordan_lee",
                                    "risk_flags": [
                                        "missing production Python evidence"
                                    ],
                                    "next_questions": [
                                        "Confirm required skill: Python"
                                    ],
                                },
                                {
                                    "candidate_id": "cand_eli_brooks",
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
                                    "risk_flags": [],
                                    "next_questions": [
                                        "Confirm whether timing fits the search plan."
                                    ],
                                },
                                {
                                    "candidate_id": "cand_iris_kim",
                                    "risk_flags": [
                                        "needs senior mentorship for platform lead scope"
                                    ],
                                    "next_questions": [
                                        "Improve evidence for seniority_fit."
                                    ],
                                },
                                {
                                    "candidate_id": "cand_sam_taylor",
                                    "risk_flags": ["needs heavy role shaping"],
                                    "next_questions": [
                                        "Review client preference conflict before shortlisting."
                                    ],
                                },
                            ],
                        },
                    ],
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
