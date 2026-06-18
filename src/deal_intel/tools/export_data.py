from __future__ import annotations

from pathlib import Path

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.reports.csv_export import save_report_csv
from deal_intel.reports.data_export import (
    VALID_DATASETS,
    build_data_export,
    preview_rows_for_response,
)
from deal_intel.schema.metrics import (
    VALID_STAGES,
    HealthBandThresholds,
    PipelineTimingSettings,
    ReportingContext,
)
from deal_intel.storage.diagnostics import storage_error_hint
from deal_intel.storage.mongodb import MongoDBClient
from deal_intel.tools.export_report import (
    DEFAULT_OUTPUT_DIR,
    _artifact,
    _raise_io_error,
    _resolve_user_output_path,
)


def handle(
    mongo: MongoDBClient,
    cfg: dict,
    *,
    dataset: str,
    output_dir: str | None = None,
    stage: str | None = None,
    industry: str | None = None,
    as_of: str | None = None,
) -> dict:
    """Export deterministic CSV datasets for spreadsheet/ledger workflows."""
    if dataset not in VALID_DATASETS:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=f"dataset {dataset!r} is not valid",
            hint={"valid_datasets": sorted(VALID_DATASETS)},
            retryable=False,
        )
    if stage and stage not in VALID_STAGES:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=f"stage {stage!r} is not valid",
            hint={"valid_stages": sorted(VALID_STAGES)},
            retryable=False,
        )

    try:
        reporting = ReportingContext.from_config(cfg, as_of=as_of)
        health_thresholds = HealthBandThresholds.from_config(cfg)
        timing_settings = PipelineTimingSettings.from_config(cfg)
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
        deals = mongo.list_deals_for_metrics()
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=str(exc),
            hint=storage_error_hint(
                exc,
                operation="export_data.read_deals",
            ),
            retryable=True,
        ) from exc

    data_export = build_data_export(
        deals,
        dataset=dataset,
        as_of=reporting.as_of,
        health_thresholds=health_thresholds,
        timing_settings=timing_settings,
        stage=stage,
        industry=industry,
    )
    csv_result = save_report_csv(
        data_export,
        output_dir=resolved_output_dir,
        generated_at=reporting.generated_at,
    )
    _raise_io_error(csv_result)

    return {
        "ok": True,
        "tool": "export_data",
        "dataset": dataset,
        **reporting.to_dict(),
        "filters": data_export["filters"],
        "row_count": data_export["row_count"],
        "columns": data_export["columns"],
        "warnings": data_export["warnings"],
        "output_dir": str(resolved_output_dir.resolve()),
        "artifacts": {
            "csv": _artifact(csv_result),
        },
        "csv_path": csv_result["path"],
        "preview_rows": preview_rows_for_response(data_export["rows"]),
    }


def _resolve_output_dir(cfg: dict, output_dir: str | None) -> Path:
    if output_dir not in (None, ""):
        if not isinstance(output_dir, str):
            raise ValueError("output_dir must be a string path")
        return _resolve_user_output_path(output_dir)

    reporting = cfg.get("reporting", {})
    if not isinstance(reporting, dict):
        raise ValueError("reporting must be a mapping")
    configured = reporting.get("data_output_dir") or reporting.get("output_dir")
    if configured in (None, ""):
        return DEFAULT_OUTPUT_DIR.expanduser()
    if not isinstance(configured, str):
        raise ValueError("reporting.data_output_dir must be a string path")
    return _resolve_user_output_path(configured)
