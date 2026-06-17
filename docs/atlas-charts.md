# Atlas Charts Dashboard

This document records the Atlas Charts setup path for the `Weekly Pipeline
Review`, `Pipeline Trend Review`, and `Customer Themes Review` dashboards in
MongoDB Atlas Charts.

Metric definitions remain in [metrics.md](metrics.md). Report/CSV contracts
remain in [reports.md](reports.md).

## Scope

- Dashboard titles:
  - `Weekly Pipeline Review`
  - `Pipeline Trend Review`
  - `Customer Themes Review`
- Data sources:
  - recommended chart-ready collections:
    - `<your cluster>` / `deal_intel` / `dashboard_weekly_pipeline`
    - `<your cluster>` / `deal_intel` / `dashboard_customer_themes`
    - `<your cluster>` / `deal_intel` / `dashboard_pipeline_trend`
  - raw reference sources:
    - `<your cluster>` / `deal_intel` / `deals`
    - `<your cluster>` / `deal_intel` / `analytics_snapshots`
- Versioned specs:
  - chart-ready:
    - [weekly_pipeline_review.v1.json](../atlas/chart_ready/weekly_pipeline_review.v1.json)
    - [pipeline_trend.v1.json](../atlas/chart_ready/pipeline_trend.v1.json)
    - [customer_themes.v1.json](../atlas/chart_ready/customer_themes.v1.json)
  - raw aggregation reference:
    - [weekly_pipeline_review.v1.json](../atlas/charts/weekly_pipeline_review.v1.json)
    - [pipeline_trend.v1.json](../atlas/charts/pipeline_trend.v1.json)
    - [customer_themes.v1.json](../atlas/charts/customer_themes.v1.json)
- Renderer: `deal_intel.reports.atlas_charts`
- CLI helper: `deal-intel render-atlas-dashboard`
- LLM / embedding: none
- MongoDB writes: none from this repository

Atlas UI changes are manual because Atlas Charts dashboard objects live inside
MongoDB Atlas. The repository stores two setup paths:

- `chart-ready` (recommended): refresh small materialized dashboard rows, then
  build charts from simple fields in Atlas.
- `raw`: paste longer aggregation pipelines that calculate from source
  collections directly. Keep this as a reference or fallback path.

Official Atlas Charts references:

- [Dashboards](https://www.mongodb.com/docs/charts/dashboards/)
- [Build Charts](https://www.mongodb.com/docs/charts/build-charts/)
- [Run Aggregation Pipelines on Your Data](https://www.mongodb.com/docs/charts/aggregation-pipeline/)

## Recommended Chart-Ready Flow

The chart-ready flow avoids the Query bar becoming the main interface. It
materializes small dashboard rows first, then Atlas Charts mostly becomes field
selection and encoding.

1. Refresh the dashboard collections in dry-run mode:

```bash
~/miniconda3/envs/deal-intel/python.exe -m deal_intel.cli mongo refresh-chart-ready --target all --as-of 2026-06-10 --lookback-days 7
```

2. If the dry-run row counts look right, apply the refresh:

```bash
~/miniconda3/envs/deal-intel/python.exe -m deal_intel.cli mongo refresh-chart-ready --target all --as-of 2026-06-10 --lookback-days 7 --apply
```

3. Render the chart-ready specs:

```bash
~/miniconda3/envs/deal-intel/python.exe -m deal_intel.cli render-atlas-dashboard --source chart-ready --as-of 2026-06-10 --output outputs/atlas_charts/weekly_pipeline_review_chart_ready_20260610.json
~/miniconda3/envs/deal-intel/python.exe -m deal_intel.cli render-atlas-dashboard --source chart-ready --dashboard pipeline_trend --as-of 2026-06-10 --lookback-days 7 --output outputs/atlas_charts/pipeline_trend_chart_ready_20260610.json
~/miniconda3/envs/deal-intel/python.exe -m deal_intel.cli render-atlas-dashboard --source chart-ready --dashboard customer_themes --as-of 2026-06-10 --output outputs/atlas_charts/customer_themes_chart_ready_20260610.json
```

4. In Atlas Charts, use the dashboard collections as data sources:

| Dashboard | Data Source |
|---|---|
| `Weekly Pipeline Review` | `deal_intel.dashboard_weekly_pipeline` |
| `Pipeline Trend Review` | `deal_intel.dashboard_pipeline_trend` |
| `Customer Themes Review` | `deal_intel.dashboard_customer_themes` |

5. For each chart, either paste the short rendered chart-ready pipeline or use
   Atlas field encoding directly with the `chart_id`/date filters shown in the
   rendered spec.

Single chart-ready pipeline example:

```bash
~/miniconda3/envs/deal-intel/python.exe -m deal_intel.cli render-atlas-dashboard --source chart-ready --as-of 2026-06-10 --chart-id pipeline_kpis
```

The rendered JSON files are operator helpers only. They do not create or update
Atlas dashboard objects by themselves.

## Validated Chart-Ready UI Setup

This section records the manual Atlas Charts setup that was validated on
2026-06-17 after rebuilding the dashboard against a fresh M0/free cluster.

Use these chart-ready filters unless you intentionally render/paste a pipeline:

| Dashboard | Collection | Common Filters |
|---|---|---|
| `Weekly Pipeline Review` | `dashboard_weekly_pipeline` | `dashboard_id = weekly_pipeline_review`, `as_of = 2026-06-10`, `schema_version = 1` |
| `Customer Themes Review` | `dashboard_customer_themes` | `dashboard_id = customer_themes`, `as_of = 2026-06-10`, `schema_version = 1` |
| `Pipeline Trend Review` | `dashboard_pipeline_trend` | `dashboard_id = pipeline_trend`, `window_start = 2026-06-03`, `window_end = 2026-06-10`, `lookback_days = 7`, `schema_version = 1` |

### Weekly Pipeline Review

Create charts from `deal_intel.dashboard_weekly_pipeline`.

| Card | Chart ID Filter | Chart Type | Encoding |
|---|---|---|---|
| Active Deal Count | `pipeline_kpis` | Number | Number: `active_deal_count`; use `MAX` or `SUM` |
| Attention Deal Count | `pipeline_kpis` | Number | Number: `attention_deal_count`; use `MAX` or `SUM` |
| Average Health | `pipeline_kpis` | Number | Number: `avg_health_pct`; use `MAX` or `AVG`; format as percent-like value |
| Open Deal Count | `pipeline_kpis` | Number | Number: `open_deal_count`; use `MAX` or `SUM` |
| Stage Breakdown | `stage_breakdown` | Grouped Bar | X: `count` as `SUM`; Y: `stage`; filter to open stages (`discovery`, `qualification`, `proposal`, `negotiation`, `stalled`) |
| Health Bands | `health_bands` | Donut | Label: `health_band`; Arc: `count` as `SUM` |
| Attention Deals | `attention_deals` | Table | Groups: `company`, `deal_stage`, `expected_close_date`, `days_in_stage`, `is_overdue`, `is_stuck`, `health_pct`, `health_band`; avoid array fields such as `attention_reasons` |

Notes:

- Prefer stage count for the first M0/full dashboard. Pipeline value charts are
  useful only when deal value coverage is healthy.
- Atlas may show array fields such as `attention_reasons` as counts in tables.
  Leave those out unless you build a dedicated unwind/pipeline chart.

### Customer Themes Review

Create charts from `deal_intel.dashboard_customer_themes`.

| Card | Chart ID Filter | Chart Type | Encoding |
|---|---|---|---|
| Top Customer Themes | `theme_overview` | Grouped Bar | X: `deal_count` as `SUM`; Y: `label`; sort by value descending |
| Decision Criteria Mix by Stage | `decision_criteria_by_stage` | Stacked Bar | X: `count` as `SUM`; Y: `stage`; Series/Color: `label` |
| Theme Evidence Drill-down | `theme_evidence_drilldown` | Table | Columns: `label`, `company`, `deal_stage`, `dimension`, `source_label`, `evidence`; disable binning for `importance` or omit it |

`pain_by_industry` and `pain_by_industry_tag` are useful optional charts, but
industry taxonomy is still evolving. Keep them secondary until the taxonomy is
stable enough for decision-making.

### Pipeline Trend Review

Create charts from `deal_intel.dashboard_pipeline_trend`.

| Card | Chart ID Filter | Chart Type | Encoding |
|---|---|---|---|
| Pipeline Trend KPIs | `trend_kpis` | Table | Include `snapshot_count`, `deal_count`, start/end/delta fields, and currency fields |
| Pipeline Trend Delta | `trend_delta_bars` | Bar or Table | X: `delta` as `SUM`; Y: `metric` |

When baseline snapshots were seeded from the same current-state dataset,
`trend_delta_bars` may show all-zero deltas. That is expected and still verifies
that trend source data is connected. Real movement appears after live deal
events create snapshots over time.

## Raw Pipeline Reference

Use this path when you want to inspect the source aggregation logic or when
chart-ready collections have not been refreshed yet.

Always render placeholders before pasting a pipeline into Atlas Charts.

Full dashboard spec:

```bash
~/miniconda3/envs/deal-intel/python.exe -m deal_intel.cli render-atlas-dashboard --as-of 2026-06-09 --output outputs/atlas_charts/weekly_pipeline_review_20260609.json
```

Pipeline trend dashboard spec:

```bash
~/miniconda3/envs/deal-intel/python.exe -m deal_intel.cli render-atlas-dashboard --dashboard pipeline_trend --as-of 2026-06-10 --lookback-days 7 --output outputs/atlas_charts/pipeline_trend_20260610.json
```

Customer themes dashboard spec:

```bash
~/miniconda3/envs/deal-intel/python.exe -m deal_intel.cli render-atlas-dashboard --dashboard customer_themes --as-of 2026-06-10 --output outputs/atlas_charts/customer_themes_20260610.json
```

Single chart pipeline:

```bash
~/miniconda3/envs/deal-intel/python.exe -m deal_intel.cli render-atlas-dashboard --as-of 2026-06-09 --chart-id pipeline_kpis
```

Pipeline trend single chart pipeline:

```bash
~/miniconda3/envs/deal-intel/python.exe -m deal_intel.cli render-atlas-dashboard --dashboard pipeline_trend --as-of 2026-06-10 --lookback-days 7 --chart-id trend_kpis
```

Customer themes single chart pipeline:

```bash
~/miniconda3/envs/deal-intel/python.exe -m deal_intel.cli render-atlas-dashboard --dashboard customer_themes --as-of 2026-06-10 --chart-id theme_overview
```

The single-chart output is already a JSON array, so it can be pasted directly
into the Atlas Charts Query bar.

Rendered defaults on 2026-06-09:

```json
{
  "as_of_datetime": "2026-06-09T00:00:00Z",
  "healthy_min": 70.0,
  "watch_min": 40.0,
  "overdue_grace_days": 0,
  "stuck_days": {
    "discovery": 7,
    "qualification": 14,
    "proposal": 21,
    "negotiation": 30
  }
}
```

## Create The Dashboard

1. In MongoDB Atlas, open the project that contains your `deal_intel`
   database.
2. Open Atlas Charts:
   - From Data Explorer, select `deal_intel.dashboard_weekly_pipeline` and
     click `Visualize Your Data`; or
   - From the Atlas sidebar, open `Visualization`, then `Project Dashboards`.
3. Create a dashboard named `Weekly Pipeline Review`.
4. Add each chart below using data source
   `deal_intel.dashboard_weekly_pipeline`.
5. Prefer direct field encoding from the chart-ready rows. Use the rendered
   query only when you need to pre-filter to one `chart_id`.
6. Save each chart back to the `Weekly Pipeline Review` dashboard.

If Atlas shows the free-tier Charts banner, that is expected on M0 and is not a
blocker for this MVP dashboard.

## Create The Trend Dashboard

1. In MongoDB Atlas, open the project that contains your `deal_intel`
   database.
2. Open Atlas Charts.
3. Create a dashboard named `Pipeline Trend Review`.
4. Add each chart below using data source
   `deal_intel.dashboard_pipeline_trend`.
5. Prefer direct field encoding from the chart-ready rows. Use the rendered
   query only when you need to pre-filter to one `chart_id`.
6. Save each chart back to the `Pipeline Trend Review` dashboard.

If the snapshot history is still sparse, `trend_kpis` will still render a
single row with zeros/nulls and `trend_delta_bars` will render the known metric
delta rows. That is expected until enough deal events create snapshots.

## Create The Customer Themes Dashboard

1. In MongoDB Atlas, open the project that contains your `deal_intel`
   database.
2. Open Atlas Charts.
3. Create a dashboard named `Customer Themes Review`.
4. Add each chart below using data source
   `deal_intel.dashboard_customer_themes`.
5. Prefer direct field encoding from the chart-ready rows. Use the rendered
   query only when you need to pre-filter to one `chart_id`.
6. Save each chart back to the `Customer Themes Review` dashboard.

This dashboard is intentionally exploratory. It should help answer:

- Which customer pains are most common across active deals?
- Which decision criteria dominate each stage?
- Which industries have different pain patterns?
- Which cross-industry tags have different pain patterns?
- Which curated evidence snippets justify the theme ranking?

## Chart Contract

Weekly Pipeline chart pipelines start with:

```json
{"$match": {"archived": {"$ne": true}}}
```

If you already created the dashboard manually in Atlas, re-render and re-paste
the Weekly Pipeline chart pipelines after this contract changes. Existing Atlas
Charts do not automatically update from repository JSON files.

| Chart ID | Title | Chart Type | Primary Fields |
|---|---|---|---|
| `pipeline_kpis` | Pipeline KPIs | Table | `deal_count`, `active_deal_count`, `open_deal_count`, `active_pipeline_value_amount`, `open_pipeline_value_amount`, `avg_health_pct`, `health_coverage_pct`, `stuck_deal_count`, `overdue_deal_count`, `attention_deal_count` |
| `stage_breakdown` | Stage Breakdown | Bar or Table | `stage`, `count`, `pipeline_value_amount`, `avg_health_pct`, `health_coverage_pct`, `stuck_count`, `overdue_count` |
| `health_bands` | Health Bands | Donut | `health_band`, `count` |
| `attention_deals` | Stuck / Overdue / At Risk Deals | Table | `company`, `industry`, `customer_segment`, `deal_stage`, `deal_size_amount`, `deal_size_currency`, `expected_close_date`, `days_in_stage`, `is_stuck`, `is_overdue`, `health_pct`, `health_band`, `attention_reasons` |
| `qualification_gap_distribution` | Qualification Gap Distribution | Bar | `gap`, `count` |
| `meddpicc_gap_distribution` | Qualification Gap Distribution (legacy id) | Bar | `gap`, `count` |

`qualification_gap_distribution` reads `qualification_latest.gaps` first and
falls back to `meddpicc_latest.gaps` for older/sample data. The
`meddpicc_gap_distribution` id is retained so existing manually created Atlas
dashboards can be updated without breaking saved chart references.

The v1 Atlas dashboard is intended for a single reporting currency per
dashboard. Python metrics and CSV/Markdown reports detect mixed currencies and
return per-currency breakdowns; re-check Atlas values against `get_metrics`
when operating with more than one currency.

## Trend Chart Contract

| Chart ID | Title | Chart Type | Primary Fields |
|---|---|---|---|
| `trend_kpis` | Pipeline Trend KPIs | Table | `window_start`, `window_end`, `lookback_days`, `snapshot_count`, start/end/delta fields for active/open count, open pipeline value, avg health, attention, won, lost |
| `trend_delta_bars` | Pipeline Trend Delta | Bar or Table | `metric`, `start_value`, `end_value`, `delta` |

## Customer Themes Chart Contract

| Chart ID | Title | Chart Type | Primary Fields |
|---|---|---|---|
| `theme_overview` | Top Customer Themes | Bar or Table | `theme_key`, `label`, `deal_count`, `avg_importance` |
| `decision_criteria_by_stage` | Decision Criteria By Stage | Grouped Bar or Table | `stage`, `theme_key`, `label`, `count`, `avg_importance` |
| `pain_by_industry` | Pain By Industry | Grouped Bar or Table | `industry`, `theme_key`, `label`, `count`, `avg_importance` |
| `pain_by_industry_tag` | Pain By Industry Tag | Grouped Bar or Table | `industry_tag`, `theme_key`, `label`, `count`, `avg_importance` |
| `theme_evidence_drilldown` | Theme Evidence Drill-down | Table | `company`, `industry`, `customer_segment`, `deal_stage`, `theme_key`, `label`, `dimension`, `importance`, `evidence`, `interaction_type`, `source_confidence`, `source_label`, `subject`, `interaction_date` |

`pain_by_industry` groups by the single primary `industry`. Use it when you want
the same vertical boundary as pipeline and forecast metrics. `pain_by_industry_tag`
unwinds `industry_tags`, so one cross-industry account can appear in multiple
semantic tag groups.

Suggested customer themes layout:

1. Top row: `theme_overview`
2. Middle row: `decision_criteria_by_stage`, `pain_by_industry`
3. Optional middle/bottom card: `pain_by_industry_tag`
4. Bottom row: `theme_evidence_drilldown`

Suggested trend layout:

1. Top row: `trend_kpis`
2. Bottom row: `trend_delta_bars`

Suggested layout:

1. Top row: `pipeline_kpis`
2. Middle row: `stage_breakdown`, `health_bands`
3. Bottom row: `attention_deals`, `qualification_gap_distribution`

## Verification Checklist

After creating the dashboard:

- No rendered pipeline contains `{{...}}` placeholders.
- `pipeline_kpis.open_pipeline_value_amount` matches
  `get_metrics(metric_type="pipeline_health").kpis.open_pipeline_value_amount`.
- `pipeline_kpis.active_pipeline_value_amount` matches the same `get_metrics`
  result.
- `pipeline_kpis.avg_health_pct`, `health_coverage_pct`, `stuck_deal_count`,
  `overdue_deal_count`, and `attention_deal_count` match `get_metrics`.
- `stage_breakdown` stage order is:
  `discovery`, `qualification`, `proposal`, `negotiation`, `stalled`, `won`,
  `lost`.
- `attention_deals` contains no `meetings.raw_notes`,
  `interactions.raw_content`, `contacts`, or `summary_embedding`.
- `Pipeline Trend Review` uses `dashboard_pipeline_trend` for normal manual
  setup. `analytics_snapshots` is the raw source and fallback reference.
- `trend_kpis` and `trend_delta_bars` contain no raw notes, contacts, or
  embeddings.
- `Customer Themes Review` uses `dashboard_customer_themes`, which contains
  selected evidence snippets only, not raw meeting notes or raw interaction
  content.
- `pain_by_industry` uses primary `industry`; `pain_by_industry_tag` uses
  `industry_tags` and may count one deal in multiple tag groups.
- `theme_evidence_drilldown` contains no contacts, embeddings, raw meeting
  notes, or raw interaction content.

Milestone 3.3 is the formal cross-check between:

- `get_metrics`
- CSV/Markdown export
- Atlas Charts dashboard data

Run it with:

```bash
~/miniconda3/envs/deal-intel/python.exe -m deal_intel.cli crosscheck-weekly-dashboard --as-of 2026-06-09 --output-dir outputs/m3_3_crosscheck
```

The command uses the same versioned aggregation pipelines as the dashboard, so a
passing result means the dashboard data source is aligned with the MCP and report
metric surfaces.
