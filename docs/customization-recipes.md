# Customization Recipes

These recipes are short starting points for forks. They are not the only way to
customize the project, but they point to the right seams so a developer or AI
coding agent does not need to rediscover the codebase from scratch.

For architecture context, read `docs/extending.md` and `docs/architecture.md`
first.

## Recipe 1: Replace MEDDPICC With BANT Or A Custom Framework

Use this when your team qualifies deals with a different method.

Start with:

- `docs/qualification-framework-v2.md`
- `src/deal_intel/schema/qualification_framework.py`
- MCP tools: `get_qualification_templates`,
  `validate_qualification_framework`, `update_qualification_framework`,
  `set_active_qualification_framework`

Steps:

1. Copy the MEDDPICC template or another built-in template.
2. Create a new framework key, for example `bant` or `founder_sales_v1`.
3. Define each dimension with a label, description, extraction hint, weight,
   gap threshold, and suggested question.
4. Validate the framework.
5. Save it as a custom framework.
6. Activate it.
7. Run deterministic backfill first. Use LLM re-extraction only when stored
   evidence does not contain enough structured signals for the new framework.

Validate with:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m pytest tests/test_qualification_framework.py tests/test_qualification_config.py -q -p no:cacheprovider
```

Gotchas:

- Built-in framework presets are recovery anchors. Do not overwrite them.
- A custom framework with vague extraction hints will produce weak evidence.
- If you change framework semantics, inspect deal review, gaps, metrics,
  reports, and chart-ready collections before release.

## Recipe 2: Add A Custom Deal Field Such As `renewal_risk`

Use this when your process needs a durable field that is not part of the base
deal schema.

Start with:

- storage adapters under `src/deal_intel/storage`
- deal create/update tools
- report/data export row builders
- `docs/storage-backends.md`

Steps:

1. Decide whether the field is operational metadata, forecast metadata, or
   report-only derived data.
2. Add validation and write support only where users should be allowed to edit
   it.
3. Add the field to safe read paths only if it is safe for list, report, BI,
   and export output.
4. Add report/export columns only when the field has clear user value.
5. Update docs if the field becomes part of the public MCP contract.

Validate with storage and export tests.

Gotchas:

- Do not add raw notes, contacts, or secrets to restricted read paths.
- If the field affects KPI math, update `docs/metrics.md` and metric tests.

## Recipe 3: Add A New MCP Tool

Use this when a new user intent cannot be served well by existing tools.

Start with:

- `src/deal_intel/mcp_server.py`
- `src/deal_intel/tool_surfaces.py`
- `docs/baseline.md`
- `docs/architecture.md`

Steps:

1. Add implementation under `src/deal_intel/tools`.
2. Keep MCP registration thin and delegate to the tool module.
3. Classify the tool in `tool_surfaces.py`.
4. Add tests for registration, profile visibility, and handler behavior.
5. Update `docs/baseline.md` and user-facing tool-selection docs.

Validate with:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m pytest tests/test_tool_surfaces.py tests/test_mcpb_manifest.py -q -p no:cacheprovider
```

Gotchas:

- Avoid exposing internal helper functions as tools.
- Keep config/recovery tools visible enough that users can recover from broken
  setup.

## Recipe 4: Create A Founder-Style Weekly Report

Use this when the default weekly pipeline report is too team-manager oriented.

Start with:

- `src/deal_intel/reports/weekly_pipeline.py`
- `src/deal_intel/reports/markdown_summary.py`
- `src/deal_intel/tools/export_report.py`
- `docs/reports.md`

Steps:

1. Decide whether this is a new `report_type` or a language/style option.
2. Reuse the shared metric engines for numbers.
3. Add founder-facing sections, such as focus accounts, expected closes,
   unresolved risks, and next-week commitments.
4. Keep CSV/ledger output separate unless the user needs spreadsheet rows.
5. Add tests that compare the report numbers to shared metric outputs.

Gotchas:

- Do not recompute official KPI math inside Markdown rendering.
- If you add host-assisted prose, keep deterministic data as the source of
  truth and make LLM cost explicit.

## Recipe 5: Hide Write Tools For Read-Only Review Mode

Use this when a team wants Claude/Codex to inspect pipeline data without making
changes.

Start with:

- `src/deal_intel/tool_surfaces.py`
- `docs/tool-surfaces.md`
- `config_doctor` output

Steps:

1. Create or configure a surface that exposes read/review/report tools only.
2. Keep `config_doctor` and `get_tool_catalog` visible.
3. Hide lifecycle and destructive tools.
4. Smoke with natural questions that only read data.

Gotchas:

- A read-only surface should still let users diagnose why setup failed.
- Hiding tools is not a database permission system. Use database controls for
  real security boundaries.

## Recipe 6: Use Local MongoDB Or Another Storage Backend

Use this when Atlas is not the right deployment target.

Start with:

- `src/deal_intel/storage/backend.py`
- `src/deal_intel/storage/mongodb.py`
- `src/deal_intel/storage/local_sample.py`
- `docs/storage-backends.md`

Steps:

1. Decide whether MongoDB-compatible connection settings are enough.
2. If not, implement the storage backend contract.
3. Add diagnostic output for `config_doctor`.
4. Add restricted projection behavior for BI/report/export paths.
5. Add migration or smoke commands if users need to move data.

Gotchas:

- Tools should not import database drivers directly.
- Storage errors should return actionable hints without leaking secrets.

## Recipe 7: Add A Product Context Parser

Use this when your product collateral lives in a format not currently parsed.

Start with:

- `src/deal_intel/product_context.py`
- `tools/index_product_context.py`
- `tests/test_product_context.py`

Steps:

1. Add parsing behind the product context engine boundary.
2. Keep source-file limits, chunk budgets, and secret scanning intact.
3. Return warnings for unsupported or partially indexed files.
4. Store cache metadata, not raw document text, in tool responses.
5. Confirm `add_interaction` sees only bounded seller-side snippets.

Gotchas:

- Product context is not customer evidence.
- Do not let product context directly raise qualification scores or customer
  theme counts.
