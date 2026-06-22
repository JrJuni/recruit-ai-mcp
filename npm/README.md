# recruit-ai-mcp Bootstrapper

This is the published `npx` front door for Recruit AI MCP.

Current status: `recruit-ai-mcp@0.2.3` is the npm front door. It installs the
Python package from PyPI by default and places a matching local MCPB file under
`~/.recruit-ai/runtime/mcpb/`. The bootstrapper removes the need for a git clone
or editable install, but it does not bundle Node.js or Python itself.

The Node package must not reimplement the MCP server. It installs, finds, and
runs the Python package described by `docs/bootstrapper-contract.md`.

## Commands

```bash
node bin/deal-intel-mcp.js where
node bin/deal-intel-mcp.js doctor
node bin/deal-intel-mcp.js smoke
node bin/deal-intel-mcp.js mcp
node bin/deal-intel-mcp.js mcp-config
node bin/deal-intel-mcp.js mcpb
node bin/deal-intel-mcp.js setup
```

`setup --dry-run` prints the install plan without changing files. Running
`setup` without `--dry-run` creates `~/.recruit-ai/runtime/venv`, installs the
selected Python package source, copies the bundled MCPB file to
`~/.recruit-ai/runtime/mcpb/`, and runs `smoke-profile --profile sample` as a
post-install check.

`setup` intentionally does not fail just because MongoDB or API keys are not
configured yet. After the user enters real config values, run:

```bash
node bin/deal-intel-mcp.js doctor --live
```

For normal full mode, the user also needs a MongoDB Atlas URI. Create a
Free/M0 Atlas cluster, create a database user, add the current IP under Network
Access, then copy the Connect -> Drivers connection string. Enter that URI only
in the MCPB form, `.env`, or a local shell environment. If the user is not ready
to create Atlas yet, ask whether they want to continue in zero-config
`local_sample` mode for now.

`mcpb` prints the local MCPB file path and the Python interpreter path to paste
into the Claude Desktop MCPB form. `mcp-config` prints the same MCPB handoff
plus a copy-paste Claude Desktop JSON snippet for users who configure MCP
manually.

After installing the MCPB and running `config_doctor`, the first real user
action should be adding recruiting records, not only asking analytics
questions: create a client company, position, and candidate, then run
`recommend_candidates_for_position`, `recommend_positions_for_candidate`, or
`get_recruiting_metrics`.

For local development without the managed runtime, point the wrapper at an
existing Python environment:

```bash
RECRUIT_AI_PYTHON=/path/to/python node bin/deal-intel-mcp.js doctor
```

On Windows PowerShell:

```powershell
$env:RECRUIT_AI_PYTHON="$HOME\miniconda3\envs\deal-intel\python.exe"
node bin\deal-intel-mcp.js doctor
```

## Release smoke

For normal public-release smoke, use the published package:

```powershell
npx.cmd recruit-ai-mcp@0.2.3 setup --python "<path-to-python-3.11+>"
npx.cmd recruit-ai-mcp@0.2.3 smoke --profile-only
npx.cmd recruit-ai-mcp@0.2.3 where --json
npx.cmd recruit-ai-mcp@0.2.3 mcpb --json
npx.cmd recruit-ai-mcp@0.2.3 mcp-config --json
```

For pre-publish or local regression smoke, use a local wheel:

```powershell
$env:RECRUIT_AI_HOME = (Resolve-Path ".tmp\d35-fresh-home").Path
$wheel = (Resolve-Path ".tmp\d2_3_dist\recruit_ai_mcp-0.2.3-py3-none-any.whl").Path

node npm\bin\deal-intel-mcp.js setup --wheel-url $wheel --python "$HOME\miniconda3\envs\deal-intel\python.exe"
node npm\bin\deal-intel-mcp.js smoke --profile-only
node npm\bin\deal-intel-mcp.js mcp-config --json
```

Keep the detailed checklist in `docs/bootstrapper-fresh-smoke.md`.
