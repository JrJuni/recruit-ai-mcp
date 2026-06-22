from __future__ import annotations

import json

from typer.testing import CliRunner

from deal_intel import _env
from deal_intel.cli import app
from deal_intel.storage.local_personal import (
    LOCAL_PERSONAL_DEALS_FILE,
    LOCAL_PERSONAL_RECRUITING_FILE,
    LocalPersonalStore,
)
from deal_intel.storage.local_sample import LocalSampleClient
from deal_intel.workflow_trace import (
    build_workflow_trace_event,
    workflow_trace_path,
    write_trace_event,
)


def _write_sample_config(monkeypatch, tmp_path) -> None:
    user_config = tmp_path / "config.yaml"
    local_data_dir = tmp_path / "local-data"
    user_config.write_text(
        "storage:\n"
        "  backend: local_sample\n"
        f"  local_data_dir: {json.dumps(str(local_data_dir))}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(_env, "_USER_CONFIG_PATH", user_config)


def _seed_local_data(tmp_path) -> LocalPersonalStore:
    store = LocalPersonalStore(tmp_path / "local-data")
    store.upsert_deal(
        {
            "deal_id": "local-cli-1",
            "company": "Local CLI Co",
            "deal_stage": "discovery",
            "meetings": [
                {
                    "summary": "safe summary",
                    "raw_notes": "private raw note sentinel",
                }
            ],
            "contacts": [{"email": "private@example.com"}],
            "summary_embedding": [0.1, 0.2],
        }
    )
    store.insert_delete_audit_log(
        {
            "deal_id": "deleted-local-cli",
            "delete_reason": "test cleanup",
            "deal_snapshot": {
                "deal_id": "deleted-local-cli",
                "company": "Deleted Local CLI Co",
                "meetings": [{"raw_notes": "deleted private note sentinel"}],
                "contacts": [{"email": "deleted@example.com"}],
                "summary_embedding": [0.3],
            },
        }
    )
    store.upsert_recruiting_record(
        "candidates",
        {
            "candidate_id": "cand_local_cli",
            "name": "Local CLI Candidate",
            "raw_content": "private recruiting note sentinel",
        },
    )
    return store


def test_local_data_status_cli_reports_configured_directory(
    monkeypatch,
    tmp_path,
) -> None:
    _write_sample_config(monkeypatch, tmp_path)
    _seed_local_data(tmp_path)

    result = CliRunner().invoke(app, ["local-data", "status", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["dataset"] == "local_personal"
    assert payload["deal_count"] == 1
    assert payload["recruiting_record_count"] == 1
    assert payload["delete_audit_log_count"] == 1
    assert payload["data_dir"].endswith("local-data")


def test_local_data_export_cli_writes_secret_safe_snapshot(
    monkeypatch,
    tmp_path,
) -> None:
    _write_sample_config(monkeypatch, tmp_path)
    _seed_local_data(tmp_path)
    output_path = tmp_path / "exports" / "snapshot.json"

    result = CliRunner().invoke(
        app,
        [
            "local-data",
            "export",
            "--output",
            str(output_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    exported = json.loads(output_path.read_text(encoding="utf-8"))
    exported_text = json.dumps(exported, ensure_ascii=False)
    assert payload["ok"] is True
    assert payload["export_path"] == str(output_path)
    assert exported["export_type"] == "local_personal_snapshot"
    assert exported["counts"] == {
        "deals": 1,
        "recruiting_records": 1,
        "delete_audit_logs": 1,
    }
    assert "private raw note sentinel" not in exported_text
    assert "private recruiting note sentinel" not in exported_text
    assert "private@example.com" not in exported_text
    assert "summary_embedding" not in exported_text


def test_local_data_reset_cli_is_dry_run_by_default(
    monkeypatch,
    tmp_path,
) -> None:
    _write_sample_config(monkeypatch, tmp_path)
    store = _seed_local_data(tmp_path)

    result = CliRunner().invoke(app, ["local-data", "reset", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["dry_run"] is True
    assert payload["storage_written"] is False
    assert payload["would_delete_deal_count"] == 1
    assert payload["would_delete_recruiting_record_count"] == 1
    assert len(store.load_deals()) == 1
    assert sum(len(rows) for rows in store.load_recruiting_records().values()) == 1
    assert len(store.load_delete_audit_logs()) == 1


def test_local_data_reset_cli_force_clears_local_records_and_preserves_audit_logs(
    monkeypatch,
    tmp_path,
) -> None:
    _write_sample_config(monkeypatch, tmp_path)
    store = _seed_local_data(tmp_path)

    result = CliRunner().invoke(
        app,
        ["local-data", "reset", "--force", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["dry_run"] is False
    assert payload["storage_written"] is True
    assert payload["deleted_deal_count"] == 1
    assert payload["deleted_recruiting_record_count"] == 1
    assert store.load_deals() == []
    assert sum(len(rows) for rows in store.load_recruiting_records().values()) == 0
    assert len(store.load_delete_audit_logs()) == 1

    raw_payload = json.loads(
        (tmp_path / "local-data" / LOCAL_PERSONAL_DEALS_FILE).read_text(
            encoding="utf-8"
        )
    )
    raw_recruiting_payload = json.loads(
        (tmp_path / "local-data" / LOCAL_PERSONAL_RECRUITING_FILE).read_text(
            encoding="utf-8"
        )
    )
    client = LocalSampleClient(local_data_dir=tmp_path / "local-data")
    assert raw_payload["deals"] == []
    assert all(not rows for rows in raw_recruiting_payload["records"].values())
    assert client.ping()["data_mode"] == "local_personal"
    assert client.get_deal("sample-pavebridge") is None


def test_local_data_trace_status_cli_reports_recent_events(
    monkeypatch,
    tmp_path,
) -> None:
    _write_sample_config(monkeypatch, tmp_path)
    cfg = {"storage": {"local_data_dir": str(tmp_path / "local-data")}}
    path = workflow_trace_path(cfg, environ={})
    write_trace_event(
        path,
        build_workflow_trace_event(
            tool_name="create_candidate",
            arguments={"candidate_id": "cand_local_cli"},
            result={"ok": True},
            timestamp="2026-06-22T00:00:00+00:00",
        ),
        max_events=10,
    )
    write_trace_event(
        path,
        build_workflow_trace_event(
            tool_name="recommend_candidates_for_position",
            arguments={"position_id": "pos_local_cli"},
            result={"ok": True},
            timestamp="2026-06-22T00:00:01+00:00",
        ),
        max_events=10,
    )
    path.write_text(
        path.read_text(encoding="utf-8") + "{not-json}\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["local-data", "trace-status", "--limit", "1", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["trace_path"] == str(path)
    assert payload["trace_exists"] is True
    assert payload["event_count"] == 2
    assert payload["invalid_event_count"] == 1
    assert [event["tool_name"] for event in payload["recent_events"]] == [
        "recommend_candidates_for_position"
    ]


def test_local_data_trace_reset_cli_is_dry_run_first(
    monkeypatch,
    tmp_path,
) -> None:
    _write_sample_config(monkeypatch, tmp_path)
    cfg = {"storage": {"local_data_dir": str(tmp_path / "local-data")}}
    path = workflow_trace_path(cfg, environ={})
    write_trace_event(
        path,
        build_workflow_trace_event(tool_name="get_tool_catalog", result={"ok": True}),
        max_events=10,
    )

    dry_run = CliRunner().invoke(app, ["local-data", "trace-reset", "--json"])

    assert dry_run.exit_code == 0
    dry_run_payload = json.loads(dry_run.stdout)
    assert dry_run_payload["dry_run"] is True
    assert dry_run_payload["storage_written"] is False
    assert dry_run_payload["would_delete_event_count"] == 1
    assert dry_run_payload["invalid_event_count"] == 0
    assert path.exists()
    applied = CliRunner().invoke(
        app,
        ["local-data", "trace-reset", "--force", "--json"],
    )
    assert applied.exit_code == 0
    applied_payload = json.loads(applied.stdout)
    assert applied_payload["dry_run"] is False
    assert applied_payload["storage_written"] is True
    assert applied_payload["deleted_event_count"] == 1
    assert applied_payload["invalid_event_count"] == 0
    assert not path.exists()
