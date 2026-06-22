from __future__ import annotations

from deal_intel.schema.recruiting import (
    CandidateProfile,
    CompensationExpectation,
    Position,
)
from deal_intel.schema.recruiting_retrieval import (
    rank_candidates_for_position_retrieval,
    rank_positions_for_candidate_retrieval,
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
        "locations": ["Remote"],
        "availability": "30 days",
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


def test_rank_candidates_for_position_retrieval_orders_by_lexical_overlap() -> None:
    results = rank_candidates_for_position_retrieval(
        position=_position(),
        candidates=[
            _candidate("cand_blake", skills=["Excel"], domains=["Retail"], seniority="junior"),
            _candidate("cand_avery"),
        ],
    )

    assert [result.target_id for result in results] == ["cand_avery", "cand_blake"]
    assert {"python", "mongodb", "remote"}.issubset(set(results[0].matched_terms))
    assert results[0].score > results[1].score


def test_rank_positions_for_candidate_retrieval_limits_results() -> None:
    results = rank_positions_for_candidate_retrieval(
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

    assert [result.target_id for result in results] == ["pos_backend_lead"]


def test_retrieval_accepts_mongo_style_dict_inputs() -> None:
    candidate = _candidate("cand_avery").model_dump(mode="json")
    candidate["_id"] = "mongo-candidate-id"
    position = _position().model_dump(mode="json")
    position["_id"] = "mongo-position-id"

    results = rank_candidates_for_position_retrieval(
        position=position,
        candidates=[candidate],
    )

    assert results[0].target_id == "cand_avery"
    assert results[0].score > 0
