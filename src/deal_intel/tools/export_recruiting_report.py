from __future__ import annotations

from pathlib import Path
from typing import Any

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.reports.csv_export import save_report_csv
from deal_intel.reports.markdown_export import save_report_markdown
from deal_intel.reports.recruiting_pipeline import (
    REPORT_TYPE,
    build_recruiting_pipeline_markdown,
    build_recruiting_pipeline_report,
)
from deal_intel.schema.metrics import ReportingContext
from deal_intel.storage.diagnostics import storage_error_hint
from deal_intel.tools.export_report import (
    DEFAULT_OUTPUT_DIR,
    _artifact,
    _raise_io_error,
    _resolve_user_output_path,
)
from deal_intel.tools.recruiting_metrics import get_recruiting_metrics


def handle(
    mongo: Any,
    cfg: dict,
    *,
    output_dir: str | None = None,
    as_of: str | None = None,
    candidate_limit: int = 500,
    position_limit: int = 500,
    submission_limit: int = 1000,
    feedback_limit: int = 1000,
    position_status: str | None = None,
) -> dict[str, Any]:
    try:
        reporting = ReportingContext.from_config(cfg, as_of=as_of)
        resolved_output_dir = _resolve_output_dir(cfg, output_dir)
    except ValueError as exc:
        error_code = (
            ErrorCode.INVALID_INPUT
            if str(exc).startswith(("as_of", "output_dir"))
            else ErrorCode.CONFIG_ERROR
        )
        raise MCPError(
            error_code=error_code,
            stage=Stage.PREFLIGHT,
            message=str(exc),
            retryable=False,
        ) from exc

    try:
        metrics = get_recruiting_metrics(
            mongo,
            candidate_limit=candidate_limit,
            position_limit=position_limit,
            submission_limit=submission_limit,
            feedback_limit=feedback_limit,
            position_status=position_status,
        )
    except MCPError:
        raise
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=str(exc),
            hint=storage_error_hint(
                exc,
                operation="export_recruiting_report.read_recruiting_records",
            ),
            retryable=True,
        ) from exc

    report = build_recruiting_pipeline_report(metrics)
    markdown_summary = build_recruiting_pipeline_markdown(
        report,
        generated_at=reporting.generated_at,
        timezone=reporting.timezone,
    )
    csv_result = save_report_csv(
        report,
        output_dir=resolved_output_dir,
        generated_at=reporting.generated_at,
    )
    _raise_io_error(csv_result)
    markdown_result = save_report_markdown(
        markdown_summary["markdown"],
        report_type=REPORT_TYPE,
        output_dir=resolved_output_dir,
        generated_at=reporting.generated_at,
    )
    _raise_io_error(markdown_result)
    return {
        "ok": True,
        "report_type": REPORT_TYPE,
        **reporting.to_dict(),
        "filters": metrics["filters"],
        "limits": metrics["limits"],
        "row_count": report["row_count"],
        "warnings": report["warnings"],
        "metrics": markdown_summary["metrics"],
        "briefing": markdown_summary["briefing"],
        "output_dir": str(resolved_output_dir.resolve()),
        "artifacts": {
            "csv": _artifact(csv_result),
            "markdown": _artifact(markdown_result),
        },
        "csv_path": csv_result["path"],
        "markdown_path": markdown_result["path"],
    }


def _resolve_output_dir(cfg: dict, output_dir: str | None) -> Path:
    if output_dir not in (None, ""):
        if not isinstance(output_dir, str):
            raise ValueError("output_dir must be a string path")
        return _resolve_user_output_path(output_dir)

    reporting = cfg.get("reporting", {})
    if not isinstance(reporting, dict):
        raise ValueError("reporting must be a mapping")
    configured = reporting.get("recruiting_output_dir") or reporting.get("output_dir")
    if configured in (None, ""):
        return DEFAULT_OUTPUT_DIR.expanduser()
    if not isinstance(configured, str):
        raise ValueError("reporting.recruiting_output_dir must be a string path")
    return _resolve_user_output_path(configured)
