from __future__ import annotations

from deal_intel.schema.recruiting import (
    CandidateProfile,
    CompensationExpectation,
    EvidenceReference,
    Position,
)
from deal_intel.schema.recruiting_recommendation import (
    build_candidate_position_recommendation_run,
    build_position_candidate_recommendation_run,
)
from deal_intel.storage.recruiting_collections import CANDIDATES, FEEDBACK, POSITIONS
from deal_intel.tools.sample_dataset import build_sample_recruiting_records


def _evidence(candidate_id: str) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=f"ev_{candidate_id}",
        source_type="profile",
        source_id=candidate_id,
        summary="Recruiter screen confirmed profile details.",
        confidence="candidate_stated",
    )


def _candidate(candidate_id: str, **updates: object) -> CandidateProfile:
    payload = {
        "candidate_id": candidate_id,
        "name": "Avery Chen" if candidate_id == "cand_avery" else "Blake Rivera",
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
        "evidence": [_evidence(candidate_id)],
    }
    payload.update(updates)
    return CandidateProfile.model_validate(payload)


def _position(position_id: str = "pos_backend_lead", **updates: object) -> Position:
    payload = {
        "position_id": position_id,
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
    }
    payload.update(updates)
    return Position.model_validate(payload)


def test_position_candidate_recommendation_run_ranks_candidates() -> None:
    run = build_position_candidate_recommendation_run(
        position=_position(ideal_candidate_examples=["cand_avery"]),
        candidates=[
            _candidate("cand_blake", skills=["Excel"], domains=["Retail"], seniority="junior"),
            _candidate("cand_avery"),
        ],
        recommendation_run_id="rec_rank_candidates",
        query={"source": "unit-test"},
    )

    assert run.mode == "position_to_candidates"
    assert run.anchor_type == "position"
    assert run.anchor_id == "pos_backend_lead"
    assert [result.target_id for result in run.results] == ["cand_avery", "cand_blake"]
    assert [result.rank for result in run.results] == [1, 2]
    assert run.results[0].recommendation_reason.startswith(
        "Strongest evidence-backed dimensions:"
    )
    assert run.query == {"source": "unit-test"}


def test_candidate_position_recommendation_run_ranks_positions() -> None:
    run = build_candidate_position_recommendation_run(
        candidate=_candidate("cand_avery"),
        positions=[
            _position(
                "pos_sales_manager",
                title="Sales Manager",
                seniority="manager",
                must_have=["Salesforce"],
                nice_to_have=[],
                locations=["New York"],
                remote_policy="onsite",
            ),
            _position("pos_backend_lead"),
        ],
        limit=1,
    )

    assert run.mode == "candidate_to_positions"
    assert run.anchor_type == "candidate"
    assert run.anchor_id == "cand_avery"
    assert run.recommendation_run_id == "rec_positions_for_cand_avery"
    assert [result.target_id for result in run.results] == ["pos_backend_lead"]
    assert run.results[0].rank == 1


def test_candidate_position_recommendation_respects_excluded_company() -> None:
    run = build_candidate_position_recommendation_run(
        candidate=_candidate(
            "cand_avery",
            preferences={"excluded_companies": ["Acme"]},
        ),
        positions=[
            _position("pos_acme_backend", client_company_id="client_acme"),
            _position("pos_beta_backend", client_company_id="client_beta"),
        ],
    )

    results = {result.target_id: result for result in run.results}

    assert [result.target_id for result in run.results] == [
        "pos_beta_backend",
        "pos_acme_backend",
    ]
    assert results["pos_acme_backend"].risk_flags == ["review_match_risk"]
    assert "Confirm whether the candidate exclusion can be revisited." in (
        results["pos_acme_backend"].next_questions
    )


def test_recommendation_result_exposes_low_fit_reason_and_questions() -> None:
    run = build_position_candidate_recommendation_run(
        position=_position(ideal_candidate_examples=[]),
        candidates=[
            _candidate(
                "cand_blake",
                skills=[],
                domains=[],
                seniority="",
                compensation_expectation=None,
                locations=[],
                availability="",
                evidence=[],
            )
        ],
    )

    result = run.results[0]
    assert result.fit_snapshot.overall_score < 40
    assert result.rejected_reason.startswith("Below threshold due to weak")
    assert "Capture candidate skills with source evidence." in result.next_questions
    assert "Improve evidence for skill_fit." in result.next_questions


def test_recommendation_result_carries_risk_flags_from_candidate_and_fit() -> None:
    run = build_position_candidate_recommendation_run(
        position=_position(),
        candidates=[
            _candidate(
                "cand_avery",
                risk_flags=["counteroffer risk", "limited availability"],
            )
        ],
    )

    result = run.results[0]
    assert result.risk_flags == [
        "counteroffer risk",
        "limited availability",
        "high_match_risk",
    ]


def test_recommendation_run_accepts_mongo_style_dict_inputs() -> None:
    candidate = _candidate("cand_avery").model_dump(mode="json")
    candidate["_id"] = "mongo-candidate-id"
    position = _position().model_dump(mode="json")
    position["_id"] = "mongo-position-id"

    run = build_position_candidate_recommendation_run(
        position=position,
        candidates=[candidate],
    )

    assert run.results[0].target_id == "cand_avery"
    assert run.results[0].fit_snapshot.rubric_key == "recruiting_fit"


def test_recruiting_sample_stress_candidate_does_not_outrank_aligned_match() -> None:
    records = build_sample_recruiting_records(loaded_at="2026-06-22T00:00:00+00:00")
    positions = {row["position_id"]: row for row in records[POSITIONS]}

    run = build_position_candidate_recommendation_run(
        position=positions["pos_northstar_backend_lead"],
        candidates=records[CANDIDATES],
        client_feedback=records[FEEDBACK],
        limit=5,
    )

    results = {result.target_id: result for result in run.results}

    assert run.results[0].target_id == "cand_avery_chen"
    assert results["cand_nora_weiss"].rank > results["cand_avery_chen"].rank
    assert results["cand_nora_weiss"].fit_snapshot.overall_score < (
        results["cand_avery_chen"].fit_snapshot.overall_score
    )
    assert results["cand_nora_weiss"].risk_flags == [
        "compensation above current budget",
        "requires UK remote exception",
        "late availability",
        "high_match_risk",
    ]


def test_recruiting_sample_manager_only_keyword_match_does_not_outrank_ic_fit() -> None:
    records = build_sample_recruiting_records(loaded_at="2026-06-22T00:00:00+00:00")
    positions = {row["position_id"]: row for row in records[POSITIONS]}

    run = build_position_candidate_recommendation_run(
        position=positions["pos_northstar_backend_lead"],
        candidates=records[CANDIDATES],
        client_feedback=records[FEEDBACK],
        limit=7,
    )

    results = {result.target_id: result for result in run.results}

    assert run.results[0].target_id == "cand_avery_chen"
    assert results["cand_eli_brooks"].rank > results["cand_avery_chen"].rank
    assert results["cand_eli_brooks"].fit_snapshot.overall_score < (
        results["cand_avery_chen"].fit_snapshot.overall_score
    )
    assert results["cand_eli_brooks"].risk_flags == [
        "requires manager scope",
        "compensation above current budget",
        "passive candidate",
        "high_match_risk",
    ]


def test_recruiting_sample_junior_keyword_match_does_not_outrank_senior_fit() -> None:
    records = build_sample_recruiting_records(loaded_at="2026-06-22T00:00:00+00:00")
    positions = {row["position_id"]: row for row in records[POSITIONS]}

    run = build_position_candidate_recommendation_run(
        position=positions["pos_orbitpay_payments_lead"],
        candidates=records[CANDIDATES],
        client_feedback=records[FEEDBACK],
        limit=6,
    )

    results = {result.target_id: result for result in run.results}

    assert run.results[0].target_id == "cand_mateo_rivera"
    assert results["cand_iris_kim"].rank > results["cand_mateo_rivera"].rank
    assert results["cand_iris_kim"].fit_snapshot.overall_score < (
        results["cand_mateo_rivera"].fit_snapshot.overall_score
    )
    assert results["cand_iris_kim"].risk_flags == [
        "needs senior mentorship for platform lead scope",
        "review_match_risk",
    ]


def test_recruiting_sample_client_preference_conflict_does_not_outrank_match() -> None:
    records = build_sample_recruiting_records(loaded_at="2026-06-22T00:00:00+00:00")
    positions = {row["position_id"]: row for row in records[POSITIONS]}

    run = build_position_candidate_recommendation_run(
        position=positions["pos_orbitpay_payments_lead"],
        candidates=records[CANDIDATES],
        client_feedback=records[FEEDBACK],
        limit=8,
    )

    results = {result.target_id: result for result in run.results}

    assert run.results[0].target_id == "cand_mateo_rivera"
    assert results["cand_sam_taylor"].rank > results["cand_mateo_rivera"].rank
    assert results["cand_sam_taylor"].fit_snapshot.overall_score < (
        results["cand_mateo_rivera"].fit_snapshot.overall_score
    )
    assert (
        results["cand_sam_taylor"]
        .fit_snapshot.dimensions["client_preference_fit"]
        .score
        == 1
    )
    assert results["cand_sam_taylor"].risk_flags == [
        "needs heavy role shaping",
        "review_match_risk",
    ]
