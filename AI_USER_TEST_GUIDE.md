# AI User Test Guide

This guide is for an AI assistant helping a first external tester try Deal
Intelligence MCP.

Use this after the maintainer has provided one usable install path:

- a Claude Desktop MCPB artifact; or
- the future `npx deal-intel-mcp` bootstrapper after npm/PyPI publication.

Do not ask the tester to paste MongoDB URIs, API keys, OAuth tokens, or raw
private files into chat. Ask them to enter secrets only in the local MCPB form,
local `.env`, local shell environment, or local config file.

## Recommended Test Path

For real evaluation, use `full` mode with MongoDB Atlas. `sample` mode is useful
for a quick no-database trial, but it does not prove the tester's real data path.

Recommended order:

1. Confirm prerequisites.
2. Install or connect the MCP server.
3. Run config/readiness checks.
4. Ask five natural questions.
5. Create one disposable test deal or use sample data.
6. Export one report or data ledger.
7. Record feedback.

## Prerequisites To Confirm

Ask the tester to prepare:

- MongoDB Atlas account and an M0/free cluster for `full` mode;
- Claude Desktop, Codex/ChatGPT with MCP support, or another MCP host;
- one LLM path: ChatGPT OAuth, Anthropic API key, or OpenAI API key;
- Python 3.11+ if using the git-clone or MCPB Python-interpreter path;
- Node.js 18+ only if using the future `npx` bootstrapper path.

If the tester does not have MongoDB ready, start with `sample` mode and clearly
say that it is a trial profile.

## Install Path A: MCPB Artifact

Use this when the maintainer has provided a `.mcpb` file.

Ask the tester to install the MCPB bundle in the host app, then fill the MCPB
form:

| Field | Guidance |
|---|---|
| Python interpreter path | A Python 3.11+ interpreter where `deal-intel-mcp` is installed |
| Storage backend | `mongo` for real evaluation, `local_sample` for quick trial |
| MCP tool surface | `auto` |
| MongoDB Atlas URI | Enter locally, never in chat |
| LLM provider | `chatgpt_oauth`, `anthropic`, or `openai_api` |
| API key fields | Enter locally, never in chat |

Then ask the host app:

```text
Run config_doctor and summarize whether Deal Intelligence MCP is ready.
```

## Install Path B: Future npx Bootstrapper

Use this only after npm and Python package publication is complete.

Ask the tester to run:

```bash
npx deal-intel-mcp setup
npx deal-intel-mcp smoke --profile-only
npx deal-intel-mcp mcp-config
```

Then use the Python interpreter path printed by `mcp-config` in MCPB or manual
host configuration.

After MongoDB/API values are configured, ask the host app:

```text
Run config_doctor and tell me what still needs setup.
```

## First Five Questions

Ask these first. They are short enough for a new tester and cover the main
workflow:

1. What is the current pipeline health?
2. Which deals need attention first?
3. Show me the status of one specific deal.
4. Create this week's pipeline report.
5. What decision criteria do customers mention most often?

Expected behavior:

- The assistant should pick MCP tools without asking the tester to choose tool
  names.
- The answer should not expose raw notes, contacts, embeddings, API keys, or
  MongoDB URI values.
- If data quality is weak, the answer should say what is missing instead of
  pretending the numbers are certain.

## Minimal Smoke Prompts

Use these exact prompts when checking a newly installed host app:

```text
Run config_doctor and show me the profile, storage backend, LLM provider, and
tool surface.
```

```text
List active deals and highlight overdue or at-risk deals.
```

```text
Generate a weekly pipeline report and tell me where the files were saved.
```

```text
Search for deals related to cost reduction.
```

```text
What customer themes or decision criteria appear most often?
```

## Feedback To Collect

Ask the tester:

- Was installation blocked by Python, Node, MongoDB, API keys, or the MCP host?
- Did the assistant choose the right tool without being told?
- Were answers useful without sounding overconfident?
- Did any output leak sensitive raw content?
- Did report files open on the tester's machine?
- Which one question did the tester expect to work but did not?

Record feedback in issues or user-memory docs. Do not paste secrets into
feedback.

## Stop Conditions

Stop and ask the maintainer before proceeding if:

- a command asks for registry credentials;
- MongoDB writes would affect a non-disposable production database;
- a report or tool response exposes secrets or raw private documents;
- the tester wants a destructive delete;
- the MCP host cannot load the server after repeated restart attempts.
