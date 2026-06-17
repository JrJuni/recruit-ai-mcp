# MongoDB Atlas And Pro Track

This document records the MongoDB Atlas/Pro workstream. It separates
Free/M0-compatible MongoDB features that belong in `full` from paid-infra
features that belong in `pro`.

## MDB-0 Current-State Audit - 2026-06-17

### Summary

The current repository already has three Atlas dashboard specs, MongoDB schema
and index maintenance commands, Mongo doctor checks, and a guarded Atlas Vector
Search skeleton.

The main usability gap is Atlas Charts setup. Today, users paste large rendered
aggregation pipelines into the Atlas Charts query bar. This works, but it is a
poor non-developer experience. The next practical `full` improvement is a
chart-ready collection refresh path that materializes slim dashboard rows in
MongoDB, so Atlas Charts can mostly use field selection instead of large custom
pipelines.

The paid-infra `pro` path should remain focused on Atlas Vector Search and
M10+ validation. It should not block the Free/M0 chart-ready work.

### Existing Atlas Dashboard Specs

| Dashboard | Resource | Source Collection | Charts | Current Status |
|---|---|---:|---:|---|
| Weekly Pipeline Review | `src/deal_intel/resources/atlas/charts/weekly_pipeline_review.v1.json` | `deals` | 6 | Works through rendered raw aggregation pipelines. |
| Pipeline Trend Review | `src/deal_intel/resources/atlas/charts/pipeline_trend.v1.json` | `analytics_snapshots` | 2 | Works through rendered raw aggregation pipelines. |
| Customer Themes Review | `src/deal_intel/resources/atlas/charts/customer_themes.v1.json` | `deals` | 5 | Works through rendered raw aggregation pipelines. |

Weekly Pipeline chart ids:

- `pipeline_kpis`
- `stage_breakdown`
- `health_bands`
- `attention_deals`
- `meddpicc_gap_distribution`
- `qualification_gap_distribution`

Pipeline Trend chart ids:

- `trend_kpis`
- `trend_delta_bars`

Customer Themes chart ids:

- `theme_overview`
- `decision_criteria_by_stage`
- `pain_by_industry`
- `pain_by_industry_tag`
- `theme_evidence_drilldown`

### Existing Runtime Surfaces

| Surface | Owner | Classification | Notes |
|---|---|---|---|
| `deal-intel render-atlas-dashboard` | `src/deal_intel/cli.py`, `reports/atlas_charts.py` | `full` compatible | Renders dashboard JSON or one chart pipeline for Atlas UI copy/paste. No DB writes. |
| `deal-intel crosscheck-weekly-dashboard` | `src/deal_intel/cli.py`, `reports/dashboard_crosscheck.py` | `full` compatible | Compares `get_metrics`, report output, and Atlas aggregation output. Requires Mongo reads and local report writes. |
| `deal-intel mongo doctor` | `src/deal_intel/mongo_doctor.py` | `full` compatible | Read-only check for URI, ping, ordinary indexes, collection validators, and vector mode. |
| `deal-intel mongo apply-indexes` | `src/deal_intel/cli.py`, `mongo_contracts.py` | `full` compatible | Dry-run by default; applies ordinary indexes only with `--apply`. |
| `deal-intel mongo apply-schema` | `src/deal_intel/cli.py`, `mongo_contracts.py` | `full` compatible | Dry-run by default; applies permissive validators only with `--apply`. |
| `deal-intel mongo apply-vector-index` | `src/deal_intel/cli.py`, `atlas_vector_indexes.py` | `pro` only | Dry-run by default; apply requires Atlas Vector Search support on M10+. |
| `search_deals` with `mongodb.vector_search: python_cosine` | `tools/search_deals.py`, `storage/mongodb.py` | `full` compatible | Uses Mongo-backed embeddings plus Python cosine. |
| `search_deals` with `mongodb.vector_search: atlas` | `tools/search_deals.py`, `storage/mongodb.py` | `pro` only | Uses `$vectorSearch`; must not silently fall back to Python cosine. |

### Existing MongoDB Contracts

Managed schema validators:

- `deals`
- `analytics_snapshots`
- `delete_audit_logs`

Managed ordinary indexes:

- `deals`
  - `deal_id_unique`
  - `stage_updated`
  - `updated_desc`
  - `archived_updated`
  - `archived_stage_updated`
  - `health_pct_desc`
  - `stage_customer_theme`
  - `sample_batch`
- `analytics_snapshots`
  - `analytics_snapshot_event_id_unique`
  - `analytics_snapshot_deal_occurred`
  - `analytics_snapshot_event_occurred`
  - `analytics_snapshot_as_of_occurred_created`
- `delete_audit_logs`
  - `delete_audit_deal_deleted`

Audit note: `health_pct_desc` still indexes `meddpicc_latest.health_pct`.
Generic qualification reads now prefer `qualification_latest`. This is not a
blocking bug, but MDB work should consider whether a generic
`qualification_latest.health_pct` index is now a better default.

### Full/M0 Scope

The following belong in `full` because they are compatible with Atlas Free/M0
and improve normal real-data operation:

- ordinary schema validators and indexes;
- Mongo doctor checks that do not require paid admin APIs;
- raw dashboard aggregation specs and renderer;
- dashboard cross-checks that use ordinary aggregations;
- chart-ready collections or views for Atlas Charts usability;
- refresh commands that materialize deterministic dashboard rows only after an
  explicit apply;
- freshness/schema/row-count checks for chart-ready collections.

Chart-ready data should be deterministic and server-side LLM-free. It should
not include raw notes, contacts, embeddings, secrets, or full product-context
documents.

### Pro Scope

The following belong in `pro` because they assume paid infrastructure, paid API
operation, or scale paths:

- Atlas Vector Search index creation and validation;
- `$vectorSearch` query execution;
- M10+ live smoke;
- paid API-key LLM defaults, currently `openai_api` with `gpt-5.4-mini`;
- future admin checks that require paid cluster APIs or dedicated search
  infrastructure.

Pro mode must not silently fall back from Atlas Vector Search to Python cosine.
If Atlas vector search fails, return a structured error and record repeatable
cases in `docs/pro-fallback-errors.md`.

### Gaps For MDB-1+

1. No chart-ready collections exist yet.
2. No chart-ready refresh engine exists yet.
3. No chart-ready schemas, ordinary indexes, doctor checks, or freshness
   checks exist yet.
4. Atlas setup remains query-bar-heavy for non-developers.
5. Existing raw dashboard specs should remain as compatibility/reference until
   chart-ready specs are live-smoked.
6. Generic qualification migration is mostly reflected in chart specs, but the
   ordinary `health_pct_desc` index still points at `meddpicc_latest.health_pct`.
7. Live M10+ Atlas Vector Search smoke is still deferred until disposable paid
   infra is available.

### Recommended MDB Implementation Order

1. MDB-1 chart-ready data contract:
   - status: implemented as versioned contracts, not refresh/write behavior;
   - start with materialized collections, not views, because manual Atlas UI
     setup is simpler and freshness can be inspected directly;
   - collections:
     - `dashboard_weekly_pipeline`
     - `dashboard_customer_themes`
     - `dashboard_pipeline_trend`
   - common fields:
     - `dashboard_id`
     - `chart_id`
     - `row_type`
     - `row_key`
     - `schema_version`
     - `generated_at`
     - plus `as_of` for point-in-time dashboards or `window_start`,
       `window_end`, and `lookback_days` for trend dashboards;
   - contracts live in `src/deal_intel/resources/mongo/dashboard_*.v1.json`
     and load through `deal_intel.chart_ready_contracts`.
2. MDB-2 refresh engine:
   - status: implemented as CLI refresh path;
   - dry-run-first;
   - explicit apply;
   - replaces rows by dashboard/as_of/schema scope to prevent stale chart rows;
   - source rows are computed from existing deterministic metric, report,
     customer-theme, and trend engines;
   - no LLM or embedding calls;
   - command:
     `deal-intel mongo refresh-chart-ready --target all --as-of YYYY-MM-DD`
     and add `--apply` only after reviewing dry-run output.
3. MDB-3 simplified Atlas specs:
   - status: implemented as parallel chart-ready Atlas specs;
   - target chart-ready collections;
   - keep old raw aggregation specs as reference;
   - render with:
     `deal-intel render-atlas-dashboard --source chart-ready --as-of YYYY-MM-DD`;
   - specs live in `atlas/chart_ready/*.v1.json` and packaged copies under
     `src/deal_intel/resources/atlas/chart_ready/*.v1.json`.
4. MDB-4 doctor/cross-check:
   - report collection presence, freshness, schema version, row counts, and
     KPI mismatch hints.
5. MDB-5 pro vector-search validation:
   - harden M10+ path after chart-ready full work is stable.

### User Action Needed

None for MDB-0.

User action will be needed later for:

- live M0/full Atlas UI smoke after chart-ready refresh exists;
- optional M10+ Pro smoke if we decide to verify Atlas Vector Search on paid
  infrastructure.
