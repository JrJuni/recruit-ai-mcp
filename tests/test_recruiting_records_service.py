from __future__ import annotations

from copy import deepcopy

import pytest

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.storage.recruiting_records import normalize_recruiting_record
from deal_intel.tools import recruiting_records


class FakeRecruitingStorage:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.candidates: dict[str, dict] = {}
        self.client_companies: dict[str, dict] = {}
        self.positions: dict[str, dict] = {}

    def upsert_candidate(self, candidate: object) -> bool:
        if self.fail:
            raise RuntimeError("database unavailable")
        record = normalize_recruiting_record("candidates", candidate)
        self.candidates[record["candidate_id"]] = record
        return True

    def get_candidate(self, candidate_id: str) -> dict | None:
        return deepcopy(self.candidates.get(candidate_id))

    def upsert_client_company(self, client_company: object) -> bool:
        if self.fail:
            raise RuntimeError("database unavailable")
        record = normalize_recruiting_record("client_companies", client_company)
        self.client_companies[record["client_company_id"]] = record
        return True

    def get_client_company(self, client_company_id: str) -> dict | None:
        return deepcopy(self.client_companies.get(client_company_id))

    def upsert_position(self, position: object) -> bool:
        if self.fail:
            raise RuntimeError("database unavailable")
        record = normalize_recruiting_record("positions", position)
        self.positions[record["position_id"]] = record
        return True

    def get_position(self, position_id: str) -> dict | None:
        return deepcopy(self.positions.get(position_id))


def test_create_candidate_generates_id_normalizes_lists_and_returns_safe_record() -> None:
    mongo = FakeRecruitingStorage()

    result = recruiting_records.create_candidate(
        mongo,
        name="Avery Chen",
        skills=["Python", "Python", "MongoDB"],
        domains=["B2B SaaS"],
        locations=["Remote"],
    )

    assert result["ok"] is True
    assert result["entity"] == "candidate"
    assert result["candidate_id"] == "cand_avery_chen"
    assert result["record"]["skills"] == ["Python", "MongoDB"]
    assert result["record"]["domains"] == ["B2B SaaS"]
    assert result["record"]["created_at"]
    assert result["record"]["updated_at"]
    assert "_id" not in result["record"]


def test_create_candidate_accepts_explicit_id() -> None:
    mongo = FakeRecruitingStorage()

    result = recruiting_records.create_candidate(
        mongo,
        candidate_id="cand_custom_1",
        name="Avery Chen",
    )

    assert result["candidate_id"] == "cand_custom_1"
    assert "cand_custom_1" in mongo.candidates


def test_create_client_company_generates_id_and_persists_preferences() -> None:
    mongo = FakeRecruitingStorage()

    result = recruiting_records.create_client_company(
        mongo,
        name="Acme Robotics",
        industry="Robotics",
        hiring_preferences=["Enterprise SaaS background"],
    )

    assert result["client_company_id"] == "client_acme_robotics"
    assert result["record"]["hiring_preferences"] == ["Enterprise SaaS background"]
    assert result["record"]["industry"] == "Robotics"


def test_create_position_validates_compensation_and_preserves_rubric() -> None:
    mongo = FakeRecruitingStorage()

    result = recruiting_records.create_position(
        mongo,
        client_company_id="client_acme_robotics",
        title="Backend Engineering Lead",
        status="open",
        must_have=["Python", "distributed systems", "Python"],
        target_compensation={"currency": "usd", "minimum": 150000, "maximum": 190000},
        ideal_candidate_examples=["cand_custom_1"],
    )

    assert result["position_id"] == "pos_backend_engineering_lead"
    assert result["record"]["must_have"] == ["Python", "distributed systems"]
    assert result["record"]["target_compensation"]["currency"] == "USD"
    assert "skill_fit" in result["record"]["rubric"]["dimensions"]


def test_create_position_rejects_invalid_input_without_echoing_secret() -> None:
    mongo = FakeRecruitingStorage()
    secret = "mongodb+srv://user:pass@example.mongodb.net/recruit_ai"

    with pytest.raises(MCPError) as exc_info:
        recruiting_records.create_position(
            mongo,
            client_company_id="client_acme",
            title=secret,
        )

    exc = exc_info.value
    assert exc.error_code == ErrorCode.INVALID_INPUT
    assert exc.stage == Stage.PREFLIGHT
    assert exc.message == "invalid position input"
    assert secret not in str(exc.hint)


def test_create_candidate_wraps_storage_failure() -> None:
    mongo = FakeRecruitingStorage(fail=True)

    with pytest.raises(MCPError) as exc_info:
        recruiting_records.create_candidate(mongo, name="Avery Chen")

    exc = exc_info.value
    assert exc.error_code == ErrorCode.STORAGE_ERROR
    assert exc.stage == Stage.STORAGE
    assert exc.retryable is True
