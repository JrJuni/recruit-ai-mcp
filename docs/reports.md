# Reporting Contract

This document records report-specific contracts. Metric definitions remain in
[metrics.md](metrics.md).

## Milestone 2.1 - Weekly Pipeline Rows

`deal_intel.reports.weekly_pipeline.build_weekly_pipeline_rows` builds the
in-memory table rows for the `weekly_pipeline` report.

### Scope

- Input: already-fetched deal documents, `as_of` date, metric settings, and
  optional exact `stage` / `industry` filters.
- Output: JSON-serializable dict.
- Side effects: none.
- Storage access: none.
- LLM / embedding: none.
- File writing: none.

The default population is Open deals only:

- `discovery`
- `qualification`
- `proposal`
- `negotiation`
- `stalled`

Terminal deals, `won` and `lost`, are excluded from weekly pipeline rows.

### Output Shape

```json
{
  "report_type": "weekly_pipeline",
  "filters": {"stage": null, "industry": null},
  "columns": [],
  "rows": [],
  "row_count": 0,
  "warnings": []
}
```

### Row Columns

- `deal_id`
- `company`
- `industry`
- `deal_stage`
- `deal_size_krw`
- `deal_size_status`
- `expected_close_date`
- `days_in_stage`
- `stuck_status`
- `is_stuck`
- `close_date_status`
- `is_overdue`
- `overdue_days`
- `health_pct`
- `health_band`
- `meddpicc_gaps`
- `last_meeting_date`
- `primary_pain`
- `primary_decision_criteria`
- `attention_reasons`
- `data_quality`

`primary_pain` is selected from `customer_themes` where
`dimension == "identify_pain"`. `primary_decision_criteria` is selected where
`dimension == "decision_criteria"`. Selection order is highest `importance`,
then latest `meeting_date`.

### Sorting

Rows are sorted for weekly review attention:

1. overdue
2. stuck
3. stalled
4. at risk
5. earliest valid `expected_close_date`
6. largest valid deal amount
7. company name

### Privacy

Weekly pipeline rows must not include:

- `meetings.raw_notes`
- `contacts`
- `summary_embedding`

Evidence snippets in `customer_themes` may be included because they are already
curated report evidence, not raw meeting notes.

### Warnings

The row builder can return these warning codes:

- `no_open_deals`
- `unassessed_health`
- `missing_expected_close_date`
- `invalid_expected_close_date`
- `missing_last_meeting_date`
- `missing_primary_pain`
- `missing_primary_decision_criteria`
- `incomplete_data_quality`

### Out Of Scope

Milestone 2.1 does not create CSV files, Markdown summaries, Atlas Charts, or
MCP tools. Those consume this row contract in later milestones.

## Milestone 2.2 - CSV Export

`deal_intel.reports.csv_export.save_report_csv` writes report rows to a local
CSV file.

### Scope

- Input: report dict with `report_type`, `columns`, and `rows`.
- Required option: explicit `output_dir`.
- Output: structured success or structured file-write error dict.
- Side effects: creates `output_dir` if missing and writes one CSV file.
- Storage access: none.
- LLM / embedding: none.
- MongoDB access: none.

### Filename

CSV filenames use the report type plus a UTC timestamp:

```text
{report_type}_YYYYMMDD_HHMMSS.csv
```

Example:

```text
weekly_pipeline_20260609_123456.csv
```

`generated_at` must be timezone-aware. It is converted to UTC before building
the filename.

### Encoding

CSV files are written as `utf-8-sig`, which includes a UTF-8 BOM for smoother
Korean display in Excel.

### Cell Serialization

- `None` is written as an empty cell.
- Boolean values are written as `true` or `false`.
- `dict` and `list` values are written as compact JSON with `ensure_ascii=False`.
- Other values are stringified.

### Formula Injection Guard

After stringification, a cell is prefixed with a single quote when its first
non-whitespace character is one of:

```text
= + - @
```

This prevents spreadsheet apps from interpreting exported report data as a
formula.

### Success Shape

```json
{
  "ok": true,
  "report_type": "weekly_pipeline",
  "path": "C:/absolute/path/weekly_pipeline_20260609_123456.csv",
  "filename": "weekly_pipeline_20260609_123456.csv",
  "row_count": 7,
  "encoding": "utf-8-sig",
  "formula_injection_protected": true
}
```

### Error Shape

File write failures return a structured error instead of raising `OSError`:

```json
{
  "ok": false,
  "error_code": "IO_ERROR",
  "stage": "storage",
  "message": "...",
  "hint": {"output_dir": "C:/target"},
  "retryable": true
}
```

Programmer errors, such as a naive `generated_at`, may still raise a local
exception because they indicate an invalid caller contract rather than a runtime
storage failure.
