from __future__ import annotations

import asyncio
import json

from deal_intel import _context, mcp_server
from deal_intel.workflow_trace import (
    append_workflow_trace,
    build_workflow_trace_event,
    read_workflow_traces,
    workflow_trace_enabled,
    workflow_trace_path,
    write_trace_event,
)


def test_workflow_trace_is_disabled_by_default(tmp_path) -> None:
    cfg = {"storage": {"local_data_dir": str(tmp_path)}}

    result = append_workflow_trace(
        cfg,
        tool_name="create_candidate",
        arguments={"candidate_id": "cand_1"},
        result={"ok": True},
        duration_ms=12,
        environ={},
    )

    assert workflow_trace_enabled(cfg, environ={}) is False
    assert result == {
        "ok": True,
        "trace_written": False,
        "reason": "workflow_trace_disabled",
    }
    assert not workflow_trace_path(cfg, environ={}).exists()


def test_workflow_trace_redacts_sensitive_arguments_and_results(tmp_path) -> None:
    cfg = {
        "storage": {"local_data_dir": str(tmp_path)},
        "observability": {"workflow_trace": {"enabled": True}},
    }

    result = append_workflow_trace(
        cfg,
        tool_name="add_recruiting_interaction",
        arguments={
            "candidate_id": "cand_avery",
            "raw_content": "private screen transcript",
            "content": "full note should not persist",
            "mongodb_uri": "mongodb+srv://user:pass@example/test",
            "nested": {"openai_api_key": "sk-test-secret", "subject_id": "pos_1"},
            "tags": ["one", "two"],
        },
        result={
            "ok": True,
            "storage_written": True,
            "summary": {"candidate_count": 3, "note": "private"},
            "raw_content": "must not persist",
            "warnings": ["small warning"],
        },
        duration_ms=17.4,
        environ={},
    )

    events = read_workflow_traces(workflow_trace_path(cfg, environ={}))
    serialized = json.dumps(events, ensure_ascii=False)

    assert result["trace_written"] is True
    assert len(events) == 1
    event = events[0]
    assert event["tool_name"] == "add_recruiting_interaction"
    assert event["success"] is True
    assert event["argument_summary"]["candidate_id"] == "cand_avery"
    assert event["argument_summary"]["raw_content"] == "[redacted]"
    assert event["argument_summary"]["content"] == "[redacted]"
    assert event["argument_summary"]["mongodb_uri"] == "[redacted]"
    assert event["argument_summary"]["nested"]["openai_api_key"] == "[redacted]"
    assert event["argument_summary"]["nested"]["subject_id"] == "pos_1"
    assert event["argument_summary"]["tags"] == {"type": "list", "length": 2}
    assert event["result_summary"]["ok"] is True
    assert event["result_summary"]["storage_written"] is True
    assert event["result_summary"]["summary_counts"] == {"candidate_count": 3}
    assert event["result_summary"]["warning_count"] == 1
    assert "private screen transcript" not in serialized
    assert "full note should not persist" not in serialized
    assert "mongodb+srv" not in serialized
    assert "sk-test-secret" not in serialized
    assert "must not persist" not in serialized


def test_workflow_trace_can_be_enabled_by_env_and_is_bounded(tmp_path) -> None:
    cfg = {"storage": {"local_data_dir": str(tmp_path)}}
    path = workflow_trace_path(cfg, environ={})

    for index in range(5):
        write_trace_event(
            path,
            build_workflow_trace_event(
                tool_name="recommend_candidates_for_position",
                arguments={"position_id": f"pos_{index}"},
                result={"ok": index % 2 == 0, "error_code": "TEST" if index % 2 else ""},
                duration_ms=index,
                timestamp=f"2026-06-22T00:00:0{index}+00:00",
            ),
            max_events=3,
        )

    events = read_workflow_traces(path)

    assert workflow_trace_enabled(
        cfg,
        environ={"RECRUIT_AI_WORKFLOW_TRACE": "1"},
    ) is True
    assert [row["argument_summary"]["position_id"] for row in events] == [
        "pos_2",
        "pos_3",
        "pos_4",
    ]
    assert events[1]["success"] is False
    assert events[1]["error_category"] == "TEST"


def test_mcp_call_tool_writes_opt_in_workflow_trace(monkeypatch, tmp_path) -> None:
    trace_path = tmp_path / "workflow_traces.jsonl"
    monkeypatch.setenv("RECRUIT_AI_WORKFLOW_TRACE", "1")
    monkeypatch.setenv("RECRUIT_AI_WORKFLOW_TRACE_PATH", str(trace_path))
    monkeypatch.setattr(
        _context,
        "config",
        lambda: {
            "tools": {"surface": "developer"},
            "storage": {"local_data_dir": str(tmp_path)},
        },
    )

    result = asyncio.run(
        mcp_server.app.call_tool("get_tool_catalog", {"include_hidden": False})
    )
    events = read_workflow_traces(trace_path)

    assert result is not None
    assert len(events) == 1
    assert events[0]["tool_name"] == "get_tool_catalog"
    assert events[0]["success"] is True
    assert events[0]["argument_summary"] == {"include_hidden": False}
    assert events[0]["duration_ms"] >= 0
