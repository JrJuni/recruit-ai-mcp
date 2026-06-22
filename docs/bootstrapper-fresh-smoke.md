# Bootstrapper Fresh Smoke

This checklist validates the dependency-inclusive Node bootstrapper before a
new user tries it.

The goal is to prove that the bootstrapper can create a Recruit AI
runtime, install the Python package, run a zero-config sample smoke, and print
the MCP handoff path.

## Current Pre-Publish Smoke

Before the npm/PyPI release path is public, use a local wheel as the install
source.

PowerShell example:

```powershell
$env:RECRUIT_AI_HOME = (Resolve-Path ".tmp\recruit-fresh-home").Path
$wheel = (Resolve-Path ".tmp\dist\recruit_ai_mcp-0.1.0-py3-none-any.whl").Path

node npm\bin\recruit-ai-mcp.js setup --wheel-url $wheel --python "$HOME\miniconda3\envs\deal-intel\python.exe"
node npm\bin\recruit-ai-mcp.js smoke --profile-only
node npm\bin\recruit-ai-mcp.js mcp-config --json
```

Expected result:

- `setup` exits `0`;
- `setup` creates `~/.recruit-ai/runtime/venv` under the selected
  `RECRUIT_AI_HOME`;
- `install-state.json` has `last_post_install_check_status: "pass"`;
- `smoke --profile-only` passes for the `sample` profile;
- `mcp-config --json` prints the Python interpreter path and Claude Desktop
  snippet;
- no MongoDB URI, API key, OAuth token, raw note, or raw product document is
  printed.

## Published npx Smoke

The user-facing smoke is:

```bash
npx recruit-ai-mcp setup
npx recruit-ai-mcp smoke --profile-only
npx recruit-ai-mcp mcp-config
```

If Python is installed but not discoverable, pass it explicitly:

```bash
npx recruit-ai-mcp setup --python /path/to/python
```

Then, after MongoDB/API values are configured:

```bash
npx recruit-ai-mcp doctor --live
```

## Important Boundary

`setup` validates installation with the zero-config sample profile. It should
not fail only because MongoDB or API values are missing.

MongoDB/API readiness belongs to:

```bash
recruit-ai-mcp doctor --live
```

This keeps the first install experience from looking broken before the user has
entered their real configuration.

## Cleanup

For disposable local smoke runs, delete the selected `RECRUIT_AI_HOME`
directory after inspection.

Do not delete the user's real `~/.recruit-ai` directory unless they explicitly
ask for a full local reset.

## Current Evidence To Collect

Before public handoff, record fresh evidence for the current Recruit AI package
line:

```powershell
$env:RECRUIT_AI_HOME = (Resolve-Path ".tmp\recruit-public-home").Path
npx --yes recruit-ai-mcp@0.1.0 setup --python <python-3.11+>
npx --yes recruit-ai-mcp@0.1.0 where --json
npx --yes recruit-ai-mcp@0.1.0 smoke --profile-only
npx --yes recruit-ai-mcp@0.1.0 mcpb --json
npx --yes recruit-ai-mcp@0.1.0 mcp-config --json
```

Pass criteria:

- PyPI fresh install of `recruit-ai-mcp[embedding]==0.1.0` succeeds.
- `setup` creates a managed runtime and runs sample profile smoke
  successfully.
- `where --json` returns managed runtime paths under the selected
  `RECRUIT_AI_HOME`.
- `smoke --profile-only` passes.
- `mcpb --json` returns a local `recruit-ai-mcp-0.1.0.mcpb` path.
- `mcp-config --json` returns the MCPB/manual host Python interpreter path and
  Claude Desktop snippet.

## External-Machine Evidence

This evidence is outside the local Windows release gate. Collect it before a
broader external announcement, or after any bootstrapper/platform change that
could affect shell path handling:

```bash
export RECRUIT_AI_HOME="$(pwd)/.tmp/recruit-macos-home"
npx --yes recruit-ai-mcp@0.1.0 setup --python /path/to/python3.11
npx --yes recruit-ai-mcp@0.1.0 smoke --profile-only
npx --yes recruit-ai-mcp@0.1.0 mcp-config --json
```

Pass criteria:

- commands run on a clean macOS user account or fresh machine;
- runtime paths stay under the selected `RECRUIT_AI_HOME`;
- sample profile smoke passes;
- MCP config output uses the macOS/Linux venv interpreter path shape
  `~/.recruit-ai/runtime/venv/bin/python`;
- no secrets are printed.

## Current Public Registry Evidence

As of 2026-06-23, public registry smoke is still pending publication:

- `npm view recruit-ai-mcp@0.1.0 version` returns npm `E404`.
- `python -m pip index versions recruit-ai-mcp` returns
  `No matching distribution found for recruit-ai-mcp`.

Do not mark the public `npx recruit-ai-mcp@0.1.0` path ready until both
packages are published and the public fresh smoke commands above pass from a
disposable `RECRUIT_AI_HOME`.
