from __future__ import annotations

from copy import deepcopy

import pytest

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.schema.recruiting import (
    CandidateProfile,
    CompensationExpectation,
    Position,
)
from deal_intel.storage.recruiting_collections import CANDIDATES, FEEDBACK, POSITIONS
from deal_intel.tools import recruiting_recommendations
from deal_intel.tools.sample_dataset import build_sample_recruiting_records


class FakeRecommendationStorage:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.candidates: dict[str, dict] = {}
        self.positions: dict[str, dict] = {}
        self.feedback: list[dict] = []
        self.recommendation_runs: dict[str, dict] = {}

    def get_candidate(self, candidate_id: str) -> dict | None:
        if self.fail:
            raise RuntimeError("database unavailable")
        return deepcopy(self.candidates.get(candidate_id))

    def list_candidates(self, *, query: dict | None = None, limit: int = 50) -> list[dict]:
        if self.fail:
            raise RuntimeError("database unavailable")
        rows = [
            deepcopy(row)
            for row in self.candidates.values()
            if all(row.get(key) == value for key, value in (query or {}).items())
        ]
        return rows[:limit]

    def get_position(self, position_id: str) -> dict | None:
        if self.fail:
            raise RuntimeError("database unavailable")
        return deepcopy(self.positions.get(position_id))

    def list_positions(
        self,
        *,
        client_company_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        if self.fail:
            raise RuntimeError("database unavailable")
        rows = []
        for row in self.positions.values():
            if client_company_id is not None and row.get("client_company_id") != client_company_id:
                continue
            if status is not None and row.get("status") != status:
                continue
            rows.append(deepcopy(row))
        return rows[:limit]

    def list_feedback(
        self,
        *,
        position_id: str | None = None,
        candidate_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        if self.fail:
            raise RuntimeError("database unavailable")
        rows = []
        for row in self.feedback:
            if position_id is not None and row.get("position_id") != position_id:
                continue
            if candidate_id is not None and row.get("candidate_id") != candidate_id:
                continue
            rows.append(deepcopy(row))
        return rows[:limit]

    def save_recommendation_run(self, recommendation_run: object) -> bool:
        if self.fail:
            raise RuntimeError("database unavailable")
        record = recommendation_run.model_dump(mode="json")
        self.recommendation_runs[record["recommendation_run_id"]] = record
        return True

    def get_recommendation_run(self, recommendation_run_id: str) -> dict | None:
        if self.fail:
            raise RuntimeError("database unavailable")
        return deepcopy(self.recommendation_runs.get(recommendation_run_id))


def _candidate(candidate_id: str, **updates: object) -> dict:
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
        ).model_dump(mode="json"),
        "locations": ["Remote"],
        "availability": "30 days",
        "risk_flags": [],
        "evidence": [
            {
                "evidence_id": f"ev_{candidate_id}",
                "source_type": "profile",
                "source_id": candidate_id,
                "summary": "Candidate profile includes source-backed backend evidence.",
                "confidence": "candidate_stated",
            }
        ],
    }
    payload.update(updates)
    return CandidateProfile.model_validate(payload).model_dump(mode="json")


def _position(position_id: str = "pos_backend_lead", **updates: object) -> dict:
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
        ).model_dump(mode="json"),
        "locations": ["Remote"],
        "remote_policy": "remote",
    }
    payload.update(updates)
    return Position.model_validate(payload).model_dump(mode="json")


def _storage() -> FakeRecommendationStorage:
    storage = FakeRecommendationStorage()
    storage.positions["pos_backend_lead"] = _position(ideal_candidate_examples=["cand_avery"])
    storage.positions["pos_sales_manager"] = _position(
        "pos_sales_manager",
        title="Sales Manager",
        seniority="manager",
        must_have=["Salesforce"],
        nice_to_have=[],
        locations=["New York"],
        remote_policy="onsite",
    )
    storage.candidates["cand_avery"] = _candidate("cand_avery")
    storage.candidates["cand_blake"] = _candidate(
        "cand_blake",
        skills=["Excel"],
        domains=["Retail"],
        seniority="junior",
    )
    return storage


def test_recommend_candidates_for_position_ranks_and_optionally_saves() -> None:
    storage = _storage()

    result = recruiting_recommendations.recommend_candidates_for_position(
        storage,
        position_id="pos_backend_lead",
        save_run=True,
    )

    assert result["ok"] is True
    assert result["mode"] == "position_to_candidates"
    assert result["anchor_id"] == "pos_backend_lead"
    assert result["storage_written"] is True
    assert result["record"]["results"][0]["target_id"] == "cand_avery"
    assert result["recommendation_run_id"] in storage.recommendation_runs


def test_get_recommendation_run_reads_saved_record() -> None:
    storage = _storage()
    saved = recruiting_recommendations.recommend_candidates_for_position(
        storage,
        position_id="pos_backend_lead",
        save_run=True,
    )

    result = recruiting_recommendations.get_recommendation_run(
        storage,
        recommendation_run_id=saved["recommendation_run_id"],
    )

    assert result["ok"] is True
    assert result["entity"] == "recommendation_run"
    assert result["storage_written"] is False
    assert result["recommendation_run_id"] == saved["recommendation_run_id"]
    assert result["record"]["results"][0]["target_id"] == "cand_avery"


def test_recommend_positions_for_candidate_filters_open_positions() -> None:
    storage = _storage()
    storage.positions["pos_sales_manager"]["status"] = "paused"

    result = recruiting_recommendations.recommend_positions_for_candidate(
        storage,
        candidate_id="cand_avery",
        position_status="open",
    )

    assert result["mode"] == "candidate_to_positions"
    assert result["storage_written"] is False
    assert [row["target_id"] for row in result["record"]["results"]] == [
        "pos_backend_lead"
    ]


def test_recommend_positions_for_candidate_respects_excluded_company() -> None:
    storage = FakeRecommendationStorage()
    storage.candidates["cand_avery"] = _candidate(
        "cand_avery",
        preferences={"excluded_companies": ["Acme"]},
    )
    storage.positions["pos_acme_backend"] = _position(
        "pos_acme_backend",
        client_company_id="client_acme",
    )
    storage.positions["pos_beta_backend"] = _position(
        "pos_beta_backend",
        client_company_id="client_beta",
    )

    result = recruiting_recommendations.recommend_positions_for_candidate(
        storage,
        candidate_id="cand_avery",
    )

    rows = result["record"]["results"]
    acme = next(row for row in rows if row["target_id"] == "pos_acme_backend")

    assert [row["target_id"] for row in rows] == [
        "pos_beta_backend",
        "pos_acme_backend",
    ]
    assert acme["risk_flags"] == ["client_exclusion", "review_match_risk"]
    assert "Confirm whether the candidate exclusion can be revisited." in (
        acme["next_questions"]
    )


def test_recommend_positions_for_candidate_defaults_to_open_sample_roles() -> None:
    records = build_sample_recruiting_records(loaded_at="2026-06-22T00:00:00+00:00")
    storage = FakeRecommendationStorage()
    storage.candidates = {row["candidate_id"]: row for row in records[CANDIDATES]}
    storage.positions = {row["position_id"]: row for row in records[POSITIONS]}
    storage.feedback = records[FEEDBACK]

    default_result = recruiting_recommendations.recommend_positions_for_candidate(
        storage,
        candidate_id="cand_lin_park",
    )
    all_status_result = recruiting_recommendations.recommend_positions_for_candidate(
        storage,
        candidate_id="cand_lin_park",
        position_status=None,
    )

    assert {
        row["target_id"] for row in default_result["record"]["results"]
    } == {"pos_northstar_backend_lead", "pos_orbitpay_payments_lead"}
    assert "pos_northstar_data_manager" not in {
        row["target_id"] for row in default_result["record"]["results"]
    }
    assert all_status_result["record"]["results"][0]["target_id"] == (
        "pos_northstar_data_manager"
    )
    assert all_status_result["record"]["query"]["position_status"] is None


def test_recommend_candidates_for_position_applies_retrieval_limit() -> None:
    storage = _storage()

    result = recruiting_recommendations.recommend_candidates_for_position(
        storage,
        position_id="pos_backend_lead",
        retrieval_limit=1,
        result_limit=10,
    )

    assert result["record"]["query"]["retrieval_limit"] == 1
    assert [row["target_id"] for row in result["record"]["results"]] == [
        "cand_avery"
    ]


def test_recommendation_service_applies_feedback_deltas() -> None:
    storage = _storage()
    storage.feedback.append(
        {
            "feedback_id": "fb_blake_skill",
            "subject_type": "submission",
            "subject_id": "sub_blake_backend",
            "candidate_id": "cand_blake",
            "position_id": "pos_backend_lead",
            "sentiment": "positive",
            "decision_signal": "advance",
            "rubric_deltas": {"skill_fit": 2},
        }
    )

    result = recruiting_recommendations.recommend_candidates_for_position(
        storage,
        position_id="pos_backend_lead",
    )

    blake = next(
        row for row in result["record"]["results"] if row["target_id"] == "cand_blake"
    )
    assert blake["fit_snapshot"]["dimensions"]["skill_fit"]["score"] == 3
    assert blake["feedback_adjustments"][0]["dimension"] == "skill_fit"
    assert blake["feedback_adjustments"][0]["adjusted_score"] == 3


def test_recommendation_service_surfaces_inferred_skill_gap_when_saved() -> None:
    storage = FakeRecommendationStorage()
    storage.positions["pos_platform_lead"] = _position(
        "pos_platform_lead",
        must_have=["Python", "MongoDB", "data platforms"],
        nice_to_have=[],
    )
    storage.candidates["cand_blake"] = _candidate(
        "cand_blake",
        skills=["Python"],
        domains=[],
    )

    saved = recruiting_recommendations.recommend_candidates_for_position(
        storage,
        position_id="pos_platform_lead",
        save_run=True,
    )
    read_back = recruiting_recommendations.get_recommendation_run(
        storage,
        recommendation_run_id=saved["recommendation_run_id"],
    )

    row = read_back["record"]["results"][0]
    assert row["target_id"] == "cand_blake"
    assert row["fit_snapshot"]["dimensions"]["skill_fit"]["score"] == 2
    assert row["risk_flags"] == ["skill_gap"]
    assert "Confirm required skill: MongoDB" in row["next_questions"]
    assert "Confirm required skill: data platforms" in row["next_questions"]


def test_recommendation_service_preserves_domain_and_seniority_flags() -> None:
    storage = FakeRecommendationStorage()
    storage.positions["pos_healthcare_staff"] = _position(
        "pos_healthcare_staff",
        title="Healthcare Data Platform Staff Engineer",
        seniority="staff",
        must_have=["Python", "MongoDB"],
        nice_to_have=["HIPAA", "clinical workflows"],
    )
    storage.candidates["cand_blake"] = _candidate(
        "cand_blake",
        skills=["Python", "MongoDB"],
        domains=["Retail analytics"],
        seniority="junior",
    )

    saved = recruiting_recommendations.recommend_candidates_for_position(
        storage,
        position_id="pos_healthcare_staff",
        save_run=True,
    )
    read_back = recruiting_recommendations.get_recommendation_run(
        storage,
        recommendation_run_id=saved["recommendation_run_id"],
    )

    row = read_back["record"]["results"][0]
    assert row["target_id"] == "cand_blake"
    assert row["fit_snapshot"]["dimensions"]["domain_fit"]["score"] == 2
    assert row["fit_snapshot"]["dimensions"]["seniority_fit"]["score"] == 1
    assert row["risk_flags"] == ["domain_mismatch", "seniority_mismatch"]
    assert "Confirm whether candidate domain experience transfers to this role." in (
        row["next_questions"]
    )
    assert "Improve evidence for seniority_fit." in row["next_questions"]


def test_recommendation_service_raises_not_found_for_missing_anchor() -> None:
    storage = _storage()

    with pytest.raises(MCPError) as exc_info:
        recruiting_recommendations.recommend_candidates_for_position(
            storage,
            position_id="pos_missing",
        )

    exc = exc_info.value
    assert exc.error_code == ErrorCode.NOT_FOUND
    assert exc.stage == Stage.STORAGE
    assert exc.retryable is False


def test_recommendation_service_wraps_storage_failure() -> None:
    storage = FakeRecommendationStorage(fail=True)

    with pytest.raises(MCPError) as exc_info:
        recruiting_recommendations.recommend_positions_for_candidate(
            storage,
            candidate_id="cand_avery",
        )

    exc = exc_info.value
    assert exc.error_code == ErrorCode.STORAGE_ERROR
    assert exc.stage == Stage.STORAGE
    assert exc.retryable is True


def test_get_recommendation_run_raises_not_found() -> None:
    storage = _storage()

    with pytest.raises(MCPError) as exc_info:
        recruiting_recommendations.get_recommendation_run(
            storage,
            recommendation_run_id="rec_missing",
        )

    exc = exc_info.value
    assert exc.error_code == ErrorCode.NOT_FOUND
    assert exc.stage == Stage.STORAGE
    assert exc.retryable is False
