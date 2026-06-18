# Extending deal-intel-mcp

`deal-intel-mcp` is meant to be forked when your deal process is too specific
for a generic CRM, but too important to live only in notes, spreadsheets, and
memory.

The default product path is `full`: MongoDB Atlas-backed real deal data, an MCP
host such as Claude Desktop or Codex, and one LLM path for extraction. `sample`
is an optional zero-config trial, not the default architecture for real use.

This guide is the first stop for developers who want to customize the server
for their own sales motion.

## Extension Principles

- Prefer existing extension seams before changing core logic: qualification
  frameworks, tool surfaces, config profiles, product context, reports, and
  storage adapters.
- Keep customer evidence, seller-side product context, user memory, and BI
  metrics separate. Mixing these layers makes later analysis unreliable.
- Keep read-only BI/report paths deterministic and LLM-free. Let the host app
  narrate deterministic outputs unless a server-side LLM result must be stored.
- Use dry-run and confirmation patterns for writes, migrations, destructive
  actions, and expensive LLM backfills.
- Keep secrets out of docs, user memory, tool responses, and test fixtures.

## Common Customization Paths

| Goal | Start Here | Main Contracts | Validation |
|---|---|---|---|
| Add or change a qualification framework | `docs/qualification-framework-v2.md`, `src/deal_intel/schema/qualification_framework.py` | Built-in frameworks are immutable; copy a preset before customizing | `tests/test_qualification_framework.py`, `tests/test_qualification_config.py` |
| Change deal stages | `src/deal_intel/schema/stage.py`, stage-dependent metric/review logic | Stage names affect timing, reports, charts, and lifecycle rules | stage, timing, report, and chart tests |
| Add custom deal metadata | storage adapters, schema/read projections, report/data export rows | Restricted BI projections must not expose raw notes, contacts, or vectors | storage contract tests, report/export tests |
| Add a new MCP tool | `src/deal_intel/mcp_server.py`, `src/deal_intel/tool_surfaces.py` | Tool names remain the public API; classify by profile and intent group | `tests/test_tool_surfaces.py`, `tests/test_mcpb_manifest.py` |
| Add a storage backend | `src/deal_intel/storage/backend.py` | Match the storage contract used by tools and reports | `tests/test_storage_backend_contract.py` |
| Add an LLM provider | `src/deal_intel/providers/llm.py` | Construct through `make_llm_provider(config)`; report usage safely | LLM provider tests, usage tests |
| Customize reports | `src/deal_intel/reports/*`, `docs/reports.md` | `export_report` is human-facing; `export_data` is spreadsheet-ledger output | report/export tests plus artifact inspection |
| Extend product context parsers | `src/deal_intel/product_context.py` | Product context is seller-side only; never count it as customer evidence | product context tests, add-interaction tests |
| Change tool visibility | `src/deal_intel/tool_surfaces.py` | Keep `config_doctor`, `update_config`, and `get_tool_catalog` recoverable | tool surface tests |

## Architecture Entry Points

Use these docs in this order:

1. `docs/architecture.md` for the module map and change playbooks.
2. `docs/baseline.md` for MCP tool contracts.
3. `docs/config-profiles.md` for `sample`, `full`, `pro`, and tool-surface
   behavior.
4. `docs/storage-backends.md` for storage contracts and restricted read paths.
5. `docs/reports.md` for report and export contracts.
6. `docs/customization-recipes.md` for practical examples.

If a doc conflicts with code, prefer source code and tests first.

## MCP Tool Extension Checklist

When adding a tool:

1. Put implementation logic under `src/deal_intel/tools`.
2. Keep the MCP wrapper in `mcp_server.py` thin.
3. Use `_context` for config, storage, LLM, and embedding providers.
4. Add the tool to `tool_surfaces.py` with the right profile visibility and
   intent group.
5. Update `mcpb/manifest.json` only if the desktop bundle needs to expose new
   user-facing configuration.
6. Add targeted tests for handler behavior and tool-surface registration.
7. Update `docs/baseline.md` and tool-selection guidance if the user-facing
   workflow changes.

Do not add a tool only because an internal helper exists. Add it when it maps
to a user intent that an MCP host should be able to choose.

## Qualification Framework Extension Checklist

When adding a custom framework:

1. Start from a built-in template rather than mutating MEDDPICC directly.
2. Give each dimension a stable snake_case key, label, description,
   extraction hint, weight, gap threshold, and suggested question.
3. Validate the framework before writing it to user config.
4. Activate it explicitly.
5. Decide whether existing interactions need deterministic backfill or LLM
   re-extraction.
6. Confirm reports, deal review, gaps, metrics, search metadata, and charts
   still describe the active framework correctly.

Missing evidence should increase uncertainty. Do not fake neutral scores just
to make health look complete.

## Storage Backend Extension Checklist

When adding or replacing storage:

1. Implement the storage contract instead of calling the database directly from
   tools.
2. Provide restricted read paths for BI, reports, exports, themes, and metrics.
3. Keep raw notes, raw interaction content, contacts, and embeddings out of
   restricted outputs.
4. Preserve dry-run and confirmation behavior for writes and destructive
   actions.
5. Add a diagnostic path so `config_doctor` can explain readiness and next
   actions.

## Report And Export Extension Checklist

Use `export_report` when the user needs a human-readable meeting or manager
artifact. Use `export_data` when the user needs an Excel/CSV ledger.

When customizing reports:

1. Keep KPI math in the shared metric engines.
2. Shape report rows separately from spreadsheet ledger rows.
3. Keep raw notes, contacts, and vectors out of outputs.
4. Make the output directory safe and explainable.
5. Add tests that compare report numbers against the shared metric contract.

## Fork Positioning

Good fork targets:

- early B2B SaaS or AI teams that need structure before adopting a heavy CRM;
- RevOps-minded developers who want BANT, SPICED, or a custom framework;
- MCP workflow builders experimenting with chat-first deal operations;
- consulting, SI, or agency teams with meeting-heavy sales processes.

This project is MIT-licensed. You may use, copy, modify, merge, publish,
distribute, sublicense, and sell modified versions, subject to the license
terms. Keep the license and attribution notices when redistributing a fork.
