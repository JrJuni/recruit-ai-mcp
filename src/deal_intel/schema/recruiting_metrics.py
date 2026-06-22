from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

from deal_intel.schema.recruiting import (
    CandidateProfile,
    ClientFeedback,
    Position,
    Submission,
)

_SUBMISSION_FUNNEL = (
    "draft",
    "submitted",
    "client_review",
    "interviewing",
    "offer",
    "placed",
)


def build_recruiting_pipeline_metrics(
    *,
    candidates: Iterable[CandidateProfile | dict[str, Any]] = (),
    positions: Iterable[Position | dict[str, Any]] = (),
    submissions: Iterable[Submission | dict[str, Any]] = (),
    feedback: Iterable[ClientFeedback | dict[str, Any]] = (),
) -> dict[str, Any]:
    """Build deterministic recruiting pipeline metrics from safe records."""

    candidate_rows = [_coerce_candidate(row) for row in candidates]
    position_rows = [_coerce_position(row) for row in positions]
    submission_rows = [_coerce_submission(row) for row in submissions]
    feedback_rows = [_coerce_feedback(row) for row in feedback]
    submission_status_counts = Counter(row.status for row in submission_rows)
    position_status_counts = Counter(row.status for row in position_rows)
    feedback_sentiment_counts = Counter(row.sentiment for row in feedback_rows)
    decision_signal_counts = Counter(row.decision_signal for row in feedback_rows)

    return {
        "ok": True,
        "summary": {
            "candidate_count": len(candidate_rows),
            "position_count": len(position_rows),
            "open_position_count": position_status_counts.get("open", 0),
            "submission_count": len(submission_rows),
            "feedback_count": len(feedback_rows),
            "active_submission_count": _active_submission_count(submission_status_counts),
            "placed_count": submission_status_counts.get("placed", 0),
        },
        "positions": {
            "by_status": _sorted_counts(position_status_counts),
            "open_rate": _rate(position_status_counts.get("open", 0), len(position_rows)),
        },
        "submissions": {
            "by_status": _sorted_counts(submission_status_counts),
            "funnel": _submission_funnel(submission_status_counts),
            "placed_rate": _rate(submission_status_counts.get("placed", 0), len(submission_rows)),
            "interview_rate": _rate(
                submission_status_counts.get("interviewing", 0)
                + submission_status_counts.get("offer", 0)
                + submission_status_counts.get("placed", 0),
                len(submission_rows),
            ),
        },
        "feedback": {
            "by_sentiment": _sorted_counts(feedback_sentiment_counts),
            "by_decision_signal": _sorted_counts(decision_signal_counts),
            "positive_rate": _rate(
                feedback_sentiment_counts.get("positive", 0),
                len(feedback_rows),
            ),
            "advance_rate": _rate(
                decision_signal_counts.get("advance", 0),
                len(feedback_rows),
            ),
        },
        "data_quality": _data_quality(
            candidates=candidate_rows,
            positions=position_rows,
            submissions=submission_rows,
            feedback=feedback_rows,
        ),
    }


def _submission_funnel(status_counts: Counter[str]) -> list[dict[str, Any]]:
    total = sum(status_counts.values())
    return [
        {
            "status": status,
            "count": status_counts.get(status, 0),
            "rate": _rate(status_counts.get(status, 0), total),
        }
        for status in _SUBMISSION_FUNNEL
    ]


def _active_submission_count(status_counts: Counter[str]) -> int:
    return sum(
        count
        for status, count in status_counts.items()
        if status not in {"rejected", "withdrawn", "paused"}
    )


def _data_quality(
    *,
    candidates: list[CandidateProfile],
    positions: list[Position],
    submissions: list[Submission],
    feedback: list[ClientFeedback],
) -> dict[str, Any]:
    return {
        "candidates_missing_skills": sum(1 for row in candidates if not row.skills),
        "candidates_missing_availability": sum(1 for row in candidates if not row.availability),
        "positions_missing_must_have": sum(1 for row in positions if not row.must_have),
        "positions_missing_compensation": sum(
            1 for row in positions if row.target_compensation is None
        ),
        "submissions_missing_fit_snapshot": sum(
            1 for row in submissions if row.fit_snapshot is None
        ),
        "feedback_missing_position_or_candidate": sum(
            1 for row in feedback if not row.position_id or not row.candidate_id
        ),
    }


def _sorted_counts(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _coerce_candidate(value: CandidateProfile | dict[str, Any]) -> CandidateProfile:
    if isinstance(value, CandidateProfile):
        return value
    return CandidateProfile.model_validate(_strip_mongo_id(value))


def _coerce_position(value: Position | dict[str, Any]) -> Position:
    if isinstance(value, Position):
        return value
    return Position.model_validate(_strip_mongo_id(value))


def _coerce_submission(value: Submission | dict[str, Any]) -> Submission:
    if isinstance(value, Submission):
        return value
    return Submission.model_validate(_strip_mongo_id(value))


def _coerce_feedback(value: ClientFeedback | dict[str, Any]) -> ClientFeedback:
    if isinstance(value, ClientFeedback):
        return value
    return ClientFeedback.model_validate(_strip_mongo_id(value))


def _strip_mongo_id(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "_id"}
