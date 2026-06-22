# Public Demo Script

Use this when showing Recruit AI MCP to a new user or posting a short demo in a
community such as r/mcp.

The goal is not to demonstrate every tool. The goal is to show that a recruiter
or search-firm team can ask normal recruiting questions and get useful answers
from structured candidate, client, position, submission, feedback, and
interaction memory.

## Setup Assumption

Run the demo after `config_doctor` is green.

For a real workspace, use `full`/MongoDB-backed mode. For a zero-config trial,
sample mode is acceptable, but say clearly that the candidates, companies,
positions, submissions, and feedback are fictional.

If the demo workspace has no recruiting data yet, seed fictional data with
`create_sample_data` using the `recruiting_pipeline_demo` dataset.

## Five-Question Demo

Ask these in order:

```text
Which candidates best match this open position?
```

Expected tool path: `recommend_candidates_for_position`.

What this should show:

- ranked candidates for one position;
- deterministic fit scores across skills, domain, seniority, compensation,
  location, availability, client preference, and risk;
- plain reasons, risk flags, and next questions;
- no Atlas Vector Search requirement on M0.

```text
Which open positions best fit this candidate?
```

Expected tool path: `recommend_positions_for_candidate`.

What this should show:

- candidate-to-position matching from the other direction;
- why each role is or is not a fit;
- compensation, location, availability, and seniority constraints that prevent
  naive keyword matching from over-ranking a role.

```text
How healthy is the recruiting pipeline?
```

Expected tool path: `get_recruiting_metrics`.

What this should show:

- candidate, company, position, submission, feedback, and interaction counts;
- open position status mix;
- submission funnel rates;
- feedback sentiment and data-quality counters.

```text
Generate a recruiting pipeline report.
```

Expected tool path: `export_recruiting_report`.

What this should show:

- generated Markdown and CSV artifact paths;
- deterministic KPI sections and rows;
- no raw recruiting interaction content, contacts, embeddings, or secrets.

```text
What client feedback changed the recommendation?
```

Expected tool path: `add_client_feedback` first if new feedback needs to be
captured, then `recommend_candidates_for_position`.

What this should show:

- structured feedback linked to a candidate, position, submission, or client;
- rubric deltas applied transparently to the recommendation run;
- inspectable reasons instead of hidden model scoring.

## Demo Boundaries

Do not start with admin or maintenance tools.

- Do not use Atlas Vector Search on Free/M0. The current Recruit AI path uses
  M0-safe lexical retrieval and deterministic scoring.
- Do not paste real resumes, client notes, MongoDB URIs, API keys, OAuth tokens,
  or passwords into chat.
- Do not use inherited deal-intelligence tools as the primary demo path. They
  remain compatibility tools during the staged cutover.
- Do not use destructive tools in a public demo unless you are explaining
  dry-run and confirmation gates.

## One-Minute Positioning

Recruit AI MCP is for recruiters and search-firm operators who want a
self-owned recruiting intelligence layer before adopting or customizing a
larger ATS/CRM stack.

It turns candidate profiles, client companies, open roles, submissions,
feedback, interviews, emails, and call summaries into fit scoring,
recommendations, recruiting pipeline metrics, and report artifacts. MongoDB is
the recommended full backend; local sample mode exists so an AI host can try
the flow quickly before a real setup.

The project is MIT-licensed, so forks and workflow-specific customization are
welcome as long as license and attribution notices are preserved.

## Short Community Post Draft

Use or adapt this for a short public post:

```text
I built Recruit AI MCP, a lightweight recruiting-memory MCP server for
recruiters and search-firm teams.

The idea is simple: capture candidate profiles, client companies, open roles,
submissions, feedback, interviews, emails, and call summaries, and the MCP turns
them into structured fit scoring, recommendations, recruiting metrics, and
pipeline reports.

It is not a mature ATS replacement, but it can act as a first self-owned
recruiting intelligence layer if your current system is notes, spreadsheets,
email threads, and memory. It is for teams that already work inside
Claude/Codex/ChatGPT and want to ask questions like:

- Which candidates best match this open position?
- Which open positions best fit this candidate?
- How healthy is the recruiting pipeline?
- What client feedback changed the recommendation?
- Generate a recruiting pipeline report.

The default backend is MongoDB Atlas full mode, and the free/M0 tier is enough
for the current MVP because matching stays on deterministic local retrieval and
scoring. There is also a zero-config sample mode with fictional recruiting data
so an AI host can try the workflow before any real setup.

It is MIT-licensed, so you can fork and adapt it to your own workflow. Please
keep license and attribution notices if you redistribute a modified version.
```
