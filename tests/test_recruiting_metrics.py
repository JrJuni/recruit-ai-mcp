from __future__ import annotations

from deal_intel.schema.recruiting import CompensationExpectation
from deal_intel.schema.recruiting_metrics import build_recruiting_pipeline_metrics


def _candidate(candidate_id: str, *, missing: bool = False) -> dict:
    return {
        "candidate_id": candidate_id,
        "name": "Avery Chen",
        "skills": [] if missing else ["Python", "MongoDB"],
        "availability": "" if missing else "30 days",
    }


def _position(position_id: str, *, status: str = "open", missing: bool = False) -> dict:
    return {
        "position_id": position_id,
        "client_company_id": "client_acme",
        "title": "Backend Lead",
        "status": status,
        "must_have": [] if missing else ["Python"],
        "target_compensation": None
        if missing
        else CompensationExpectation(maximum=200000).model_dump(mode="json"),
    }


def _submission(submission_id: str, *, status: str, fit_snapshot: dict | None = None) -> dict:
    return {
        "submission_id": submission_id,
        "candidate_id": "cand_avery",
        "position_id": "pos_backend",
        "status": status,
        "fit_snapshot": fit_snapshot,
    }


def _feedback(
    feedback_id: str,
    *,
    sentiment: str,
    decision_signal: str,
    missing_links: bool = False,
) -> dict:
    return {
        "feedback_id": feedback_id,
        "subject_type": "submission",
        "subject_id": "sub_1",
        "position_id": None if missing_links else "pos_backend",
        "candidate_id": None if missing_links else "cand_avery",
        "sentiment": sentiment,
        "decision_signal": decision_signal,
    }


def test_recruiting_pipeline_metrics_counts_statuses_and_rates() -> None:
    metrics = build_recruiting_pipeline_metrics(
        candidates=[_candidate("cand_avery"), _candidate("cand_blake", missing=True)],
        positions=[
            _position("pos_backend", status="open"),
            _position("pos_sales", status="paused", missing=True),
        ],
        submissions=[
            _submission("sub_1", status="submitted"),
            _submission("sub_2", status="interviewing"),
            _submission(
                "sub_3",
                status="placed",
                fit_snapshot={
                    "overall_score": 80,
                    "dimensions": {"skill_fit": {"score": 4}, "risk": {"score": 1}},
                },
            ),
            _submission("sub_4", status="rejected"),
        ],
        feedback=[
            _feedback("fb_1", sentiment="positive", decision_signal="advance"),
            _feedback("fb_2", sentiment="negative", decision_signal="reject"),
        ],
    )

    assert metrics["summary"] == {
        "candidate_count": 2,
        "position_count": 2,
        "open_position_count": 1,
        "submission_count": 4,
        "feedback_count": 2,
        "active_submission_count": 3,
        "placed_count": 1,
    }
    assert metrics["positions"]["by_status"] == {"open": 1, "paused": 1}
    assert metrics["positions"]["open_rate"] == 0.5
    assert metrics["submissions"]["by_status"] == {
        "interviewing": 1,
        "placed": 1,
        "rejected": 1,
        "submitted": 1,
    }
    assert metrics["submissions"]["placed_rate"] == 0.25
    assert metrics["submissions"]["interview_rate"] == 0.5
    assert metrics["feedback"]["positive_rate"] == 0.5
    assert metrics["feedback"]["advance_rate"] == 0.5


def test_recruiting_pipeline_metrics_reports_data_quality_gaps() -> None:
    metrics = build_recruiting_pipeline_metrics(
        candidates=[_candidate("cand_missing", missing=True)],
        positions=[_position("pos_missing", missing=True)],
        submissions=[_submission("sub_missing", status="submitted")],
        feedback=[
            _feedback(
                "fb_missing",
                sentiment="neutral",
                decision_signal="needs_more_info",
                missing_links=True,
            )
        ],
    )

    assert metrics["data_quality"] == {
        "candidates_missing_skills": 1,
        "candidates_missing_availability": 1,
        "positions_missing_must_have": 1,
        "positions_missing_compensation": 1,
        "submissions_missing_fit_snapshot": 1,
        "feedback_missing_position_or_candidate": 1,
    }


def test_recruiting_pipeline_metrics_handles_empty_input() -> None:
    metrics = build_recruiting_pipeline_metrics()

    assert metrics["ok"] is True
    assert metrics["summary"]["candidate_count"] == 0
    assert metrics["positions"]["open_rate"] == 0.0
    assert metrics["submissions"]["placed_rate"] == 0.0
    assert metrics["feedback"]["positive_rate"] == 0.0
    assert metrics["submissions"]["funnel"][0] == {
        "status": "draft",
        "count": 0,
        "rate": 0.0,
    }


def test_recruiting_pipeline_metrics_accepts_mongo_style_dicts() -> None:
    candidate = _candidate("cand_avery")
    candidate["_id"] = "mongo-candidate-id"
    feedback = _feedback("fb_1", sentiment="positive", decision_signal="advance")
    feedback["_id"] = "mongo-feedback-id"
    feedback["updated_at"] = "2026-06-22T00:00:00+00:00"

    metrics = build_recruiting_pipeline_metrics(
        candidates=[candidate],
        feedback=[feedback],
    )

    assert metrics["summary"]["candidate_count"] == 1
    assert metrics["summary"]["feedback_count"] == 1
    assert metrics["feedback"]["advance_rate"] == 1.0
