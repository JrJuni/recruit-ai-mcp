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

## Pending Decisions

Part A intentionally does not define:

- Pipeline value behavior when `deal_size_krw` is missing
- Stuck versus overdue semantics
- Win-rate denominator and minimum sample warning
- Required fields and data-quality coverage
- Reporting timezone and reproducible `as_of` behavior

These decisions must be completed before the common metric aggregation module.
