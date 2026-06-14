from __future__ import annotations

from datetime import datetime
from typing import Any

from deal_intel.reports.markdown_summary import validate_report_language

REPORT_TYPE = "pipeline_trend"

COLUMNS = [
    "section",
    "item",
    "start_value",
    "end_value",
    "delta",
    "count",
    "notes",
]

KPI_ORDER = [
    "active_deal_count",
    "open_deal_count",
    "open_pipeline_value_amount",
    "avg_health_pct",
    "attention_deal_count",
    "won_deal_count",
    "lost_deal_count",
]

KPI_LABELS = {
    "active_deal_count": "Active deals",
    "open_deal_count": "Open deals",
    "open_pipeline_value_amount": "Open pipeline value",
    "avg_health_pct": "Average health pct",
    "attention_deal_count": "Attention deals",
    "won_deal_count": "Won deals",
    "lost_deal_count": "Lost deals",
}

KPI_LABELS_KO = {
    "active_deal_count": "활성 딜",
    "open_deal_count": "오픈 딜",
    "open_pipeline_value_amount": "오픈 파이프라인 금액",
    "avg_health_pct": "평균 헬스",
    "attention_deal_count": "주의 필요 딜",
    "won_deal_count": "수주 딜",
    "lost_deal_count": "실주 딜",
}

TREND_TEXT = {
    "en": {
        "title": "Pipeline Trend Report",
        "generated_at": "Generated at",
        "window": "Window",
        "to": "to",
        "lookback_days": "Lookback days",
        "snapshot_count": "Snapshot count",
        "deal_count": "Deal count",
        "kpi_delta": "KPI Delta",
        "metric": "Metric",
        "start": "Start",
        "end": "End",
        "delta": "Delta",
        "stage_changes": "Stage Changes",
        "transition_count": "Transition count",
        "section": "Section",
        "item": "Item",
        "count": "Count",
        "warnings": "Warnings",
        "none": "none",
    },
    "ko": {
        "title": "파이프라인 추세 보고서",
        "generated_at": "생성 시각",
        "window": "기간",
        "to": "~",
        "lookback_days": "조회 일수",
        "snapshot_count": "스냅샷 수",
        "deal_count": "딜 수",
        "kpi_delta": "KPI 변화",
        "metric": "지표",
        "start": "시작",
        "end": "종료",
        "delta": "변화",
        "stage_changes": "스테이지 변화",
        "transition_count": "전환 수",
        "section": "구분",
        "item": "항목",
        "count": "건수",
        "warnings": "경고",
        "none": "없음",
    },
}


def build_pipeline_trend_report(summary: dict) -> dict:
    _validate_summary(summary)
    rows = _kpi_rows(summary)
    rows.extend(_stage_change_rows(summary))

    return {
        "report_type": REPORT_TYPE,
        "filters": dict(summary.get("filters") or {}),
        "window": dict(summary.get("window") or {}),
        "snapshot_count": int(summary.get("snapshot_count") or 0),
        "deal_count": int(summary.get("deal_count") or 0),
        "row_count": len(rows),
        "columns": COLUMNS,
        "rows": rows,
        "warnings": list(summary.get("warnings") or []),
        "metrics": {
            "window": dict(summary.get("window") or {}),
            "snapshot_count": int(summary.get("snapshot_count") or 0),
            "deal_count": int(summary.get("deal_count") or 0),
            "start": dict(summary.get("start") or {}),
            "end": dict(summary.get("end") or {}),
            "delta": dict(summary.get("delta") or {}),
            "stage_changes": dict(summary.get("stage_changes") or {}),
        },
    }


def build_pipeline_trend_markdown(
    report: dict,
    *,
    generated_at: datetime,
    language: str = "en",
) -> dict:
    if report.get("report_type") != REPORT_TYPE:
        raise ValueError("report_type must be pipeline_trend")
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")

    report_language = validate_report_language(language)
    metrics = report.get("metrics") or {}
    window = metrics.get("window") or {}
    lines = [
        f"# {_trend_text(report_language, 'title')}",
        "",
        f"- {_trend_text(report_language, 'generated_at')}: {generated_at.isoformat()}",
        f"- {_trend_text(report_language, 'window')}: "
        f"{window.get('start_date', '')} {_trend_text(report_language, 'to')} "
        f"{window.get('end_date', '')}",
        f"- {_trend_text(report_language, 'lookback_days')}: "
        f"{window.get('lookback_days', '')}",
        f"- {_trend_text(report_language, 'snapshot_count')}: "
        f"{metrics.get('snapshot_count', 0)}",
        f"- {_trend_text(report_language, 'deal_count')}: "
        f"{metrics.get('deal_count', 0)}",
        "",
        f"## {_trend_text(report_language, 'kpi_delta')}",
        "",
        "| "
        + " | ".join(
            _trend_text(report_language, key)
            for key in ("metric", "start", "end", "delta")
        )
        + " |",
        "|---|---:|---:|---:|",
    ]
    start = metrics.get("start") or {}
    end = metrics.get("end") or {}
    delta = metrics.get("delta") or {}
    for key in KPI_ORDER:
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_md(_kpi_label(key, report_language)),
                    _format_value(start.get(key)),
                    _format_value(end.get(key)),
                    _format_value(delta.get(key)),
                ]
            )
            + " |"
        )

    stage_changes = metrics.get("stage_changes") or {}
    lines.extend(
        [
            "",
            f"## {_trend_text(report_language, 'stage_changes')}",
            "",
            f"- {_trend_text(report_language, 'transition_count')}: "
            f"{stage_changes.get('transition_count', 0)}",
            "",
            "| "
            + " | ".join(
                _trend_text(report_language, key)
                for key in ("section", "item", "count")
            )
            + " |",
            "|---|---|---:|",
        ]
    )
    change_rows = [
        row for row in report.get("rows", []) if row.get("section") != "kpi"
    ]
    if change_rows:
        for row in change_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _escape_md(str(row.get("section") or "")),
                        _escape_md(str(row.get("item") or "")),
                        _format_value(row.get("count")),
                    ]
                )
                + " |"
            )
    else:
        none = _trend_text(report_language, "none")
        lines.append(f"| {none} | {none} | 0 |")

    warnings = report.get("warnings") or []
    if warnings:
        lines.extend(
            [
                "",
                f"## {_trend_text(report_language, 'warnings')}",
                "",
                *[f"- `{_escape_md(str(warning))}`" for warning in warnings],
            ]
        )

    markdown = "\n".join(lines) + "\n"
    return {"markdown": markdown, "language": report_language, "metrics": metrics}


def _validate_summary(summary: dict) -> None:
    for key in ("filters", "window", "start", "end", "delta", "stage_changes"):
        if not isinstance(summary.get(key), dict):
            raise ValueError(f"pipeline trend summary missing {key}")


def _kpi_rows(summary: dict) -> list[dict]:
    start = summary.get("start") or {}
    end = summary.get("end") or {}
    delta = summary.get("delta") or {}
    return [
        {
            "section": "kpi",
            "item": key,
            "start_value": start.get(key),
            "end_value": end.get(key),
            "delta": delta.get(key),
            "count": None,
            "notes": KPI_LABELS[key],
        }
        for key in KPI_ORDER
    ]


def _stage_change_rows(summary: dict) -> list[dict]:
    stage_changes = summary.get("stage_changes") or {}
    rows: list[dict] = []
    for section, values in (
        ("stage_transition", stage_changes.get("transitions") or {}),
        ("stage_entered", stage_changes.get("entered") or {}),
        ("stage_exited", stage_changes.get("exited") or {}),
    ):
        for item, count in sorted(values.items()):
            rows.append(
                {
                    "section": section,
                    "item": item,
                    "start_value": None,
                    "end_value": None,
                    "delta": None,
                    "count": int(count),
                    "notes": "",
                }
            )
    return rows


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _trend_text(language: str, key: str) -> str:
    return TREND_TEXT[language][key]


def _kpi_label(key: str, language: str) -> str:
    if language == "ko":
        return KPI_LABELS_KO.get(key, KPI_LABELS[key])
    return KPI_LABELS[key]


def _escape_md(value: str) -> str:
    return value.replace("|", "\\|").replace("\r", " ").replace("\n", " ")
