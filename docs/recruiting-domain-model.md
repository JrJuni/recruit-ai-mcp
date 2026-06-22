# Recruiting Domain Model

This document defines the Work 1 recruiting data model for `recruit-ai-mcp`.
It is a planning and schema contract only. Storage cutover, MCP tool renaming,
and recommendation execution belong to later work.

## Research Inputs

The model is based on a small scan of experienced hiring and recruiting sources:

- Laszlo Bock / Google hiring practice: structured interviews, consistent
  rubrics, work-sample evidence, and written rationale reduce first-impression
  bias and make evaluations more comparable.
- WIRED reporting on Interviewing.io, CoderPad, and current technical hiring:
  overly burdensome assessments can create bias and candidate drop-off; better
  assessments resemble real work and preserve candidate experience.
- LinkedIn Talent Search papers: recruiting search is not one-way relevance.
  It requires both recruiter/job relevance and candidate interest. Complex
  searches mix structured fields such as title, skill, company, and region with
  free text. Recruiters often express needs more easily through examples of
  ideal candidates than through perfect queries.

Sources:

- <https://www.wired.com/2015/04/hire-like-google/>
- <https://www.wired.com/story/tech-job-interviews-out-of-control/>
- <https://www.wired.com/story/why-tech-job-interviews-became-such-a-nightmare/>
- <https://arxiv.org/abs/1809.06481>
- <https://arxiv.org/abs/1602.08186>

## Product Principle

Recruit AI should behave like an evidence-aware recruiting workbench, not a
black-box ATS. It should preserve what was observed, who said it, when it was
known, how confident the recruiter is, and how that evidence affected a
candidate-position match.

Core rules:

- Keep raw evidence separate from derived fit signals.
- Store recommendation rationale and missing information, not only scores.
- Treat client feedback as reusable preference memory for future matches.
- Support both `position -> candidates` and `candidate -> positions`.
- Keep human decision authority explicit; recommendations are ranked evidence,
  not automatic decisions.
- Prefer role-specific rubrics over generic keyword matching.
- Make ideal-candidate examples first-class inputs because recruiters and
  hiring managers often express search needs through examples.

## Entity Overview

### candidate

Canonical profile for one person.

Primary fields:

- `candidate_id`
- `name`
- `headline`
- `current_company`
- `current_title`
- `skills`
- `domains`
- `seniority`
- `compensation_expectation`
- `locations`
- `work_authorization`
- `availability`
- `preferences`
- `risk_flags`
- `evidence`

Design notes:

- Skills and domains are normalized lists, but the original source text stays
  in evidence records.
- Compensation, location, availability, and preferences are not minor metadata;
  they are core match constraints.
- Candidate profile facts should carry source provenance when possible.

### client_company

Hiring customer or target account.

Primary fields:

- `client_company_id`
- `name`
- `industry`
- `stage`
- `locations`
- `hiring_preferences`
- `feedback_patterns`
- `risk_notes`

Design notes:

- Client preference is learned over time from explicit intake notes and
  repeated feedback.
- Preference memory must distinguish explicit client statements from recruiter
  inference.

### position

Open role or search mandate.

Primary fields:

- `position_id`
- `client_company_id`
- `title`
- `status`
- `seniority`
- `must_have`
- `nice_to_have`
- `target_compensation`
- `locations`
- `remote_policy`
- `ideal_candidate_examples`
- `rubric`

Design notes:

- A position is not just a JD. It is the current search hypothesis: role need,
  constraints, client preferences, ideal examples, and scoring weights.
- `ideal_candidate_examples` enable query-by-example search.

### interaction

Evidence from a candidate, client, hiring manager, or recruiter note.

Primary fields:

- `interaction_id`
- `subject_type`
- `subject_id`
- `interaction_type`
- `direction`
- `source_confidence`
- `participants`
- `occurred_at`
- `summary`
- `raw_content`
- `evidence_refs`

Design notes:

- Interactions are the canonical evidence store for recruiting, mirroring the
  deal-side move from legacy `meetings` to `interactions`.
- Internal notes may inform workflow but should be marked separately from
  candidate-stated or client-stated evidence.

### submission

Lifecycle record for presenting one candidate to one position.

Primary fields:

- `submission_id`
- `candidate_id`
- `position_id`
- `status`
- `submitted_at`
- `fit_snapshot`
- `client_feedback_ids`
- `next_step`

Design notes:

- Store the fit snapshot as it was at submission time. Later candidate updates
  should not rewrite historical submission judgment.
- Reasons for rejection, pause, or advancement become training signals for
  later recommendation runs.

### feedback

Structured client, hiring-manager, candidate, or recruiter feedback.

Primary fields:

- `feedback_id`
- `subject_type`
- `subject_id`
- `position_id`
- `candidate_id`
- `sentiment`
- `decision_signal`
- `rubric_deltas`
- `evidence_refs`
- `preference_learning`

Design notes:

- Feedback should be decomposed into reusable preference updates when safe:
  for example, "prefers enterprise SaaS implementation experience" should
  become a client preference signal, while one-off comments remain attached to
  the submission.

### recommendation_run

Audit log for one recommendation request.

Primary fields:

- `recommendation_run_id`
- `mode`
- `anchor_type`
- `anchor_id`
- `query`
- `rubric`
- `results`
- `created_at`

Design notes:

- `mode` is either `position_to_candidates` or `candidate_to_positions`.
- Store the query interpretation, selected rubric, result rankings, rejected
  reasons, and missing-information questions.
- Recommendation output must be explainable and replayable enough for debugging
  even when future scoring changes.

## Fit Rubric

The default recruiting fit rubric uses a fixed 0-5 scale:

| Key | Meaning |
|---|---|
| `skill_fit` | Match between required skills and observed candidate capability |
| `domain_fit` | Similarity of industry, product, customer, or operating context |
| `seniority_fit` | Scope, ownership, leadership, and level alignment |
| `compensation_fit` | Alignment between candidate expectations and role budget |
| `location_fit` | Location, remote policy, timezone, and work authorization fit |
| `availability_fit` | Start-date and process-timing fit |
| `client_preference_fit` | Alignment with explicit or learned client preferences |
| `risk` | Delivery, retention, credibility, process, or mismatch risk |

Each dimension has:

- `score`: 0-5
- `weight`: position-specific weighting
- `evidence_refs`: source-backed rationale
- `missing_info`: questions needed to improve confidence

The `risk` dimension is directionally different. A high risk score means higher
risk, while high scores on the other dimensions mean stronger fit. Aggregate
recommendation logic should account for this in later scoring work.

## Work 3A Fit Scoring Contract

Work 3A adds deterministic recruiting fit scoring. It does not use LLMs,
embeddings, storage, or MCP tool registration.

Scoring policy:

- Inputs are a recruiting fit rubric and dimension signals.
- Every rubric dimension participates in the denominator.
- Missing dimensions contribute zero and produce `missing_dimension` warnings.
- Normal dimensions contribute `score / 5 * 100`.
- `risk` and any dimension with `higher_is_better=false` contribute
  `(5 - score) / 5 * 100`.
- Dimension weights are applied after normalization.
- `overall_score` is the weighted average rounded to two decimals.
- Dimensions without evidence references produce `missing_evidence` warnings.
- Dimensions with `missing_info` produce `missing_info` warnings.
- Dimensions whose normalized score is at or below their gap threshold produce
  `low_dimension_score` warnings.
- The output is a validated `FitSnapshot`, per-dimension normalized scores,
  and warnings.

## Work 3B Candidate-Position Fit Builder

Work 3B adds a deterministic candidate-position fit builder on top of the Work
3A scoring engine. It still does not use LLMs, embeddings, storage, or MCP tool
registration.

Builder policy:

- Inputs are a `CandidateProfile`, a `Position`, and optional client feedback
  records. Plain dictionaries from storage reads are accepted and validated
  through the same Pydantic models.
- The builder emits all eight default fit dimensions:
  `skill_fit`, `domain_fit`, `seniority_fit`, `compensation_fit`,
  `location_fit`, `availability_fit`, `client_preference_fit`, and `risk`.
- Skill fit is based on must-have and nice-to-have coverage against captured
  candidate skills.
- Domain fit compares candidate domain history with role context and learned
  preference text.
- Seniority, compensation, location, and availability use deterministic
  field-to-field comparisons and expose missing-information questions when the
  comparison is under-specified.
- Client preference fit uses ideal-candidate examples first, then applicable
  feedback and learned preference text.
- Risk remains directionally inverted by the Work 3A rubric. Candidate risk
  flags and negative feedback increase raw risk.
- The output is a validated `FitSnapshot`, per-dimension normalized scores,
  raw dimension signals, and structured warnings.

## Collections For Work 2

Recommended Mongo collections:

- `candidates`
- `client_companies`
- `positions`
- `submissions`
- `feedback`
- `interactions`
- `recommendation_runs`

Deferred compatibility:

- Existing `deals` collections stay untouched until the MCP tool surface is
  explicitly cut over.
- Work 2 should add recruiting storage paths beside existing deal storage
  rather than rewriting deal documents in place.

## Work 2A Storage Contract

Work 2A introduces the recruiting collections as Mongo-managed storage
contracts. It does not expose new MCP tools and does not change recommendation
scoring yet.

Managed collections and primary IDs:

| Collection | Primary ID | Main lookup indexes |
|---|---|---|
| `candidates` | `candidate_id` | `candidate_id_unique`, `candidate_updated` |
| `client_companies` | `client_company_id` | `client_company_id_unique`, `client_company_name` |
| `positions` | `position_id` | `position_id_unique`, `position_client_status_updated` |
| `submissions` | `submission_id` | `submission_id_unique`, `submission_candidate_position`, `submission_position_status_updated` |
| `feedback` | `feedback_id` | `feedback_id_unique`, `feedback_position_candidate_created` |
| `interactions` | `interaction_id` | `interaction_id_unique`, `interaction_subject_occurred` |
| `recommendation_runs` | `recommendation_run_id` | `recommendation_run_id_unique`, `recommendation_run_anchor_created` |

Storage read policy:

- Default recruiting reads exclude Mongo `_id`.
- Default `interactions` reads also exclude `raw_content`.
- Raw interaction content is available only through explicit internal
  `include_raw=True` storage calls. No public MCP surface exposes it in Work 2A.
- Collection validators are permissive `warn` / `moderate` contracts so early
  real data can be inspected without blocking writes.
- Atlas Vector Search remains out of scope for M0; regular indexes only are
  managed in this step.

## Work 2B Storage Normalization

Work 2B adds the storage payload normalization layer used before Mongo writes.
It keeps the storage boundary ready for future MCP tools without exposing those
tools yet.

Write policy:

- `MongoDBClient` recruiting upsert wrappers accept either plain mappings or
  Pydantic recruiting models.
- Pydantic models are serialized with JSON-safe nested values before storage.
- Mongo `_id` is stripped before replacement writes.
- `created_at` is filled when missing or blank and preserved when already set.
- `updated_at` is refreshed on every recruiting replacement write.
- The collection primary ID remains required before any write.

Read wrapper policy:

- Typed storage wrappers exist for common future tool paths:
  candidates, client companies, positions, submissions, feedback,
  interactions, and recommendation runs.
- List wrappers build the common filters for client/status, candidate/position,
  subject, and recommendation anchor lookups.
- Interaction list/get wrappers keep `raw_content` hidden unless
  `include_raw=True` is passed internally.

## Work 2C Internal Create Services

Work 2C adds internal service functions for the first future recruiting write
tools. It still does not register public MCP tools.

Service entry points:

- `create_candidate`
- `create_client_company`
- `create_position`

Service policy:

- Inputs are validated through the Work 1 Pydantic models before storage.
- Missing IDs are generated deterministically from the human-facing name or
  title using entity prefixes: `cand_`, `client_`, and `pos_`.
- Explicit IDs are accepted only if the Pydantic model accepts them.
- Validation errors are converted to secret-safe `INVALID_INPUT` errors without
  echoing raw user input.
- Storage errors are converted to retryable `STORAGE_ERROR` errors.
- Responses return `ok`, entity type, entity ID, stored safe record, and
  warnings.
- The service calls the typed storage wrappers from Work 2B, so timestamps and
  raw-content projection policy remain centralized.

## Work 2D Internal Lifecycle Services

Work 2D extends the same internal service module to recruiting lifecycle
records. It still does not register public MCP tools.

Service entry points:

- `add_recruiting_interaction`
- `create_submission`
- `add_client_feedback`

Lifecycle policy:

- Interactions are validated through `RecruitingInteraction` and stored through
  the typed storage wrapper.
- Interaction `raw_content` may be stored, but service responses use the safe
  read wrapper and do not return raw content by default.
- Submissions are validated through `Submission` and may store a fit snapshot
  from the recommendation/scoring layer.
- Feedback is validated through `ClientFeedback`.
- Feedback against `subject_type="submission"` attempts to append the feedback
  ID to `submission.client_feedback_ids`.
- Missing submissions do not block feedback capture; the service returns a
  warning and leaves the feedback stored.
- Validation and storage errors use the same secret-safe MCP-style error
  envelope policy as Work 2C.

## Out Of Scope For Work 1

- No storage migration.
- No MCP tool registration changes.
- No LLM extraction prompt changes.
- No production recommendation ranking.
- No Atlas Vector Search requirement. M0 remains on Python cosine.
