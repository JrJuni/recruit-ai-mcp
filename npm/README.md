# deal-intel-mcp Bootstrapper

This is the future `npx` front door for Deal Intelligence MCP.

Current status: D3.2 command skeleton only.

The Node package must not reimplement the MCP server. It should install, find,
and run the Python package described by `docs/bootstrapper-contract.md`.

## Commands

```bash
node bin/deal-intel-mcp.js where
node bin/deal-intel-mcp.js doctor
node bin/deal-intel-mcp.js smoke
node bin/deal-intel-mcp.js mcp
node bin/deal-intel-mcp.js setup
```

`setup` is intentionally not active yet. Runtime installation belongs to D3.3.

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
