# Bootstrapper Contract

This contract defines the first dependency-inclusive bootstrapper for
`deal-intel-mcp`.

The bootstrapper is the future `npx` front door for users who should not need
to clone the repository, run editable installs, or manually reason about Python
interpreter paths before the first doctor check.

It must not become a second implementation of the MCP server. Its job is to
install, locate, and run the Python package safely.

## Product Goal

Target user:

- a non-developer or AI-assisted user trying Deal Intelligence for the first
  time;
- a small team that wants the `full` MongoDB-backed path but needs guided setup;
- a developer who wants a fast disposable setup without reading the repo first.

The bootstrapper should make these commands possible after npm publication:

```bash
npx deal-intel-mcp setup
npx deal-intel-mcp doctor
npx deal-intel-mcp smoke
npx deal-intel-mcp mcp
npx deal-intel-mcp mcp-config
```

## Non-Goals

The bootstrapper must not:

- reimplement MCP tools in JavaScript;
- parse deal data itself;
- call LLMs directly;
- mutate Claude Desktop config without explicit user confirmation;
- install or create MongoDB Atlas clusters;
- hide paid Atlas/API requirements;
- store secrets inside the npm package directory;
- bundle Python, PyTorch, or local embedding models inside the npm tarball.

## Runtime Layout

Use the user-owned Deal Intelligence runtime directory:

```text
~/.deal-intel/
  config.yaml
  reports/
  smoke/
  product-context/
  runtime/
    install-state.json
    venv/
    logs/
```

Platform-specific Python paths:

```text
Windows: ~/.deal-intel/runtime/venv/Scripts/python.exe
macOS/Linux: ~/.deal-intel/runtime/venv/bin/python
```

The bootstrapper may also create small launcher scripts under:

```text
~/.deal-intel/runtime/bin/
```

Do not write mutable runtime state under:

- the npm package install directory;
- the cloned repository;
- MCPB bundle directories;
- system-level Python locations.

## Install Source

Preferred release path:

1. Install `deal-intel-mcp[embedding]` from PyPI once package metadata is ready.
2. Use TestPyPI only for pre-release validation.
3. Allow a GitHub release wheel URL as an explicit fallback or development
   override.

Do not install from a moving branch such as `main` for the normal user path.

The first implementation may support these explicit modes:

```bash
npx deal-intel-mcp setup --source pypi
npx deal-intel-mcp setup --source testpypi
npx deal-intel-mcp setup --wheel-url https://...
```

Default dependency profile:

```text
deal-intel-mcp[embedding]
```

Reason: product context, semantic search, and most realistic local demos need
embeddings. A lightweight mode may exist, but it should be explicit:

```bash
npx deal-intel-mcp setup --lightweight
```

## Command Contract

### `setup`

Purpose: create or repair the local Python runtime.

Required behavior:

- detect OS and architecture;
- detect usable Python 3.11+;
- prefer `uv` if available;
- if `uv` is unavailable, fall back to `python -m venv` and `pip`;
- create or reuse `~/.deal-intel/runtime/venv`;
- install the selected Python package source;
- write `~/.deal-intel/runtime/install-state.json`;
- print the resolved Python interpreter path;
- run `deal-intel smoke-profile --profile sample` after install to prove the
  runtime works without MongoDB or API keys.

`setup` should not fail merely because the user has not configured MongoDB yet.
Full/pro readiness is diagnosed by `doctor` after the user provides Mongo/API
configuration.

Failure messages must name the failed layer:

- Python missing;
- Python too old;
- venv creation failed;
- package install failed;
- doctor failed;
- permission denied in runtime directory.

### `doctor`

Purpose: explain whether the installed runtime can start.

Required behavior:

- call installed Python:
  `python -m deal_intel.cli config doctor --offline`;
- if the runtime is missing, tell the user to run `setup`;
- never print secrets;
- show the current profile and storage backend.

Optional:

- `--live` may call `deal-intel config doctor` without `--offline`.

### `smoke`

Purpose: run a bounded local validation after setup.

Required behavior:

- call:
  `deal-intel smoke-profile --profile sample`;
- call:
  `deal-intel smoke-natural-questions --as-of 2026-06-10 --output-dir ~/.deal-intel/smoke`;
- keep output under `~/.deal-intel/smoke`;
- summarize pass/fail and output path.

Do not call live LLM completions, embeddings, Atlas admin APIs, or writes by
default.

### `mcp`

Purpose: start the MCP server using the managed runtime.

Required behavior:

- call the installed package through the managed Python interpreter;
- pass through MCP stdio without wrapping tool responses;
- use environment variables already provided by the host/MCPB/user shell;
- fail fast with a useful message if setup has not run.

### `where`

Purpose: print runtime paths for support and MCPB handoff.

Required output:

- Python interpreter path;
- config path;
- report output path;
- smoke output path;
- product context source/cache paths;
- install-state path.

### `mcp-config`

Purpose: print copy-paste MCP handoff material.

Required output:

- MCPB-ready Python interpreter path;
- Claude Desktop `mcpServers` JSON snippet;
- server name used in the snippet;
- note that secrets are intentionally excluded.

This command may be used before the runtime exists because it is a handoff aid.
It should not validate the runtime; `doctor` owns validation.

## Configuration And Secrets

The bootstrapper may create a starter `~/.deal-intel/config.yaml`, but it must
not write API keys or MongoDB URIs unless the user explicitly provides them.

Secrets should be supplied through:

- MCPB user config environment variables;
- the user's shell environment;
- `.env` in the runtime directory only if the user explicitly opts in.

Any generated diagnostic output must redact:

- MongoDB URI credentials;
- OpenAI, Anthropic, or OAuth tokens;
- private key blocks;
- raw product-context documents;
- raw interaction content.

## Install State

Write a JSON file:

```text
~/.deal-intel/runtime/install-state.json
```

Suggested fields:

```json
{
  "schema_version": 1,
  "installed_at": "2026-06-18T00:00:00Z",
  "bootstrapper_version": "0.0.0",
  "python_path": "...",
  "python_version": "3.11.x",
  "package_source": "pypi",
  "package_version": "0.2.1",
  "extras": ["embedding"],
  "last_post_install_check_status": "pass"
}
```

Do not put secrets in this file.

## Acceptance Gate

D3 implementation is not done until these pass:

- fresh Windows setup smoke;
- fresh macOS setup smoke;
- `setup` can recover an already-existing runtime;
- `doctor` gives useful missing-Python and missing-runtime messages;
- `smoke` runs without MongoDB or API keys;
- `mcp` starts from the printed Python path;
- generated paths do not include maintainer-specific usernames;
- output does not print secret values;
- uninstall/manual cleanup instructions are documented.

## Relationship To MCPB

MCPB remains the Claude Desktop installation/config surface.

The bootstrapper should make MCPB easier by providing a stable Python path:

```text
~/.deal-intel/runtime/venv/...
```

MCPB should not be responsible for installing Python dependencies. The
bootstrapper owns that job.
