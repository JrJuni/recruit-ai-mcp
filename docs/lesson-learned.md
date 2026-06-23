# Lessons Learned

Append-only failure log. English is the source language. Korean summaries
belong only in `README.ko.md` and `AGENTS.ko.md`.

Use this file when a failure repeats or when a runbook needs historical
context. Prefer current code, tests, `docs/README.md`, and contract docs for
ordinary implementation work.

## Entry Format

```text
## [YYYY-MM-DD] Topic

Tried: what was attempted
Result: what failed and how it was observed
Lesson: what to do next time
Related: files or docs
```

---

## [2026-06-23] Separate necessary verification from noisy context

Tried: Run a multi-step Recruit AI implementation loop with frequent commits,
targeted tests, full recruiting smoke checks, package-artifact checks, and
status updates after each small quality improvement.

Result: The engineering path was mostly sound because each contract change was
verified close to the code that changed. The inefficient part was not the tests
themselves; it was letting broad smoke output, repeated status reconstruction,
and small-but-related commit boundaries occupy more chat context than the
decision required.

Lesson:

- Keep targeted tests close to each code change; that was normal and useful.
- Use full smoke and package gates when sample data, public handoff artifacts,
  or smoke contracts change. Otherwise prefer targeted pytest, Ruff, and the
  smallest contract test that proves the behavior.
- When smoke must run, write artifacts under `.tmp/...`, validate the summary,
  and inspect only the fields that answer the current question.
- Batch adjacent recommendation-risk improvements when they touch the same
  scoring path and share the same verification surface.
- After three or more small autonomous commits, pause for a docs checkpoint
  before selecting the next unit, especially if the maintainer asks about
  scope or token efficiency.

Related: `docs/status.md`, `docs/backlog.md`,
`tests/test_recruiting_recommendation.py`,
`scripts/validate_recruiting_smoke.py`.

---

## [2026-06-23] Make docs-first pauses explicit after long loops

Tried: Continue a long implementation/verification loop after the maintainer
asked for a pause, current-work briefing, and token-efficiency self-check.

Result: The implementation work was still useful, but the handoff needed a
clearer docs-first checkpoint so the next step could be chosen from a compact
record instead of relying on chat history.

Lesson:

- When the maintainer asks to pause and review scope, update `docs/status.md`
  and, if the issue is repeatable, this file before entering the next
  implementation unit.
- Keep the status entry short: completed work, verification commands, known
  risk, and the next recommended work unit.
- Treat high-volume command output as evidence to summarize, not context to
  preserve verbatim. Prefer targeted tests, validator JSON, and `git diff
  --stat` over broad terminal dumps.
- Resume implementation only after the docs checkpoint is committed or the
  maintainer explicitly redirects.
- For the next implementation unit, make the first pass narrow by reading only
  the affected files and line ranges. Avoid repo-wide searches unless a
  contract name or stale phrase must be proven absent.

Related: `docs/status.md`, `docs/backlog.md`,
`scripts/validate_recruiting_smoke.py`.

---

## [2026-06-23] Keep smoke verification high-signal during autonomous loops

Tried: During the Recruit AI recommendation-quality loop, repeatedly run the
recruiting natural-question smoke pack with full JSON output printed to the
terminal while also making small one-flag-at-a-time commits.

Result: The implementation stayed on scope and the verification discipline was
useful, but the full smoke JSON output consumed unnecessary context and was
truncated several times. Some related risk-flag changes could have been batched
into one implementation and verification pass without losing safety.

Lesson:

- Keep the smoke pack as a release-quality gate, but avoid printing full JSON
  payloads unless the output shape itself is under review.
- Prefer writing smoke artifacts to `.tmp/...`, validating the generated
  summary with `scripts/validate_recruiting_smoke.py`, and inspecting only the
  specific fields needed with a narrow JSON query or `Select-String`.
- Batch tightly related recommendation-quality changes, such as adjacent risk
  flags or fixture stress cases, into one scoped commit with one targeted
  pytest/Ruff/smoke/validator pass.
- Continue using `PYTHONPATH=src` for targeted tests and CLI smoke so the local
  source tree wins over any stale editable install.
- Use full smoke reruns when payload contracts, sample data, or release gates
  change. For validator-only edits, test the validator directly first.

Related: `scripts/validate_recruiting_smoke.py`,
`tests/test_cli_deal_review_smoke.py`, `tests/test_validate_recruiting_smoke.py`,
`docs/status.md`.

---

## [2026-06-19] Avoid full CI log ingestion during PR merge loops

Tried: During a `commit -> push -> PR -> merge` loop, inspect failing GitHub
Actions jobs with full `gh run view --job ... --log` output and long
`gh pr checks --watch` waits.

Result: The PR was merged successfully, but the loop took about 65 minutes and
used about 155k tokens. Most token usage came from unfiltered CI logs, not from
implementation reasoning. Long watch calls also waited on stale or slow check
state after the underlying run had already reported enough structured status.

Lesson:

- Do not start CI failure triage by ingesting full job logs.
- First inspect structured status with `gh pr checks <pr>` and
  `gh run view <run-id> --json status,conclusion,jobs`.
- Fetch only failed-step snippets with a narrow filter such as
  `Select-String -Pattern "ERROR|FAILED|FileNotFoundError|Process completed"`.
- Avoid long `--watch` calls as the primary wait strategy; poll shorter windows
  and verify run status directly when checks appear stale.
- Expected improvement for similar loops: roughly 60-80% lower token use and
  40-65% less elapsed time when CI failures require diagnosis.

Related: `.github/workflows/ci.yml`, GitHub Actions PR merge workflow.

---

## [2026-06-18] npm publish may require browser/device-key authentication

Tried: Publish `deal-intel-mcp@0.2.1` with `npm publish --access public`.

Result: The first publish attempt failed with a 403 because the npm account
required two-factor authentication or a granular token that can bypass 2FA.
With security-key/recovery-code style 2FA, there may be no one-time password to
paste at the CLI. Re-running publish prompted a browser authentication URL and
completed successfully after the account was authenticated there.

Lesson:

- Do not assume npm 2FA always means `--otp <code>`.
- If npm returns a 403 about 2FA, rerun publish and follow the browser/device
  authentication flow when offered.
- Keep npm publication steps in a maintainer-only checklist, because registry
  authentication is account-specific and should not be scripted into normal
  user setup.
- Verify the published package with `npm view deal-intel-mcp version` or a
  fresh `npx deal-intel-mcp@<version> ...` smoke after publish.

Related: `docs/release-publish-checklist.md`, `npm/README.md`.

---

## [2026-06-18] MCPB is a config surface, not a dependency installer

Tried: Treat the Claude Desktop MCPB bundle as the main non-developer install
surface.

Result: MCPB can collect sensitive runtime settings and launch a selected
Python interpreter, but it does not bundle or install Python dependencies. A
non-developer with only Claude Desktop still needs Node.js and Python for the
npx bootstrapper path, or an existing Python runtime prepared by another setup
path.

Lesson:

- Separate "host app is installed" from "server runtime is installed".
- In user-facing docs, route non-developers through `npx deal-intel-mcp setup`
  after Node.js 18+ and Python 3.11+ are available.
- Use MCPB to pass the resulting Python path and sensitive config values into
  Claude Desktop.
- Do not claim a true one-click zero-prerequisite install until the package
  actually bundles or provisions the runtime dependencies.

Related: `AI_START_HERE.md`, `mcpb/README.md`,
`docs/bootstrapper-contract.md`.

---

## [2026-06-13] PyMongo command responses can contain non-JSON types

Tried: Print the result of `deal-intel mongo apply-schema --apply --json`
directly after applying the MongoDB collection validator.

Result: The Atlas write succeeded, but CLI JSON output failed because PyMongo
returned a BSON `Timestamp` in the command response.

Lesson:

- CLI commands that print raw MongoDB command responses should call
  `json.dumps(..., default=str)`.
- Prefer a safe response summary over printing raw MongoDB command responses;
  `$clusterTime.signature` and similar internal metadata is not useful for
  users.
- Verify live DB state with a read-only doctor after a write command if the
  output layer fails.
- Add tests with non-JSON sentinel objects for admin commands that expose raw
  MongoDB results.

Related: `src/deal_intel/cli.py`, `tests/test_mongo_contracts.py`.

---

## [2026-06-11] Secret scanner false positive from realistic placeholders

Tried: Use realistic fake values in docs and CLI config tests, including
API-key-shaped strings and credential-bearing MongoDB URI-shaped sentinels.

Result: Commit `89d0aa0` was flagged by secret scanning even though no real
credential was committed. The detector was correct: the fake values had the
same shape as production secrets.

Lesson:

- Do not use realistic provider key prefixes or credential-bearing MongoDB URI
  examples in fixtures or docs.
- Prefer neutral placeholders such as `replace-with-openai-api-key` and
  scanner-safe sentinel values such as `configured-openai-key-sentinel`.
- Keep tests asserting that config output does not echo secret values, but make
  the test inputs scanner-safe.

Related: `.env.example`, `README.md`, `README.ko.md`, `mcpb/manifest.json`,
`tests/test_cli_config_profiles.py`.

---

## [2026-06-08] mcpb Windows path quoting failure

Tried: Use `cmd.exe /c <launcher.bat path>` in the mcpb manifest so the bundle
could auto-discover a Python environment.

Result: Claude Desktop installed the extension under a path containing spaces.
Electron and `cmd.exe` quoting layers fought each other. Without quotes, the
path split at the space. With escaped quotes, the quote characters became part
of the path.

Lesson:

- Do not use `cmd.exe` as `mcp_config.command` for mcpb bundles.
- Use the user-selected Python interpreter directly:
  `"command": "${user_config.python_path}"`, `"args": ["-m", "<module>"]`.
- If auto-discovery is needed, implement it in Python rather than a batch file.

Related: `mcpb/manifest.json`.

---

## [2026-06-08] sentence_transformers pre-import caused startup timeout

Tried: Pre-import `sentence_transformers` inside `mcp_server.py::main()` to
avoid first-request worker-thread import issues.

Result: Importing torch and transformers took several seconds before FastMCP
opened stdio. Claude Desktop disconnected before the server was ready.

Lesson:

- Do not pre-import heavy ML frameworks during MCP startup.
- Only pre-import modules whose import time is comfortably below the startup
  budget.
- Keep embedding model creation lazy or backgrounded after stdio is ready.

Related: `src/deal_intel/mcp_server.py`,
`src/deal_intel/providers/embedding.py`.

---

## [2026-06-08] search_deals hung until the Claude Desktop timeout

Tried: Diagnose a `search_deals` request that hung for about four minutes.
Early guesses focused on MongoDB sockets and warmup duration.

Result: The real blocker was the `SentenceTransformer()` constructor checking
HuggingFace Hub without a bounded timeout. The warmup thread held the embedding
lock while waiting, and request-time `embed()` calls waited on the same lock.

Lesson:

- MCP handlers must check readiness before calling blocking embedding work.
- Return structured `warming_up` or `load_error` responses before embedding.
- Move index creation and other maintenance work out of the first tool-call
  path.
- Protect shared singleton initialization with locks.
- Keep offline-mode behavior explicit where network checks can hang.

Related: `src/deal_intel/providers/embedding.py`,
`src/deal_intel/mcp_server.py`, `src/deal_intel/_context.py`,
`tests/test_search_deals_startup.py`.

---

## [2026-06-08] CPU-only embedding load was slowed by device auto-detection

Tried: Load `SentenceTransformer(model_name)` without an explicit device.

Result: CPU-only environments spent extra time probing GPU/CUDA availability.

Lesson:

- In CPU-only local deployments, pass `device="cpu"` explicitly.
- Do not rely on device auto-detection when startup latency matters.

Related: `src/deal_intel/providers/embedding.py`.

---

## [2026-06-08] Warmup guard was documented but not enforced in the handler

Tried: Add background embedding warmup and document readiness behavior.

Result: `search_deals` still called `embed()` without checking readiness first.
Documentation said the guard existed, but the runtime handler did not enforce
it.

Lesson:

- Treat executable tests as ground truth, not completion notes.
- After adding background warmup, add protocol-level tests proving the handler
  returns immediately while the model is not ready.
- Keep idempotent DB maintenance out of user request paths.

Related: `src/deal_intel/mcp_server.py`, `src/deal_intel/_context.py`,
`tests/test_search_deals_startup.py`.

---

## [2026-06-08] Native ML import stalled from a background thread on Windows

Tried: Start FastMCP stdio and import native ML libraries for the first time
from a background thread.

Result: NumPy/SciPy native module initialization stalled with no useful CPU
activity. Loading the same stack from the main thread completed normally.

Lesson:

- On Windows, do not first-import native ML runtimes from a background thread.
- Pre-import lightweight native modules on the main thread when needed, then
  create the model in the background after startup.
- Surface warmup phase and elapsed time; after the configured budget, return a
  stalled warmup error instead of hanging.

Related: `src/deal_intel/mcp_server.py`,
`src/deal_intel/providers/embedding.py`.

---

## [2026-06-08] ChatGPT OAuth provider required Codex backend details

Tried: Reuse ChatGPT Plus/Pro subscription access through a local OAuth-backed
provider.

Result: Several backend-specific constraints were discovered:

- Required auth URL parameters were easy to miss.
- OAuth tokens worked against the ChatGPT Codex backend, not generic public API
  endpoints.
- Model names could not be guessed.
- Some common public API payload fields were rejected by the Codex backend.

Lesson:

- Do not let AI guess backend model names or payload fields.
- Use local CLI/config ground truth first.
- Regression-test absence of rejected fields so they are not accidentally
  reintroduced.
- Treat this provider as local convenience, not a stable public API contract.

Related: `src/deal_intel/providers/llm.py`.

## Blind Review judgment log

### Product context follow-up plan, round 1 (2026-06-17)

External AI reviewed the parallel-work plan (product-context live smoke running
alongside `codex/mongodb-atlas-pro`). All five items were accepted as operational
safety nets; none required a plan rewrite.

| # | category | verdict | note |
|---|---|---|---|
| 1/7 | architecture | accepted | run the context live smoke in a separate host window; isolate via git worktree |
| 2/4 | architecture | accepted | defer `mcpb pack` + `release/latest` publish to final integration to avoid release-artifact churn vs the mongodb branch |
| 3 | corner-case | accepted | added an explicit rebase conflict-watch file list (`mcpb/manifest.json`, `config/defaults.yaml`, `tool_surfaces.py`, `mcp_server.py`) |
| 5 | corner-case | accepted | smoke writes (`add_interaction`/`analyze_deal`) only on disposable/sample deals |
| 6 | corner-case | accepted | env-var-first source config; restore `~/.deal-intel/config.yaml` if `update_config` was used |

Meta: strong on operational/release-state corner cases; no nit/style noise.
Single round, so no echo-chamber risk; the fresh-context skeptic pass was skipped.

Outcome: the rebase turned out to be a no-op (`origin/main` was still at the
branch fork point `fbe1964`), so the conflict-watch list applies only to the
future integration after `codex/mongodb-atlas-pro` merges. The live smoke also
surfaced three real fixes beyond the plan: a stale-config cache bug
(`update_config` now calls `_context.reset_config()`), product context moved out
of the MCPB installer form to runtime-only, and a friendlier first-run
"not configured" guidance message in place of an error-flavored warning.
