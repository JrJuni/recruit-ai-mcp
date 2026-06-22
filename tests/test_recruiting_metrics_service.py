from __future__ import annotations

from copy import deepcopy

import pytest

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.tools import recruiting_metrics


class FakeMetricsStorage:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.candidates = [
            {
                "candidate_id": "cand_avery",
                "name": "Avery Chen",
                "skills": ["Python"],
                "availability": "30 days",
            }
        ]
        self.positions = [
            {
                "position_id": "pos_backend",
                "client_company_id": "client_acme",
                "title": "Backend Lead",
                "status": "open",
                "must_have": ["Python"],
            }
        ]
        self.submissions = [
            {
                "submission_id": "sub_1",
                "candidate_id": "cand_avery",
                "position_id": "pos_backend",
                "status": "placed",
            }
        ]
        self.feedback = [
            {
                "feedback_id": "fb_1",
                "subject_type": "submission",
                "subject_id": "sub_1",
                "position_id": "pos_backend",
                "candidate_id": "cand_avery",
                "sentiment": "positive",
                "decision_signal": "advance",
            }
        ]

    def list_candidates(self, *, query: dict | None = None, limit: int = 50) -> list[dict]:
        if self.fail:
            raise RuntimeError("database unavailable")
        return deepcopy(self.candidates[:limit])

    def list_positions(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        if self.fail:
            raise RuntimeError("database unavailable")
        rows = [row for row in self.positions if status is None or row["status"] == status]
        return deepcopy(rows[:limit])

    def list_submissions(self, *, limit: int = 50) -> list[dict]:
        if self.fail:
            raise RuntimeError("database unavailable")
        return deepcopy(self.submissions[:limit])

    def list_feedback(self, *, limit: int = 50) -> list[dict]:
        if self.fail:
            raise RuntimeError("database unavailable")
        return deepcopy(self.feedback[:limit])


def test_get_recruiting_metrics_reads_storage_and_returns_metrics() -> None:
    result = recruiting_metrics.get_recruiting_metrics(FakeMetricsStorage())

    assert result["ok"] is True
    assert result["storage_written"] is False
    assert result["summary"]["candidate_count"] == 1
    assert result["summary"]["placed_count"] == 1
    assert result["feedback"]["advance_rate"] == 1.0


def test_get_recruiting_metrics_filters_positions() -> None:
    storage = FakeMetricsStorage()
    storage.positions.append(
        {
            "position_id": "pos_paused",
            "client_company_id": "client_acme",
            "title": "Paused Role",
            "status": "paused",
        }
    )

    result = recruiting_metrics.get_recruiting_metrics(
        storage,
        position_status="open",
    )

    assert result["filters"]["position_status"] == "open"
    assert result["summary"]["position_count"] == 1


def test_get_recruiting_metrics_wraps_storage_failure() -> None:
    with pytest.raises(MCPError) as exc_info:
        recruiting_metrics.get_recruiting_metrics(FakeMetricsStorage(fail=True))

    exc = exc_info.value
    assert exc.error_code == ErrorCode.STORAGE_ERROR
    assert exc.stage == Stage.STORAGE
    assert exc.retryable is True
