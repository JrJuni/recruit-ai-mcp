from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

app = typer.Typer(help="deal-intel CLI")

SENSITIVE_RESULT_KEYS = {"raw_notes", "contacts", "summary_embedding"}


@app.command("login-chatgpt")
def login_chatgpt(
    force: bool = typer.Option(
        False,
        "--force",
        help="Re-authenticate even with a valid cached token",
    ),
) -> None:
    """Authenticate with ChatGPT OAuth (opens browser). Run once before first use."""
    from deal_intel._env import load_config
    from deal_intel.providers import llm as _llm

    cfg = load_config()
    # Force chatgpt_oauth regardless of defaults so this command always works
    cfg.setdefault("llm", {})["provider"] = "chatgpt_oauth"
    provider = _llm.make_llm_provider(cfg)
    assert isinstance(provider, _llm.ChatGPTOAuthProvider)
    result = provider.login(force=force)
    typer.echo(f"ok  model={result['model']}  token_path={result['token_path']}")


@app.command("backfill-customer-themes")
def backfill_customer_themes(
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Write extracted themes to MongoDB. Without this flag, run as dry-run.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Reprocess meetings that already have customer_themes.",
    ),
    limit: int = typer.Option(0, "--limit", min=0, help="Maximum deals to scan; 0 means all."),
) -> None:
    """Extract customer themes for existing meeting records."""
    from deal_intel import _context
    from deal_intel.tools import backfill_customer_themes as _t

    result = _t.handle(
        mongo=_context.mongo(),
        llm=_context.llm_provider(),
        limit=limit,
        force=force,
        dry_run=not apply,
    )
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("render-atlas-dashboard")
def render_atlas_dashboard(
    as_of: str | None = typer.Option(
        None,
        "--as-of",
        help="Business date for rendered Atlas Charts placeholders, YYYY-MM-DD.",
    ),
    dashboard: str = typer.Option(
        "weekly_pipeline_review",
        "--dashboard",
        help="Dashboard id: weekly_pipeline_review, pipeline_trend, or customer_themes.",
    ),
    chart_id: str | None = typer.Option(
        None,
        "--chart-id",
        help="Optional chart id. If omitted, render the full dashboard spec.",
    ),
    lookback_days: int = typer.Option(
        7,
        "--lookback-days",
        help="Trend lookback window, used only by the pipeline_trend dashboard.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional path to write rendered JSON. Prints to stdout when omitted.",
    ),
) -> None:
    """Render Atlas Charts dashboard JSON for Atlas UI copy/paste."""
    from deal_intel._env import load_config
    from deal_intel.reports.atlas_charts import (
        render_chart_pipeline,
        render_dashboard_spec,
    )

    cfg = load_config()
    try:
        payload = (
            render_chart_pipeline(
                chart_id,
                cfg,
                as_of=as_of,
                lookback_days=lookback_days,
                dashboard=dashboard,
            )
            if chart_id
            else render_dashboard_spec(
                dashboard,
                cfg,
                as_of=as_of,
                lookback_days=lookback_days,
            )
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output is None:
        typer.echo(text)
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text + "\n", encoding="utf-8")
    typer.echo(str(output.resolve()))


@app.command("crosscheck-weekly-dashboard")
def crosscheck_weekly_dashboard(
    as_of: str | None = typer.Option(
        None,
        "--as-of",
        help="Business date for cross-checking metrics, reports, and Atlas pipelines.",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Directory for the generated CSV/Markdown report artifacts.",
    ),
) -> None:
    """Cross-check get_metrics, weekly reports, and Atlas Charts pipelines."""
    from deal_intel import _context
    from deal_intel.reports.atlas_charts import render_chart_pipeline
    from deal_intel.reports.dashboard_crosscheck import (
        build_weekly_pipeline_dashboard_crosscheck,
    )
    from deal_intel.tools import export_report as _export_report
    from deal_intel.tools import get_metrics as _get_metrics

    cfg = _context.config()
    mongo = _context.mongo()
    metrics_result = _get_metrics.handle(
        mongo=mongo,
        cfg=cfg,
        metric_type="pipeline_health",
        as_of=as_of,
    )
    report_result = _export_report.handle(
        mongo=mongo,
        cfg=cfg,
        report_type="weekly_pipeline",
        output_dir=str(output_dir) if output_dir is not None else None,
        as_of=as_of,
    )
    atlas_results = {
        chart_id: mongo.aggregate_deals(
            render_chart_pipeline(chart_id, cfg, as_of=as_of)
        )
        for chart_id in (
            "pipeline_kpis",
            "stage_breakdown",
            "health_bands",
            "attention_deals",
            "meddpicc_gap_distribution",
        )
    }
    result = build_weekly_pipeline_dashboard_crosscheck(
        metrics_result=metrics_result,
        report_result=report_result,
        atlas_results=atlas_results,
    )
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise typer.Exit(code=1)


@app.command("smoke-deal-review")
def smoke_deal_review(
    deal_id: str | None = typer.Option(
        None,
        "--deal-id",
        help="Exact deal_id to review. Overrides --company and --limit selection.",
    ),
    company: str | None = typer.Option(
        None,
        "--company",
        help="Case-insensitive company name substring to review.",
    ),
    limit: int = typer.Option(
        5,
        "--limit",
        min=1,
        max=20,
        help="Maximum deals to review when --deal-id is omitted.",
    ),
    as_of: str | None = typer.Option(
        None,
        "--as-of",
        help="Business date for deal review, YYYY-MM-DD.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print full structured JSON instead of concise text.",
    ),
) -> None:
    """Run local read-only get_deal_review smoke checks without a Desktop MCP client."""
    from deal_intel import _context
    from deal_intel.errors import MCPError
    from deal_intel.tools import get_deal_review as _get_deal_review

    cfg = _context.config()
    mongo = _context.mongo()
    try:
        deals = mongo.list_deals_for_metrics()
        selected = _select_deal_review_smoke_deals(
            deals,
            deal_id=deal_id,
            company=company,
            limit=limit,
        )
        results = [
            _get_deal_review.handle(
                mongo=mongo,
                cfg=cfg,
                deal_id=str(deal["deal_id"]),
                as_of=as_of,
            )
            for deal in selected
        ]
    except MCPError as exc:
        _emit_smoke_error(exc.to_envelope(), json_output=json_output)
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        _emit_smoke_error(
            {
                "ok": False,
                "error_code": "INVALID_INPUT",
                "stage": "preflight",
                "message": str(exc),
                "hint": None,
                "retryable": False,
            },
            json_output=json_output,
        )
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        _emit_smoke_error(
            {
                "ok": False,
                "error_code": "INTERNAL",
                "stage": "cli",
                "message": f"{type(exc).__name__}: {exc}",
                "hint": None,
                "retryable": False,
            },
            json_output=json_output,
        )
        raise typer.Exit(code=1) from exc

    payload = {
        "ok": True,
        "as_of": results[0].get("as_of") if results else as_of,
        "timezone": results[0].get("timezone") if results else None,
        "count": len(results),
        "sensitive_field_check": {"ok": True},
        "results": results,
    }
    if _contains_sensitive_result_key(payload):
        payload["ok"] = False
        payload["sensitive_field_check"]["ok"] = False
        _emit_smoke_error(
            {
                "ok": False,
                "error_code": "SENSITIVE_FIELD_EXPOSED",
                "stage": "cli",
                "message": "Smoke result contains a restricted sensitive field key.",
                "hint": {"blocked_keys": sorted(SENSITIVE_RESULT_KEYS)},
                "retryable": False,
            },
            json_output=json_output,
        )
        raise typer.Exit(code=2)

    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    typer.echo(_format_deal_review_smoke(payload))


def _select_deal_review_smoke_deals(
    deals: list[dict],
    *,
    deal_id: str | None,
    company: str | None,
    limit: int,
) -> list[dict]:
    if deal_id is not None and deal_id.strip():
        needle = deal_id.strip()
        for deal in deals:
            if deal.get("deal_id") == needle:
                return [deal]
        raise ValueError(f"deal_id {needle!r} not found")

    selected = deals
    if company is not None and company.strip():
        needle = company.strip().casefold()
        selected = [
            deal
            for deal in deals
            if needle in str(deal.get("company") or "").casefold()
        ]
        if not selected:
            raise ValueError(f"company containing {company.strip()!r} not found")

    selected = [
        deal
        for deal in selected
        if isinstance(deal.get("deal_id"), str) and deal.get("deal_id")
    ]
    if not selected:
        raise ValueError("no deals available for smoke review")
    return selected[:limit]


def _contains_sensitive_result_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            key in SENSITIVE_RESULT_KEYS or _contains_sensitive_result_key(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_sensitive_result_key(item) for item in value)
    return False


def _emit_smoke_error(payload: dict, *, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2), err=True)
        return
    typer.echo(
        f"Smoke failed: {payload.get('error_code')} "
        f"({payload.get('stage')}) - {payload.get('message')}",
        err=True,
    )


def _format_deal_review_smoke(payload: dict) -> str:
    lines = [
        f"Deal Review Smoke (as_of={payload.get('as_of')}, count={payload.get('count')})",
        "",
    ]
    for result in payload.get("results", []):
        review = result.get("review") or {}
        interpretation = review.get("health_interpretation") or {}
        lines.extend(
            [
                f"[{review.get('company')}] {review.get('deal_id')}",
                (
                    f"Stage: {review.get('deal_stage')} | "
                    f"Industry: {review.get('industry')} | "
                    f"Value: {_format_krw(review.get('deal_size_krw'))} "
                    f"({review.get('deal_size_status') or 'unknown'})"
                ),
                (
                    f"Band: {interpretation.get('review_band')} | "
                    f"Alert: {interpretation.get('alert_level')} | "
                    f"Uncertainty: {interpretation.get('uncertainty_level')}"
                ),
                (
                    f"Health: {interpretation.get('legacy_health_pct')} | "
                    f"Evidence coverage: {interpretation.get('evidence_coverage_pct')}% "
                    f"({interpretation.get('filled_meddpicc_count')}/"
                    f"{interpretation.get('total_meddpicc_count')})"
                ),
                f"Attention: {_format_string_list(review.get('attention_reasons') or [])}",
                f"Missing: {_format_gap_list(review.get('missing_information') or [])}",
                f"Risks: {_format_risk_list(review.get('confirmed_risks') or [])}",
                "Questions: "
                f"{_format_string_list(review.get('recommended_questions') or [], limit=3)}",
                f"Warnings: {_format_string_list(review.get('warnings') or [])}",
                "",
            ]
        )
    lines.append("Sensitive field check: passed")
    return "\n".join(lines)


def _format_krw(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return "unknown"
    return f"{int(value):,} KRW"


def _format_string_list(items: list[Any], *, limit: int = 5) -> str:
    values = [str(item) for item in items if item is not None]
    if not values:
        return "none"
    visible = values[:limit]
    suffix = f" (+{len(values) - limit} more)" if len(values) > limit else ""
    return "; ".join(visible) + suffix


def _format_gap_list(gaps: list[dict]) -> str:
    if not gaps:
        return "none"
    values = [
        f"{gap.get('field')}:{gap.get('status')}:{gap.get('severity')}"
        for gap in gaps[:3]
    ]
    suffix = f" (+{len(gaps) - 3} more)" if len(gaps) > 3 else ""
    return "; ".join(values) + suffix


def _format_risk_list(risks: list[dict]) -> str:
    if not risks:
        return "none"
    values = [
        f"{risk.get('risk_id')}:{risk.get('severity')}"
        for risk in risks[:3]
    ]
    suffix = f" (+{len(risks) - 3} more)" if len(risks) > 3 else ""
    return "; ".join(values) + suffix


if __name__ == "__main__":
    app()
