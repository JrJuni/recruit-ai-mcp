# AI Full Install Guide

This guide is for an AI assistant helping a non-developer or semi-technical
user install `deal-intel-mcp` in the normal **full** mode.

Full mode is the default product path. It stores real deal data in MongoDB
Atlas. Sample mode is only a zero-config trial or demo path.

## 1. First Message To The User

Start by explaining the setup in plain language:

```text
For the normal full setup, you need four things:
1. a MongoDB Atlas account and a Free/M0 cluster,
2. an Atlas connection string (MONGODB_URI),
3. an MCP client such as Claude Desktop or Codex/ChatGPT,
4. either ChatGPT OAuth or an Anthropic/OpenAI API key.

If you only want to try the product shape without MongoDB, sample mode is
available. For real team data, full mode is the default path.
```

Do not ask the user to paste API keys, OAuth tokens, MongoDB URIs, or passwords
into chat unless they explicitly choose to. Prefer `.env`, the MCPB
configuration form, or local environment variables.

## 2. Preparation Checklist

Confirm these before running commands.

| Item | Needed For | Notes |
|---|---|---|
| Windows PowerShell or macOS Terminal | Local setup | Commands below mostly use PowerShell syntax. |
| Git | Clone the repo | Skip if the user already downloaded the repo. |
| Miniconda | Python runtime | Recommended for non-developers because it gives a stable Python path. |
| Python 3.11 conda env | Package install and MCPB config | Use the exact env Python path, not bare `python` or `py`. |
| MongoDB Atlas account | Full mode storage | Free/M0 is enough for MVP use. |
| Atlas database user | MongoDB URI | Needs read/write permission for the selected database. |
| Atlas network access | MongoDB URI | Add the current IP, or use a safe temporary allowlist while testing. |
| MCP client | Chat UI | Claude Desktop MCPB is currently the simplest path. |
| LLM provider | Extraction/scoring | ChatGPT OAuth, Anthropic API key, or OpenAI API key. |

### Platform And Sandbox Notes

- On Windows, path quoting, UTF-8 display, and write permissions under
  `Downloads`, OneDrive, or protected folders can be noisier than on macOS.
  Prefer the exact conda Python path and the default `~/.deal-intel` output
  directories.
- On macOS, UTF-8 and shell quoting are usually smoother, but the user should
  still use the exact Python interpreter from the environment where this package
  is installed.
- Claude Desktop, Codex Desktop, or other AI hosts may run commands inside a
  restricted sandbox. In that case, a live MongoDB/Atlas DNS ping can fail even
  when the same config works from a normal terminal.
- If `config doctor --offline` passes but the live ping fails inside the host
  app, retry `config doctor` from the user's normal terminal before changing
  credentials.

## 3. Python Interpreter Path

The Python interpreter path is the full path to the Python executable inside the
conda environment where `deal-intel-mcp` is installed. MCPB needs this exact
path.

A newly created `deal-intel` environment will usually resolve to an absolute
path similar to:

```text
<absolute-path-to-your-conda-env>\python.exe
```

Confirm the correct path:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -c "import sys; print(sys.executable)"
```

Use the printed value in the MCPB field named `Python interpreter path`.

## 4. MongoDB Atlas Setup

Guide the user through Atlas:

1. Create or open a MongoDB Atlas account.
2. Create a Free/M0 cluster.
3. Create a database user.
4. Add the user's current IP under Network Access.
5. Copy the cluster driver connection string.
6. Replace `<password>` in the URI locally.

Tell the user:

```text
The Atlas connection string often contains a password, so treat it as a secret.
Do not paste it into chat. Put it in a local `.env` file, your shell
environment, or the MCPB configuration form.
```

## 5. Local Install

Clone the repo:

```powershell
git clone <repo-url>
cd deal-intel-mcp
```

Create a conda env if needed:

```powershell
& "$HOME\miniconda3\Scripts\conda.exe" create -n deal-intel python=3.11 -y
```

Install the package:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m pip install -e ".[dev,embedding]"
```

If the user chose a different environment name, replace the Python path with the
value printed by `sys.executable`.

## 6. Configure Full Mode

Use full mode for real data:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli config switch full
```

Store secrets outside chat. Common options:

1. A local `.env` file in the repo.
2. The MCPB configuration form.
3. Environment variables for the current shell session.

Typical `.env` entries:

```text
MONGODB_URI=<atlas-uri>
OPENAI_API_KEY=<only-if-using-openai-api>
ANTHROPIC_API_KEY=<only-if-using-anthropic>
```

For ChatGPT OAuth, run the login once:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli login-chatgpt
```

## 7. Doctor And Smoke Checks

Start with offline checks:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli config doctor --offline
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli smoke-profile --profile full --offline
```

Then run live storage checks:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli storage-status
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli mongo doctor
```

Expected direction:

- `config doctor`: no failed checks.
- `smoke-profile --profile full --offline`: pass.
- `storage-status`: MongoDB reachable.
- `mongo doctor`: indexes and schema validators visible, or actionable setup
  hints returned.

## 8. Claude Desktop MCPB Settings

When the MCPB form appears, recommend:

| Field | Recommended Value |
|---|---|
| Python interpreter path | The conda env Python where this package is installed. |
| Storage backend | `mongo` |
| MCP tool surface | `auto` |
| MongoDB Atlas URI | User's Atlas URI, entered locally only. |
| LLM provider | `chatgpt_oauth` by default. |
| Anthropic API key | Only if provider is `anthropic`. |
| OpenAI API key | Only if provider is `openai_api`. |

After installing or changing MCPB settings, restart Claude Desktop.

Ask Claude/Codex to run:

```text
Run config_doctor and check the setup status.
```

For full mode, the normal tool surface should expose the standard real-data
tools. If it shows sample mode, check the storage backend and config profile.

## 9. First Useful Questions

After setup succeeds, ask:

```text
Show me the current deal list.
How healthy is the current pipeline?
Review the riskiest deal.
What are customers most often concerned about?
Make this week's pipeline report.
```

## 10. When To Use Sample Mode

Use sample mode only when:

- the user wants a no-MongoDB trial,
- an AI assistant needs a quick product-shape check,
- a demo needs fictional bundled data,
- the user is not ready to create Atlas credentials.

Sample mode can be useful for lightweight personal testing, but tell the user
that real team operation is designed around MongoDB-backed full mode.

## 11. Troubleshooting Map

| Symptom | Likely Cause | First Check |
|---|---|---|
| Claude shows sample tools only | Storage backend/profile is sample | Run `config_doctor`. |
| Mongo doctor says backend is local_sample | Config not switched to full | Run `config switch full`. |
| Mongo ping fails | URI, password, IP allowlist, or cluster state | Check Atlas connection string and Network Access. |
| Mongo ping fails only inside an AI host | Host sandbox/network restriction | Run `config doctor` from a normal terminal and compare with `config doctor --offline`. |
| LLM tools fail | OAuth expired or API key missing | Run `login-chatgpt` or check selected provider key. |
| MCP server fails to start | Wrong Python path in MCPB | Verify the interpreter path has `deal-intel-mcp` installed. |
| Korean text looks broken | Encoding/display issue | Prefer UTF-8 files and avoid copying secrets through chat. |

## 12. AI Assistant Safety Rules

- Do not store API keys, OAuth tokens, MongoDB URIs, or passwords in docs.
- Do not put setup guides in `user_docs/`; that folder is user memory.
- Do not treat sample mode as the default path for a human user.
- For destructive actions such as delete, explain dry-run and archive gates.
- For low-risk classification/taxonomy, draft a recommendation first and let
  the user correct it when needed.

## 13. Customization And License

This project is MIT-licensed. Users may fork it, customize the storage, model,
scoring, reporting, and workflow behavior, and adapt it to their own deal
process. Keep license and attribution notices when redistributing modified
versions.

If you are helping customize this repo, prefer small explicit changes. Do not
store secrets in docs. Record meaningful local modifications in docs or user
memory so future agents can understand what changed.
