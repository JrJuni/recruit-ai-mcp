from __future__ import annotations

import pytest
from pydantic import ValidationError

from deal_intel.schema.recruiting import (
    FIT_DIMENSION_KEYS,
    CandidateProfile,
    ClientFeedback,
    EvidenceReference,
    FitSignal,
    FitSnapshot,
    Position,
    RecommendationResult,
    RecommendationRun,
    Submission,
    default_recruiting_fit_rubric,
)


def _evidence() -> EvidenceReference:
    return EvidenceReference(
        evidence_id="ev_screen_1",
        source_type="interaction",
        source_id="int_screen_1",
        summary="Candidate described recent Python data pipeline ownership.",
        confidence="candidate_stated",
    )


def _fit_snapshot() -> FitSnapshot:
    return FitSnapshot(
        overall_score=82.5,
        dimensions={
            "skill_fit": FitSignal(
                score=4,
                rationale="Recent Python and data pipeline ownership is directly relevant.",
                evidence_refs=[_evidence()],
            ),
            "risk": FitSignal(
                score=1,
                rationale="No major mismatch identified yet.",
            ),
        },
        summary="Strong initial fit with limited risk.",
    )


def test_default_recruiting_fit_rubric_has_expected_dimensions() -> None:
    rubric = default_recruiting_fit_rubric()

    assert tuple(rubric.dimensions) == FIT_DIMENSION_KEYS
    assert rubric.score_min == 0
    assert rubric.score_max == 5
    assert rubric.dimensions["risk"].higher_is_better is False
    assert rubric.dimensions["skill_fit"].weight > rubric.dimensions["availability_fit"].weight


def test_position_supports_ideal_candidate_examples_and_rubric() -> None:
    position = Position(
        position_id="pos_backend_lead",
        client_company_id="client_acme",
        title="Backend Engineering Lead",
        status="open",
        must_have=["Python", "distributed systems", "team leadership"],
        ideal_candidate_examples=["cand_reference_1", "cand_reference_2"],
    )

    assert position.rubric.dimensions["client_preference_fit"].gap_threshold == 3
    assert position.ideal_candidate_examples == ["cand_reference_1", "cand_reference_2"]


def test_candidate_profile_keeps_preferences_constraints_and_evidence() -> None:
    candidate = CandidateProfile(
        candidate_id="cand_jordan_lee",
        name="Jordan Lee",
        skills=["Python", "Python", "MongoDB"],
        domains=["B2B SaaS"],
        locations=["Seoul", "Remote"],
        availability="30 days",
        evidence=[_evidence()],
    )

    assert candidate.skills == ["Python", "MongoDB"]
    assert candidate.evidence[0].confidence == "candidate_stated"


def test_submission_snapshots_fit_at_presentation_time() -> None:
    submission = Submission(
        submission_id="sub_001",
        candidate_id="cand_jordan_lee",
        position_id="pos_backend_lead",
        status="submitted",
        fit_snapshot=_fit_snapshot(),
    )

    assert submission.fit_snapshot is not None
    assert submission.fit_snapshot.overall_score == 82.5
    evidence_ref = submission.fit_snapshot.dimensions["skill_fit"].evidence_refs[0]
    assert evidence_ref.source_id == "int_screen_1"


def test_feedback_captures_preference_learning_and_rubric_deltas() -> None:
    feedback = ClientFeedback(
        feedback_id="fb_001",
        subject_type="submission",
        subject_id="sub_001",
        position_id="pos_backend_lead",
        candidate_id="cand_jordan_lee",
        sentiment="mixed",
        decision_signal="preference_update",
        rubric_deltas={"domain_fit": 1, "risk": -1},
        preference_learning=["Client prefers enterprise SaaS implementation experience."],
    )

    assert feedback.rubric_deltas == {"domain_fit": 1, "risk": -1}
    assert feedback.preference_learning


def test_recommendation_run_supports_position_to_candidate_mode() -> None:
    run = RecommendationRun(
        recommendation_run_id="rec_001",
        mode="position_to_candidates",
        anchor_type="position",
        anchor_id="pos_backend_lead",
        query={"must_have": ["Python"]},
        results=[
            RecommendationResult(
                target_id="cand_jordan_lee",
                rank=1,
                fit_snapshot=_fit_snapshot(),
                recommendation_reason="Best current evidence-backed fit.",
                next_questions=["Confirm compensation expectations."],
            )
        ],
    )

    assert run.results[0].target_id == "cand_jordan_lee"
    assert run.results[0].next_questions == ["Confirm compensation expectations."]


def test_recommendation_run_requires_matching_anchor_type() -> None:
    with pytest.raises(ValidationError, match="anchor_type must be 'candidate'"):
        RecommendationRun(
            recommendation_run_id="rec_002",
            mode="candidate_to_positions",
            anchor_type="position",
            anchor_id="pos_backend_lead",
        )


def test_schema_rejects_unknown_fit_dimension() -> None:
    with pytest.raises(ValidationError, match="unknown fit dimensions"):
        FitSnapshot(
            overall_score=50,
            dimensions={"vibes": FitSignal(score=3)},
        )


def test_recommendation_result_rejects_unknown_feedback_adjustment_dimension() -> None:
    with pytest.raises(ValidationError, match="unknown fit dimension"):
        RecommendationResult(
            target_id="cand_jordan_lee",
            rank=1,
            fit_snapshot=_fit_snapshot(),
            feedback_adjustments=[
                {
                    "feedback_id": "fb_001",
                    "dimension": "vibes",
                    "delta": 1,
                    "original_score": 2,
                    "adjusted_score": 3,
                }
            ],
        )


def test_schema_rejects_secret_like_metadata_without_echoing_secret() -> None:
    secret = "mongodb+srv://user:pass@example.mongodb.net/recruit_ai"

    with pytest.raises(ValidationError) as exc_info:
        CandidateProfile(candidate_id="cand_secret", name=secret)

    error_text = str(exc_info.value)
    assert "secret" in error_text
    assert secret not in error_text
