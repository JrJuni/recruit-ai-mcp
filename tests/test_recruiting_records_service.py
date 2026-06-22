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
        self.interactions: dict[str, dict] = {}
        self.submissions: dict[str, dict] = {}
        self.feedback: dict[str, dict] = {}

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

    def append_recruiting_interaction(self, interaction: object) -> bool:
        if self.fail:
            raise RuntimeError("database unavailable")
        record = normalize_recruiting_record("interactions", interaction)
        self.interactions[record["interaction_id"]] = record
        return True

    def get_recruiting_interaction(self, interaction_id: str) -> dict | None:
        record = deepcopy(self.interactions.get(interaction_id))
        if record:
            record.pop("raw_content", None)
        return record

    def upsert_submission(self, submission: object) -> bool:
        if self.fail:
            raise RuntimeError("database unavailable")
        record = normalize_recruiting_record("submissions", submission)
        self.submissions[record["submission_id"]] = record
        return True

    def get_submission(self, submission_id: str) -> dict | None:
        return deepcopy(self.submissions.get(submission_id))

    def add_client_feedback(self, feedback: object) -> bool:
        if self.fail:
            raise RuntimeError("database unavailable")
        record = normalize_recruiting_record("feedback", feedback)
        self.feedback[record["feedback_id"]] = record
        return True

    def get_feedback(self, feedback_id: str) -> dict | None:
        return deepcopy(self.feedback.get(feedback_id))


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


def test_add_recruiting_interaction_hides_raw_content_in_response() -> None:
    mongo = FakeRecruitingStorage()

    result = recruiting_records.add_recruiting_interaction(
        mongo,
        subject_type="candidate",
        subject_id="cand_custom_1",
        interaction_type="candidate_screen",
        source_confidence="candidate_stated",
        summary="Strong backend screen.",
        raw_content="Full private candidate transcript.",
    )

    assert result["ok"] is True
    assert result["entity"] == "interaction"
    assert result["interaction_id"] == "int_candidate_cand_custom_1_candidate_screen"
    assert "raw_content" not in result["record"]
    stored = mongo.interactions[result["interaction_id"]]
    assert stored["raw_content"] == "Full private candidate transcript."


def test_create_submission_stores_fit_snapshot_and_next_step() -> None:
    mongo = FakeRecruitingStorage()
    fit_snapshot = {
        "overall_score": 80,
        "dimensions": {
            "skill_fit": {"score": 4, "rationale": "Recent Python ownership."},
            "risk": {"score": 1, "rationale": "Low process risk."},
        },
    }

    result = recruiting_records.create_submission(
        mongo,
        candidate_id="cand_custom_1",
        position_id="pos_backend_lead",
        status="submitted",
        fit_snapshot=fit_snapshot,
        next_step="Send to hiring manager.",
    )

    assert result["submission_id"] == "sub_cand_custom_1_pos_backend_lead"
    assert result["record"]["fit_snapshot"]["overall_score"] == 80
    assert result["record"]["next_step"] == "Send to hiring manager."


def test_add_client_feedback_links_submission_feedback_id() -> None:
    mongo = FakeRecruitingStorage()
    submission_result = recruiting_records.create_submission(
        mongo,
        candidate_id="cand_custom_1",
        position_id="pos_backend_lead",
        submission_id="sub_custom_1",
    )

    result = recruiting_records.add_client_feedback(
        mongo,
        subject_type="submission",
        subject_id=submission_result["submission_id"],
        position_id="pos_backend_lead",
        candidate_id="cand_custom_1",
        sentiment="positive",
        decision_signal="advance",
        rubric_deltas={"skill_fit": 1},
        preference_learning=["Client values recent Python ownership."],
    )

    assert result["feedback_id"] == "fb_submission_sub_custom_1"
    assert result["submission_link"] == {
        "status": "linked",
        "submission_id": "sub_custom_1",
    }
    assert mongo.submissions["sub_custom_1"]["client_feedback_ids"] == [
        "fb_submission_sub_custom_1"
    ]


def test_add_client_feedback_warns_when_submission_is_missing() -> None:
    mongo = FakeRecruitingStorage()

    result = recruiting_records.add_client_feedback(
        mongo,
        subject_type="submission",
        subject_id="sub_missing",
        sentiment="negative",
        decision_signal="reject",
    )

    assert result["ok"] is True
    assert result["submission_link"]["status"] == "missing_submission"
    assert result["warnings"][0]["code"] == "submission_not_found"


def test_add_client_feedback_rejects_unknown_rubric_delta() -> None:
    mongo = FakeRecruitingStorage()

    with pytest.raises(MCPError) as exc_info:
        recruiting_records.add_client_feedback(
            mongo,
            subject_type="submission",
            subject_id="sub_custom_1",
            rubric_deltas={"vibes": 1},
        )

    assert exc_info.value.error_code == ErrorCode.INVALID_INPUT
    assert exc_info.value.stage == Stage.PREFLIGHT
