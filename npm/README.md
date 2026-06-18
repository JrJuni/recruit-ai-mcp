# deal-intel-mcp Bootstrapper

This is the published `npx` front door for Deal Intelligence MCP.

Current status: `deal-intel-mcp@0.2.1` is published to npm and installs the
Python package from PyPI by default. Public npx smoke has passed with an
explicit Python 3.11+ interpreter path. The bootstrapper removes the need for a
git clone or editable install, but it does not bundle Node.js or Python itself.

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

## Release smoke

For normal public-release smoke, use the published package:

```powershell
npx.cmd deal-intel-mcp@0.2.1 setup --python "<path-to-python-3.11+>"
npx.cmd deal-intel-mcp@0.2.1 smoke --profile-only
npx.cmd deal-intel-mcp@0.2.1 where --json
npx.cmd deal-intel-mcp@0.2.1 mcp-config --json
```

For pre-publish or local regression smoke, use a local wheel:

```powershell
$env:DEAL_INTEL_HOME = (Resolve-Path ".tmp\d35-fresh-home").Path
$wheel = (Resolve-Path ".tmp\d2_2_dist\deal_intel_mcp-0.2.1-py3-none-any.whl").Path

node npm\bin\deal-intel-mcp.js setup --wheel-url $wheel --python "$HOME\miniconda3\envs\deal-intel\python.exe"
node npm\bin\deal-intel-mcp.js smoke --profile-only
node npm\bin\deal-intel-mcp.js mcp-config --json
```

Keep the detailed checklist in `docs/bootstrapper-fresh-smoke.md`.
