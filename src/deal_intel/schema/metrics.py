from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

ACTIVE_STAGES = frozenset({"discovery", "qualification", "proposal", "negotiation"})
STALLED_STAGES = frozenset({"stalled"})
OPEN_STAGES = ACTIVE_STAGES | STALLED_STAGES
TERMINAL_STAGES = frozenset({"won", "lost"})


class HealthBand(StrEnum):
    HEALTHY = "healthy"
    WATCH = "watch"
    AT_RISK = "at_risk"
    UNASSESSED = "unassessed"


class DealValueStatus(StrEnum):
    UNKNOWN = "unknown"
    ROUGH_ESTIMATE = "rough_estimate"
    CUSTOMER_BUDGET = "customer_budget"
    QUOTED = "quoted"
    STRATEGIC_ZERO = "strategic_zero"


KNOWN_VALUE_STATUSES = frozenset(
    {
        DealValueStatus.ROUGH_ESTIMATE,
        DealValueStatus.CUSTOMER_BUDGET,
        DealValueStatus.QUOTED,
    }
)
VALIDATED_VALUE_STATUSES = frozenset(
    {
        DealValueStatus.CUSTOMER_BUDGET,
        DealValueStatus.QUOTED,
    }
)


@dataclass(frozen=True)
class HealthBandThresholds:
    healthy_min: float = 70.0
    watch_min: float = 40.0

    @classmethod
    def from_config(cls, cfg: dict) -> HealthBandThresholds:
        raw = cfg.get("metrics", {}).get("health_bands", {})
        thresholds = cls(
            healthy_min=_as_finite_number(raw.get("healthy_min", cls.healthy_min)),
            watch_min=_as_finite_number(raw.get("watch_min", cls.watch_min)),
        )
        thresholds.validate()
        return thresholds

    def validate(self) -> None:
        if not 0 <= self.watch_min < self.healthy_min <= 100:
            raise ValueError(
                "metrics.health_bands must satisfy "
                "0 <= watch_min < healthy_min <= 100"
            )


@dataclass(frozen=True)
class DealValueAssessment:
    status: DealValueStatus | None
    amount_krw: int | None
    low_krw: int | None
    high_krw: int | None
    is_valid: bool
    is_known: bool
    is_classified: bool
    is_validated: bool
    is_strategic_zero: bool
    issue: str | None = None


def _as_finite_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("health band thresholds must be finite numbers")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("health band thresholds must be finite numbers")
    return number


def _is_krw_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def assess_deal_value(deal: dict) -> DealValueAssessment:
    """Validate a deal's amount classification without mutating the document."""
    raw_status = deal.get("deal_size_status")
    amount = deal.get("deal_size_krw")
    low = deal.get("deal_size_low_krw")
    high = deal.get("deal_size_high_krw")

    status = None
    if raw_status not in (None, ""):
        try:
            status = DealValueStatus(str(raw_status))
        except ValueError:
            return _invalid_value_assessment(amount, low, high, "invalid_status")

    for value in (amount, low, high):
        if value is not None and not _is_krw_integer(value):
            return _invalid_value_assessment(amount, low, high, "invalid_amount_type")

    if status == DealValueStatus.UNKNOWN:
        if any(value is not None for value in (amount, low, high)):
            return _invalid_value_assessment(
                amount,
                low,
                high,
                "unknown_status_must_not_have_amount",
                status=status,
            )
        return DealValueAssessment(
            status=status,
            amount_krw=None,
            low_krw=None,
            high_krw=None,
            is_valid=True,
            is_known=False,
            is_classified=True,
            is_validated=False,
            is_strategic_zero=False,
        )

    if status == DealValueStatus.STRATEGIC_ZERO:
        if amount != 0 or low not in (None, 0) or high not in (None, 0):
            return _invalid_value_assessment(
                amount,
                low,
                high,
                "strategic_zero_requires_zero_amount",
                status=status,
            )
        return DealValueAssessment(
            status=status,
            amount_krw=0,
            low_krw=0,
            high_krw=0,
            is_valid=True,
            is_known=True,
            is_classified=True,
            is_validated=False,
            is_strategic_zero=True,
        )

    if amount is None:
        if status in KNOWN_VALUE_STATUSES or low is not None or high is not None:
            return _invalid_value_assessment(
                amount,
                low,
                high,
                "known_status_requires_positive_amount",
                status=status,
            )
        return DealValueAssessment(
            status=None,
            amount_krw=None,
            low_krw=None,
            high_krw=None,
            is_valid=True,
            is_known=False,
            is_classified=False,
            is_validated=False,
            is_strategic_zero=False,
        )

    if amount <= 0:
        return _invalid_value_assessment(
            amount,
            low,
            high,
            "non_positive_amount_requires_strategic_zero",
            status=status,
        )

    effective_low = amount if low is None else low
    effective_high = amount if high is None else high
    if effective_low <= 0 or effective_high <= 0:
        return _invalid_value_assessment(
            amount,
            low,
            high,
            "estimated_range_must_be_positive",
            status=status,
        )
    if not effective_low <= amount <= effective_high:
        return _invalid_value_assessment(
            amount,
            low,
            high,
            "estimated_range_must_include_amount",
            status=status,
        )

    return DealValueAssessment(
        status=status,
        amount_krw=amount,
        low_krw=effective_low,
        high_krw=effective_high,
        is_valid=True,
        is_known=True,
        is_classified=status is not None,
        is_validated=status in VALIDATED_VALUE_STATUSES,
        is_strategic_zero=False,
    )


def _invalid_value_assessment(
    amount: Any,
    low: Any,
    high: Any,
    issue: str,
    *,
    status: DealValueStatus | None = None,
) -> DealValueAssessment:
    return DealValueAssessment(
        status=status,
        amount_krw=amount if _is_krw_integer(amount) else None,
        low_krw=low if _is_krw_integer(low) else None,
        high_krw=high if _is_krw_integer(high) else None,
        is_valid=False,
        is_known=False,
        is_classified=status is not None,
        is_validated=False,
        is_strategic_zero=False,
        issue=issue,
    )


def summarize_pipeline_value(
    deals: Iterable[dict],
    *,
    stages: frozenset[str] | set[str] | None = None,
) -> dict:
    """Summarize known deal values for the requested stage population."""
    population = [
        deal for deal in deals if stages is None or deal.get("deal_stage") in stages
    ]
    assessments = [assess_deal_value(deal) for deal in population]
    known = [item for item in assessments if item.is_valid and item.is_known]

    deal_count = len(population)
    known_count = len(known)
    coverage_pct = round(known_count / deal_count * 100, 1) if deal_count else None
    status_counts = {status.value: 0 for status in DealValueStatus}
    for item in assessments:
        if item.status is not None and item.is_valid:
            status_counts[item.status.value] += 1

    return {
        "deal_count": deal_count,
        "pipeline_value_krw": sum(item.amount_krw or 0 for item in known),
        "pipeline_value_low_krw": sum(item.low_krw or 0 for item in known),
        "pipeline_value_high_krw": sum(item.high_krw or 0 for item in known),
        "validated_pipeline_value_krw": sum(
            item.amount_krw or 0 for item in known if item.is_validated
        ),
        "known_amount_count": known_count,
        "missing_amount_count": sum(
            item.is_valid and not item.is_known for item in assessments
        ),
        "invalid_amount_count": sum(not item.is_valid for item in assessments),
        "unclassified_amount_count": sum(
            item.is_valid and item.is_known and not item.is_classified
            for item in assessments
        ),
        "strategic_zero_count": sum(item.is_strategic_zero for item in known),
        "amount_coverage_pct": coverage_pct,
        "status_counts": status_counts,
    }


def is_active_stage(stage: str | None) -> bool:
    return stage in ACTIVE_STAGES


def is_open_stage(stage: str | None) -> bool:
    return stage in OPEN_STAGES


def is_health_assessed(meddpicc_latest: dict | None) -> bool:
    snapshot = meddpicc_latest or {}
    filled_count = snapshot.get("filled_count")
    health_pct = snapshot.get("health_pct")
    return (
        isinstance(filled_count, int)
        and not isinstance(filled_count, bool)
        and filled_count >= 1
        and isinstance(health_pct, (int, float))
        and not isinstance(health_pct, bool)
        and math.isfinite(float(health_pct))
    )


def classify_health(
    meddpicc_latest: dict | None,
    thresholds: HealthBandThresholds,
) -> HealthBand:
    if not is_health_assessed(meddpicc_latest):
        return HealthBand.UNASSESSED

    health_pct = float((meddpicc_latest or {})["health_pct"])
    if health_pct >= thresholds.healthy_min:
        return HealthBand.HEALTHY
    if health_pct >= thresholds.watch_min:
        return HealthBand.WATCH
    return HealthBand.AT_RISK
