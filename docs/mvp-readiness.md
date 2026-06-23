# MVP Readiness Checklist

This checklist answers one question:

> Is the current package ready for a first external MVP trial without pretending
> that every future feature is finished?

The MVP target is a MongoDB-backed, AI-assisted recruiting/search-firm
intelligence workflow. Humans should start with the `full` profile by default.
The zero-config `sample` mode remains available for AI agents, demos, and users
who explicitly want to evaluate the workflow before configuring MongoDB.

This checklist is not the validation gate for MongoDB-backed feature work. When
changing MongoDB storage, indexes, schema validation, change streams, time
series, Atlas Charts, or other Atlas-backed behavior, validate against `full`
or `pro` as appropriate. `sample` checks only protect the first-run/no-MongoDB
experience.

## Release Position

Current position: **Recruit AI bootstrap public-trial ready, full-by-default with optional zero-config sample**.

Green:

- The recruit-ai bootstrap fork is isolated for public metadata, config paths,
  env prefix, MongoDB defaults, MCPB metadata, and first recruiting workflows.
  Remaining recommendation quality improvements are usage-driven follow-up
  work, not install or first-answer blockers.
- `full` profile is the default real-data operating path.
- Zero-config sample/local mode works without MongoDB and now includes the safe
  recruiting workflow.
- MCP tool surfaces are filtered by profile.
- User-memory tools are available for safe repo-local operating preferences,
  scoring feedback, taxonomy notes, report feedback, and evidence-policy notes.
- Recruiting records cover candidates, client companies, positions,
  submissions, client feedback, interactions, and recommendation runs.
- Recruiting recommendations use deterministic M0-safe lexical retrieval and
  fit scoring. Atlas Vector Search remains a pro/paid-infrastructure path.
- Recruiting interaction intake supports screens, client intake notes,
  interviews, call summaries, and internal notes through
  `add_recruiting_interaction`.
- Inherited deal-intelligence compatibility remains available during the staged
  cutover, including deal review, customer-theme, and pipeline-health tools.
- LLM usage/cost visibility is available through `get_usage` and
  `recruit-ai usage` so users can see estimated provider spend from the MCP
  surface.
- Local mode can create, export, reset, or migrate local personal recruiting
  records and inherited deal records through dry-run-first commands.
- Natural-question smoke covers both the inherited deal-intelligence
  compatibility path and the recruiting-first smoke pack.
- Claude Desktop MCPB `0.1.0` is the current release artifact target and
  reflects the current installer fields.
- The current local package readiness refresh rebuilt
  `recruit-ai-mcp-0.1.0.mcpb`; the root, npm-bundled, and `release/latest`
  copies share SHA256
  `369CA162C1290D9427F0A0A8FAB9C9E816A9BD4F3EA1B3E04B26684B5007BD11`.

Yellow:

- Atlas Charts are still intended for one reporting currency per dashboard.
  Python metrics and CSV/Markdown reports detect mixed currencies, but Atlas
  dashboard values should be cross-checked when operating with more than one
  currency.
- Claude Desktop MCPB reinstall should be smoked after manifest or bundle
  changes. Current package build is available, but each external evaluator's
  install still needs a quick `config_doctor` check.
- Public registry `npx recruit-ai-mcp@0.1.0` readiness remains pending until
  PyPI/npm publication is complete and the post-publish fresh smoke passes from
  a disposable `RECRUIT_AI_HOME`.
- macOS fresh-machine smoke remains external-machine evidence, not a blocker
  for the local Windows pre-publish gate.
- Full MongoDB mode has passed bounded live smoke, but each external evaluator
  should still run `config_doctor` against their own Atlas project.
- Pro mode has passed the first Atlas Vector Search smoke, but remains a paid
  infrastructure path that should be validated per user's cluster before
  relying on it operationally.
- The first-run copy is now full-by-default, but Korean companion docs may need
  a final pass before a non-English external trial.

Not MVP-blocking:

- Additional npx/uvx distribution polish beyond the current local
  pre-publish bootstrapper gate.
- Signed MCPB bundles.
- Pro-scale Atlas Vector Search hardening beyond the current live smoke.
- OpenAI API live smoke with paid credits.
- Deep account people graph / CRM-like contact model.

Remaining post-bootstrap quality candidates:

- Keep validating recruiting tool-selection descriptions through the
  recruiting-first natural-question smoke pack and real host usage.
- Improve recruiting recommendation, report, and inherited deal-review quality
  with real user traces and synthetic corner-case datasets.

Post-bootstrap tool design cleanup:

- Consolidate customer-theme analysis after real host usage is observed.
  Ranking, breakdown, and evidence are one user workflow today, but this is not
  an MVP blocker because current natural-question smoke already passes.
- Audit `update_deal` field groups. Keep the current wide schema while it
  remains one coherent "confirmed metadata correction" workflow; split only if
  unrelated decision types enter the tool.

Post-bootstrap tool design candidates:

- Add response verbosity controls such as `response_format=concise|detailed`
  only if real traces show meaningful token pressure.
- Consider broad tool namespace changes only as a breaking-version cleanup, not
  as a `0.1.x` patch.

## Required Gates

Run these before calling a build "MVP-ready".

### 1. Source And Tests

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m pytest -q
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m ruff check .
git diff --check
```

Pass criteria:

- Full pytest passes.
- Ruff passes.
- `git diff --check` has no whitespace errors. Windows line-ending warnings are
  acceptable if no actual diff-check failure is reported.

### 1b. Public Launch Hygiene

Use the Codex `launch-hygiene` skill before any public release candidate,
package handoff, MCPB rebuild, or major install-doc update.

Minimum checks:

```powershell
rg "<known-local-username>|<machine-local-path-pattern>|<old-project-name>|<old-env-name>|API_KEY|TOKEN|SECRET|BEGIN .*PRIVATE KEY" . --glob "!mcpb/outputs/**" --glob "!.git/**"
git status --short --ignored
```

Pass criteria:

- No tracked personal usernames, machine-local paths, old project/env names,
  private generated-output paths, secrets, tokens, or API keys.
- `.env`, local override YAML, generated bundles, caches, smoke outputs, and
  local DB/output directories are ignored unless intentionally tracked.
- Public docs explain how to discover the user's own Python interpreter path
  instead of copying a maintainer path.
- Public docs avoid hardcoded tool counts where a doctor/smoke command can
  report the current surface more reliably.

### 2. Full Profile Smoke

```powershell
recruit-ai config profiles
recruit-ai config doctor --offline
recruit-ai smoke-profile --profile full --offline
```

Pass criteria:

- The default human-facing path is `full`.
- `config doctor --offline` reports whether the current machine is configured
  for MongoDB-backed operation without leaking secrets.
- `smoke-profile --profile full --offline` matches the `full` profile contract
  without writes, LLM completions, embeddings, or Atlas admin calls.

### 2b. Optional Zero-Config Sample Smoke

Run this only for AI-first evaluation, demos, or no-MongoDB environments.

```powershell
recruit-ai config init --profile sample --dry-run
recruit-ai smoke-profile --profile sample
```

Pass criteria:

- The sample path does not ask for MongoDB, API keys, or Atlas Vector Search.
- `smoke-profile --profile sample` succeeds or reports only expected local
  environment warnings.

### 2c. MongoDB-Backed Feature Gate

Run this when the change touches MongoDB-backed behavior. Do not substitute the
sample smoke for this gate.

```powershell
recruit-ai smoke-profile --profile full --offline
recruit-ai config doctor --offline
```

Pass criteria:

- `smoke-profile --profile full --offline` matches the `full` profile contract.
- `config doctor --offline` reports whether the current machine is actually
  configured for MongoDB-backed operation.
- If the feature requires live reads or writes, run a bounded Atlas smoke in a
  disposable database or record why it was deferred.

### 3. Inherited Deal Natural Question Smoke

```powershell
$env:RECRUIT_AI_STORAGE_BACKEND='local_sample'
$env:RECRUIT_AI_TOOLS_SURFACE='auto'
recruit-ai smoke-natural-questions --as-of 2026-06-10
```

Pass criteria:

- `questions=12`.
- `OK: True`.
- No blocked questions.
- No sensitive failures.
- The compatibility pack covers pipeline health, company status, riskiest
  deals, uncertainty, closing gaps, closed-deal postmortem gaps, decision
  criteria, evidence drill-down, email/interview-backed evidence, pipeline
  trend, actionability separation, and interaction source coverage.

### 3b. Recruiting Workflow Smoke

Run the deterministic recruiting question pack:

```powershell
$env:RECRUIT_AI_STORAGE_BACKEND='local_sample'
$env:RECRUIT_AI_TOOLS_SURFACE='sample'
recruit-ai smoke-natural-questions --pack recruiting --as-of 2026-06-22
```

Pass criteria:

- `questions=16`.
- `OK: True`.
- No blocked questions.
- No sensitive failures.
- The pack covers recruiting metrics, position-to-candidate recommendations,
  candidate-to-position recommendations, feedback-adjusted scoring, active
  submissions, learned client preferences, candidate risk flags, raw-content
  safety, intake coverage, recruiting report preview readiness, local personal
  recruiting persistence, saved recommendation-run review, and opt-in workflow
  trace redaction.
- The pack also writes a recruiting pipeline CSV and Markdown report to a
  temporary output directory and confirms those artifacts avoid restricted
  fields.
- Candidate-to-position smoke shows the default open-role filter and the
  paused role excluded from first-pass recommendations.
- The pack also covers realistic recommendation guardrails, including
  must-have skill evidence gaps, and client shortlist readiness for open sample
  positions.

### 4. Inherited Deal Review QA

```powershell
$env:RECRUIT_AI_STORAGE_BACKEND='local_sample'
recruit-ai smoke-deal-review-audit --as-of 2026-06-10 --limit 20
```

Pass criteria:

- Sensitive field check passes.
- No quality rule failures.
- Reviews do not expose uncalibrated win-probability percentages.
- Objective CTA gaps and judgment-sensitive observations stay separated.

### 5. Tool Surface Smoke

Run the relevant tests:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m pytest tests\test_tool_surfaces.py tests\test_mcpb_manifest.py -q
```

Pass criteria:

- `sample`, `standard`, and `developer` tool counts match the documented
  contract: `sample=35`, `standard=49`, `developer=53`.
- Recruiting tools such as `create_candidate`,
  `add_recruiting_interaction`, and `recommend_candidates_for_position` are
  present on the expected surfaces.
- Deprecated `add_meeting` remains hidden from sample/standard and only visible
  on developer.
- MCPB manifest tool metadata matches the runtime contract.

### 6. Local Personal Data Safety

```powershell
recruit-ai local-data status
recruit-ai local-data export
recruit-ai local-data reset
recruit-ai local-data migrate-to-mongo
```

Pass criteria:

- Export writes a JSON snapshot when local personal data exists.
- Reset is dry-run by default.
- Migration is dry-run by default.
- Bundled fixture records are never reset or migrated as user data.

### 7. MCPB Package Smoke

From `mcpb/`:

```powershell
mcpb validate manifest.json
mcpb pack . recruit-ai-mcp-0.1.0.mcpb
mcpb info recruit-ai-mcp-0.1.0.mcpb
```

Pass criteria:

- Manifest validation passes.
- Pack succeeds.
- The bundle remains unsigned unless a signing decision has been made.
- The root, npm-bundled, and `release/latest` MCPB copies should have matching
  SHA256 checksums.
- Reinstall smoke in Claude Desktop should show the expected sample or standard
  surface based on selected config.
- For the current package, the latest known npm-bundled build is
  `npm/mcpb/recruit-ai-mcp-0.1.0.mcpb` with an unsigned-package warning only.

## User Trial Script

Use this lightweight script for a friend or first external evaluator:

1. Start with `full` and ask for/configure `MONGODB_URI`.
2. Install or reconnect the MCPB with `storage_backend=mongo` and
   `tools_surface=auto`.
3. Run `config_doctor`.
4. Create one client company with `create_client_company`.
5. Create one open search with `create_position`.
6. Create one test candidate with `create_candidate`.
7. Add one screen or client-intake note through `add_recruiting_interaction`.
8. Run `recommend_candidates_for_position` for the created position.
9. Add one structured client response through `add_client_feedback`.
10. Re-run the recommendation and confirm the feedback signal is visible.
11. Record one reporting/scoring preference through `record_user_memory`, then
    read it back with `get_user_memory`.

Optional zero-config demo script:

1. Set `RECRUIT_AI_STORAGE_BACKEND=local_sample`.
2. Run `smoke-profile --profile sample`.
3. Create fictional recruiting sample data with `create_sample_data` using the
   `recruiting_pipeline_demo` dataset.
4. Show `local-data export` and `local-data reset` dry-run behavior.
5. Explain that this is a demo/evaluation path, not the default team-storage
   path.

## Deferred After MVP

Do not block the first MVP on these:

- Additional npx/uvx distribution polish after public registry smoke evidence
  exists.
- Pro-grade Atlas Vector Search scale validation beyond the current live smoke.
- MongoDB Change Streams and Time Series Collections.
- Full customer/account people graph.
- Human-readable CSV redesign beyond the current weekly/trend reports.
- OpenAI API live smoke when no API credits are available.
- Full MEDDPICC/qualification-framework abstraction. The MVP uses MEDDPICC as
  the default framework; replacing the dimension set is v2.0 work.

## Sign-Off Template

```text
MVP readiness sign-off

Date:
Commit:
Profile tested:
Storage backend:
MCP surface:

Gates:
- Full pytest:
- Ruff:
- Natural smoke:
- Deal review audit:
- Tool surface/MCPB contract:
- MCPB install/reinstall:
- Local personal data safety:

Known non-blockers:
- 

Decision:
- Ready for full-by-default external MVP trial: yes/no
```
