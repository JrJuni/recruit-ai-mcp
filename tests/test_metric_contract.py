from __future__ import annotations

import math

import pytest

from deal_intel.schema.metrics import (
    ACTIVE_STAGES,
    OPEN_STAGES,
    STALLED_STAGES,
    TERMINAL_STAGES,
    HealthBand,
    HealthBandThresholds,
    classify_health,
    is_active_stage,
    is_health_assessed,
    is_open_stage,
)


def test_pipeline_stage_populations_are_disjoint_and_complete() -> None:
    assert ACTIVE_STAGES == {
        "discovery",
        "qualification",
        "proposal",
        "negotiation",
    }
    assert STALLED_STAGES == {"stalled"}
    assert OPEN_STAGES == ACTIVE_STAGES | STALLED_STAGES
    assert TERMINAL_STAGES == {"won", "lost"}
    assert OPEN_STAGES.isdisjoint(TERMINAL_STAGES)

    assert is_active_stage("proposal") is True
    assert is_active_stage("stalled") is False
    assert is_open_stage("stalled") is True
    assert is_open_stage("won") is False


def test_health_band_uses_default_boundaries_inclusively() -> None:
    thresholds = HealthBandThresholds.from_config({})

    assert classify_health({"filled_count": 1, "health_pct": 70}, thresholds) == "healthy"
    assert classify_health({"filled_count": 1, "health_pct": 69.9}, thresholds) == "watch"
    assert classify_health({"filled_count": 1, "health_pct": 40}, thresholds) == "watch"
    assert classify_health({"filled_count": 1, "health_pct": 39.9}, thresholds) == "at_risk"


def test_health_band_thresholds_are_configurable() -> None:
    thresholds = HealthBandThresholds.from_config(
        {
            "metrics": {
                "health_bands": {
                    "healthy_min": 80,
                    "watch_min": 55,
                }
            }
        }
    )

    assert thresholds == HealthBandThresholds(healthy_min=80, watch_min=55)
    assert classify_health({"filled_count": 2, "health_pct": 75}, thresholds) == HealthBand.WATCH
    assert (
        classify_health({"filled_count": 2, "health_pct": 54.9}, thresholds)
        == HealthBand.AT_RISK
    )


@pytest.mark.parametrize(
    "snapshot",
    [
        None,
        {},
        {"filled_count": 0, "health_pct": 0},
        {"filled_count": None, "health_pct": 80},
        {"filled_count": 1, "health_pct": None},
        {"filled_count": 1, "health_pct": math.nan},
    ],
)
def test_unassessed_health_is_separate_from_at_risk(snapshot: dict | None) -> None:
    thresholds = HealthBandThresholds.from_config({})

    assert is_health_assessed(snapshot) is False
    assert classify_health(snapshot, thresholds) == HealthBand.UNASSESSED


@pytest.mark.parametrize(
    ("healthy_min", "watch_min"),
    [
        (70, 70),
        (60, 70),
        (101, 40),
        (70, -1),
        ("70", 40),
        (70, True),
        (math.inf, 40),
        (70, math.nan),
    ],
)
def test_invalid_health_band_config_fails_explicitly(
    healthy_min: object,
    watch_min: object,
) -> None:
    with pytest.raises(ValueError, match="health band|health_bands"):
        HealthBandThresholds.from_config(
            {
                "metrics": {
                    "health_bands": {
                        "healthy_min": healthy_min,
                        "watch_min": watch_min,
                    }
                }
            }
        )
