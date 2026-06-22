# AI User Test Guide

This guide is for an AI assistant helping a first external tester try Recruit
AI MCP.

Use this after the maintainer has provided one usable install path:

- a Claude Desktop MCPB artifact; or
- the `npx recruit-ai-mcp` bootstrapper after public npm/PyPI publication.

Current handoff paths:

- use `release/latest/recruit-ai-mcp-0.1.0.mcpb`;
- before public registry publication, use the local MCPB or an editable/local
  wheel install path rather than public `npx`;
- after publication and public fresh-smoke evidence, use
  `npx recruit-ai-mcp setup` to create a managed Python runtime;
- paste the local Python interpreter path into the MCPB form;
- for npx installs, use the interpreter path printed by
  `npx recruit-ai-mcp mcp-config`.

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
5. Create one disposable recruiting client, position, and candidate, or use
   recruiting sample data.
6. Export one report or data ledger.
7. Record feedback.

## Prerequisites To Confirm

Ask the tester to prepare:

- MongoDB Atlas account and an M0/free cluster for `full` mode;
- Claude Desktop, Codex/ChatGPT with MCP support, or another MCP host;
- one LLM path: ChatGPT OAuth, Anthropic API key, or OpenAI API key;
- Python 3.11+ if using the git-clone path, MCPB Python-interpreter path, or
  the npx bootstrapper's `--python` option;
- Node.js 18+ if using the `npx` bootstrapper path.

If the tester does not have MongoDB ready, start with `sample` mode and clearly
say that it is a trial profile.

## Install Path A: MCPB Artifact

Use this when the maintainer has provided a `.mcpb` file.

For the current pre-registry user test, the repository includes:

```text
release/latest/recruit-ai-mcp-0.1.0.mcpb
```

Ask the tester to install the MCPB bundle in the host app, then fill the MCPB
form:

| Field | Guidance |
|---|---|
| Python interpreter path | A Python 3.11+ interpreter where `recruit-ai-mcp` is installed |
| Storage backend | `mongo` for real evaluation, `local_sample` for quick trial |
| MCP tool surface | `auto` |
| MongoDB Atlas URI | Enter locally, never in chat |
| LLM provider | `chatgpt_oauth`, `anthropic`, or `openai_api` |
| API key fields | Enter locally, never in chat |

Then ask the host app:

```text
Run config_doctor and summarize whether Recruit AI MCP is ready.
```

## Install Path B: npx Bootstrapper

Use this only after `recruit-ai-mcp@0.1.0` is published to npm/PyPI and public
fresh-smoke evidence exists. Ask the tester to run:

```bash
npx recruit-ai-mcp setup
npx recruit-ai-mcp smoke --profile-only
npx recruit-ai-mcp mcp-config
```

If setup cannot find Python, rerun it with an explicit Python 3.11+
interpreter:

```bash
npx recruit-ai-mcp setup --python /path/to/python
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

1. Which candidates best match this open position?
2. Which open positions best fit this candidate?
3. What client feedback is changing the ranking?
4. Create a recruiting pipeline report.
5. What risks or missing evidence should we review before submission?

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
Show active recruiting submissions and highlight risky or blocked ones.
```

```text
Generate a recruiting pipeline report and tell me where the files were saved.
```

```text
Recommend candidates for one open position.
```

```text
What client preferences or feedback patterns appear most often?
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
