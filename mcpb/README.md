# mcpb - Claude Desktop bundle

This folder builds `recruit-ai-mcp.mcpb`, a [Claude Desktop MCP Bundle](https://github.com/modelcontextprotocol/mcpb) for one-click install.

## Why .mcpb

The bundle ships the manifest + user-config schema. When the user double-clicks `recruit-ai-mcp-{version}.mcpb`, Claude Desktop prompts for the required paths/keys via a UI form instead of asking the user to hand-edit JSON.

This bundle does not include the Python package or dependencies. The easiest
no-git-clone path is to run `npx deal-intel-mcp setup` first, then paste the
Python interpreter path printed by `npx deal-intel-mcp mcp-config` into the
MCPB form.

Alternatively, install the project into an existing Python environment first,
then provide these fields:

- **`python_path`** - select the Python interpreter where `recruit-ai-mcp` is
  installed. This can be the npx-managed runtime path or an existing Python
  environment that ran `pip install "recruit-ai-mcp[embedding]"` or
  `pip install -e ".[embedding]"`.
- **`storage_backend`** - choose `mongo` for real Atlas-backed data. Use
  `local_sample` only for zero-config sample/local personal mode.
- **`tools_surface`** - choose `auto` for profile-based filtering. Advanced
  users can select `sample`, `standard`, or `developer` explicitly.
- **`mongodb_uri`** - MongoDB Atlas connection string. Required only when
  `storage_backend=mongo`; M0 free tier works for the full profile.

API keys are optional in the form - the server also loads them from the repo's
`.env` as a fallback. ChatGPT OAuth is the default and does not require an API
key.

For the normal `full` install, prepare:

1. MongoDB Atlas account.
2. Free/M0 cluster and driver connection string.
3. Claude Desktop as the MCP client.
4. ChatGPT OAuth, Anthropic API key, or OpenAI API key for LLM-backed
   extraction/scoring.

MongoDB Atlas links:

- Sign up: <https://www.mongodb.com/cloud/atlas/register>
- Free cluster guide:
  <https://www.mongodb.com/docs/atlas/tutorial/deploy-free-tier-cluster/>

## Build

```bash
cd mcpb
mcpb validate manifest.json
mcpb pack . recruit-ai-mcp-0.2.3.mcpb   # output goes into mcpb/ folder
mcpb info recruit-ai-mcp-0.2.3.mcpb
```

`mcpb` CLI: `npm install -g @anthropic-ai/mcpb` (Node.js 18+).

The `.mcpb` output is gitignored by default because it is a version-stamped
build artifact. Rebuild it in this folder for local/package smoke tests.
Update `release/latest/` only when intentionally publishing a new latest
release artifact.

## Install

Recommended no-git-clone preparation:

```bash
npx deal-intel-mcp setup --python /path/to/python
npx deal-intel-mcp mcp-config
```

Use the `mcp-config` Python path in the MCPB form.

1. Open Claude Desktop -> Settings -> Extensions
2. Drag `recruit-ai-mcp-{version}.mcpb` onto the Extensions pane (or click "Install from file")
3. Fill the user_config form:
   - **Python interpreter path** - select the npx-managed Python path or an
     existing environment's `python.exe`
   - **Storage backend** - `mongo` for real Atlas data; `local_sample` only for zero-config sample mode
   - **MCP tool surface** - `auto` for normal installs; `sample`, `standard`,
     or `developer` only when intentionally overriding the profile default
   - **MongoDB Atlas URI** - required only when `Storage backend` is `mongo`
   - **LLM provider** - `chatgpt_oauth` by default; can be `anthropic` or `openai_api`
   - **Use ChatGPT Plus/Pro** - legacy checkbox kept for older installs; the LLM provider field wins when set
   - **Anthropic API key** - required only when using `anthropic`
   - **OpenAI API key** - required only when using `openai_api`
   - For `chatgpt_oauth`, run `deal-intel login-chatgpt` once in a terminal after install to authenticate
4. Restart Claude Desktop
5. Verify the MCP tool list loads. The current tool contract is documented in
   `docs/baseline.md` and implemented in `src/deal_intel/mcp_server.py`.

If you do not have a MongoDB Atlas URI yet, choose one path explicitly:

- normal full mode: create a Free/M0 Atlas cluster, copy the Connect -> Drivers
  URI, and enter it only in the MCPB form, `.env`, or a local shell
  environment;
- temporary trial: set **Storage backend** to `local_sample` and use the
  bundled zero-config sample data until you are ready to configure Atlas.

Suggested first install:

1. Set **Storage backend** to `mongo`.
2. Set **MCP tool surface** to `auto`.
3. Fill **MongoDB Atlas URI**. M0/free tier works for the `full` profile.
4. Restart Claude Desktop and run `config_doctor(offline=true)`.
5. If `config_doctor` is OK, create the first client, position, and candidate
   with `create_client_company`, `create_position`, and `create_candidate`.
6. Run `recommend_candidates_for_position`, `recommend_positions_for_candidate`,
   or `get_recruiting_metrics` before asking broader pipeline questions.

Zero-config demo install:

1. Set **Storage backend** to `local_sample`.
2. Set **MCP tool surface** to `auto`.
3. Leave MongoDB/API-key fields blank.
4. Restart Claude Desktop and run `config_doctor(offline=true)`.
5. Try the bundled deal sample data. You can also create small local personal deals;
   once local personal data exists, active reads use that local dataset instead
   of the immutable bundled fixture.

Atlas-backed recruiting demo:

1. Set **Storage backend** to `mongo`.
2. Set **MCP tool surface** to `developer`.
3. Use a demo database different from the primary database.
4. Run `create_sample_data(dataset="recruiting_pipeline_demo")` first as a
   dry-run, then again with `dry_run=false` and `confirmed_by_user=true` when
   the preview looks right.

## Validation in this repository

The repository includes contract tests for the bundle manifest and launcher:

```bash
<python> -m pytest tests/test_mcpb_manifest.py
```

These tests verify that the manifest tool list matches the registered MCP tool
surface contract, installer fields map to runtime environment variables, and
the launcher delegates to the installed `deal_intel.mcp_server` module.

Real `mcpb validate`, `mcpb pack`, and `mcpb info` checks still require the
external `mcpb` CLI.

## Version bump

1. Update `version` in `manifest.json`
2. Update `tools[]` if the MCP tool surface changed
3. Rebuild: `mcpb pack . recruit-ai-mcp-{new_version}.mcpb`

**Note:** bundle `version` is an independent track from `pyproject.toml` version. Only bump when the install-surface (manifest fields / form) changes.
