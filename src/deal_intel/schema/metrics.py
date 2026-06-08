from __future__ import annotations

import math
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


def _as_finite_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("health band thresholds must be finite numbers")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("health band thresholds must be finite numbers")
    return number


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
