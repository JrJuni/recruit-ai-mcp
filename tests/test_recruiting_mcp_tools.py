from __future__ import annotations

from copy import deepcopy

from deal_intel import _context, mcp_server


class FakeRecruitingMCPStorage:
    def __init__(self) -> None:
        self.candidates: dict[str, dict] = {}
        self.client_companies: dict[str, dict] = {}
        self.positions: dict[str, dict] = {}
        self.interactions: dict[str, dict] = {}
        self.submissions: dict[str, dict] = {}
        self.feedback: dict[str, dict] = {}
        self.recommendation_runs: dict[str, dict] = {}

    def upsert_candidate(self, candidate: object) -> bool:
        record = _record(candidate)
        self.candidates[record["candidate_id"]] = record
        return True

    def get_candidate(self, candidate_id: str) -> dict | None:
        return deepcopy(self.candidates.get(candidate_id))

    def list_candidates(self, *, query: dict | None = None, limit: int = 50) -> list[dict]:
        rows = [
            deepcopy(row)
            for row in self.candidates.values()
            if all(row.get(key) == value for key, value in (query or {}).items())
        ]
        return rows[:limit]

    def upsert_client_company(self, client_company: object) -> bool:
        record = _record(client_company)
        self.client_companies[record["client_company_id"]] = record
        return True

    def get_client_company(self, client_company_id: str) -> dict | None:
        return deepcopy(self.client_companies.get(client_company_id))

    def upsert_position(self, position: object) -> bool:
        record = _record(position)
        self.positions[record["position_id"]] = record
        return True

    def get_position(self, position_id: str) -> dict | None:
        return deepcopy(self.positions.get(position_id))

    def list_positions(
        self,
        *,
        client_company_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        rows = []
        for row in self.positions.values():
            if client_company_id is not None and row.get("client_company_id") != client_company_id:
                continue
            if status is not None and row.get("status") != status:
                continue
            rows.append(deepcopy(row))
        return rows[:limit]

    def add_client_feedback(self, feedback: object) -> bool:
        record = _record(feedback)
        self.feedback[record["feedback_id"]] = record
        return True

    def append_recruiting_interaction(self, interaction: object) -> bool:
        record = _record(interaction)
        self.interactions[record["interaction_id"]] = record
        return True

    def get_recruiting_interaction(self, interaction_id: str) -> dict | None:
        record = deepcopy(self.interactions.get(interaction_id))
        if record is not None:
            record.pop("raw_content", None)
        return record

    def upsert_submission(self, submission: object) -> bool:
        record = _record(submission)
        self.submissions[record["submission_id"]] = record
        return True

    def get_submission(self, submission_id: str) -> dict | None:
        return deepcopy(self.submissions.get(submission_id))

    def get_feedback(self, feedback_id: str) -> dict | None:
        return deepcopy(self.feedback.get(feedback_id))

    def list_feedback(
        self,
        *,
        position_id: str | None = None,
        candidate_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        rows = []
        for row in self.feedback.values():
            if position_id is not None and row.get("position_id") != position_id:
                continue
            if candidate_id is not None and row.get("candidate_id") != candidate_id:
                continue
            rows.append(deepcopy(row))
        return rows[:limit]

    def save_recommendation_run(self, recommendation_run: object) -> bool:
        record = _record(recommendation_run)
        self.recommendation_runs[record["recommendation_run_id"]] = record
        return True


def test_mcp_recruiting_create_and_recommend_flow(monkeypatch) -> None:
    storage = FakeRecruitingMCPStorage()
    monkeypatch.setattr(_context, "mongo", lambda: storage)

    candidate = mcp_server.create_candidate(
        name="Avery Chen",
        skills="Python, MongoDB, distributed systems",
        domains="B2B SaaS",
        seniority="lead",
        locations="Remote",
        availability="30 days",
    )
    client = mcp_server.create_client_company(
        name="Acme Robotics",
        hiring_preferences="B2B SaaS, platform leadership",
    )
    position = mcp_server.create_position(
        client_company_id=client["client_company_id"],
        title="Backend Engineering Lead",
        status="open",
        seniority="lead",
        must_have="Python, MongoDB",
        nice_to_have="distributed systems, B2B SaaS",
        target_compensation_maximum=200000,
        locations="Remote",
        remote_policy="remote",
        ideal_candidate_examples=candidate["candidate_id"],
    )

    result = mcp_server.recommend_candidates_for_position(
        position_id=position["position_id"],
        retrieval_limit=5,
        result_limit=3,
    )

    assert result["ok"] is True
    assert result["storage_written"] is False
    assert result["record"]["results"][0]["target_id"] == candidate["candidate_id"]
    assert result["record"]["query"]["retrieval_limit"] == 5


def test_mcp_add_client_feedback_parses_rubric_delta_json(monkeypatch) -> None:
    storage = FakeRecruitingMCPStorage()
    monkeypatch.setattr(_context, "mongo", lambda: storage)

    result = mcp_server.add_client_feedback(
        subject_type="candidate",
        subject_id="cand_avery",
        feedback_id="fb_avery",
        candidate_id="cand_avery",
        position_id="pos_backend",
        sentiment="positive",
        decision_signal="advance",
        rubric_deltas_json='{"skill_fit": 1}',
        preference_learning="platform leadership",
        link_submission=False,
    )

    assert result["ok"] is True
    assert result["record"]["rubric_deltas"] == {"skill_fit": 1}
    assert result["record"]["preference_learning"] == ["platform leadership"]


def test_mcp_add_recruiting_interaction_hides_raw_content(monkeypatch) -> None:
    storage = FakeRecruitingMCPStorage()
    monkeypatch.setattr(_context, "mongo", lambda: storage)

    result = mcp_server.add_recruiting_interaction(
        subject_type="candidate",
        subject_id="cand_avery",
        interaction_type="candidate_screen",
        source_confidence="candidate_stated",
        participants="Avery Chen, Recruiter",
        summary="Strong platform screen.",
        raw_content="Private transcript.",
    )

    assert result["ok"] is True
    assert result["record"]["participants"] == ["Avery Chen", "Recruiter"]
    assert "raw_content" not in result["record"]
    assert storage.interactions[result["interaction_id"]]["raw_content"] == "Private transcript."


def test_mcp_create_submission_parses_fit_snapshot_json(monkeypatch) -> None:
    storage = FakeRecruitingMCPStorage()
    monkeypatch.setattr(_context, "mongo", lambda: storage)

    result = mcp_server.create_submission(
        candidate_id="cand_avery",
        position_id="pos_backend",
        fit_snapshot_json=(
            '{"overall_score": 80, "dimensions": {'
            '"skill_fit": {"score": 4}, "risk": {"score": 1}}}'
        ),
        client_feedback_ids="fb_1, fb_2",
        next_step="Send to client.",
    )

    assert result["ok"] is True
    assert result["record"]["fit_snapshot"]["overall_score"] == 80
    assert result["record"]["client_feedback_ids"] == ["fb_1", "fb_2"]


def test_mcp_recruiting_tools_return_safe_error_for_invalid_json(monkeypatch) -> None:
    monkeypatch.setattr(_context, "mongo", lambda: FakeRecruitingMCPStorage())

    result = mcp_server.add_client_feedback(
        subject_type="candidate",
        subject_id="cand_avery",
        rubric_deltas_json="{bad-json",
    )

    assert result["ok"] is False
    assert result["error_code"] == "INVALID_INPUT"
    assert result["stage"] == "preflight"
    assert "{bad-json" not in str(result["hint"])


def _record(value: object) -> dict:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")  # type: ignore[no-any-return]
    return dict(value)  # type: ignore[arg-type]
