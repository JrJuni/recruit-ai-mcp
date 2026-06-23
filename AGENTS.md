# AGENTS.md

This is the short operating guide for Codex and other coding agents working in
this repository. Keep it current and compact. Put long history in `docs/`.

## Project North Star

`recruit-ai-mcp` is a bootstrap fork of `deal-intel-mcp` for recruiter and
search-firm intelligence. Work 0 isolates public metadata, CLI alias, config
paths, env prefix, local paths, and MongoDB defaults while the Python package
still uses `deal_intel` internals. The first recruiting MCP tools now coexist
with inherited deal-intelligence compatibility tools during the staged cutover.

Default MongoDB databases are `recruit_ai` and `recruit_ai_demo`. Atlas M0 uses
the existing Python cosine search path; do not apply Atlas Vector Search unless
the user intentionally moves to paid M10+ infrastructure.

The product direction is one repository / one package with three profiles:

- `sample`: zero-config, MongoDB-free sample/local personal mode.
- `full`: Atlas-backed operating mode for real team data.
- `pro`: paid-infrastructure path with API-key LLM providers and Atlas Vector
  Search.

## Read First

Do not read every doc by default. Start here:

1. `AGENTS.md` or `CLAUDE.md` for agent rules.
2. `AI_START_HERE.md` when onboarding a new user or first-run agent.
3. `docs/README.md` for the documentation map and current reading order.
4. `docs/status.md` for the latest completed work.
5. `docs/baseline.md` for MCP tool contracts.
6. `docs/metrics.md`, `docs/reports.md`, `docs/storage-backends.md`, or
   `docs/config-profiles.md` only when the task touches that area, including
   recruiting pipeline metrics or recruiting report exports.

Append-only or historical docs such as `docs/lesson-learned.md` and old
sections of `docs/backlog.md` are archive material. Search them for a specific
failure or decision; do not load them wholesale for ordinary tasks.

Before public release, package handoff, MCPB rebuild, or major install-doc
changes, run the `launch-hygiene` skill if available and follow the public
launch hygiene gate in `docs/mvp-readiness.md`.

## Documentation Language Policy

- English is the source language for repository docs, contracts, status,
  backlog, architecture, and lesson-learned files.
- Keep persistent English source docs ASCII-only unless a file format or quoted
  external value genuinely requires otherwise.
- The only Korean-maintained companion docs are `README.ko.md` and
  `AGENTS.ko.md`.
- Update the Korean companion docs when the maintainer explicitly asks for a Korean doc
  update. Otherwise keep implementation docs English-first and translate on
  demand in chat.

## Dev Environment

Use the conda environment Python directly. Do not use bare `python` or `py` on
Windows.

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m pip install -e ".[dev,embedding]"
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m ruff check .
```

Useful CLI checks:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli storage-status
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli config profiles
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli config show
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli config doctor
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli config init --profile sample --dry-run
```

For temporary zero-config sample mode:

```powershell
$env:RECRUIT_AI_STORAGE_BACKEND='local_sample'
```

## Working Loop

Preferred maintainer loop:

1. Decide the large workstream and the next subtask.
2. For complex or product-sensitive tasks, write the detailed plan, risks,
   verification criteria, and sensemaker summary before implementation.
3. For small low-decision tasks, move directly into implement -> verify.
4. Turn suspected edge cases into targeted tests first.
5. Verify with targeted tests, relevant regressions, Ruff, and any required
   smoke test.
6. Record unverified risk in `docs/status.md` or `docs/backlog.md`.
7. For natural-question smoke or other large JSON-producing checks, keep the
   verification artifact but avoid dumping full payloads into the agent
   context. Prefer `PYTHONPATH=src`, workspace-local `.tmp/...` output
   directories, validator scripts, and narrow field queries. Batch tightly
   related risk-flag/fixture changes into one verification pass when the safety
   boundary is the same.
8. When adding or changing a data pipeline, calculator, report/export flow,
   storage read path, MCP orchestration path, or module responsibility boundary,
   use the `architecture-map` skill if available and update
   `docs/architecture.md` with the entry point, input source, calculation
   responsibility, output contract, side effects, and verification command.
9. Update docs and commit only the intended scope. Push when requested.

## CI Failure Triage Protocol

When debugging GitHub Actions or PR checks, optimize for signal before logs:

1. Start with `gh pr checks <pr>` and structured PR state such as
   `gh pr view <pr> --json mergeStateStatus,mergeable,statusCheckRollup`.
2. Inspect run/job state with
   `gh run view <run-id> --json status,conclusion,jobs`.
3. Fetch only failed-job or failed-step snippets, filtered with
   `Select-String -Pattern "ERROR|FAILED|FileNotFoundError|Process completed"`.
   Avoid full job-log ingestion unless filtered evidence is insufficient.
4. Avoid long `gh pr checks --watch` waits as the primary strategy; poll in
   short windows or inspect run status directly.
5. Treat a pending check as stale only after structured run data shows success,
   the PR is `MERGEABLE`/`CLEAN`, and no required check is failed or truly
   in progress.

Do not add third-party AI failure-analysis Actions or new LLM/API cost surfaces
unless the maintainer explicitly asks for that automation.

## Current MCP Tool Surface

Source of truth:

- registration: `src/deal_intel/mcp_server.py`
- profile filtering and user-intent grouping: `src/deal_intel/tool_surfaces.py`
- runtime escape hatch: call `get_tool_catalog`

Avoid hardcoding current tool counts in agent-facing docs unless a test updates
the number in the same change.

- Config/readiness: `config_doctor`, `update_config`
- Discovery: `get_tool_catalog`
- Recruiting write/recommendation: `create_candidate`,
  `create_client_company`, `create_position`, `add_recruiting_interaction`,
  `create_submission`, `add_client_feedback`, `recommend_candidates_for_position`,
  `recommend_positions_for_candidate`, `get_recruiting_recommendation_run`,
  `get_recruiting_metrics`, `export_recruiting_report`
- Deal write/lifecycle compatibility: `create_deal`, `add_interaction`, `update_stage`,
  `update_deal`, `archive_deal`, `restore_deal`, `delete_deal`
- Deprecated compatibility: `add_meeting` (developer surface only; use
  `add_interaction` with `interaction_type: meeting` for new work)
- Demo data: `create_sample_data`, `delete_sample_data`
- Migration: `migrate_local_data`
- Read/review: `get_deal`, `list_deals`, `get_deal_gaps`,
  `get_deal_review`
- Developer-only raw read: `get_deal_raw` (requires explicit confirmation,
  reason, and raw include flag; embeddings remain excluded)
- BI/reporting: `get_insights`, `get_metrics`, `get_usage`, `export_report`
- Data export: `export_data`
- Qualification framework admin: `get_qualification_templates`,
  `validate_qualification_framework`, `update_qualification_framework`,
  `list_qualification_frameworks`, `set_active_qualification_framework`,
  `delete_qualification_framework`, `backfill_qualification`,
  `backfill_qualification_reextract`
- User memory: `get_user_memory`, `record_user_memory`
- Customer themes: `get_customer_themes`, `get_customer_theme_breakdown`,
  `get_customer_theme_evidence`
- Search/analysis: `search_deals`, `analyze_deal`

## Architecture Rules

- Access storage and LLM providers only through `deal_intel._context`.
- Use `make_llm_provider(config)`; do not instantiate provider classes
  directly.
- Keep `pymongo` imports inside `storage/mongodb.py`, except for the explicit
  `preload_driver()` startup path.
- BI/reporting paths must not call LLMs or embeddings.
- `deal.interactions` is the canonical new evidence store. `deal.meetings`
  remains legacy read fallback only.
- Restricted metric/report read paths must exclude raw meeting notes,
  interaction raw content, contacts, and embeddings unless the tool contract
  explicitly says otherwise.
- `add_interaction` never changes `deal_stage`. It may return
  `stage_suggestion`; apply the change only after user confirmation through
  `update_stage`. `add_meeting` is a deprecated compatibility alias for
  `add_interaction` with `interaction_type: meeting`.
- Destructive tools stay conservative: dry-run first, explicit confirmation,
  exact company matching where applicable, and audit-safe snapshots.
- Do not use realistic secret-looking placeholders in tests or docs. Use
  neutral values such as `replace-with-openai-api-key` or scanner-safe
  sentinels.

## Docs Convention

- `docs/README.md`: documentation map and current reading order.
- `docs/status.md`: latest work and verification notes; older entries are
  archive.
- `docs/backlog.md`: current backlog index first, historical roadmap below.
- `docs/baseline.md`: MCP tool contracts and verification baseline.
- `docs/metrics.md`: deal BI and recruiting pipeline metric definitions and
  boundary contracts.
- `docs/reports.md`: deal and recruiting CSV/Markdown report contracts.
- `docs/storage-backends.md`: Mongo vs local sample storage contract.
- `docs/config-profiles.md`: `sample/full/pro` profile plan.
- `docs/lesson-learned.md`: append-only failure log; search it when debugging.
