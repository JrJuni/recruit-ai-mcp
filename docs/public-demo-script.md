# Public Demo Script

Use this when showing Deal Intelligence MCP to a new user or posting a short
demo in a community such as r/mcp.

The goal is not to demonstrate every tool. The goal is to show that a small
team can ask normal sales questions and get useful answers from structured deal
memory.

## Setup Assumption

Run the demo after `config_doctor` is green.

For a real workspace, use `full`/MongoDB-backed mode. For a zero-config trial,
sample mode is acceptable, but say clearly that the companies and numbers are
fictional.

## Five-Question Demo

Ask these in order:

```text
How healthy is the current pipeline?
```

Expected tool path: `get_metrics`.

What this should show:

- open pipeline value;
- active deal count;
- average health;
- attention deal count;
- health band distribution.

```text
Which deal needs attention first?
```

Expected tool path: `list_deals`, `get_deal_gaps`, or `get_deal_review`.

What this should show:

- deterministic risk signals such as overdue, stuck, stalled, or at-risk health;
- no raw notes or contacts;
- practical next questions rather than overconfident win probability.

```text
Tell me the status of PayBridge.
```

Expected tool path: `get_deal_review`.

What this should show:

- stage, value, close date, health, evidence coverage, risks, and next questions;
- no server-side LLM call required for ordinary status review.

If the sample dataset is active and PayBridge is unavailable in the current
fixture, ask for one company from `list_deals` instead.

```text
Make this week's pipeline report.
```

Expected tool path: `export_report`.

What this should show:

- generated Markdown and compatibility CSV paths;
- `briefing` / `briefing_sections`;
- `host_report_prompt` that the host app can use to polish the deterministic
  data pack into a more natural manager/team report.

Use `export_data` instead only when the user asks for Excel/CSV-ready deal
records, all-deal ledgers, or won/lost tables.

```text
What decision criteria do customers mention most often?
```

Expected tool path: `get_customer_themes`.

What this should show:

- ranked recurring decision criteria or customer concerns;
- unique-deal counts rather than raw mention spam;
- representative evidence.

Follow-up options:

- "Break that down by stage" -> `get_customer_theme_breakdown`.
- "Show evidence for the top theme" -> `get_customer_theme_evidence`.

## Demo Boundaries

Do not start with admin or maintenance tools.

- Do not use `backfill-customer-themes` in a live demo unless you are explaining
  migration. It may call the configured server-side LLM for historical records.
- Do not use `analyze_deal` for routine deal status. Use `get_deal_review`
  first. `analyze_deal` is for optional generated strategy prose and may persist
  `bd_strategy`.
- Do not use `export_report` when the user wants spreadsheet data. Use
  `export_data`.

## One-Minute Positioning

Deal Intelligence MCP is for solo founders, small AI teams, and lightweight BD
teams that need structured sales memory without adopting a heavyweight CRM
first.

It turns meetings, customer emails, interviews, and call summaries into deal
health, customer themes, follow-up gaps, and weekly review artifacts. MongoDB is
the recommended full backend; local sample mode exists so an AI host can try the
flow quickly before a real setup.

## Short Community Post Draft

Use or adapt this for a short public post:

```text
I built Deal Intelligence MCP, a lightweight sales-memory MCP server for solo
founders and small AI/BD teams.

The idea is simple: paste meeting notes, customer email replies, interviews, or
call summaries, and the MCP turns them into structured deal health, MEDDPICC
signals, customer themes, follow-up gaps, and weekly pipeline reports.

It is not trying to replace a full CRM. It is for teams that already work inside
Claude/Codex/ChatGPT and want to ask questions like:

- How healthy is the current pipeline?
- Which deal needs attention first?
- What is the status of this specific account?
- What decision criteria do customers mention most often?
- Make this week's pipeline report.

The default backend is MongoDB Atlas full mode, and the free/M0 tier is enough
for the current MVP. There is also a zero-config sample mode with fictional data
so an AI host can try the workflow before any real setup.
```
