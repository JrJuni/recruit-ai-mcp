# deal-intel-mcp Bootstrapper

This is the future `npx` front door for Deal Intelligence MCP.

Current status: D3.5 local-wheel fresh-runtime smoke passed. The npm package is
still private and not published yet, so public `npx deal-intel-mcp ...` smoke is
pending.

The Node package must not reimplement the MCP server. It installs, finds, and
runs the Python package described by `docs/bootstrapper-contract.md`.

## Commands

```bash
node bin/deal-intel-mcp.js where
node bin/deal-intel-mcp.js doctor
node bin/deal-intel-mcp.js smoke
node bin/deal-intel-mcp.js mcp
node bin/deal-intel-mcp.js mcp-config
node bin/deal-intel-mcp.js setup
```

`setup --dry-run` prints the install plan without changing files. Running
`setup` without `--dry-run` creates `~/.deal-intel/runtime/venv`, installs the
selected Python package source, and runs `smoke-profile --profile sample` as a
post-install check.

`setup` intentionally does not fail just because MongoDB or API keys are not
configured yet. After the user enters real config values, run:

```bash
node bin/deal-intel-mcp.js doctor --live
```

`mcp-config` prints the Python interpreter path for MCPB and a copy-paste
Claude Desktop JSON snippet for users who configure MCP manually.

For local development without the managed runtime, point the wrapper at an
existing Python environment:

```bash
DEAL_INTEL_PYTHON=/path/to/python node bin/deal-intel-mcp.js doctor
```

On Windows PowerShell:

```powershell
$env:DEAL_INTEL_PYTHON="$HOME\miniconda3\envs\deal-intel\python.exe"
node bin\deal-intel-mcp.js doctor
```

## Pre-publish fresh smoke

Before npm/PyPI publication, use a local wheel:

```powershell
$env:DEAL_INTEL_HOME = (Resolve-Path ".tmp\d35-fresh-home").Path
$wheel = (Resolve-Path ".tmp\d2_2_dist\deal_intel_mcp-0.2.1-py3-none-any.whl").Path

node npm\bin\deal-intel-mcp.js setup --wheel-url $wheel --python "$HOME\miniconda3\envs\deal-intel\python.exe"
node npm\bin\deal-intel-mcp.js smoke --profile-only
node npm\bin\deal-intel-mcp.js mcp-config --json
```

Keep the detailed checklist in `docs/bootstrapper-fresh-smoke.md`.
