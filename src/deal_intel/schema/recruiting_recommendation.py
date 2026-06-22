from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict
from typing import Any

from deal_intel.schema.recruiting import (
    CandidateProfile,
    ClientFeedback,
    Position,
    RecommendationResult,
    RecommendationRun,
)
from deal_intel.schema.recruiting_match import (
    CandidatePositionFitResult,
    build_candidate_position_fit,
)


def build_position_candidate_recommendation_run(
    *,
    position: Position | dict[str, Any],
    candidates: Iterable[CandidateProfile | dict[str, Any]],
    client_feedback: Iterable[ClientFeedback | dict[str, Any]] | None = None,
    recommendation_run_id: str | None = None,
    query: dict[str, Any] | None = None,
    limit: int | None = None,
    created_at: str = "",
) -> RecommendationRun:
    """Rank candidates for one position using deterministic fit snapshots."""

    position_model = _coerce_position(position)
    candidate_models = [_coerce_candidate(candidate) for candidate in candidates]
    feedback_models = _coerce_feedback(client_feedback or ())
    ranked = _rank_candidate_position_pairs(
        [
            (
                candidate.candidate_id,
                candidate.risk_flags,
                build_candidate_position_fit(
                    candidate=candidate,
                    position=position_model,
                    client_feedback=feedback_models,
                ),
            )
            for candidate in candidate_models
        ],
        limit=limit,
    )
    return RecommendationRun(
        recommendation_run_id=recommendation_run_id
        or _default_run_id("rec_candidates_for", position_model.position_id),
        mode="position_to_candidates",
        anchor_type="position",
        anchor_id=position_model.position_id,
        query=query or {},
        rubric=position_model.rubric,
        results=[
            _recommendation_result(
                target_id=target_id,
                rank=index + 1,
                fit=fit,
                risk_flags=risk_flags,
            )
            for index, (target_id, risk_flags, fit) in enumerate(ranked)
        ],
        created_at=created_at,
    )


def build_candidate_position_recommendation_run(
    *,
    candidate: CandidateProfile | dict[str, Any],
    positions: Iterable[Position | dict[str, Any]],
    client_feedback: Iterable[ClientFeedback | dict[str, Any]] | None = None,
    recommendation_run_id: str | None = None,
    query: dict[str, Any] | None = None,
    limit: int | None = None,
    created_at: str = "",
) -> RecommendationRun:
    """Rank positions for one candidate using deterministic fit snapshots."""

    candidate_model = _coerce_candidate(candidate)
    position_models = [_coerce_position(position) for position in positions]
    feedback_models = _coerce_feedback(client_feedback or ())
    ranked = _rank_candidate_position_pairs(
        [
            (
                position.position_id,
                candidate_model.risk_flags,
                build_candidate_position_fit(
                    candidate=candidate_model,
                    position=position,
                    client_feedback=feedback_models,
                ),
            )
            for position in position_models
        ],
        limit=limit,
    )
    rubric = position_models[0].rubric if position_models else None
    return RecommendationRun(
        recommendation_run_id=recommendation_run_id
        or _default_run_id("rec_positions_for", candidate_model.candidate_id),
        mode="candidate_to_positions",
        anchor_type="candidate",
        anchor_id=candidate_model.candidate_id,
        query=query or {},
        **({"rubric": rubric} if rubric is not None else {}),
        results=[
            _recommendation_result(
                target_id=target_id,
                rank=index + 1,
                fit=fit,
                risk_flags=risk_flags,
            )
            for index, (target_id, risk_flags, fit) in enumerate(ranked)
        ],
        created_at=created_at,
    )


def _rank_candidate_position_pairs(
    pairs: list[tuple[str, list[str], CandidatePositionFitResult]],
    *,
    limit: int | None,
) -> list[tuple[str, list[str], CandidatePositionFitResult]]:
    ranked = sorted(
        pairs,
        key=lambda item: (-item[2].snapshot.overall_score, item[0]),
    )
    if limit is not None:
        return ranked[: max(0, limit)]
    return ranked


def _recommendation_result(
    *,
    target_id: str,
    rank: int,
    fit: CandidatePositionFitResult,
    risk_flags: list[str],
) -> RecommendationResult:
    return RecommendationResult(
        target_id=target_id,
        rank=rank,
        fit_snapshot=fit.snapshot,
        recommendation_reason=_recommendation_reason(fit),
        risk_flags=_risk_flags(risk_flags, fit),
        rejected_reason=_rejected_reason(fit),
        next_questions=_next_questions(fit),
        feedback_adjustments=[asdict(item) for item in fit.feedback_adjustments],
    )


def _recommendation_reason(fit: CandidatePositionFitResult) -> str:
    strongest = _dimension_names_at_or_above(fit, 80.0)
    if strongest:
        return "Strongest evidence-backed dimensions: " + ", ".join(strongest[:3]) + "."
    if fit.snapshot.overall_score >= 50:
        return "Moderate evidence-backed fit with open information gaps."
    return "Weak current fit based on captured evidence."


def _risk_flags(
    candidate_risk_flags: list[str],
    fit: CandidatePositionFitResult,
) -> list[str]:
    flags = list(candidate_risk_flags[:20])
    risk_score = fit.signals["risk"].score
    if risk_score >= 4 and "high_match_risk" not in flags:
        flags.append("high_match_risk")
    elif risk_score >= 2 and "review_match_risk" not in flags:
        flags.append("review_match_risk")
    return flags[:30]


def _rejected_reason(fit: CandidatePositionFitResult) -> str:
    if fit.snapshot.overall_score >= 40:
        return ""
    low_dimensions = _dimension_names_below(fit, 40.0)
    if low_dimensions:
        return "Below threshold due to weak " + ", ".join(low_dimensions[:3]) + "."
    return "Below threshold based on current captured evidence."


def _next_questions(fit: CandidatePositionFitResult) -> list[str]:
    questions = list(fit.snapshot.missing_info[:20])
    seen = set(questions)
    for warning in fit.warnings:
        if warning.get("code") != "low_dimension_score":
            continue
        question = f"Improve evidence for {warning['dimension']}."
        if question not in seen:
            seen.add(question)
            questions.append(question)
    return questions[:30]


def _dimension_names_at_or_above(
    fit: CandidatePositionFitResult,
    threshold: float,
) -> list[str]:
    return [
        dimension
        for dimension, score in fit.dimension_scores.items()
        if score >= threshold
    ]


def _dimension_names_below(
    fit: CandidatePositionFitResult,
    threshold: float,
) -> list[str]:
    return [
        dimension
        for dimension, score in fit.dimension_scores.items()
        if score < threshold
    ]


def _coerce_candidate(value: CandidateProfile | dict[str, Any]) -> CandidateProfile:
    if isinstance(value, CandidateProfile):
        return value
    return CandidateProfile.model_validate(_strip_mongo_id(value))


def _coerce_position(value: Position | dict[str, Any]) -> Position:
    if isinstance(value, Position):
        return value
    return Position.model_validate(_strip_mongo_id(value))


def _coerce_feedback(values: Iterable[ClientFeedback | dict[str, Any]]) -> list[ClientFeedback]:
    output: list[ClientFeedback] = []
    for value in values:
        output.append(
            value
            if isinstance(value, ClientFeedback)
            else ClientFeedback.model_validate(_strip_mongo_id(value))
        )
    return output


def _strip_mongo_id(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "_id"}


def _default_run_id(prefix: str, anchor_id: str) -> str:
    return f"{prefix}_{anchor_id}"[:80]
