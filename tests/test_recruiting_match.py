from __future__ import annotations

from deal_intel.schema.recruiting import (
    CandidateProfile,
    CompensationExpectation,
    EvidenceReference,
    Position,
)
from deal_intel.schema.recruiting_match import build_candidate_position_fit


def _evidence() -> EvidenceReference:
    return EvidenceReference(
        evidence_id="ev_profile_1",
        source_type="profile",
        source_id="cand_avery_chen",
        summary="Recruiter screen confirmed recent Python platform ownership.",
        confidence="candidate_stated",
    )


def _candidate(**updates: object) -> CandidateProfile:
    payload = {
        "candidate_id": "cand_avery_chen",
        "name": "Avery Chen",
        "headline": "Backend platform lead",
        "current_title": "Lead Backend Engineer",
        "skills": ["Python", "MongoDB", "distributed systems"],
        "domains": ["B2B SaaS"],
        "seniority": "lead",
        "compensation_expectation": CompensationExpectation(
            currency="USD",
            minimum=160000,
            target=175000,
            period="annual",
        ),
        "locations": ["Remote"],
        "availability": "30 days",
        "risk_flags": [],
        "evidence": [_evidence()],
    }
    payload.update(updates)
    return CandidateProfile.model_validate(payload)


def _position(**updates: object) -> Position:
    payload = {
        "position_id": "pos_backend_lead",
        "client_company_id": "client_acme",
        "title": "Backend Engineering Lead",
        "status": "open",
        "seniority": "lead",
        "must_have": ["Python", "MongoDB"],
        "nice_to_have": ["distributed systems", "B2B SaaS"],
        "target_compensation": CompensationExpectation(
            currency="USD",
            minimum=150000,
            maximum=200000,
            period="annual",
        ),
        "locations": ["Remote"],
        "remote_policy": "remote",
        "ideal_candidate_examples": ["cand_avery_chen"],
    }
    payload.update(updates)
    return Position.model_validate(payload)


def test_candidate_position_fit_builds_strong_snapshot() -> None:
    result = build_candidate_position_fit(candidate=_candidate(), position=_position())

    assert result.snapshot.overall_score > 90
    assert result.signals["skill_fit"].score == 5
    assert result.signals["domain_fit"].score == 5
    assert result.signals["seniority_fit"].score == 5
    assert result.signals["compensation_fit"].score == 5
    assert result.signals["location_fit"].score == 5
    assert result.signals["client_preference_fit"].score == 5
    assert result.signals["risk"].score == 0
    assert result.warnings == []


def test_candidate_position_fit_warns_on_missing_candidate_information() -> None:
    result = build_candidate_position_fit(
        candidate=_candidate(
            skills=[],
            domains=[],
            seniority="",
            compensation_expectation=None,
            locations=[],
            availability="",
            evidence=[],
        ),
        position=_position(ideal_candidate_examples=[]),
    )

    assert result.snapshot.overall_score < 20
    warning_codes = {warning["code"] for warning in result.warnings}
    assert "missing_evidence" in warning_codes
    assert "missing_info" in warning_codes
    assert "low_dimension_score" in warning_codes
    assert "Capture candidate skills with source evidence." in result.snapshot.missing_info


def test_candidate_position_fit_scores_partial_must_have_coverage() -> None:
    result = build_candidate_position_fit(
        candidate=_candidate(skills=["Python"]),
        position=_position(must_have=["Python", "MongoDB"], ideal_candidate_examples=[]),
    )

    assert result.signals["skill_fit"].score == 3
    assert "Confirm required skill: MongoDB" in result.signals["skill_fit"].missing_info
    low_dimensions = {
        warning["dimension"]
        for warning in result.warnings
        if warning["code"] == "low_dimension_score"
    }
    assert "skill_fit" in low_dimensions


def test_candidate_position_fit_applies_feedback_rubric_delta_to_any_dimension() -> None:
    result = build_candidate_position_fit(
        candidate=_candidate(skills=["Python"]),
        position=_position(must_have=["Python", "MongoDB"], ideal_candidate_examples=[]),
        client_feedback=[
            {
                "feedback_id": "fb_skill_override",
                "subject_type": "submission",
                "subject_id": "sub_avery_backend",
                "candidate_id": "cand_avery_chen",
                "position_id": "pos_backend_lead",
                "sentiment": "positive",
                "decision_signal": "advance",
                "rubric_deltas": {"skill_fit": 2},
            }
        ],
    )

    assert result.signals["skill_fit"].score == 5
    assert result.feedback_adjustments[0].dimension == "skill_fit"
    assert result.feedback_adjustments[0].original_score == 3
    assert result.feedback_adjustments[0].adjusted_score == 5


def test_candidate_position_fit_clamps_feedback_rubric_delta() -> None:
    result = build_candidate_position_fit(
        candidate=_candidate(),
        position=_position(),
        client_feedback=[
            {
                "feedback_id": "fb_comp_negative",
                "subject_type": "submission",
                "subject_id": "sub_avery_backend",
                "candidate_id": "cand_avery_chen",
                "position_id": "pos_backend_lead",
                "sentiment": "negative",
                "decision_signal": "reject",
                "rubric_deltas": {"compensation_fit": -5, "risk": 5},
            }
        ],
    )

    assert result.signals["compensation_fit"].score == 0
    assert result.signals["risk"].score == 5
    assert result.dimension_scores["risk"] == 0.0
    assert [(item.dimension, item.adjusted_score) for item in result.feedback_adjustments] == [
        ("compensation_fit", 0),
        ("risk", 5),
    ]


def test_candidate_position_fit_inverts_candidate_risk_flags() -> None:
    result = build_candidate_position_fit(
        candidate=_candidate(risk_flags=["counteroffer risk", "limited availability"]),
        position=_position(),
    )

    assert result.signals["risk"].score == 4
    assert result.dimension_scores["risk"] == 20.0
    assert ("low_dimension_score", "risk") in {
        (warning["code"], warning["dimension"]) for warning in result.warnings
    }


def test_candidate_position_fit_penalizes_learned_negative_client_preference() -> None:
    result = build_candidate_position_fit(
        candidate=_candidate(
            preferences={
                "notes": "Needs heavy role shaping before client interviews.",
            },
            risk_flags=["needs heavy role shaping"],
        ),
        position=_position(ideal_candidate_examples=[]),
        client_feedback=[
            {
                "feedback_id": "fb_orbitpay_preference",
                "subject_type": "client_company",
                "subject_id": "client_orbitpay",
                "position_id": "pos_backend_lead",
                "sentiment": "neutral",
                "decision_signal": "preference_update",
                "preference_learning": [
                    "Rejects candidates who need heavy role-shaping before interviews.",
                ],
            }
        ],
    )

    assert result.signals["client_preference_fit"].score == 1
    assert result.signals["client_preference_fit"].rationale == (
        "Candidate profile overlaps learned negative client preference text."
    )
    assert "Review client preference conflict before shortlisting." in (
        result.signals["client_preference_fit"].missing_info
    )


def test_candidate_position_fit_penalizes_candidate_excluded_company() -> None:
    result = build_candidate_position_fit(
        candidate=_candidate(
            preferences={
                "excluded_companies": ["Acme"],
            },
        ),
        position=_position(ideal_candidate_examples=["cand_avery_chen"]),
    )

    assert result.signals["client_preference_fit"].score == 0
    assert result.signals["client_preference_fit"].rationale == (
        "Candidate excluded this client company from target searches."
    )
    assert result.signals["risk"].score == 2
    assert "Confirm whether the candidate exclusion can be revisited." in (
        result.snapshot.missing_info
    )


def test_candidate_position_fit_ignores_unrelated_feedback_for_risk() -> None:
    result = build_candidate_position_fit(
        candidate=_candidate(),
        position=_position(),
        client_feedback=[
            {
                "feedback_id": "fb_other_candidate",
                "subject_type": "candidate",
                "subject_id": "cand_other",
                "candidate_id": "cand_other",
                "position_id": "pos_backend_lead",
                "sentiment": "negative",
                "decision_signal": "reject",
            }
        ],
    )

    assert result.signals["risk"].score == 0
    assert result.dimension_scores["risk"] == 100.0
    assert result.feedback_adjustments == []


def test_candidate_position_fit_accepts_mongo_style_dict_inputs() -> None:
    candidate = _candidate().model_dump(mode="json")
    candidate["_id"] = "mongo-object-id"
    position = _position(ideal_candidate_examples=[]).model_dump(mode="json")
    position["_id"] = "mongo-position-id"

    result = build_candidate_position_fit(candidate=candidate, position=position)

    assert result.snapshot.rubric_key == "recruiting_fit"
    assert result.signals["skill_fit"].score == 5
    assert result.signals["client_preference_fit"].score == 0
