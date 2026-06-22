# Distribution Plan: Git Clone, uvx, npx, and MCPB

This plan keeps distribution priorities straight:

1. The public `0.2.3` line ships through PyPI, npm/npx, and MCPB artifacts.
2. The main human setup path remains `full` with MongoDB Atlas; `sample` is an
   optional no-MongoDB trial.
3. The npm package is a bootstrapper, not a second implementation of the MCP
   server.
4. The next distribution work is install UX hardening, not another thin
   wrapper.

## Current Decision

The dependency-inclusive bootstrapper is available as `npx recruit-ai-mcp`.
It is the preferred no-git-clone path when the user has Node.js 18+ and a
usable Python 3.11+ interpreter.

The bootstrapper reduces the current prerequisite burden:

- no manual git clone for normal users;
- no manual editable install;
- no need to understand Python interpreter paths before the first doctor check;
- no manual dependency extra selection such as `.[embedding]`;
- no hidden second implementation of the MCP server.

The recommended path is:

1. Publish or otherwise install the Python package from an immutable source.
2. Use a Node `npx` bootstrapper as the user-friendly front door.
3. Let that bootstrapper manage a Python runtime environment under
   `~/.recruit-ai/runtime`.
4. Keep MCPB as the Claude Desktop installer/config surface, but stop making it
   responsible for Python dependency installation.

## Current Public Distribution

Supported today:

- PyPI: `pip install "recruit-ai-mcp[embedding]==0.2.3"`.
- npm/npx: `npx recruit-ai-mcp@0.2.3 setup --python <python-3.11+>`.
- Git clone plus editable install for contributors and customizers.
- Claude Desktop MCPB bundle that points at either the npx-managed Python
  runtime or a user-selected Python interpreter.
- `full` profile for the default human install path.
- `sample` profile for zero-config AI evaluation or demos.
- `pro` profile for paid-infra Atlas Vector Search/API-key defaults.
- Safe user-memory tools for repo-local operating preferences and feedback.

Point AI-assisted installers at `AI_START_HERE.md`. It is the canonical entry
for npx, PyPI/editable install, and sample/full/pro setup choices.

## Packaging Constraint

The Python package has passed wheel/sdist and clean-install smoke, and the npm
bootstrapper is published. Future wrapper work should focus on first-run
guidance, prerequisite detection, and cross-platform smoke, not duplicating the
Python server.

Current contract:

- Editable repo installs keep reading repo-root `config/defaults.yaml` and
  `atlas/charts/*.json` first.
- Wheel/uvx-style installs fall back to packaged resources under
  `deal_intel.resources`.
- `.env` is still loaded from the repo/runtime root, not from packaged
  resources.
- MCPB user-config secrets are injected as runtime environment variables when
  Claude Desktop starts the server; local CLI commands still need `.env` or
  shell environment variables for equivalent live checks.

Implication:

- A plain wheel or `uvx recruit-ai-mcp` install has the config/dashboard
  resources it needs.
- A Node `npx` bridge can work around this by copying the npm package into a
  stable runtime directory and installing that copy in editable mode, but that
  adds a Node maintenance surface.

## Recommended Sequence

### D0. Package-data readiness

Goal: make the Python package runnable without assuming a git checkout.

Status: implemented as a first pass.

Tasks:

- Include `config/defaults.yaml` and required Atlas/chart specs as package
  data.
- Replace repo-root config reads with `importlib.resources` fallback logic.
- Keep `.env` loading from the runtime working directory or explicit user path,
  not from package resources.
- Keep `pyproject.toml`, MCPB manifest, and future npm package versions aligned.
- Add a wheel smoke:
  `python -m pip wheel . --no-deps --wheel-dir .tmp/wheelhouse`.
- Install that wheel into an isolated env or temp target and run
  `recruit-ai config doctor --offline`.

Why first:

- This lowers risk for both `uvx` and `npx`.
- It also makes future PyPI packaging cleaner.

### D1. External MVP trial readiness

Goal: keep first-run documentation clear across the current published paths:
npx bootstrapper, PyPI, MCPB, and git clone for customizers.

Current status: first-pass checklist implemented. Public release readiness is
tracked through `docs/mvp-readiness.md` and `AI_START_HERE.md`.

Scope boundary: D1 is a first-run distribution gate, not deep MongoDB feature
validation. The human-facing trial should start in `full`. `sample` is an
optional zero-config path for AI evaluation or demos. MongoDB ecosystem work
must be validated against the `full` profile, with `pro` added only for
paid-infra paths such as Atlas Vector Search.

Tasks:

- Keep README, AI start guide, MCPB README, and this distribution plan aligned
  on the same full-by-default install story.
- Verify that `config doctor --offline` and
  `smoke-profile --profile full --offline` are the first recommended human
  setup checks.
- Keep `sample` smoke documented as an optional zero-config evaluation path.
- Keep tool surface counts aligned with the runtime contract:
  `sample=24`, `standard=38`, `developer=42`.
- Keep user-memory, canonical interaction intake, industry metadata, and local
  personal data commands represented in the MVP checklist.
- Record any live MongoDB or MCPB reinstall checks that could not be completed
  as non-blocking risks in `docs/status.md`.

MongoDB-backed feature checks belong outside D1:

- `smoke-profile --profile full --offline`
- current-config `config doctor --offline`
- targeted storage/index/schema tests
- bounded Atlas read/write smoke when the change touches live persistence

Why this still matters after wrappers:

- It tests the experience users have today.
- It prevents npx from covering over unclear product setup language.
- It gives a concrete checklist for friend-review and AI-assisted setup without
  turning the demo profile into the product default.

### D2. Python package distribution hardening

Goal: keep the Python package installable from an immutable distribution source
so npx/MCPB/generic Python installs all rely on the same server package.

Current status:

- D2.1 local artifact smoke is complete.
- D2.2 clean wheel install smoke is complete.
- PyPI `recruit-ai-mcp==0.2.3` is published.
- Local `--no-isolation` build produced both wheel and sdist artifacts.
- The wheel installs into a temp target and can load packaged defaults, sample
  data, Atlas chart specs, chart-ready specs, Mongo validators, and vector-index
  specs without using the repo source tree.
- A rebuilt wheel installs into a fresh virtual environment with dependency
  resolution enabled.
- SRV-capable MongoDB installs now use explicit `pymongo>=4.7` plus
  `dnspython>=2.0`; current PyMongo no longer exposes a useful `srv` extra.
- Base installs do not pull `sentence-transformers`; semantic embedding
  dependencies remain opt-in through the `embedding` extra.
- Installed-artifact CLI smoke passed for `config doctor --offline`,
  `smoke-profile --profile sample`, chart-ready render, and
  `smoke-natural-questions` with an explicit writable output directory.
- Build-isolated artifact creation still needs a CI/release gate. A local
  Windows build-isolation attempt hit a pip-output decoding issue while
  creating the isolated environment.
- Fresh-install guidance and the npx bootstrapper should make smoke output
  directories explicit, because a local Windows run found `~/.recruit-ai/smoke`
  can be permission-sensitive on an already-used machine.
- Locally built artifacts under `.tmp\d2_*_dist` can inherit restrictive
  Windows sandbox ACLs. Release automation should build/copy artifacts from a
  normal CI or release workspace and validate that a fresh environment can read
  and install the final wheel.

Optional uvx-style target for future validation:

```bash
uvx recruit-ai-mcp config doctor --offline
uvx recruit-ai-mcp smoke-profile --profile sample
uvx recruit-ai-mcp smoke-natural-questions --as-of 2026-06-10
```

Implementation tasks:

- Build source distribution and wheel artifacts from `pyproject.toml`. Done for
  local D2.1/D2.2 with `--no-isolation`.
- Verify packaged resource loading for:
  - default config;
  - sample datasets;
  - Atlas chart specs;
  - chart-ready specs;
  - Mongo validators;
  - vector-index specs.
- Add a clean wheel install smoke in a temporary environment. Done for D2.2:
  - `recruit-ai config doctor --offline`
  - `recruit-ai smoke-profile --profile sample`
  - `recruit-ai smoke-natural-questions --as-of 2026-06-10`
- Keep dependency profile split explicit:
  - base install for config/read-only/sample features;
  - `embedding` extra for semantic search and product context.
- Registry:
  - PyPI is the public registry for the Python package.
  - TestPyPI remains useful only for pre-release validation.

Pros:

- Smallest conceptual surface for a Python MCP project.
- No Node bridge needed.
- Easier to keep versioning and dependencies in one ecosystem.

Remaining risks:

- Claude Desktop MCPB still needs a configured Python command or launcher.
- Build-isolated Windows artifact creation should be validated in CI or a clean
  release workspace.

### D3. Full npx bootstrapper

Status: implemented and published for `0.2.3`.

Goal: provide a true no-git-clone command path for non-developer and
AI-assisted setup.

Current public UX:

```bash
npx recruit-ai-mcp setup
npx recruit-ai-mcp doctor
npx recruit-ai-mcp smoke
npx recruit-ai-mcp mcp
```

On machines where Python is installed but not discoverable, pass the
interpreter explicitly:

```bash
npx recruit-ai-mcp setup --python /path/to/python
```

Bootstrapper behavior:

- Detect OS and architecture.
- Detect an existing usable Python 3.11+ interpreter.
- Use Python `venv` plus `pip` as the portable baseline.
- Future versions may optionally prefer `uv`, but `uv` is not required today.
- Create or reuse:
  - `~/.recruit-ai/runtime/venv`
  - `~/.recruit-ai/runtime/bin` or Windows launcher scripts
  - `~/.recruit-ai/config.yaml`
- Install the Python package with the intended extras:
  - default: `recruit-ai-mcp[embedding]`
  - lightweight option: `recruit-ai-mcp`
- Run first checks:
  - `recruit-ai smoke-profile --profile sample`
  - optional `recruit-ai config doctor` after Mongo/API values are configured.
- Do not fail `setup` only because MongoDB or API values are not configured yet.
  Those are readiness/configuration issues for `doctor`, not installation
  failures.
- Print the exact Python path for MCPB/Claude Desktop:
  - Windows: `~/.recruit-ai/runtime/venv/Scripts/python.exe`
  - macOS/Linux: `~/.recruit-ai/runtime/venv/bin/python`
- Optionally generate a Claude Desktop MCP config snippet for users who do not
  install via MCPB.
- Never store secrets inside the npm package directory.

Pros:

- Familiar to many AI-assisted setup flows.
- Can guide Python discovery, package installation, config checks, sample/full
  profile selection, and MCP startup from one entry point.
- Can avoid requiring users to learn `uv`.

Cons:

- Still needs Python.
- Adds a second packaging ecosystem.
- Must be careful not to hide Python install failures behind Node errors.
- Should not become a second implementation of the app.
- Should not ship as a thin wrapper that still requires users to understand
  Python interpreter paths before they can try the product.

Non-goals for the first npx version:

- Installing MongoDB Atlas or creating clusters.
- Mutating Claude Desktop config without user confirmation.
- Bundling Python, PyTorch, or the embedding model into the npm package.
- Reimplementing MCP tools in JavaScript.
- Hiding paid API or Atlas requirements.

Recommended implementation split:

#### D3.1 Bootstrapper design contract

- Add `docs/bootstrapper-contract.md`. Done.
- Define runtime directories, command names, environment variables, and failure
  messages. Done.
- Decide whether the npm package installs from PyPI, GitHub release artifacts,
  or both. Current default: PyPI after package metadata is ready, TestPyPI for
  pre-release validation, GitHub release wheel URL only as an explicit fallback
  or development override.

#### D3.2 Node CLI skeleton

- Create a small npm package directory. Done under `npm/`.
- Implement command routing. Initial skeleton done:
  - `setup`
  - `doctor`
  - `smoke`
  - `mcp`
  - `where`
- All commands should shell out to the installed Python package after setup.
  `doctor`, `smoke`, and `mcp` already delegate when `RECRUIT_AI_PYTHON` or a
  managed runtime Python exists. Full runtime installation is D3.3.

#### D3.3 Runtime environment installer

- Detect Python 3.11+. Initial implementation done.
- Create the venv. Initial implementation done.
- Install `recruit-ai-mcp[embedding]`. Initial implementation done.
- Cache installation state in `~/.recruit-ai/runtime/install-state.json`.
  Initial implementation done.
- `uv` preference is still deferred; current implementation uses Python venv
  plus pip as the portable baseline.

#### D3.4 MCP/Claude handoff

- Print MCPB-ready Python path. Initial implementation done with
  `recruit-ai-mcp mcp-config`.
- Generate a copy-paste Claude Desktop config snippet. Initial implementation
  done with `recruit-ai-mcp mcp-config --json`.
- Keep MCPB as the nicer UI path when users already have the `.mcpb` artifact.

#### D3.5 Fresh-machine smoke

- Windows clean install smoke.
- macOS clean install smoke.
- Confirm:
  - no git clone needed;
  - sample profile runs;
  - full profile doctor gives useful missing Mongo/API guidance;
  - MCP server starts from the generated Python path;
  - uninstall instructions are clear.

Current status:

- Windows local-wheel fresh-runtime smoke passed with an isolated
  `RECRUIT_AI_HOME`.
- Python and npm package metadata are version-aligned at `0.2.3`.
- PyPI and npm registry publication are complete for `0.2.3`.
- `setup` now runs `smoke-profile --profile sample` as the post-install check
  so missing MongoDB/API values do not make the first install look broken.
- `smoke --profile-only` and `mcp-config --json` passed from the managed
  runtime.
- Public npm/PyPI `npx` smoke passed on Windows with an explicit Python 3.11+
  interpreter path.
- macOS fresh-machine smoke remains pending.
- Keep the detailed checklist in
  [bootstrapper-fresh-smoke.md](bootstrapper-fresh-smoke.md).
- Keep maintainer registry publication steps in
  [release-publish-checklist.md](release-publish-checklist.md).

### D4. MCPB installer polish

Goal: make Claude Desktop install less brittle.

Tasks:

- Rebuild MCPB after manifest changes.
- Reinstall smoke in Claude Desktop.
- Keep MCPB user config labels friendly for non-developers.
- Decide whether signing is needed before broader external release.

## Which Distribution To Implement First?

Recommendation after v2 integration: **D2 then D3.**

Reason:

- D0 and D1 are effectively complete for the public MVP path.
- The product architecture is now stable enough to justify wrapper work.
- D2 reduces risk for every wrapper by proving the Python package works outside
  a repo checkout.
- D3 is the highest-impact non-developer distribution surface because it can
  handle setup, doctor checks, smoke checks, and MCP handoff from one entry
  point.
- MCPB remains useful, but by itself it cannot install Python dependencies.

## Acceptance Criteria

For any implemented distribution path:

- `sample` profile runs without MongoDB or API keys.
- `config doctor --offline` gives a useful result.
- Natural smoke runs on local sample data.
- The command path does not print secrets.
- The command path has a documented failure mode for missing Python, missing
  OAuth login, missing MongoDB URI, and missing API keys.
- The wrapper does not reimplement MCP tool behavior.

## Deferred

- Fully automatic Python installation.
- Automatic Claude Desktop config mutation.
- Signed release bundles.
- One-click GUI installer.
- Pro profile full live validation.
