# Release Publish Checklist

This checklist is for the maintainer. It starts after local package metadata,
MCPB, and smoke checks pass.

Actual npm/PyPI publication requires maintainer credentials and should not be
performed by an AI agent without explicit approval.

## Current Release Shape

- Python package: `deal-intel-mcp`
- Node bootstrapper package: `deal-intel-mcp`
- Current version: `0.2.1`
- License: MIT
- Source repository: `https://github.com/JrJuni/deal-intel-mcp`

The Node package is a bootstrapper. It must not reimplement the Python MCP
server.

## Pre-Publish Local Gate

Run from the repository root:

```powershell
git status --short
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m ruff check .
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m pytest tests\test_bootstrapper_skeleton.py tests\test_mcpb_manifest.py -q -p no:cacheprovider --basetemp .tmp\pytest-publish-checklist
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m build --no-isolation --outdir .tmp\publish-dist
npm pack .\npm --dry-run --cache .tmp\npm-cache
git diff --check
```

Pass criteria:

- Python wheel and sdist build successfully.
- npm dry-run tarball contains only the bootstrapper files.
- targeted bootstrapper/MCPB tests pass.
- Ruff passes.
- no whitespace errors.

## Publication Order

Publish Python first, then npm.

Reason: `npx deal-intel-mcp setup` installs the Python package. If npm is
published first but Python is not reachable, the no-git-clone path will fail.

Recommended order:

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
.\.tmp\testpypi-install\Scripts\python.exe -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ "deal-intel-mcp[embedding]==0.2.1"
.\.tmp\testpypi-install\Scripts\python.exe -m deal_intel.cli smoke-profile --profile sample
```

## PyPI Publish

Publish only after TestPyPI or local wheel smoke is acceptable:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m twine upload .tmp\publish-dist\*
```

After publishing, verify:

```powershell
python -m venv .tmp\pypi-install
.\.tmp\pypi-install\Scripts\python.exe -m pip install --upgrade pip
.\.tmp\pypi-install\Scripts\python.exe -m pip install "deal-intel-mcp[embedding]==0.2.1"
.\.tmp\pypi-install\Scripts\python.exe -m deal_intel.cli smoke-profile --profile sample
```

## npm Publish

Publish from the `npm/` directory after the Python package is reachable:

```powershell
cd npm
npm publish --access public
```

Then run a fresh public `npx` smoke from a disposable home:

```powershell
$env:DEAL_INTEL_HOME = (Resolve-Path "..\.tmp\npx-public-home").Path
npx --yes deal-intel-mcp@0.2.1 setup
npx --yes deal-intel-mcp@0.2.1 smoke --profile-only
npx --yes deal-intel-mcp@0.2.1 mcp-config --json
```

Pass criteria:

- setup creates a managed runtime;
- setup post-install sample profile check passes;
- `smoke --profile-only` passes;
- `mcp-config --json` prints a usable Python interpreter path;
- no secrets are printed.

## MCPB Release Artifact

If refreshing the MCPB bundle:

```powershell
mcpb validate mcpb\manifest.json
Push-Location mcpb
mcpb pack . deal-intel-mcp-0.2.1.mcpb
mcpb info deal-intel-mcp-0.2.1.mcpb
Pop-Location
```

Do not overwrite `release/latest` on every development change. Refresh it only
when the maintainer intentionally wants a new latest handoff artifact.

## Post-Publish Docs

After successful publication, update:

- `docs/status.md` with exact command evidence;
- `docs/bootstrapper-fresh-smoke.md` current evidence;
- `AI_NPX_INSTALL_GUIDE.md` if any command changed;
- release notes or GitHub release text if creating a tagged release.

## Rollback Notes

Package registries generally do not allow reusing the same version cleanly after
publication. If a bad artifact is published, prefer:

1. document the issue;
2. publish a patch version;
3. mark the broken version as not recommended where the registry supports it.
