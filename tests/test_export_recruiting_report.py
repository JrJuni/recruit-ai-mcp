from __future__ import annotations

import csv
from copy import deepcopy
from pathlib import Path

import pytest

from deal_intel import _context, mcp_server
from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.tools import export_recruiting_report


class FakeRecruitingReportStorage:
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
                "updated_at": "2026-06-22T00:00:00+00:00",
            }
        ]

    def list_candidates(self, *, query: dict | None = None, limit: int = 50) -> list[dict]:
        if self.fail:
            raise RuntimeError("database unavailable")
        return deepcopy(self.candidates[:limit])

    def list_positions(self, *, status: str | None = None, limit: int = 50) -> list[dict]:
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


def test_export_recruiting_report_writes_csv_and_markdown(tmp_path) -> None:
    result = export_recruiting_report.handle(
        mongo=FakeRecruitingReportStorage(),
        cfg={"reporting": {"output_dir": str(tmp_path)}},
        as_of="2026-06-22",
    )

    assert result["ok"] is True
    assert result["report_type"] == "recruiting_pipeline"
    assert result["as_of"] == "2026-06-22"
    assert result["row_count"] > 0
    assert result["metrics"]["open_position_count"] == 1
    assert result["metrics"]["placed_count"] == 1
    assert result["briefing"] == "1 open positions, 1 active submissions, 1 placements."

    csv_path = Path(result["csv_path"])
    markdown_path = Path(result["markdown_path"])
    assert csv_path.exists()
    assert markdown_path.exists()
    assert csv_path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert markdown_path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert "Recruiting Pipeline Report" in markdown_path.read_text(encoding="utf-8-sig")

    with csv_path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert {"section", "metric", "value"} == set(rows[0])
    assert any(
        row["section"] == "summary"
        and row["metric"] == "open_position_count"
        and row["value"] == "1"
        for row in rows
    )


def test_export_recruiting_report_uses_configured_recruiting_output_dir(tmp_path) -> None:
    result = export_recruiting_report.handle(
        mongo=FakeRecruitingReportStorage(),
        cfg={"reporting": {"recruiting_output_dir": str(tmp_path)}},
    )

    assert result["output_dir"] == str(tmp_path.resolve())


def test_export_recruiting_report_validates_as_of_before_storage() -> None:
    with pytest.raises(MCPError) as exc_info:
        export_recruiting_report.handle(
            mongo=FakeRecruitingReportStorage(fail=True),
            cfg={},
            as_of="not-a-date",
        )

    exc = exc_info.value
    assert exc.error_code == ErrorCode.INVALID_INPUT
    assert exc.stage == Stage.PREFLIGHT


def test_export_recruiting_report_wraps_storage_failure(tmp_path) -> None:
    with pytest.raises(MCPError) as exc_info:
        export_recruiting_report.handle(
            mongo=FakeRecruitingReportStorage(fail=True),
            cfg={"reporting": {"output_dir": str(tmp_path)}},
        )

    exc = exc_info.value
    assert exc.error_code == ErrorCode.STORAGE_ERROR
    assert exc.stage == Stage.STORAGE
    assert exc.retryable is True


def test_mcp_export_recruiting_report(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(_context, "mongo", lambda: FakeRecruitingReportStorage())
    monkeypatch.setattr(
        _context,
        "config",
        lambda: {"reporting": {"output_dir": str(tmp_path)}},
    )

    result = mcp_server.export_recruiting_report(as_of="2026-06-22")

    assert result["ok"] is True
    assert Path(result["csv_path"]).exists()
    assert Path(result["markdown_path"]).exists()
