from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

EXPECTED_CONTRACT = {
    "ok": True,
    "question_count": 13,
    "candidate_count": 9,
    "written_record_count": 29,
    "reloaded_record_count": 29,
    "guardrail_candidate_count": 5,
    "open_position_count": 2,
    "positions_with_shortlist": 2,
}
_REQUIRED_QUESTIONS = (
    "rq01_recruiting_pipeline_metrics",
    "rq11_local_recruiting_persistence",
    "rq12_recommendation_guardrails",
    "rq13_client_shortlist_readiness",
)


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    questions = _questions_by_id(payload)
    metrics = _summary(questions, "rq01_recruiting_pipeline_metrics")
    persistence = _summary(questions, "rq11_local_recruiting_persistence")
    guardrails = _summary(questions, "rq12_recommendation_guardrails")
    shortlist = _summary(questions, "rq13_client_shortlist_readiness")
    actual = {
        "ok": _required_key(payload, "ok", scope="top-level payload"),
        "question_count": _required_key(
            payload,
            "question_count",
            scope="top-level payload",
        ),
        "candidate_count": _required_key(
            metrics,
            "candidate_count",
            scope="rq01_recruiting_pipeline_metrics summary",
        ),
        "written_record_count": _required_key(
            persistence,
            "written_record_count",
            scope="rq11_local_recruiting_persistence summary",
        ),
        "reloaded_record_count": _required_key(
            persistence,
            "reloaded_record_count",
            scope="rq11_local_recruiting_persistence summary",
        ),
        "guardrail_candidate_count": _required_key(
            guardrails,
            "guardrail_candidate_count",
            scope="rq12_recommendation_guardrails summary",
        ),
        "open_position_count": _required_key(
            shortlist,
            "open_position_count",
            scope="rq13_client_shortlist_readiness summary",
        ),
        "positions_with_shortlist": _required_key(
            shortlist,
            "positions_with_shortlist",
            scope="rq13_client_shortlist_readiness summary",
        ),
    }
    if actual != EXPECTED_CONTRACT:
        raise ValueError(
            "Recruiting natural-question smoke contract mismatch: "
            f"expected={EXPECTED_CONTRACT!r}, actual={actual!r}"
        )
    return actual


def _questions_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_questions = _required_key(payload, "questions", scope="top-level payload")
    if not isinstance(raw_questions, list):
        raise ValueError("Recruiting smoke payload field 'questions' must be a list.")
    questions = {
        item.get("id"): item
        for item in raw_questions
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    missing = [question_id for question_id in _REQUIRED_QUESTIONS if question_id not in questions]
    if missing:
        raise ValueError(
            "Recruiting smoke payload missing required question ids: "
            + ", ".join(missing)
        )
    return questions


def _summary(questions: dict[str, dict[str, Any]], question_id: str) -> dict[str, Any]:
    payload = _required_key(questions[question_id], "payload", scope=question_id)
    if not isinstance(payload, dict):
        raise ValueError(f"Recruiting smoke question {question_id} payload must be a mapping.")
    summary = _required_key(payload, "summary", scope=f"{question_id} payload")
    if not isinstance(summary, dict):
        raise ValueError(f"Recruiting smoke question {question_id} summary must be a mapping.")
    return summary


def _required_key(mapping: dict[str, Any], key: str, *, scope: str) -> Any:
    if key not in mapping:
        raise ValueError(f"Recruiting smoke {scope} missing required field {key!r}.")
    return mapping[key]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the Recruit AI natural-question smoke contract."
    )
    parser.add_argument("payload", type=Path)
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.payload.read_text(encoding="utf-8"))
        actual = validate_payload(payload)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps({"ok": True, "contract": actual}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
