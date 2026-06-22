from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.validate_recruiting_smoke import validate_payload

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_recruiting_smoke.py"


def _payload(*, candidate_count: int = 8) -> dict:
    return {
        "ok": True,
        "question_count": 13,
        "questions": [
            {
                "id": "rq01_recruiting_pipeline_metrics",
                "payload": {"summary": {"candidate_count": candidate_count}},
            },
            {
                "id": "rq11_local_recruiting_persistence",
                "payload": {
                    "summary": {
                        "written_record_count": 27,
                        "reloaded_record_count": 27,
                    }
                },
            },
            {
                "id": "rq12_recommendation_guardrails",
                "payload": {"summary": {"guardrail_candidate_count": 4}},
            },
            {
                "id": "rq13_client_shortlist_readiness",
                "payload": {
                    "summary": {
                        "open_position_count": 2,
                        "positions_with_shortlist": 2,
                    }
                },
            },
        ],
    }


def test_validate_recruiting_smoke_accepts_current_contract() -> None:
    assert validate_payload(_payload()) == {
        "ok": True,
        "question_count": 13,
        "candidate_count": 8,
        "written_record_count": 27,
        "reloaded_record_count": 27,
        "guardrail_candidate_count": 4,
        "open_position_count": 2,
        "positions_with_shortlist": 2,
    }


def test_validate_recruiting_smoke_cli_fails_on_contract_mismatch(tmp_path) -> None:
    payload_path = tmp_path / "recruiting-natural-questions.json"
    payload_path.write_text(json.dumps(_payload(candidate_count=7)), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(payload_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Recruiting natural-question smoke contract mismatch" in result.stderr
    assert "'candidate_count': 8" in result.stderr
    assert "'candidate_count': 7" in result.stderr


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
