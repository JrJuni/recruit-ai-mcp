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
    "guardrails_with_risk_flags": 5,
    "guardrails_with_next_questions": 5,
    "guardrail_risk_row_count": 5,
    "guardrail_next_question_row_count": 5,
    "guardrail_dimension_score_row_count": 5,
    "candidate_position_available_count": 2,
    "candidate_position_excluded_count": 1,
    "open_position_count": 2,
    "positions_with_shortlist": 2,
    "positions_with_review_risks": 2,
    "positions_with_next_questions": 2,
    "shortlist_risk_row_count": 4,
    "shortlist_next_question_row_count": 5,
}
_REQUIRED_QUESTIONS = (
    "rq01_recruiting_pipeline_metrics",
    "rq03_positions_for_avery",
    "rq11_local_recruiting_persistence",
    "rq12_recommendation_guardrails",
    "rq13_client_shortlist_readiness",
)
_REQUIRED_FIT_DIMENSIONS = (
    "skill_fit",
    "domain_fit",
    "seniority_fit",
    "compensation_fit",
    "location_fit",
    "availability_fit",
    "client_preference_fit",
    "risk",
)


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    questions = _questions_by_id(payload)
    metrics = _summary(questions, "rq01_recruiting_pipeline_metrics")
    candidate_positions = _summary(questions, "rq03_positions_for_avery")
    persistence = _summary(questions, "rq11_local_recruiting_persistence")
    guardrail_payload = _question_payload(questions, "rq12_recommendation_guardrails")
    guardrails = _summary_from_payload(
        guardrail_payload,
        question_id="rq12_recommendation_guardrails",
    )
    shortlist_payload = _question_payload(questions, "rq13_client_shortlist_readiness")
    shortlist = _summary_from_payload(
        shortlist_payload,
        question_id="rq13_client_shortlist_readiness",
    )
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
        "guardrails_with_risk_flags": _required_key(
            guardrails,
            "guardrails_with_risk_flags",
            scope="rq12_recommendation_guardrails summary",
        ),
        "guardrails_with_next_questions": _required_key(
            guardrails,
            "guardrails_with_next_questions",
            scope="rq12_recommendation_guardrails summary",
        ),
        "guardrail_risk_row_count": _guardrail_row_count(
            guardrail_payload,
            field="guardrail_risk_flags",
        ),
        "guardrail_next_question_row_count": _guardrail_row_count(
            guardrail_payload,
            field="guardrail_next_questions",
        ),
        "guardrail_dimension_score_row_count": _guardrail_dimension_score_row_count(
            guardrail_payload
        ),
        "candidate_position_available_count": _required_key(
            candidate_positions,
            "available_position_count",
            scope="rq03_positions_for_avery summary",
        ),
        "candidate_position_excluded_count": _required_key(
            candidate_positions,
            "excluded_position_count",
            scope="rq03_positions_for_avery summary",
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
        "positions_with_review_risks": _required_key(
            shortlist,
            "positions_with_review_risks",
            scope="rq13_client_shortlist_readiness summary",
        ),
        "positions_with_next_questions": _required_key(
            shortlist,
            "positions_with_next_questions",
            scope="rq13_client_shortlist_readiness summary",
        ),
        "shortlist_risk_row_count": _shortlist_row_count(
            shortlist_payload,
            field="risk_flags",
        ),
        "shortlist_next_question_row_count": _shortlist_row_count(
            shortlist_payload,
            field="next_questions",
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
    payload = _question_payload(questions, question_id)
    return _summary_from_payload(payload, question_id=question_id)


def _question_payload(
    questions: dict[str, dict[str, Any]],
    question_id: str,
) -> dict[str, Any]:
    payload = _required_key(questions[question_id], "payload", scope=question_id)
    if not isinstance(payload, dict):
        raise ValueError(f"Recruiting smoke question {question_id} payload must be a mapping.")
    return payload


def _summary_from_payload(payload: dict[str, Any], *, question_id: str) -> dict[str, Any]:
    summary = _required_key(payload, "summary", scope=f"{question_id} payload")
    if not isinstance(summary, dict):
        raise ValueError(f"Recruiting smoke question {question_id} summary must be a mapping.")
    return summary


def _shortlist_row_count(payload: dict[str, Any], *, field: str) -> int:
    shortlists = _required_key(
        payload,
        "shortlists",
        scope="rq13_client_shortlist_readiness payload",
    )
    if not isinstance(shortlists, list):
        raise ValueError("Recruiting smoke rq13 shortlists must be a list.")
    count = 0
    for shortlist_index, shortlist in enumerate(shortlists):
        if not isinstance(shortlist, dict):
            raise ValueError(
                "Recruiting smoke rq13 shortlist rows must be mappings."
            )
        candidates = _required_key(
            shortlist,
            "candidates",
            scope=f"rq13_client_shortlist_readiness shortlist {shortlist_index}",
        )
        if not isinstance(candidates, list):
            raise ValueError(
                "Recruiting smoke rq13 shortlist candidates must be a list."
            )
        for candidate_index, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                raise ValueError(
                    "Recruiting smoke rq13 candidate rows must be mappings."
                )
            values = _required_key(
                candidate,
                field,
                scope=(
                    "rq13_client_shortlist_readiness "
                    f"candidate {candidate_index}"
                ),
            )
            if not isinstance(values, list):
                raise ValueError(
                    "Recruiting smoke rq13 candidate "
                    f"field {field!r} must be a list."
                )
            if values:
                count += 1
    return count


def _guardrail_row_count(payload: dict[str, Any], *, field: str) -> int:
    guardrails = _required_key(
        payload,
        "guardrails",
        scope="rq12_recommendation_guardrails payload",
    )
    if not isinstance(guardrails, list):
        raise ValueError("Recruiting smoke rq12 guardrails must be a list.")
    count = 0
    for guardrail_index, guardrail in enumerate(guardrails):
        if not isinstance(guardrail, dict):
            raise ValueError("Recruiting smoke rq12 guardrail rows must be mappings.")
        values = _required_key(
            guardrail,
            field,
            scope=f"rq12_recommendation_guardrails guardrail {guardrail_index}",
        )
        if not isinstance(values, list):
            raise ValueError(
                "Recruiting smoke rq12 guardrail "
                f"field {field!r} must be a list."
            )
        if values:
            count += 1
    return count


def _guardrail_dimension_score_row_count(payload: dict[str, Any]) -> int:
    guardrails = _required_key(
        payload,
        "guardrails",
        scope="rq12_recommendation_guardrails payload",
    )
    if not isinstance(guardrails, list):
        raise ValueError("Recruiting smoke rq12 guardrails must be a list.")
    count = 0
    for guardrail_index, guardrail in enumerate(guardrails):
        if not isinstance(guardrail, dict):
            raise ValueError("Recruiting smoke rq12 guardrail rows must be mappings.")
        scores = _required_key(
            guardrail,
            "guardrail_dimension_scores",
            scope=f"rq12_recommendation_guardrails guardrail {guardrail_index}",
        )
        if not isinstance(scores, dict):
            raise ValueError(
                "Recruiting smoke rq12 guardrail_dimension_scores must be a mapping."
            )
        missing = [
            dimension
            for dimension in _REQUIRED_FIT_DIMENSIONS
            if dimension not in scores
        ]
        if missing:
            raise ValueError(
                "Recruiting smoke rq12 guardrail_dimension_scores missing "
                + ", ".join(missing)
            )
        count += 1
    return count


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
