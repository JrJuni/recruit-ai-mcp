from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from deal_intel.reports.markdown_summary import validate_report_language
from deal_intel.schema.metrics import DEFAULT_DEAL_CURRENCY

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
        "executive_summary": "Executive Summary",
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
        "sparse_history_note": (
            "Snapshot history is sparse. Treat this as a diagnostic view until "
            "more snapshots are collected."
        ),
        "open_value_sentence": (
            "Open pipeline value moved from {start} to {end} ({delta})."
        ),
        "active_sentence": "Active deals moved from {start} to {end} ({delta}).",
        "attention_sentence": (
            "Attention deals moved from {start} to {end} ({delta})."
        ),
        "terminal_sentence": "Closed movement: {won_delta} won, {lost_delta} lost.",
    },
    "ko": {
        "title": "파이프라인 추세 보고서",
        "generated_at": "생성 시각",
        "window": "기간",
        "to": "~",
        "lookback_days": "조회 일수",
        "snapshot_count": "스냅샷 수",
        "deal_count": "딜 수",
        "executive_summary": "핵심 요약",
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
        "sparse_history_note": (
            "스냅샷 이력이 아직 부족합니다. 더 많은 스냅샷이 쌓이기 전까지는 "
            "추세 확정보다 진단용으로 읽으세요."
        ),
        "open_value_sentence": (
            "오픈 파이프라인 금액은 {start}에서 {end}로 이동했습니다 ({delta})."
        ),
        "active_sentence": "활성 딜은 {start}에서 {end}로 이동했습니다 ({delta}).",
        "attention_sentence": (
            "주의 필요 딜은 {start}에서 {end}로 이동했습니다 ({delta})."
        ),
        "terminal_sentence": "종료 딜 변화: 수주 {won_delta}, 실주 {lost_delta}.",
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
    timezone: str = "UTC",
) -> dict:
    if report.get("report_type") != REPORT_TYPE:
        raise ValueError("report_type must be pipeline_trend")
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")

    report_language = validate_report_language(language)
    timezone_name = _validate_timezone(timezone)
    generated_display = _format_generated_at_display(
        generated_at,
        timezone_name=timezone_name,
    )
    metrics = report.get("metrics") or {}
    window = metrics.get("window") or {}
    warnings = report.get("warnings") or []
    lines = [
        f"# {_trend_text(report_language, 'title')}",
        "",
        f"- {_trend_text(report_language, 'generated_at')}: {generated_display}",
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
        f"## {_trend_text(report_language, 'executive_summary')}",
        "",
        *_trend_summary_lines(metrics, warnings, report_language),
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
                    _format_kpi_value(
                        key,
                        start.get(key),
                        start,
                        language=report_language,
                    ),
                    _format_kpi_value(
                        key,
                        end.get(key),
                        end,
                        language=report_language,
                    ),
                    _format_kpi_delta(
                        key,
                        delta.get(key),
                        end,
                        language=report_language,
                    ),
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
    return {
        "markdown": markdown,
        "language": report_language,
        "metrics": metrics,
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "generated_at_display": generated_display,
        "timezone": timezone_name,
    }


def _validate_summary(summary: dict) -> None:
    for key in ("filters", "window", "start", "end", "delta", "stage_changes"):
        if not isinstance(summary.get(key), dict):
            raise ValueError(f"pipeline trend summary missing {key}")


def _validate_timezone(value: str | None) -> str:
    timezone_name = value or "UTC"
    if not isinstance(timezone_name, str) or not timezone_name.strip():
        raise ValueError("timezone must be a non-empty IANA timezone")
    timezone_name = timezone_name.strip()
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("timezone must be a valid IANA timezone") from exc
    return timezone_name


def _format_generated_at_display(value: datetime, *, timezone_name: str) -> str:
    local_time = value.astimezone(ZoneInfo(timezone_name))
    return f"{local_time:%Y-%m-%d %H:%M:%S} {timezone_name}"


def _trend_summary_lines(metrics: dict, warnings: list[str], language: str) -> list[str]:
    start = metrics.get("start") or {}
    end = metrics.get("end") or {}
    delta = metrics.get("delta") or {}
    lines = [
        "- "
        + _trend_text(language, "open_value_sentence").format(
            start=_format_kpi_value(
                "open_pipeline_value_amount",
                start.get("open_pipeline_value_amount"),
                start,
                language=language,
            ),
            end=_format_kpi_value(
                "open_pipeline_value_amount",
                end.get("open_pipeline_value_amount"),
                end,
                language=language,
            ),
            delta=_format_kpi_delta(
                "open_pipeline_value_amount",
                delta.get("open_pipeline_value_amount"),
                end,
                language=language,
            ),
        ),
        "- "
        + _trend_text(language, "active_sentence").format(
            start=_format_kpi_value(
                "active_deal_count",
                start.get("active_deal_count"),
                start,
                language=language,
            ),
            end=_format_kpi_value(
                "active_deal_count",
                end.get("active_deal_count"),
                end,
                language=language,
            ),
            delta=_format_kpi_delta(
                "active_deal_count",
                delta.get("active_deal_count"),
                end,
                language=language,
            ),
        ),
        "- "
        + _trend_text(language, "attention_sentence").format(
            start=_format_kpi_value(
                "attention_deal_count",
                start.get("attention_deal_count"),
                start,
                language=language,
            ),
            end=_format_kpi_value(
                "attention_deal_count",
                end.get("attention_deal_count"),
                end,
                language=language,
            ),
            delta=_format_kpi_delta(
                "attention_deal_count",
                delta.get("attention_deal_count"),
                end,
                language=language,
            ),
        ),
        "- "
        + _trend_text(language, "terminal_sentence").format(
            won_delta=_format_kpi_delta(
                "won_deal_count",
                delta.get("won_deal_count"),
                end,
                language=language,
            ),
            lost_delta=_format_kpi_delta(
                "lost_deal_count",
                delta.get("lost_deal_count"),
                end,
                language=language,
            ),
        ),
    ]
    if warnings:
        lines.append(f"- {_trend_text(language, 'sparse_history_note')}")
    return lines


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


def _format_kpi_value(
    key: str,
    value: Any,
    row: dict,
    *,
    language: str,
) -> str:
    if value is None:
        return _trend_text(language, "none")
    if key == "open_pipeline_value_amount":
        currency = row.get("open_pipeline_value_currency") or DEFAULT_DEAL_CURRENCY
        if row.get("mixed_open_pipeline_value_currency") is True:
            by_currency = row.get("open_pipeline_value_by_currency")
            if isinstance(by_currency, dict) and by_currency:
                return ", ".join(
                    f"{_format_number(amount)} {currency_code}"
                    for currency_code, amount in sorted(by_currency.items())
                )
            return _trend_text(language, "none")
        return f"{_format_number(value)} {currency}"
    if key == "avg_health_pct":
        return f"{_format_number(value)}%"
    return _format_number(value)


def _format_kpi_delta(
    key: str,
    value: Any,
    end_row: dict,
    *,
    language: str,
) -> str:
    if value is None:
        return _trend_text(language, "none")
    prefix = "+" if isinstance(value, (int, float)) and value > 0 else ""
    formatted = f"{prefix}{_format_number(value)}"
    if key == "open_pipeline_value_amount":
        currency = end_row.get("open_pipeline_value_currency") or DEFAULT_DEAL_CURRENCY
        return f"{formatted} {currency}"
    if key == "avg_health_pct":
        return f"{formatted}pp"
    return formatted


def _format_number(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value):,}"
        return f"{value:,.1f}"
    return str(value)


def _trend_text(language: str, key: str) -> str:
    return TREND_TEXT[language][key]


def _kpi_label(key: str, language: str) -> str:
    if language == "ko":
        return KPI_LABELS_KO.get(key, KPI_LABELS[key])
    return KPI_LABELS[key]


def _escape_md(value: str) -> str:
    return value.replace("|", "\\|").replace("\r", " ").replace("\n", " ")
