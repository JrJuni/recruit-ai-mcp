# BI Metric Contract

BI, CSV, and Atlas Charts must use the same definitions in this document.
Implementation helpers live in `deal_intel.schema.metrics`.

## Part A - Pipeline Scope and Health

### Pipeline populations

| Population | Included stages | Meaning |
|---|---|---|
| Active | `discovery`, `qualification`, `proposal`, `negotiation` | Deals with ongoing sales activity |
| Stalled | `stalled` | Open deals that need recovery or explicit closure |
| Open | Active + Stalled | Every deal not yet closed |
| Terminal | `won`, `lost` | Closed outcomes |

Stalled value must not be presented as active pipeline value. A report may show
Open value, but it must also expose Active and Stalled values separately.

### Health assessment

- `filled_count >= 1` with a finite numeric `health_pct` means Assessed.
- Assessed deals use the existing MEDDPICC formula. Missing dimensions already
  contribute zero through that formula.
- Deals without a valid assessment are `unassessed`, not `at_risk`.
- Average health must use Assessed deals only.
- Every average health result must include health coverage and unassessed count.

### Health bands

The default bands are:

| Band | Default rule |
|---|---|
| `healthy` | `health_pct >= 70` |
| `watch` | `40 <= health_pct < 70` |
| `at_risk` | `health_pct < 40` |
| `unassessed` | No valid health assessment |

These are MEDDPICC qualification bands, not win probabilities.

The boundaries are operating configuration:

```yaml
metrics:
  health_bands:
    healthy_min: 70
    watch_min: 40
```

Override them in `~/.deal-intel/config.yaml`. Valid configuration must satisfy:

```text
0 <= watch_min < healthy_min <= 100
```

Invalid, non-numeric, or non-finite values fail explicitly instead of being
silently corrected.

## Part B - Pipeline Value

### Amount classifications

`deal_size_krw` is the current central estimate of contract value, not a
probability-weighted forecast. Its confidence and source are represented by
`deal_size_status`.

| Status | Meaning | Valid amount |
|---|---|---|
| `unknown` | The opportunity is real but it is too early to estimate value | No amount or range |
| `rough_estimate` | Seller estimate based on scope, seats, or comparable deals | Positive amount; optional positive range |
| `customer_budget` | The customer disclosed a budget or budget range | Positive amount; optional positive range |
| `quoted` | A quote or formal commercial proposal was sent | Positive amount; optional positive range |
| `strategic_zero` | Deliberate no-revenue work such as a reference project or free sample | Exactly zero |

The optional range fields are `deal_size_low_krw` and
`deal_size_high_krw`. When omitted, both default to `deal_size_krw` for metric
calculation. A range must contain the central estimate.

`None` and zero have different meanings:

- Missing amount with `unknown` means the value is not known yet.
- Zero is valid only with `strategic_zero`.
- A zero or negative amount without `strategic_zero` is invalid data.

Existing positive `deal_size_krw` values without a status remain included for
backward compatibility, but they increment `unclassified_amount_count`.

### Pipeline value outputs

For each requested stage population:

- `pipeline_value_krw`: sum of valid central amounts
- `pipeline_value_low_krw` / `pipeline_value_high_krw`: known value range
- `validated_pipeline_value_krw`: sum of `customer_budget` and `quoted`
  central amounts
- `amount_coverage_pct`: known values, including `strategic_zero`, divided by
  all deals in the population
- `missing_amount_count`: valid unknown or missing values
- `invalid_amount_count`: contradictory or malformed amount data
- `unclassified_amount_count`: legacy positive amounts without a status
- `strategic_zero_count`: intentional zero-revenue opportunities

Unknown and invalid amounts are excluded from value sums. They are never
silently imputed as zero. When the population is empty,
`amount_coverage_pct` is `null`, not 100%.

Active, Stalled, and Open pipeline values use the stage populations from Part
A. Won and lost amounts are excluded from current pipeline value and belong
to historical outcome metrics.

Weighted forecast is deliberately separate. It will require an explicit
probability contract and must not reuse MEDDPICC health bands as win
probabilities.

### Expected versus actual close date

- `expected_close_date` is the current sales estimate and may change while a
  deal is open.
- `actual_close_date` is the business-effective won/lost date and exists only
  for terminal deals.
- `stage_history.entered_at` is the system mutation timestamp used for audit
  and stage velocity. It is not a substitute for the business close date.
- Moving a terminal deal back to an open stage clears `actual_close_date`.

When win-rate period filtering is implemented, it must use
`actual_close_date`. Terminal records without it may temporarily fall back to
the terminal stage-history timestamp, but the result must include a data
quality warning.

### User approval before persistence

Meeting analysis may propose a value, range, status, and evidence, but it must
not mutate stored deal-value fields.

1. Surface the proposed status, central value, range, and evidence.
2. Ask the user whether that classification should be saved.
3. Persist it only after an affirmative response through an explicit
   deal-value update operation.

A value explicitly supplied by the user while creating or editing a deal
counts as approval. LLM inference, meeting-note extraction, bulk backfill, and
similar-deal estimation do not. The future update tool must enforce this
boundary and store the user's optional rationale in `deal_size_note`.

## Pending Decisions

Parts A and B intentionally do not define:

- Stuck versus overdue semantics
- Win-rate denominator and minimum sample warning
- Required fields and data-quality coverage
- Reporting timezone and reproducible `as_of` behavior

These decisions must be completed before the common metric aggregation module.
