# Release Publish Checklist

This checklist is for the maintainer. It starts after local package metadata,
MCPB, and smoke checks pass.

Actual npm/PyPI publication requires maintainer credentials and should not be
performed by an AI agent without explicit approval.

AI agents may run the local gates in this checklist, inspect public registry
state, and prepare documentation. Stop and ask the maintainer before any action
that changes external state:

- pushing `main` or any release branch;
- creating, moving, or pushing `v0.1.0` or another release tag;
- running `twine upload`, `npm publish`, `npm dist-tag`, or registry
  credential setup;
- triggering a release workflow that publishes to PyPI or npm;
- marking public `npx recruit-ai-mcp@0.1.0` readiness as complete.

Preferred publication path: GitHub Actions trusted publishing. Local `twine`
and `npm publish` remain fallback/debug paths only, because maintainer accounts
may use security-key/WebAuthn authentication that does not expose a CLI OTP.

## Current Release Shape

- Python package: `recruit-ai-mcp`
- Node bootstrapper package: `recruit-ai-mcp`
- Current version: `0.1.0`
- License: MIT
- Source repository: `https://github.com/JrJuni/recruit-ai-mcp`

Current public registry evidence, last checked on 2026-06-23:

- `npm view recruit-ai-mcp@0.1.0 version` returns npm `E404`.
- `python -m pip index versions recruit-ai-mcp` returns
  `No matching distribution found for recruit-ai-mcp`.

This means local package/MCPB gates can be complete, but public `npx` freshness
cannot be claimed until the PyPI and npm publications happen and the
post-publish smoke below passes.

The Node package is a bootstrapper. It must not reimplement the Python MCP
server.

## Pre-Publish Local Gate

Run from the repository root:

```powershell
git status --short
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m ruff check .
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m pytest tests\test_bootstrapper_skeleton.py tests\test_mcpb_manifest.py -q -p no:cacheprovider --basetemp .tmp\pytest-publish-checklist
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m build --no-isolation --outdir .tmp\publish-dist
Push-Location mcpb
mcpb validate manifest.json
mcpb pack . recruit-ai-mcp-0.1.0.mcpb
mcpb info recruit-ai-mcp-0.1.0.mcpb
Pop-Location
npm pack .\npm --dry-run --cache .tmp\npm-cache
git diff --check
```

Pass criteria:

- Python wheel and sdist build successfully as
  `.tmp\publish-dist\recruit_ai_mcp-0.1.0-py3-none-any.whl` and
  `.tmp\publish-dist\recruit_ai_mcp-0.1.0.tar.gz`.
- MCPB manifest validates and the release artifact is inspectable after the
  MCPB artifact rebuilds.
- npm dry-run tarball contains only the bootstrapper files.
- targeted bootstrapper/MCPB tests pass.
- Ruff passes.
- no whitespace errors.

## Publication Order

Publish Python first, then npm.

Reason: `npx recruit-ai-mcp setup` installs the Python package. If npm is
published first but Python is not reachable, the no-git-clone path will fail.

The release workflow in `.github/workflows/release.yml` enforces this order:

1. Validate that the release is a stable `vX.Y.Z` tag and package versions match.
2. Run release-targeted tests and package smoke.
3. Publish the Python package to PyPI.
4. Publish or promote the npm bootstrapper package.

The release test job uploads `release-smoke-evidence-<version>` so the
recruiting natural-question JSON used by the validator is retained with the
workflow run.

Before using it, configure trusted publishers on both registries.

PyPI trusted publisher values:

- Owner: `JrJuni`
- Repository: `recruit-ai-mcp`
- Workflow filename: `release.yml`
- Environment name: `pypi`

npm trusted publisher values:

- Provider: GitHub Actions
- Owner: `JrJuni`
- Repository: `recruit-ai-mcp`
- Workflow filename: `release.yml`
- Environment name: `npm`

Then publish by pushing a version tag:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

Only stable `vX.Y.Z` tags are production release tags. Do not use `v*` as the
release trigger pattern, because it can also match release-candidate tags such
as `v0.1.0-rc.1`.

If the Python package published successfully but the npm job failed, fix the
workflow and rerun only the npm target instead of republishing the same Python
version:

```powershell
gh workflow run release.yml -f target=npm
```

The npm job checks the registry before publishing. If
`recruit-ai-mcp@0.1.0` already exists, do not run `npm publish` again; promote
the existing package with the `latest` dist-tag instead:

```powershell
npm view recruit-ai-mcp@0.1.0 version
npm dist-tag add recruit-ai-mcp@0.1.0 latest
```

The npm trusted publishing job must use Node 22.14+ and npm 11.5.1+.

Fallback manual order:

1. Build Python wheel/sdist.
2. Optionally upload to TestPyPI.
3. Run TestPyPI install smoke.
4. Upload to PyPI.
5. Publish npm package.
6. Run public `npx` fresh smoke.
7. Update status/docs with the exact evidence.

## Optional TestPyPI Smoke

Use this if package metadata changed materially.

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m twine upload --repository testpypi .tmp\publish-dist\*
```

Then install in a disposable virtual environment. TestPyPI does not mirror all
dependencies, so include PyPI as an extra index:

```powershell
python -m venv .tmp\testpypi-install
.\.tmp\testpypi-install\Scripts\python.exe -m pip install --upgrade pip
.\.tmp\testpypi-install\Scripts\python.exe -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ "recruit-ai-mcp[embedding]==0.1.0"
.\.tmp\testpypi-install\Scripts\python.exe -m deal_intel.cli smoke-profile --profile sample --json
```

The repeatable installed-package smoke is also available as a manual GitHub
Actions workflow:

```powershell
gh workflow run staging-smoke.yml -f version=0.1.0 -f source=testpypi
gh workflow run staging-smoke.yml -f version=0.1.0 -f source=pypi
```

Installed-package smoke passes when:

- the requested package version installs in a fresh virtual environment;
- `smoke-profile --profile sample --json` exits successfully;
- `smoke-natural-questions --pack recruiting --as-of 2026-06-22 --json` exits
  successfully with the current 14-question recruiting pack;
- the recruiting smoke contract verifies `candidate_count=10`,
  `written_record_count=30`, `reloaded_record_count=30`, and
  `guardrail_candidate_count=6`;
- the same contract verifies candidate-to-position smoke uses open-role
  defaults with `candidate_position_available_count=2` and
  `candidate_position_excluded_count=1`;
- `deal_intel.mcp_server.app.list_tools()` returns the sample MCP surface;
- the core tools `config_doctor`, `get_tool_catalog`, `create_candidate`,
  `add_recruiting_interaction`, `recommend_candidates_for_position`, and
  `get_recruiting_metrics` are present;
- the workflow uploads a `smoke-evidence` artifact with the package,
  profile-smoke, recruiting natural-question, and MCP tool-list JSON.

## PyPI Publish

Publish only after TestPyPI or local wheel smoke is acceptable:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m twine upload .tmp\publish-dist\*
```

After publishing, verify:

```powershell
python -m venv .tmp\pypi-install
.\.tmp\pypi-install\Scripts\python.exe -m pip install --upgrade pip
.\.tmp\pypi-install\Scripts\python.exe -m pip install "recruit-ai-mcp[embedding]==0.1.0"
.\.tmp\pypi-install\Scripts\python.exe -m deal_intel.cli smoke-profile --profile sample --json
```

## npm Publish

Publish from the `npm/` directory after the Python package is reachable:

```powershell
cd npm
npm publish --access public
```

Maintainer auth note:

- npm accounts may use security-key/WebAuthn 2FA instead of a visible
  authenticator-app OTP.
- If `npm publish` returns `EOTP` but the npm website only shows security keys
  and recovery codes, do not keep looking for a nonexistent OTP field.
- The previously successful path for this project was to rerun
  `npm publish --access public`, follow the browser authentication URL printed
  by the CLI, and authenticate with the account security key/device flow.
- If the browser/device flow is not offered or fails, use one of these
  supported alternatives:
  - create a short-lived granular access token on npm with package write access
    and "bypass 2FA" enabled, then publish with that token; or
  - configure trusted publishing for a future CI release flow.
- Never paste npm tokens into chat or committed files.

Then run a fresh public `npx` smoke from a disposable home:

```powershell
$env:RECRUIT_AI_HOME = (Resolve-Path "..\.tmp\npx-public-home").Path
npx --yes recruit-ai-mcp@0.1.0 setup
npx --yes recruit-ai-mcp@0.1.0 smoke --profile-only
npx --yes recruit-ai-mcp@0.1.0 mcpb --json
npx --yes recruit-ai-mcp@0.1.0 mcp-config --json
```

Pass criteria:

- setup creates a managed runtime;
- setup post-install sample profile check passes;
- `smoke --profile-only` passes;
- `mcpb --json` prints a local MCPB file path and usable Python interpreter path;
- `mcp-config --json` prints a usable manual fallback config;
- no secrets are printed.

## MCPB Release Artifact

If refreshing the MCPB bundle:

```powershell
Push-Location mcpb
mcpb validate manifest.json
mcpb pack . recruit-ai-mcp-0.1.0.mcpb
mcpb info recruit-ai-mcp-0.1.0.mcpb
Pop-Location
```

Do not overwrite `release/latest` on every development change. Refresh it only
when the maintainer intentionally wants a new latest handoff artifact.

## Post-Publish Docs

After successful publication, update:

- `docs/status.md` with exact command evidence;
- `docs/bootstrapper-fresh-smoke.md` current evidence;
- `AI_START_HERE.md` if any install command changed;
- release notes or GitHub release text if creating a tagged release.

## Rollback Notes

Package registries generally do not allow reusing the same version cleanly after
publication. If a bad artifact is published, prefer:

1. document the issue;
2. publish a patch version;
3. mark the broken version as not recommended where the registry supports it.

## CD Automation MVP Exclusions

The current automation intentionally does not include live MongoDB/LLM smoke,
release-candidate staging publication, or automated rollback. Add those only
after they become repeated work worth automating.
