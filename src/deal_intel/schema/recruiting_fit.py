from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from deal_intel.schema.recruiting import (
    DEFAULT_RECRUITING_FIT_RUBRIC,
    FIT_DIMENSION_KEYS,
    FitSignal,
    FitSnapshot,
    RecruitingFitRubric,
)


@dataclass(frozen=True)
class RecruitingFitScoreResult:
    snapshot: FitSnapshot
    dimension_scores: dict[str, float]
    warnings: list[dict[str, Any]]


def build_fit_snapshot(
    *,
    dimensions: dict[str, FitSignal | dict[str, Any]],
    rubric: RecruitingFitRubric | None = None,
    summary: str = "",
    risk_summary: str = "",
    missing_info: list[str] | None = None,
) -> RecruitingFitScoreResult:
    """Build a deterministic weighted fit snapshot from rubric dimension signals."""

    active_rubric = rubric or DEFAULT_RECRUITING_FIT_RUBRIC
    signals = _coerce_signals(dimensions)
    dimension_scores: dict[str, float] = {}
    warnings: list[dict[str, Any]] = []
    weighted_total = 0.0
    weight_total = 0.0

    for key in FIT_DIMENSION_KEYS:
        rubric_dimension = active_rubric.dimensions[key]
        weight = rubric_dimension.weight
        weight_total += weight
        signal = signals.get(key)
        if signal is None:
            warnings.append(_warning("missing_dimension", key, "Fit dimension is missing."))
            dimension_scores[key] = 0.0
            continue

        normalized_score = _normalized_dimension_score(
            signal.score,
            higher_is_better=rubric_dimension.higher_is_better,
            score_max=active_rubric.score_max,
        )
        dimension_score = round((normalized_score / active_rubric.score_max) * 100, 2)
        dimension_scores[key] = dimension_score
        weighted_total += dimension_score * weight

        if not signal.evidence_refs:
            warnings.append(
                _warning(
                    "missing_evidence",
                    key,
                    "Fit dimension has no evidence references.",
                )
            )
        if signal.missing_info:
            warnings.append(
                _warning(
                    "missing_info",
                    key,
                    "Fit dimension still has open information gaps.",
                    missing_info=list(signal.missing_info),
                )
            )
        if normalized_score <= rubric_dimension.gap_threshold:
            warnings.append(
                _warning(
                    "low_dimension_score",
                    key,
                    "Fit dimension is at or below its gap threshold.",
                    score=signal.score,
                    normalized_score=normalized_score,
                    gap_threshold=rubric_dimension.gap_threshold,
                )
            )

    overall_score = round(weighted_total / weight_total, 2) if weight_total else 0.0
    snapshot = FitSnapshot(
        rubric_key=active_rubric.key,
        dimensions=signals,
        overall_score=overall_score,
        summary=summary,
        risk_summary=risk_summary,
        missing_info=missing_info or [],
    )
    return RecruitingFitScoreResult(
        snapshot=snapshot,
        dimension_scores=dimension_scores,
        warnings=warnings,
    )


def calculate_overall_score(
    *,
    dimensions: dict[str, FitSignal | dict[str, Any]],
    rubric: RecruitingFitRubric | None = None,
) -> float:
    return build_fit_snapshot(dimensions=dimensions, rubric=rubric).snapshot.overall_score


def _coerce_signals(dimensions: dict[str, FitSignal | dict[str, Any]]) -> dict[str, FitSignal]:
    return {
        key: value if isinstance(value, FitSignal) else FitSignal.model_validate(value)
        for key, value in dimensions.items()
    }


def _normalized_dimension_score(
    score: int,
    *,
    higher_is_better: bool,
    score_max: int,
) -> int:
    return score if higher_is_better else score_max - score


def _warning(
    code: str,
    dimension: str,
    message: str,
    **details: Any,
) -> dict[str, Any]:
    payload = {
        "code": code,
        "dimension": dimension,
        "message": message,
    }
    payload.update(details)
    return payload
