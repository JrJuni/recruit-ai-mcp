# Bootstrapper Fresh Smoke

This checklist validates the dependency-inclusive Node bootstrapper before a
new user tries it.

The goal is to prove that the bootstrapper can create a Deal Intelligence
runtime, install the Python package, run a zero-config sample smoke, and print
the MCP handoff path.

## Current Pre-Publish Smoke

Before the npm/PyPI release path is public, use a local wheel as the install
source.

PowerShell example:

```powershell
$env:DEAL_INTEL_HOME = (Resolve-Path ".tmp\d35-fresh-home").Path
$wheel = (Resolve-Path ".tmp\d2_2_dist\deal_intel_mcp-0.2.1-py3-none-any.whl").Path

node npm\bin\deal-intel-mcp.js setup --wheel-url $wheel --python "$HOME\miniconda3\envs\event-intel\python.exe"
node npm\bin\deal-intel-mcp.js smoke --profile-only
node npm\bin\deal-intel-mcp.js mcp-config --json
```

Expected result:

- `setup` exits `0`;
- `setup` creates `~/.deal-intel/runtime/venv` under the selected
  `DEAL_INTEL_HOME`;
- `install-state.json` has `last_post_install_check_status: "pass"`;
- `smoke --profile-only` passes for the `sample` profile;
- `mcp-config --json` prints the Python interpreter path and Claude Desktop
  snippet;
- no MongoDB URI, API key, OAuth token, raw note, or raw product document is
  printed.

## Future Published Smoke

After npm/PyPI publication, the user-facing smoke should be:

```bash
npx deal-intel-mcp setup
npx deal-intel-mcp smoke --profile-only
npx deal-intel-mcp mcp-config
```

Then, after MongoDB/API values are configured:

```bash
npx deal-intel-mcp doctor --live
```

## Important Boundary

`setup` validates installation with the zero-config sample profile. It should
not fail only because MongoDB or API values are missing.

MongoDB/API readiness belongs to:

```bash
deal-intel-mcp doctor --live
```

This keeps the first install experience from looking broken before the user has
entered their real configuration.

## Cleanup

For disposable local smoke runs, delete the selected `DEAL_INTEL_HOME`
directory after inspection.

Do not delete the user's real `~/.deal-intel` directory unless they explicitly
ask for a full local reset.

## Current Evidence

Windows local-wheel smoke passed on 2026-06-18:

- local wheel install completed;
- post-install `smoke-profile --profile sample` passed;
- `smoke --profile-only` passed from the managed runtime;
- `mcp-config --json` returned the managed Python path and Claude Desktop
  snippet.

Not yet complete:

- public `npx` install from npm;
- PyPI/TestPyPI install source smoke;
- macOS fresh-machine smoke.
