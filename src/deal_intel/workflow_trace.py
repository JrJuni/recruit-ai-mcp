from __future__ import annotations

import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from deal_intel.storage.local_personal import resolve_local_data_dir

DEFAULT_TRACE_FILE = "workflow_traces.jsonl"
DEFAULT_MAX_EVENTS = 500

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off"}
_SENSITIVE_KEY_PARTS = (
    "api_key",
    "authorization",
    "contact",
    "content",
    "email",
    "embedding",
    "mongodb_uri",
    "note",
    "password",
    "prompt",
    "raw",
    "secret",
    "token",
)
_SAFE_STRING_KEYS = {
    "candidate_id",
    "client_company_id",
    "collection",
    "deal_id",
    "decision_signal",
    "dry_run",
    "feedback_id",
    "interaction_id",
    "mode",
    "position_id",
    "stage",
    "status",
    "subject_id",
    "subject_type",
    "submission_id",
    "tool_name",
}
_SUMMARY_KEYS = {
    "dry_run",
    "error_code",
    "ok",
    "stage",
    "storage_written",
}


def workflow_trace_enabled(
    cfg: Mapping[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
) -> bool:
    env = environ if environ is not None else os.environ
    raw = _env_value(env, "RECRUIT_AI_WORKFLOW_TRACE", "DEAL_INTEL_WORKFLOW_TRACE")
    if raw.lower() in _TRUTHY:
        return True
    if raw.lower() in _FALSY:
        return False
    trace_cfg = _trace_cfg(cfg)
    return bool(trace_cfg.get("enabled", False))


def workflow_trace_path(
    cfg: Mapping[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    env = environ if environ is not None else os.environ
    env_path = _env_value(
        env,
        "RECRUIT_AI_WORKFLOW_TRACE_PATH",
        "DEAL_INTEL_WORKFLOW_TRACE_PATH",
    )
    if env_path:
        return Path(os.path.expandvars(env_path)).expanduser()
    trace_cfg = _trace_cfg(cfg)
    configured = str(trace_cfg.get("path") or "").strip()
    if configured:
        return Path(os.path.expandvars(configured)).expanduser()
    storage = cfg.get("storage") if isinstance(cfg.get("storage"), Mapping) else {}
    return resolve_local_data_dir(storage.get("local_data_dir")) / DEFAULT_TRACE_FILE


def workflow_trace_max_events(
    cfg: Mapping[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    env = environ if environ is not None else os.environ
    raw = _env_value(
        env,
        "RECRUIT_AI_WORKFLOW_TRACE_MAX_EVENTS",
        "DEAL_INTEL_WORKFLOW_TRACE_MAX_EVENTS",
    )
    value = _safe_int(raw)
    if value is None:
        value = _safe_int(_trace_cfg(cfg).get("max_events"))
    if value is None:
        value = DEFAULT_MAX_EVENTS
    return max(1, min(value, 10_000))


def build_workflow_trace_event(
    *,
    tool_name: str,
    arguments: Mapping[str, Any] | None = None,
    result: Any = None,
    error: BaseException | None = None,
    duration_ms: int | float | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    success = error is None and _result_success(result)
    return {
        "timestamp": timestamp or datetime.now(UTC).isoformat(timespec="seconds"),
        "tool_name": str(tool_name or "unknown")[:120],
        "duration_ms": round(float(duration_ms or 0), 3),
        "success": success,
        "error_category": None if success else _error_category(result=result, error=error),
        "argument_summary": summarize_trace_value(dict(arguments or {})),
        "result_summary": summarize_result(result, error=error),
    }


def append_workflow_trace(
    cfg: Mapping[str, Any],
    *,
    tool_name: str,
    arguments: Mapping[str, Any] | None = None,
    result: Any = None,
    error: BaseException | None = None,
    duration_ms: int | float | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not workflow_trace_enabled(cfg, environ=environ):
        return {"ok": True, "trace_written": False, "reason": "workflow_trace_disabled"}
    path = workflow_trace_path(cfg, environ=environ)
    max_events = workflow_trace_max_events(cfg, environ=environ)
    event = build_workflow_trace_event(
        tool_name=tool_name,
        arguments=arguments,
        result=result,
        error=error,
        duration_ms=duration_ms,
    )
    write_trace_event(path, event, max_events=max_events)
    return {
        "ok": True,
        "trace_written": True,
        "trace_path": str(path),
        "max_events": max_events,
    }


def build_workflow_trace_status(
    cfg: Mapping[str, Any],
    *,
    limit: int = 5,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    path = workflow_trace_path(cfg, environ=environ)
    events = read_workflow_traces(path)
    recent_limit = max(0, min(_safe_int(limit) or 0, 50))
    return {
        "ok": True,
        "enabled": workflow_trace_enabled(cfg, environ=environ),
        "trace_path": str(path),
        "trace_exists": path.exists(),
        "event_count": len(events),
        "max_events": workflow_trace_max_events(cfg, environ=environ),
        "recent_events": events[-recent_limit:] if recent_limit else [],
    }


def reset_workflow_trace(
    cfg: Mapping[str, Any],
    *,
    force: bool = False,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    path = workflow_trace_path(cfg, environ=environ)
    events = read_workflow_traces(path)
    payload = {
        "ok": True,
        "dry_run": not force,
        "trace_path": str(path),
        "trace_exists": path.exists(),
        "would_delete_event_count": len(events),
        "deleted_event_count": 0,
        "storage_written": False,
    }
    if not force:
        return payload
    if path.exists():
        path.unlink()
        payload["storage_written"] = True
        payload["trace_exists"] = False
    payload["deleted_event_count"] = len(events)
    return payload


def write_trace_event(path: str | Path, event: Mapping[str, Any], *, max_events: int) -> None:
    trace_path = Path(path)
    events = [*read_workflow_traces(trace_path), dict(event)]
    if max_events > 0:
        events = events[-max_events:]
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = trace_path.with_name(f"{trace_path.name}.tmp")
    tmp_path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in events),
        encoding="utf-8",
    )
    tmp_path.replace(trace_path)


def read_workflow_traces(path: str | Path) -> list[dict[str, Any]]:
    trace_path = Path(path)
    if not trace_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def summarize_trace_value(value: Any, *, key: str = "") -> Any:
    if _is_sensitive_key(key):
        return "[redacted]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        if _looks_secret_like(value):
            return "[redacted]"
        if _is_safe_string_key(key):
            return value[:200]
        return {
            "type": "str",
            "length": len(value),
            "sha256_8": sha256(value.encode("utf-8")).hexdigest()[:8],
        }
    if isinstance(value, Mapping):
        return {
            str(child_key): summarize_trace_value(child_value, key=str(child_key))
            for child_key, child_value in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, list | tuple | set):
        return {
            "type": "list",
            "length": len(value),
        }
    return {"type": type(value).__name__}


def summarize_result(result: Any, *, error: BaseException | None = None) -> dict[str, Any]:
    if error is not None:
        return {"error_type": type(error).__name__}
    if not isinstance(result, Mapping):
        return {"type": type(result).__name__}

    summary: dict[str, Any] = {
        key: summarize_trace_value(result.get(key), key=key)
        for key in sorted(_SUMMARY_KEYS.intersection(result))
    }
    nested_summary = result.get("summary")
    if isinstance(nested_summary, Mapping):
        summary["summary_counts"] = {
            str(key): value
            for key, value in sorted(nested_summary.items(), key=lambda item: str(item[0]))
            if isinstance(value, bool | int | float)
            or str(key).endswith(("_count", "_rate"))
        }
    warnings = result.get("warnings")
    if isinstance(warnings, list):
        summary["warning_count"] = len(warnings)
    summary["keys"] = sorted(str(key) for key in result.keys())[:50]
    return summary


def _trace_cfg(cfg: Mapping[str, Any]) -> Mapping[str, Any]:
    observability = cfg.get("observability")
    if not isinstance(observability, Mapping):
        return {}
    trace_cfg = observability.get("workflow_trace")
    return trace_cfg if isinstance(trace_cfg, Mapping) else {}


def _env_value(env: Mapping[str, str], primary: str, legacy: str) -> str:
    value = str(env.get(primary, "")).strip()
    if value:
        return value
    return str(env.get(legacy, "")).strip()


def _safe_int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _result_success(result: Any) -> bool:
    if isinstance(result, Mapping) and result.get("ok") is False:
        return False
    return True


def _error_category(*, result: Any, error: BaseException | None) -> str:
    if error is not None:
        return type(error).__name__
    if isinstance(result, Mapping):
        value = result.get("error_code") or result.get("stage")
        if value:
            return str(value)[:120]
    return "tool_returned_not_ok"


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


def _is_safe_string_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in _SAFE_STRING_KEYS or lowered.endswith("_id") or lowered.endswith("_type")


def _looks_secret_like(value: str) -> bool:
    lowered = value.lower()
    return (
        "mongodb://" in lowered
        or "mongodb+srv://" in lowered
        or value.startswith(("sk-", "sk_", "xoxb-", "ghp_"))
    )
