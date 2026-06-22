# Extending recruit-ai-mcp

`recruit-ai-mcp` is meant to be forked when your recruiting or search process
is too specific for a generic ATS/CRM, but too important to live only in notes,
spreadsheets, email threads, and memory.

The default product path is `full`: MongoDB Atlas-backed real recruiting/team
data, an MCP host such as Claude Desktop or Codex, and one optional LLM path for
extraction or narrative work. `sample` is an optional zero-config trial, not the
default architecture for real use.

This bootstrap fork still keeps the Python package internals under
`deal_intel`. Public package names, CLI guidance, env prefixes, config paths,
and current workflows should present Recruit AI while code references keep the
inherited module path until the full package rename is planned.

This guide is the first stop for developers who want to customize the server
for their own recruiting workflow.

## Extension Principles

- Prefer existing extension seams before changing core logic: recruiting
  schemas, fit scoring, recommendation services, tool surfaces, config
  profiles, reports, storage adapters, and provider factories.
- Keep candidate evidence, client feedback, recruiting interactions,
  compatibility deal records, product context, user memory, and metrics
  separate. Mixing these layers makes later analysis unreliable.
- Keep read-only metrics/report paths deterministic and LLM-free. Let the host
  app narrate deterministic outputs unless a server-side LLM result must be
  stored.
- Use dry-run and confirmation patterns for writes, migrations, destructive
  actions, and expensive LLM backfills.
- Keep secrets out of docs, user memory, tool responses, and test fixtures.

## Common Customization Paths

| Goal | Start Here | Main Contracts | Validation |
|---|---|---|---|
| Change the recruiting fit rubric | `src/deal_intel/schema/recruiting_fit.py`, `src/deal_intel/schema/recruiting_match.py`, `docs/recruiting-domain-model.md` | Fit dimensions stay inspectable on the 0-5 scale; `risk` is inverted in aggregate scoring | `tests/test_recruiting_fit.py`, `tests/test_recruiting_match.py` |
| Change candidate, client, position, submission, or feedback fields | `src/deal_intel/schema/recruiting.py`, `src/deal_intel/storage/recruiting_collections.py` | Mongo validators remain permissive enough for staged rollout; safe reads exclude raw content by default | `tests/test_recruiting_schema.py`, `tests/test_recruiting_storage_contract.py` |
| Improve recommendation ranking | `src/deal_intel/schema/recruiting_recommendation.py`, `src/deal_intel/tools/recruiting_recommendations.py` | M0-safe retrieval stays deterministic; final ranking comes from fit scoring and feedback adjustments | `tests/test_recruiting_recommendation.py`, `tests/test_recruiting_recommendations_service.py` |
| Add or change recruiting MCP tools | `src/deal_intel/mcp_server.py`, `src/deal_intel/tool_surfaces.py`, `src/deal_intel/tools/recruiting_records.py` | Tool names remain the public API; classify by profile and intent group | `tests/test_recruiting_mcp_tools.py`, `tests/test_tool_surfaces.py`, `tests/test_mcpb_manifest.py` |
| Customize recruiting metrics or reports | `src/deal_intel/tools/recruiting_metrics.py`, `src/deal_intel/reports/recruiting_pipeline.py`, `docs/metrics.md`, `docs/reports.md` | Metrics and report rows must avoid raw interaction content, contacts, embeddings, and LLM calls | `tests/test_recruiting_metrics.py`, `tests/test_recruiting_metrics_service.py`, `tests/test_export_recruiting_report.py` |
| Add or replace a storage backend | `src/deal_intel/storage/backend.py`, `src/deal_intel/storage/recruiting_records.py` | Match the storage contract used by tools, reports, metrics, and migration paths | `tests/test_storage_backend_contract.py`, `tests/test_local_sample_backend.py` |
| Add an LLM provider | `src/deal_intel/providers/llm.py` | Construct through `make_llm_provider(config)`; report usage safely | LLM provider tests, usage tests |
| Preserve or customize inherited deal workflows | `docs/baseline.md`, `docs/qualification-framework-v2.md`, `src/deal_intel/schema/qualification_framework.py` | Treat deal-intelligence tools as compatibility surfaces during the staged cutover | qualification framework, deal review, report/export, and tool-surface tests |
| Change tool visibility | `src/deal_intel/tool_surfaces.py` | Keep `config_doctor`, `update_config`, and `get_tool_catalog` recoverable | `tests/test_tool_surfaces.py` |

## Architecture Entry Points

Use these docs in this order:

1. `docs/recruiting-domain-model.md` for the recruiting data model, fit rubric,
   and recommendation records.
2. `docs/architecture.md` for the module map and change playbooks.
3. `docs/baseline.md` for MCP tool contracts.
4. `docs/config-profiles.md` for `sample`, `full`, `pro`, and tool-surface
   behavior.
5. `docs/storage-backends.md` for Mongo/local sample storage contracts and
   restricted read paths.
6. `docs/metrics.md` and `docs/reports.md` for recruiting KPI and export
   contracts.
7. `docs/customization-recipes.md` for practical examples.

If a doc conflicts with code, prefer source code and tests first.

## MCP Tool Extension Checklist

When adding a tool:

1. Put implementation logic under `src/deal_intel/tools`.
2. Keep the MCP wrapper in `mcp_server.py` thin.
3. Use `_context` for config, storage, LLM, and embedding providers.
4. Add the tool to `tool_surfaces.py` with the right profile visibility and
   intent group.
5. Update `mcpb/manifest.json` when a user-facing MCPB config or visible tool
   catalog entry changes.
6. Add targeted tests for handler behavior and tool-surface registration.
7. Update `docs/baseline.md` and tool-selection guidance if the user-facing
   workflow changes.

Do not add a tool only because an internal helper exists. Add it when it maps
to a user intent that an MCP host should be able to choose.

## Recruiting Fit And Recommendation Checklist

When changing fit scoring or recommendations:

1. Keep every dimension inspectable: score, evidence, missing information, and
   warning flags should be visible in the returned fit snapshot.
2. Keep `risk` semantics clear: higher raw risk should reduce aggregate fit.
3. Preserve deterministic behavior before adding optional generated narrative.
4. Add stress fixtures where keyword-strong but weak-fit candidates or roles do
   not outrank aligned matches.
5. Confirm feedback adjustments are visible in the adjustment ledger.
6. Re-run recruiting natural-question smoke when the user journey changes.

## Storage Backend Extension Checklist

When adding or replacing storage:

1. Implement the storage contract instead of calling the database directly from
   tools.
2. Provide restricted read paths for metrics, reports, exports, recommendations,
   and safe review flows.
3. Keep raw notes, raw interaction content, contacts, embeddings, API keys,
   OAuth tokens, and MongoDB URIs out of restricted outputs.
4. Preserve dry-run and confirmation behavior for writes and destructive
   actions.
5. Add a diagnostic path so `config_doctor` can explain readiness and next
   actions.

## Report And Export Extension Checklist

Use `export_recruiting_report` when the user needs a human-readable recruiting
pipeline artifact. Use inherited `export_report`/`export_data` only for
compatibility deal workflows.

When customizing reports:

1. Keep KPI math in the shared metric engines.
2. Shape report rows separately from spreadsheet ledger rows.
3. Keep raw notes, contacts, raw interaction content, and vectors out of
   outputs.
4. Make the output directory safe and explainable.
5. Add tests that compare report numbers against the shared metric contract.

## Fork Positioning

Good fork targets:

- recruiters and search firms with a repeatable client/candidate workflow;
- talent teams that need a lightweight AI-assisted memory layer before a large
  ATS rollout;
- operators who want custom fit rubrics for domain, seniority, compensation,
  location, availability, preferences, and risk;
- MCP workflow builders experimenting with chat-first recruiting operations.

This project is MIT-licensed. You may use, copy, modify, merge, publish,
distribute, sublicense, and sell modified versions, subject to the license
terms. Keep the license and attribution notices when redistributing a fork.
