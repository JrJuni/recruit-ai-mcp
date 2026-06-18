# AI npx Install Guide

This guide is for an AI assistant helping a user install Deal Intelligence MCP
through the no-git-clone `npx deal-intel-mcp` bootstrapper.

Use this when the user wants the quickest install path and has Node.js plus a
usable Python 3.11+ interpreter. For manual git-clone setup, use
`AI_FULL_INSTALL_GUIDE.md`.

## What This Path Should Do

The npx bootstrapper should:

1. find a usable Python 3.11+ interpreter;
2. create a managed runtime under `~/.deal-intel/runtime`;
3. install `deal-intel-mcp[embedding]`;
4. run a zero-config sample smoke;
5. print the Python interpreter path for MCPB or manual Claude Desktop config.

It should not ask the user to clone this repository.

## Prerequisites

Ask the user to prepare:

- Node.js 18+ with `npx`;
- Python 3.11+ installed somewhere on the machine;
- for real full-mode use, a MongoDB Atlas account and M0/free cluster;
- one MCP host such as Claude Desktop or Codex/ChatGPT with MCP support;
- one LLM credential path: ChatGPT OAuth, Anthropic API key, or OpenAI API key.

Do not ask the user to paste MongoDB URIs, API keys, or OAuth tokens into chat.
Use the MCPB form, local `.env`, or local shell environment variables.

## First Install

Run:

```bash
npx deal-intel-mcp setup
```

Expected result:

- exits `0`;
- creates `~/.deal-intel/runtime/venv`;
- installs the Python package;
- runs `smoke-profile --profile sample`;
- prints the next action.

On Windows, Python is often installed but not on `PATH`. If setup says Python is
missing or reports `detected unknown`, point the bootstrapper at an existing
interpreter:

```bash
npx deal-intel-mcp setup --python /path/to/python
```

PowerShell example:

```powershell
npx.cmd deal-intel-mcp setup --python "$HOME\miniconda3\envs\deal-intel\python.exe"
```

## Verify The Runtime

Run:

```bash
npx deal-intel-mcp smoke --profile-only
npx deal-intel-mcp mcp-config
```

`mcp-config` should print:

- the managed Python interpreter path;
- a Claude Desktop config snippet;
- a reminder that secrets are not included.

## Connect Claude Desktop With MCPB

In the MCPB form:

| Field | Value |
|---|---|
| Python interpreter path | The path printed by `npx deal-intel-mcp mcp-config` |
| Storage backend | `mongo` for real use, `local_sample` only for trial |
| MCP tool surface | `auto` |
| MongoDB Atlas URI | User's local Atlas URI |
| LLM provider | `chatgpt_oauth`, `anthropic`, or `openai_api` |

Restart Claude Desktop after changing MCPB settings.

## Full-Mode Readiness Check

After MongoDB/API values are configured, ask the MCP host to run
`config_doctor`, or run from the terminal:

```bash
npx deal-intel-mcp doctor --live
```

Expected direction:

- profile is `full` or `pro` for real data;
- storage backend is `mongo`;
- MongoDB ping passes;
- tool surface resolves to the standard real-data surface;
- LLM readiness is pass or gives an actionable login/API-key hint.

## First Useful Questions

Ask the MCP host:

```text
Show me the current deal list.
How healthy is the current pipeline?
Which deal needs attention first?
Make this week's pipeline report.
What are customers most often concerned about?
```

## Troubleshooting

| Symptom | First Check |
|---|---|
| `npx` cannot find the package | Check network access to the public npm registry. |
| setup cannot find Python | Install Python 3.11+ or rerun with `--python`. On Windows, this often means Python is installed but not on `PATH`. |
| setup fails during package install | Check network access to PyPI or the configured wheel source. |
| sample smoke passes but Mongo fails | Configure `MONGODB_URI`, Atlas user, password, and IP allowlist. |
| MCPB starts sample mode | Check Storage backend and run `config_doctor`. |
| LLM tools fail | Run ChatGPT OAuth login or provide the selected API key locally. |

## Safety Rules For AI Assistants

- Never store secrets in docs, user memory, package files, or screenshots.
- Do not mutate Claude Desktop config automatically without explicit approval.
- Do not present sample mode as the normal real-data path.
- If setup works but full mode fails, treat it as a configuration issue, not an
  installation failure.
