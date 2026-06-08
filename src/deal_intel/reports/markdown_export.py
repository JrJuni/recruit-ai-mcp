from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from deal_intel.errors import ErrorCode, Stage


def save_report_markdown(
    markdown: str,
    *,
    report_type: str,
    output_dir: str | Path,
    generated_at: datetime | None = None,
) -> dict:
    """Write a Markdown report to disk and return a structured result."""
    generated = _generated_at(generated_at)
    filename = f"{_safe_filename_part(report_type)}_{generated:%Y%m%d_%H%M%S}.md"
    directory = Path(output_dir).expanduser()
    path = directory / filename

    try:
        directory.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        return {
            "ok": False,
            "error_code": ErrorCode.IO_ERROR.value,
            "stage": Stage.STORAGE.value,
            "message": str(exc),
            "hint": {"output_dir": str(directory)},
            "retryable": True,
        }

    return {
        "ok": True,
        "report_type": report_type,
        "path": str(path.resolve()),
        "filename": filename,
        "encoding": "utf-8",
    }


def _generated_at(value: datetime | None) -> datetime:
    generated = value or datetime.now(UTC)
    if generated.tzinfo is None or generated.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    return generated.astimezone(UTC)


def _safe_filename_part(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)
    return cleaned.strip("_") or "report"
