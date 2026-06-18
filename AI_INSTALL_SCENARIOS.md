# AI Install Scenarios

This guide is for an AI assistant choosing the right install path for a user
who already has Claude Desktop installed.

The main product path is still `full`: real deal data in the user's MongoDB
Atlas project. `sample` is for a no-MongoDB trial.

## Quick Decision Table

| User scenario | Recommended path | What the user still needs |
|---|---|---|
| Non-developer: Claude installed, no Python, no IDE | `npx` bootstrapper after installing Node.js and Python 3.11+ | Node.js 18+, Python 3.11+, MongoDB Atlas for full mode |
| Beginner: Python or VS Code/Warp exists | `npx` bootstrapper if they only want to use it; git clone if they want to inspect/customize | Existing Python 3.11+ path, MongoDB Atlas for full mode |
| Developer/infra engineer | Existing Python environment, `pip install`, editable install, or `npx` by preference | Their own env/secrets/deployment choices |

Do not present `sample` as the normal human setup unless the user explicitly
wants a no-database trial.

## Scenario 1: Non-Developer, Claude Installed, No Python Or IDE

Current state: this is not yet a fully one-click install. The `npx`
bootstrapper removes git clone and editable install work, but it still needs:

- Node.js 18+ so `npx` can run;
- Python 3.11+ so the bootstrapper can create the managed runtime;
- MongoDB Atlas M0/free cluster for real `full` mode;
- one LLM path: ChatGPT OAuth, Anthropic API key, or OpenAI API key.

Recommended assistant flow:

1. Ask the user to install Node.js LTS from the official Node.js site.
2. Ask the user to install Python 3.11+ or Miniconda.
3. Help the user find the Python executable path.
4. Run:

```powershell
npx.cmd deal-intel-mcp setup --python "<path-to-python-3.11+>"
npx.cmd deal-intel-mcp smoke --profile-only
npx.cmd deal-intel-mcp mcp-config
```

5. Tell the user to paste the `mcp-config` Python interpreter path into the
   Claude Desktop MCPB `Python interpreter path` field.
6. In MCPB, set:
   - Storage backend: `mongo` for real use;
   - MCP tool surface: `auto`;
   - MongoDB Atlas URI: entered locally in the MCPB form;
   - LLM provider: `chatgpt_oauth`, `anthropic`, or `openai_api`.
7. Restart Claude Desktop and ask it to run `config_doctor`.

If the user refuses Python or Node.js installation, only the MCPB artifact is
not enough today because MCPB does not bundle Python dependencies.

## Scenario 2: Beginner, Python / VS Code / Warp Exists

Recommended default: use `npx` unless they want to edit the repo.

Use `npx` when:

- they want the fastest path to Claude Desktop usage;
- they do not plan to modify code;
- they are comfortable giving the bootstrapper an existing Python path.

Use git clone when:

- they want to inspect docs and source locally;
- they want to customize prompts, scoring, reports, or storage;
- they already use VS Code/Warp and are comfortable with a repo checkout.

For `npx`:

```powershell
npx.cmd deal-intel-mcp setup --python "<existing-python-3.11+>"
npx.cmd deal-intel-mcp mcp-config
```

For git clone:

```powershell
git clone https://github.com/JrJuni/deal-intel-mcp.git
cd deal-intel-mcp
<python-3.11+> -m pip install -e ".[embedding]"
<python-3.11+> -m deal_intel.cli config doctor --offline
```

Then use the same MCPB form as Scenario 1.

## Scenario 3: Developer / Infra Engineer

Let them choose their own runtime. Recommended options:

- PyPI package:

```bash
python -m pip install "deal-intel-mcp[embedding]==0.2.1"
python -m deal_intel.cli config doctor --offline
```

- Editable repo install:

```bash
git clone https://github.com/JrJuni/deal-intel-mcp.git
cd deal-intel-mcp
python -m pip install -e ".[dev,embedding]"
python -m pytest -q -p no:cacheprovider
```

- `npx` bootstrapper when they want a managed local runtime:

```bash
npx deal-intel-mcp setup --python /path/to/python
npx deal-intel-mcp mcp-config
```

For infra users, the main value is that the package keeps the MCP server,
storage config, MongoDB schema/index helpers, report exports, and Atlas
chart-ready collections in one installable surface. They can still manage
secrets through environment variables, MCPB sensitive fields, or their own
deployment system.

## Common Validation For All Scenarios

After connecting Claude Desktop, ask the host:

```text
Run config_doctor and summarize whether Deal Intelligence MCP is ready.
```

Then ask:

```text
Show me the current deal list.
How healthy is the current pipeline?
Which deal needs attention first?
Make this week's pipeline report.
```

Expected result:

- `full` mode should use MongoDB Atlas and the standard tool surface.
- `sample` mode should be called a trial/demo path.
- Tool responses should not expose raw notes, contacts, embeddings, API keys,
  MongoDB URI values, or full product documents.
