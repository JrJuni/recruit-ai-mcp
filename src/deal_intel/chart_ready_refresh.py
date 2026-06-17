from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any

from deal_intel.chart_ready_contracts import (
    CUSTOMER_THEMES_COLLECTION,
    PIPELINE_TREND_COLLECTION,
    WEEKLY_PIPELINE_COLLECTION,
    load_chart_ready_collection_spec,
)
from deal_intel.reports.weekly_pipeline import build_weekly_pipeline_rows
from deal_intel.schema.customer_theme_insights import (
    MAX_TOP_K,
    build_customer_theme_breakdown,
    build_customer_theme_ranking,
)
from deal_intel.schema.customer_themes import THEME_TAXONOMY
from deal_intel.schema.evidence_sources import evidence_source_label
from deal_intel.schema.metrics import (
    OPEN_STAGES,
    HealthBandThresholds,
    PipelineTimingSettings,
    ReportingContext,
    WinRateSettings,
)
from deal_intel.schema.pipeline_metrics import (
    CANONICAL_STAGE_ORDER,
    build_pipeline_health_summary,
)
from deal_intel.schema.pipeline_trends import (
    DEFAULT_LOOKBACK_DAYS,
    build_pipeline_trend_summary,
    validate_lookback_days,
)
from deal_intel.schema.qualification_read import select_qualification_snapshot

TARGET_WEEKLY_PIPELINE = "weekly_pipeline"
TARGET_CUSTOMER_THEMES = "customer_themes"
TARGET_PIPELINE_TREND = "pipeline_trend"
TARGET_ALL = "all"

VALID_REFRESH_TARGETS = (
    TARGET_ALL,
    TARGET_WEEKLY_PIPELINE,
    TARGET_CUSTOMER_THEMES,
    TARGET_PIPELINE_TREND,
)

TARGET_COLLECTIONS = {
    TARGET_WEEKLY_PIPELINE: WEEKLY_PIPELINE_COLLECTION,
    TARGET_CUSTOMER_THEMES: CUSTOMER_THEMES_COLLECTION,
    TARGET_PIPELINE_TREND: PIPELINE_TREND_COLLECTION,
}

KPI_DELTA_KEYS = (
    "active_deal_count",
    "open_deal_count",
    "open_pipeline_value_amount",
    "avg_health_pct",
    "attention_deal_count",
    "won_deal_count",
    "lost_deal_count",
)


def refresh_chart_ready_collections(
    mongo: Any,
    cfg: dict,
    *,
    target: str = TARGET_ALL,
    as_of: str | date | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    apply: bool = False,
    generated_at: datetime | None = None,
) -> dict:
    """Build and optionally write chart-ready rows for Atlas Charts.

    The refresh path is deterministic and deliberately LLM/embedding-free.
    Dry-run returns row counts and bounded sample rows only. Apply replaces the
    materialized rows for the same refresh scope so stale rows do not linger in
    Atlas Charts.
    """

    if target not in VALID_REFRESH_TARGETS:
        valid = ", ".join(VALID_REFRESH_TARGETS)
        raise ValueError(f"target must be one of: {valid}")
    validate_lookback_days(lookback_days)
    reporting = ReportingContext.from_config(
        cfg,
        as_of=as_of,
        generated_at=generated_at,
    )

    selected = (
        tuple(TARGET_COLLECTIONS)
        if target == TARGET_ALL
        else (target,)
    )
    target_results = []
    for item in selected:
        collection = TARGET_COLLECTIONS[item]
        spec = load_chart_ready_collection_spec(collection)
        rows, scope_filter, warnings = _build_target_rows(
            item,
            mongo=mongo,
            cfg=cfg,
            reporting=reporting,
            lookback_days=lookback_days,
            spec=spec,
        )
        result = {
            "target": item,
            "collection": collection,
            "dashboard_id": spec["dashboard_id"],
            "row_count": len(rows),
            "scope_filter": scope_filter,
            "storage_written": False,
            "write_result": None,
            "sample_rows": rows[:3],
            "warnings": warnings,
        }
        if apply:
            if not hasattr(mongo, "replace_chart_ready_rows"):
                raise RuntimeError(
                    "chart-ready apply requires MongoDB storage; "
                    "run dry-run in sample mode or switch to full/mongo"
                )
            result["write_result"] = mongo.replace_chart_ready_rows(
                collection=collection,
                scope_filter=scope_filter,
                rows=rows,
            )
            result["storage_written"] = True
        target_results.append(result)

    warnings = _dedupe(
        warning
        for result in target_results
        for warning in result.get("warnings", [])
    )
    return {
        "ok": True,
        "dry_run": not apply,
        "target": target,
        "targets": target_results,
        "target_count": len(target_results),
        "total_row_count": sum(result["row_count"] for result in target_results),
        "storage_written": bool(apply),
        "lookback_days": lookback_days,
        **reporting.to_dict(),
        "warnings": warnings,
    }


def _build_target_rows(
    target: str,
    *,
    mongo: Any,
    cfg: dict,
    reporting: ReportingContext,
    lookback_days: int,
    spec: dict,
) -> tuple[list[dict], dict, list[str]]:
    if target == TARGET_WEEKLY_PIPELINE:
        deals = mongo.list_deals_for_metrics()
        rows, warnings = build_weekly_pipeline_chart_ready_rows(
            deals,
            cfg=cfg,
            reporting=reporting,
            spec=spec,
        )
        return rows, _point_scope(spec, reporting), warnings
    if target == TARGET_CUSTOMER_THEMES:
        deals = mongo.list_deals_for_metrics()
        rows, warnings = build_customer_themes_chart_ready_rows(
            deals,
            reporting=reporting,
            spec=spec,
        )
        return rows, _point_scope(spec, reporting), warnings
    if target == TARGET_PIPELINE_TREND:
        start_date = reporting.as_of - timedelta(days=lookback_days)
        snapshots = mongo.list_analytics_snapshots(
            start_date=start_date.isoformat(),
            end_date=reporting.as_of.isoformat(),
        )
        rows, warnings = build_pipeline_trend_chart_ready_rows(
            snapshots,
            reporting=reporting,
            spec=spec,
            lookback_days=lookback_days,
        )
        return rows, _trend_scope(spec, reporting, lookback_days), warnings
    raise ValueError(f"unsupported target {target!r}")


def build_weekly_pipeline_chart_ready_rows(
    deals: list[dict],
    *,
    cfg: dict,
    reporting: ReportingContext,
    spec: dict | None = None,
) -> tuple[list[dict], list[str]]:
    spec = spec or load_chart_ready_collection_spec(WEEKLY_PIPELINE_COLLECTION)
    health_thresholds = HealthBandThresholds.from_config(cfg)
    timing_settings = PipelineTimingSettings.from_config(cfg)
    win_rate_settings = WinRateSettings.from_config(cfg)
    summary = build_pipeline_health_summary(
        deals,
        as_of=reporting.as_of,
        health_thresholds=health_thresholds,
        timing_settings=timing_settings,
        win_rate_settings=win_rate_settings,
    )
    report = build_weekly_pipeline_rows(
        deals,
        as_of=reporting.as_of,
        health_thresholds=health_thresholds,
        timing_settings=timing_settings,
    )
    rows: list[dict] = []
    rows.append(_weekly_kpi_row(summary, reporting=reporting, spec=spec))
    rows.extend(_weekly_stage_rows(summary, reporting=reporting, spec=spec))
    rows.extend(_weekly_health_band_rows(summary, reporting=reporting, spec=spec))
    rows.extend(_weekly_attention_rows(report, reporting=reporting, spec=spec))
    rows.extend(_weekly_gap_rows(deals, reporting=reporting, spec=spec))
    return rows, _dedupe([*summary.get("warnings", []), *report.get("warnings", [])])


def build_customer_themes_chart_ready_rows(
    deals: list[dict],
    *,
    reporting: ReportingContext,
    spec: dict | None = None,
) -> tuple[list[dict], list[str]]:
    spec = spec or load_chart_ready_collection_spec(CUSTOMER_THEMES_COLLECTION)
    rows: list[dict] = []
    ranking = build_customer_theme_ranking(
        deals,
        dimension="all",
        stage="active",
        top_k=MAX_TOP_K,
    )
    for theme in ranking["themes"]:
        rows.append(
            {
                **_point_row_base(
                    spec,
                    "theme_overview",
                    f"theme_overview:{theme['theme_key']}",
                    reporting,
                ),
                "theme_key": theme["theme_key"],
                "label": theme["label"],
                "deal_count": theme["deal_count"],
                "avg_importance": theme["avg_importance"],
            }
        )
    rows.extend(
        _theme_breakdown_rows(
            deals,
            spec=spec,
            reporting=reporting,
            row_type="decision_criteria_by_stage",
            dimension="decision_criteria",
            group_by="stage",
            group_field="stage",
        )
    )
    rows.extend(
        _theme_breakdown_rows(
            deals,
            spec=spec,
            reporting=reporting,
            row_type="pain_by_industry",
            dimension="identify_pain",
            group_by="industry",
            group_field="industry",
        )
    )
    rows.extend(
        _theme_breakdown_rows(
            deals,
            spec=spec,
            reporting=reporting,
            row_type="pain_by_industry_tag",
            dimension="identify_pain",
            group_by="industry_tag",
            group_field="industry_tag",
        )
    )
    rows.extend(_theme_evidence_rows(deals, spec=spec, reporting=reporting))
    return rows, ranking.get("warnings", [])


def build_pipeline_trend_chart_ready_rows(
    snapshots: list[dict],
    *,
    reporting: ReportingContext,
    spec: dict | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> tuple[list[dict], list[str]]:
    spec = spec or load_chart_ready_collection_spec(PIPELINE_TREND_COLLECTION)
    summary = build_pipeline_trend_summary(
        snapshots,
        as_of=reporting.as_of,
        lookback_days=lookback_days,
    )
    rows = [
        {
            **_trend_row_base(spec, "trend_kpi", "trend_kpi", reporting, lookback_days),
            "snapshot_count": summary["snapshot_count"],
            "deal_count": summary["deal_count"],
            "start_active_deal_count": summary["start"].get("active_deal_count"),
            "end_active_deal_count": summary["end"].get("active_deal_count"),
            "delta_active_deal_count": summary["delta"].get("active_deal_count"),
            "start_open_pipeline_value_amount": summary["start"].get(
                "open_pipeline_value_amount"
            ),
            "end_open_pipeline_value_amount": summary["end"].get(
                "open_pipeline_value_amount"
            ),
            "delta_open_pipeline_value_amount": summary["delta"].get(
                "open_pipeline_value_amount"
            ),
            "pipeline_value_currency": summary["end"].get(
                "open_pipeline_value_currency"
            ),
            "pipeline_value_currencies": summary["end"].get(
                "open_pipeline_value_currencies"
            ),
        }
    ]
    for key in KPI_DELTA_KEYS:
        rows.append(
            {
                **_trend_row_base(
                    spec,
                    "trend_delta",
                    f"trend_delta:{key}",
                    reporting,
                    lookback_days,
                ),
                "metric": key,
                "start_value": summary["start"].get(key),
                "end_value": summary["end"].get(key),
                "delta": summary["delta"].get(key),
            }
        )
    return rows, summary.get("warnings", [])


def _weekly_kpi_row(
    summary: dict,
    *,
    reporting: ReportingContext,
    spec: dict,
) -> dict:
    kpis = summary["kpis"]
    return {
        **_point_row_base(spec, "kpi", "kpi", reporting),
        "deal_count": kpis["deal_count"],
        "active_deal_count": kpis["active_deal_count"],
        "open_deal_count": kpis["open_deal_count"],
        "open_pipeline_value_amount": kpis["open_pipeline_value_amount"],
        "open_pipeline_value_currency": kpis["pipeline_value_currency"],
        "open_pipeline_value_currencies": kpis["pipeline_value_currencies"],
        "avg_health_pct": kpis["avg_health_pct"],
        "health_coverage_pct": kpis["health_coverage_pct"],
        "attention_deal_count": kpis["attention_deal_count"],
    }


def _weekly_stage_rows(
    summary: dict,
    *,
    reporting: ReportingContext,
    spec: dict,
) -> list[dict]:
    rows = []
    for item in summary["stage_breakdown"]:
        stage = item["stage"]
        rows.append(
            {
                **_point_row_base(spec, "stage", f"stage:{stage}", reporting),
                "stage": stage,
                "stage_order": CANONICAL_STAGE_ORDER.index(stage),
                "count": item["count"],
                "pipeline_value_amount": item["pipeline_value_amount"],
                "pipeline_value_currency": item["pipeline_value_currency"],
                "mixed_pipeline_value_currency": item[
                    "mixed_pipeline_value_currency"
                ],
                "avg_health_pct": item["avg_health_pct"],
                "health_coverage_pct": item["health_coverage_pct"],
                "stuck_count": item["stuck_count"],
                "overdue_count": item["overdue_count"],
            }
        )
    return rows


def _weekly_health_band_rows(
    summary: dict,
    *,
    reporting: ReportingContext,
    spec: dict,
) -> list[dict]:
    return [
        {
            **_point_row_base(
                spec,
                "health_band",
                f"health_band:{health_band}",
                reporting,
            ),
            "health_band": health_band,
            "count": count,
        }
        for health_band, count in summary["health_bands"].items()
    ]


def _weekly_attention_rows(
    report: dict,
    *,
    reporting: ReportingContext,
    spec: dict,
) -> list[dict]:
    rows = []
    for row in report["rows"]:
        if not row.get("attention_reasons"):
            continue
        deal_id = str(row.get("deal_id") or "")
        rows.append(
            {
                **_point_row_base(
                    spec,
                    "attention_deal",
                    f"attention_deal:{deal_id}",
                    reporting,
                ),
                "deal_id": row.get("deal_id"),
                "company": row.get("company"),
                "deal_stage": row.get("deal_stage"),
                "expected_close_date": row.get("expected_close_date"),
                "days_in_stage": row.get("days_in_stage"),
                "is_overdue": row.get("is_overdue"),
                "is_stuck": row.get("is_stuck"),
                "health_pct": row.get("health_pct"),
                "health_band": row.get("health_band"),
                "attention_reasons": row.get("attention_reasons"),
                "deal_size_amount": row.get("deal_size_amount"),
                "deal_size_currency": row.get("deal_size_currency"),
            }
        )
    return rows


def _weekly_gap_rows(
    deals: list[dict],
    *,
    reporting: ReportingContext,
    spec: dict,
) -> list[dict]:
    counts: Counter[str] = Counter()
    for deal in deals:
        if deal.get("deal_stage") not in OPEN_STAGES:
            continue
        for gap in select_qualification_snapshot(deal).gaps:
            counts[str(gap)] += 1
    return [
        {
            **_point_row_base(
                spec,
                "qualification_gap",
                f"qualification_gap:{gap}",
                reporting,
            ),
            "gap": gap,
            "count": count,
        }
        for gap, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _theme_breakdown_rows(
    deals: list[dict],
    *,
    spec: dict,
    reporting: ReportingContext,
    row_type: str,
    dimension: str,
    group_by: str,
    group_field: str,
) -> list[dict]:
    breakdown = build_customer_theme_breakdown(
        deals,
        dimension=dimension,
        stage="active",
        group_by=group_by,
        top_k=MAX_TOP_K,
    )
    rows = []
    for group in breakdown["groups"]:
        group_value = group["group_value"] or "unknown"
        for theme in group["themes"]:
            rows.append(
                {
                    **_point_row_base(
                        spec,
                        row_type,
                        f"{row_type}:{group_value}:{theme['theme_key']}",
                        reporting,
                    ),
                    group_field: group_value,
                    "theme_key": theme["theme_key"],
                    "label": theme["label"],
                    "count": theme["deal_count"],
                    "avg_importance": theme["avg_importance"],
                }
            )
    return rows


def _theme_evidence_rows(
    deals: list[dict],
    *,
    spec: dict,
    reporting: ReportingContext,
) -> list[dict]:
    evidence_rows = []
    for deal in deals:
        if deal.get("deal_stage") not in OPEN_STAGES:
            continue
        for index, theme in enumerate(deal.get("customer_themes") or []):
            if not isinstance(theme, dict):
                continue
            evidence = theme.get("evidence")
            if not isinstance(evidence, str) or not evidence.strip():
                continue
            theme_key = str(theme.get("theme_key") or "")
            evidence_rows.append(
                {
                    "deal_id": deal.get("deal_id"),
                    "company": deal.get("company"),
                    "deal_stage": deal.get("deal_stage"),
                    "theme_key": theme_key,
                    "label": theme.get("label") or THEME_TAXONOMY.get(theme_key, theme_key),
                    "dimension": theme.get("dimension"),
                    "importance": theme.get("importance"),
                    "evidence": evidence.strip(),
                    "source_label": evidence_source_label(theme),
                    "interaction_type": theme.get("interaction_type"),
                    "source_confidence": theme.get("source_confidence"),
                    "interaction_date": theme.get("interaction_date"),
                    "meeting_date": theme.get("meeting_date"),
                    "_sort_date": theme.get("interaction_date")
                    or theme.get("meeting_date")
                    or "",
                    "_index": index,
                }
            )
    evidence_rows.sort(
        key=lambda row: (
            -_safe_int(row.get("importance")),
            -_date_ordinal(row.get("_sort_date")),
            str(row.get("company") or ""),
            str(row.get("evidence") or ""),
        ),
    )
    rows = []
    for index, row in enumerate(evidence_rows[:50]):
        deal_id = str(row.get("deal_id") or "unknown")
        theme_key = str(row.get("theme_key") or "unknown")
        dimension = str(row.get("dimension") or "unknown")
        rows.append(
            {
                **_point_row_base(
                    spec,
                    "theme_evidence",
                    f"theme_evidence:{index}:{deal_id}:{theme_key}:{dimension}",
                    reporting,
                ),
                **{key: value for key, value in row.items() if not key.startswith("_")},
            }
        )
    return rows


def _point_row_base(
    spec: dict,
    row_type: str,
    row_key: str,
    reporting: ReportingContext,
) -> dict:
    return {
        "dashboard_id": spec["dashboard_id"],
        "chart_id": spec["row_types"][row_type]["chart_id"],
        "row_type": row_type,
        "row_key": row_key,
        "as_of": reporting.as_of.isoformat(),
        "source_collections": list(spec["source_collections"]),
        "schema_version": spec["version"],
        "generated_at": reporting.generated_at.isoformat(),
    }


def _trend_row_base(
    spec: dict,
    row_type: str,
    row_key: str,
    reporting: ReportingContext,
    lookback_days: int,
) -> dict:
    window_start = reporting.as_of - timedelta(days=lookback_days)
    return {
        "dashboard_id": spec["dashboard_id"],
        "chart_id": spec["row_types"][row_type]["chart_id"],
        "row_type": row_type,
        "row_key": row_key,
        "window_start": window_start.isoformat(),
        "window_end": reporting.as_of.isoformat(),
        "lookback_days": lookback_days,
        "source_collections": list(spec["source_collections"]),
        "schema_version": spec["version"],
        "generated_at": reporting.generated_at.isoformat(),
    }


def _point_scope(spec: dict, reporting: ReportingContext) -> dict:
    return {
        "dashboard_id": spec["dashboard_id"],
        "as_of": reporting.as_of.isoformat(),
        "schema_version": spec["version"],
    }


def _trend_scope(
    spec: dict,
    reporting: ReportingContext,
    lookback_days: int,
) -> dict:
    return {
        "dashboard_id": spec["dashboard_id"],
        "window_start": (reporting.as_of - timedelta(days=lookback_days)).isoformat(),
        "window_end": reporting.as_of.isoformat(),
        "lookback_days": lookback_days,
        "schema_version": spec["version"],
    }


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def _date_ordinal(value: Any) -> int:
    if not isinstance(value, str) or not value:
        return 0
    try:
        return date.fromisoformat(value[:10]).toordinal()
    except ValueError:
        return 0


def _dedupe(items: Any) -> list[str]:
    seen = set()
    unique = []
    for item in items:
        text = str(item)
        if text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique
