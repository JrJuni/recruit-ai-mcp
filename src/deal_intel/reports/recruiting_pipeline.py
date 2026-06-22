from __future__ import annotations

from datetime import datetime
from typing import Any

REPORT_TYPE = "recruiting_pipeline"


def build_recruiting_pipeline_report(metrics: dict[str, Any]) -> dict[str, Any]:
    rows = [
        *_metric_rows("summary", metrics.get("summary", {})),
        *_metric_rows("positions", metrics.get("positions", {})),
        *_metric_rows("submissions", metrics.get("submissions", {})),
        *_metric_rows("feedback", metrics.get("feedback", {})),
        *_metric_rows("data_quality", metrics.get("data_quality", {})),
    ]
    return {
        "report_type": REPORT_TYPE,
        "columns": ["section", "metric", "value"],
        "rows": rows,
        "row_count": len(rows),
        "metrics": metrics,
        "warnings": [],
    }


def build_recruiting_pipeline_markdown(
    report: dict[str, Any],
    *,
    generated_at: datetime,
    timezone: str,
) -> dict[str, Any]:
    metrics = report["metrics"]
    summary = metrics.get("summary", {})
    positions = metrics.get("positions", {})
    submissions = metrics.get("submissions", {})
    feedback = metrics.get("feedback", {})
    data_quality = metrics.get("data_quality", {})
    lines = [
        "# Recruiting Pipeline Report",
        "",
        f"Generated at: {generated_at.isoformat()}",
        f"Timezone: {timezone}",
        "",
        "## Summary",
        "",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Positions: {summary.get('position_count', 0)}",
        f"- Open positions: {summary.get('open_position_count', 0)}",
        f"- Submissions: {summary.get('submission_count', 0)}",
        f"- Active submissions: {summary.get('active_submission_count', 0)}",
        f"- Placements: {summary.get('placed_count', 0)}",
        f"- Feedback records: {summary.get('feedback_count', 0)}",
        "",
        "## Funnel",
        "",
        *[
            f"- {row['status']}: {row['count']} ({_pct(row['rate'])})"
            for row in submissions.get("funnel", [])
        ],
        "",
        "## Rates",
        "",
        f"- Open-position rate: {_pct(positions.get('open_rate', 0.0))}",
        f"- Interview rate: {_pct(submissions.get('interview_rate', 0.0))}",
        f"- Placement rate: {_pct(submissions.get('placed_rate', 0.0))}",
        f"- Positive feedback rate: {_pct(feedback.get('positive_rate', 0.0))}",
        f"- Advance feedback rate: {_pct(feedback.get('advance_rate', 0.0))}",
        "",
        "## Data Quality",
        "",
        *[
            f"- {key}: {value}"
            for key, value in sorted(data_quality.items())
        ],
    ]
    briefing = (
        f"{summary.get('open_position_count', 0)} open positions, "
        f"{summary.get('active_submission_count', 0)} active submissions, "
        f"{summary.get('placed_count', 0)} placements."
    )
    return {
        "markdown": "\n".join(lines) + "\n",
        "briefing": briefing,
        "metrics": {
            "open_position_count": summary.get("open_position_count", 0),
            "active_submission_count": summary.get("active_submission_count", 0),
            "placed_count": summary.get("placed_count", 0),
            "positive_feedback_rate": feedback.get("positive_rate", 0.0),
        },
    }


def _metric_rows(section: str, payload: Any, *, prefix: str = "") -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if isinstance(payload, dict):
        for key in sorted(payload):
            rows.extend(_metric_rows(section, payload[key], prefix=_join(prefix, key)))
        return rows
    if isinstance(payload, list):
        for index, item in enumerate(payload):
            rows.extend(_metric_rows(section, item, prefix=_join(prefix, str(index))))
        return rows
    rows.append(
        {
            "section": section,
            "metric": prefix,
            "value": "" if payload is None else str(payload),
        }
    )
    return rows


def _join(prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key


def _pct(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return f"{number * 100:.1f}%"
