# deal-intel-mcp Bootstrapper

This is the future `npx` front door for Deal Intelligence MCP.

Current status: D3.4 MCP/Claude handoff draft.

The Node package must not reimplement the MCP server. It should install, find,
and run the Python package described by `docs/bootstrapper-contract.md`.

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
`setup` without `--dry-run` creates `~/.deal-intel/runtime/venv` and installs
the selected Python package source.

`mcp-config` prints the Python interpreter path for MCPB and a copy-paste
Claude Desktop JSON snippet for users who configure MCP manually.

For local development before D3.3, point the wrapper at an existing Python
environment:

```bash
DEAL_INTEL_PYTHON=/path/to/python node bin/deal-intel-mcp.js doctor
```

On Windows PowerShell:

```powershell
$env:DEAL_INTEL_PYTHON="$HOME\miniconda3\envs\deal-intel\python.exe"
node bin\deal-intel-mcp.js doctor
```
