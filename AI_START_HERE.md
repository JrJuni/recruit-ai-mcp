# AI Start Here

This is the canonical first-run guide for an AI agent helping a new user set up
`recruit-ai-mcp`. Use it before reading deeper install docs.

Bootstrap note: this repo is a recruiting fork. Public metadata, config paths,
env prefix, and MongoDB defaults are isolated for `recruit-ai-mcp`, while the
Python package still uses `deal_intel` internals during the staged cutover. The
first recruiting MCP tools now coexist with inherited deal-intelligence
compatibility tools.

For a step-by-step walkthrough for non-developer full-mode setup, read
[`AI_FULL_INSTALL_GUIDE.md`](AI_FULL_INSTALL_GUIDE.md). For Korean users, use
[`AI_FULL_INSTALL_GUIDE.ko.md`](AI_FULL_INSTALL_GUIDE.ko.md).

For first external tester handoff, read
[`AI_USER_TEST_GUIDE.md`](AI_USER_TEST_GUIDE.md).

For a short public/community demo script, read
[`docs/public-demo-script.md`](docs/public-demo-script.md).

For fork/customization work, read [`docs/extending.md`](docs/extending.md)
first, then [`docs/customization-recipes.md`](docs/customization-recipes.md),
then [`docs/architecture.md`](docs/architecture.md) for the deeper module map.

## Default Decision

Start human users in **`full`** mode.

- `full` = normal product path, MongoDB Atlas-backed real recruiting/team data.
  Atlas M0 is enough.
- `sample` = optional zero-config trial for AI evaluation, demos, or users who
  explicitly do not want MongoDB yet.
- `pro` = paid-infra upgrade path for Atlas Vector Search and API-key LLM
  operation.

Do not present `sample` as the normal install path. It is useful, but it is not
the main product posture.

## First Run For A Human User

First classify the user's setup and choose one route. Keep the human product
default as `full`; the route only decides how the package gets installed.

- Non-developer: use the npx bootstrapper after installing Node.js 18+ and
  Python 3.11+.
- Python/VS Code/Warp already exists: use npx for fast usage, or git clone /
  editable install for customization.
- Developer/infra engineer: let them use their own Python environment,
  editable install, PyPI install, or npx by preference.

Before asking the user to run commands, explain the required pieces in plain
language:

- MongoDB Atlas account and a Free/M0 cluster for real recruiting/team storage.
- A MongoDB connection string (`MONGODB_URI`) from that cluster.
- One chat surface:
  - Claude Desktop with the MCPB extension, or
  - Codex/ChatGPT with MCP support.
- One LLM path for extraction/scoring:
  - ChatGPT OAuth if the user has a compatible ChatGPT/Codex subscription, or
  - Anthropic API key, or
  - OpenAI API key.

Use this short prompt if the user asks what to prepare:

```text
For the normal full setup, prepare four things:
1. a MongoDB Atlas account,
2. a free Atlas cluster and connection string,
3. Claude Desktop or Codex/ChatGPT as the MCP client,
4. either ChatGPT OAuth from your subscription or an Anthropic/OpenAI API key.

If you do not want to set up MongoDB yet, we can run the sample mode first, but
that is a trial path, not the default real-data setup.
```

### MongoDB Atlas URI Quick Guide

If the user does not already have `MONGODB_URI`, guide them through this short
flow:

1. Go to <https://www.mongodb.com/cloud/atlas/register> and create or sign in
   to a MongoDB Atlas account.
2. Create a Free/M0 cluster.
3. In Database Access, create a database user with read/write access.
4. In Network Access, add the user's current IP address.
5. Open the cluster's Connect -> Drivers flow and copy the connection string.
6. Replace `<password>` locally. Store the URI in the MCPB form, `.env`, or a
   shell environment variable. Do not ask the user to paste the URI into chat.

If the user is not ready to create the URI, ask:

```text
MongoDB Atlas is the normal full-mode storage path. Do you want to set that up
now, or continue in zero-config sample mode for now and come back to MongoDB
later?
```

### Conda First-Run Terms Of Service

If the user just installed Miniconda/Anaconda, the first `conda create` or
`conda install` can stop and ask for Terms of Service acceptance for Anaconda's
default channels. This is expected. The usual channels are:

- `https://repo.anaconda.com/pkgs/main`
- `https://repo.anaconda.com/pkgs/r`

Guide the user to read the prompt and enter `a` for each channel they accept.
If they prefer to accept from the command line after reviewing the terms, use:

```bash
conda tos accept
```

If conda asks for channel-specific acceptance, use:

```bash
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
```

Reference:
<https://www.anaconda.com/docs/getting-started/tos-plugin>

Use the conda environment Python directly. First help the user identify the
interpreter path for the environment where `recruit-ai-mcp` is installed. For a
new local setup, the recommended environment name is `deal-intel`:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -c "import sys; print(sys.executable)"
```

If the user wants the no-git-clone install path, run the npx bootstrapper with
the Python path you just found:

```powershell
npx.cmd recruit-ai-mcp setup --python "$HOME\miniconda3\envs\deal-intel\python.exe"
npx.cmd recruit-ai-mcp mcp-config
```

The bootstrapper creates a managed runtime under `~/.recruit-ai/runtime`,
installs the Python package, runs a sample smoke check, and prints the Python
interpreter path to use in MCPB or manual MCP config. It still requires Node.js
and Python to be installed first.

If the user wants to inspect or customize source code, have them clone or
download the repo, open a terminal in the repo root, and run:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m pip install -e ".[embedding]"
```

Use the printed path in later commands and in the MCPB `Python interpreter path`
field. In examples below, replace the path if the user chose a different conda
environment:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli config profiles
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli config show
```

Then guide the user through the `full` path:

1. Confirm the package is installed in the selected Python environment.
2. Help the user create or locate a MongoDB Atlas Free/M0 cluster.
3. Help the user copy the driver connection string and save it as
   `MONGODB_URI`.
4. Keep `tools.surface=auto`.
5. Keep `llm.provider=chatgpt_oauth` unless the user chose API keys.
6. Run:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli config doctor --offline
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli smoke-profile --profile full --offline
```

If Atlas is reachable and the user wants a live storage check:

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli storage-status
```

## Optional Zero-Config Trial

Use this only when the user asks to try without MongoDB, or when an AI agent
needs a fast product-shape check before asking the user to configure Atlas.

```powershell
$env:RECRUIT_AI_STORAGE_BACKEND='local_sample'
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli smoke-profile --profile sample
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli smoke-natural-questions --as-of 2026-06-10
```

Sample mode starts with immutable fictional data. If the user creates their own
local deals, the fixture is hidden from the active working view and the local
personal dataset becomes active.

## Claude Desktop / MCPB Install

When installing the MCPB, recommend:

- Python interpreter path: the env where `recruit-ai-mcp` is installed.
- Storage backend: `mongo` for real use; `local_sample` only for zero-config
  trial.
- MCP tool surface: `auto`.
- MongoDB Atlas URI: required for `mongo`.
- LLM provider: `chatgpt_oauth` by default.

Expected visible tool counts:

- `sample`: 24 tools
- `standard` / `full`: 48 tools
- `developer`: 52 tools

If the host app's tool search shows only a handful of tools, that is usually a
host-side search limit rather than a server loading failure. Ask it to call
`get_tool_catalog` for the full current Recruit AI tool surface.

After restart, ask Claude/Codex to run `config_doctor` first.

## First Useful Recruiting Data

If `config_doctor` is OK, do not stop at diagnostics. Help the user add the
first real recruiting records so the system has something useful to match,
score, and remember.

For a new recruiting `full` workspace, the first value path is:

1. Create the hiring customer with `create_client_company`.
2. Create one search mandate with `create_position`.
3. Create one candidate profile with `create_candidate`.
4. Add useful evidence with `add_recruiting_interaction` or
   `add_client_feedback`.
5. Run `recommend_candidates_for_position`, `recommend_positions_for_candidate`,
   or `get_recruiting_metrics`.

Use this prompt after a successful first `config_doctor`:

```text
Setup looks ready. The next step is to add the first recruiting records.

Please give me one client/company, one open role, and one candidate profile.
Useful details are: role title, must-have skills, seniority, location/remote
policy, target compensation if known, candidate skills, current title,
locations, availability, and any client preference or feedback.

I will create the client, position, and candidate, then run the first
candidate-position recommendation or recruiting pipeline metric.
```

Inherited deal-intelligence tools still exist during the staged cutover. If
the user is using the legacy deal workflow instead, use this path:

1. Create or identify the first deal with `create_deal` or `list_deals`.
2. Ask the user to paste one customer evidence item:
   - a meeting note,
   - a customer email reply,
   - a call summary,
   - a user interview,
   - or an internal sales note.
3. Store it with `add_interaction`.
4. Run `get_deal_review` on that deal to show health, gaps, uncertainty, and
   next questions.

Prompt for the inherited deal workflow:

```text
Setup looks ready. The next step is to add your first customer evidence.

Please paste one of these:
- a meeting note,
- a customer email reply,
- a call summary,
- a user interview,
- or an internal sales note.

If this is a new prospect, also tell me the company name, industry if known,
current stage, rough deal size if known, and expected close date if known.
I will create or select the deal, store the evidence with add_interaction, then
show you the first deal review.
```

For sample mode, explain that fictional deal records already exist. For an
Atlas-backed fictional recruiting demo, switch to the `developer` surface and
run `create_sample_data(dataset="recruiting_pipeline_demo")` against the demo
database.

## First Useful Questions

After at least one recruiting or deal evidence item exists, ask:

```text
Who are the strongest candidates for this position?
Which open positions fit this candidate?
Show recruiting pipeline metrics.
How healthy is the current pipeline?
Show me the current deal list.
Which deal needs attention first?
What are customers most often concerned about?
```

## Tool Selection Defaults

Prefer deterministic read tools for normal questions:

- Candidate recommendations for a role -> `recommend_candidates_for_position`
- Open-position recommendations for a candidate -> `recommend_positions_for_candidate`
- Recruiting KPI / funnel / feedback metrics -> `get_recruiting_metrics`
- Recruiting Markdown/CSV pipeline report -> `export_recruiting_report`
- Pipeline health / KPI / trend -> `get_metrics`
- Pipeline table / stuck deals at a glance -> `list_deals`
- One deal's stored history -> `get_deal`
- One deal's status, risk, uncertainty, and next questions -> `get_deal_review`
- Missing customer or forecast information -> `get_deal_gaps`
- Manager/team meeting report -> `export_report`
- Excel/CSV-ready deal ledger -> `export_data`
- Server-side LLM usage / rough cost check -> `get_usage`
- Product/solution docs folder setup -> `update_config(product_context_source_dirs=...)`
- Pasted product/solution note -> `add_product_context_note`
- Product context indexing -> `index_product_context`
- Product context lookup/verification -> `get_product_context`
- Customer concern or decision-criteria ranking -> start with `get_customer_themes`
- Stage/industry/tag theme comparison -> then use `get_customer_theme_breakdown`
- Evidence snippets for one known theme -> then use `get_customer_theme_evidence`

Use LLM/write tools only when the user intent requires them:

- New evidence to store and score -> `add_interaction`
- Confirmed stage transition -> `update_stage`
- Confirmed metadata/value correction -> `update_deal`
- Optional generated BD strategy memo -> `analyze_deal`

Do not use `analyze_deal` as the default deal-review tool. It calls the
configured server-side LLM, previews by default, and persists `bd_strategy`
only when called with explicit persistence confirmation. For routine review,
use `get_deal_review` first.
If product context has been indexed, `analyze_deal` may use bounded seller-side
snippets for strategy/positioning context, while storing only refs metadata.

For new evidence, use `add_interaction` as the single public intake:

- meeting notes: `interaction_type=meeting`
- customer email replies: `interaction_type=email_thread`
- user interviews: `interaction_type=user_interview`
- internal notes: `interaction_type=internal_note`

Check the returned `source_policy`. Customer-stated inbound evidence can update
qualification/customer themes. MEDDPICC is the default framework, but custom
qualification frameworks may be active. Outbound-only or internal-only content
is retained as context but should not be described as confirmed deal health.

## Product / Solution Context

Product context is seller-side knowledge, not customer evidence. Use it for
product facts, ICP notes, positioning, pricing/packaging notes, integrations,
security posture, competitor notes, and disqualifiers.

Two normal flows:

1. The user has a folder of product docs:
   - Call `update_config(product_context_source_dirs="path1;path2")` if the
     configured folder needs to change.
   - Call `index_product_context(dry_run=true)` to preview.
   - If the preview is acceptable, call `index_product_context(dry_run=false)`.
   - Verify with `get_product_context(query="...")`.

2. The user pastes product/solution text into the chat:
   - Call `add_product_context_note(title="...", content="...", dry_run=true)`.
   - If the user confirms, call it again with `dry_run=false` and
     `confirmed_by_user=true`.
   - Then run `index_product_context` and verify with `get_product_context`.

Do not treat product context as customer-stated evidence. It can help
`add_interaction` interpret terminology, fit, value props, competitors, and
disqualifiers, but it must not directly raise qualification scores or customer
theme counts.

## User Memory

If the user gives durable preferences about reporting style, scoring behavior,
taxonomy, or evidence policy, use `record_user_memory`. To inspect those notes,
use `get_user_memory`.

Never store secrets, raw transcripts, full emails, contacts, API keys, OAuth
tokens, or MongoDB connection strings in user memory.

## Customization And License

This project is MIT-licensed. Users may fork it, customize storage/model/report
behavior, and adapt it to their own deal workflow. Keep license and attribution
notices when redistributing modified versions.

If you are helping customize this repo, prefer small explicit changes. Avoid
storing secrets in docs. Record meaningful local modifications in docs or user
memory so future agents can understand what changed.

When the user asks to customize or fork the project:

1. Read `docs/extending.md` for the available extension seams.
2. Check `docs/customization-recipes.md` for a matching recipe.
3. Use `docs/architecture.md` only after identifying the subsystem to change.
4. Prefer built-in extension paths before rewriting core modules.
5. Keep the default product posture full-first; use sample only as an optional
   zero-config trial.

## Do Not

- Do not use bare `python` or `py` on Windows.
- Do not ask for API keys before the user chooses an API-key provider.
- Do not run `config switch ... --force` without explicit user approval.
- Do not print secrets from `.env`, user config, or command output.
- Do not auto-change deal stage from interaction content. `add_interaction`
  can suggest; `update_stage` performs the actual stage change after user
  confirmation.
