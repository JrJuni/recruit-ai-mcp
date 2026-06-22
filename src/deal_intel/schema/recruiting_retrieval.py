from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from deal_intel.schema.recruiting import CandidateProfile, Position

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "and",
    "for",
    "the",
    "with",
    "role",
    "lead",
    "engineer",
    "engineering",
    "manager",
}


@dataclass(frozen=True)
class RecruitingRetrievalResult:
    target_id: str
    score: float
    matched_terms: list[str]
    record: CandidateProfile | Position


def rank_candidates_for_position_retrieval(
    *,
    position: Position | dict[str, Any],
    candidates: Iterable[CandidateProfile | dict[str, Any]],
    limit: int | None = None,
) -> list[RecruitingRetrievalResult]:
    position_model = _coerce_position(position)
    query_terms = _position_query_terms(position_model)
    results = [
        _retrieval_result(
            target_id=candidate.candidate_id,
            record=candidate,
            query_terms=query_terms,
            target_terms=_candidate_terms(candidate),
        )
        for candidate in (_coerce_candidate(candidate) for candidate in candidates)
    ]
    return _rank_results(results, limit=limit)


def rank_positions_for_candidate_retrieval(
    *,
    candidate: CandidateProfile | dict[str, Any],
    positions: Iterable[Position | dict[str, Any]],
    limit: int | None = None,
) -> list[RecruitingRetrievalResult]:
    candidate_model = _coerce_candidate(candidate)
    query_terms = _candidate_terms(candidate_model)
    results = [
        _retrieval_result(
            target_id=position.position_id,
            record=position,
            query_terms=query_terms,
            target_terms=_position_query_terms(position),
        )
        for position in (_coerce_position(position) for position in positions)
    ]
    return _rank_results(results, limit=limit)


def _retrieval_result(
    *,
    target_id: str,
    record: CandidateProfile | Position,
    query_terms: set[str],
    target_terms: set[str],
) -> RecruitingRetrievalResult:
    matched = sorted(query_terms & target_terms)
    union = query_terms | target_terms
    score = round(len(matched) / len(union), 4) if union else 0.0
    return RecruitingRetrievalResult(
        target_id=target_id,
        score=score,
        matched_terms=matched,
        record=record,
    )


def _rank_results(
    results: list[RecruitingRetrievalResult],
    *,
    limit: int | None,
) -> list[RecruitingRetrievalResult]:
    ranked = sorted(results, key=lambda item: (-item.score, item.target_id))
    if limit is not None:
        return ranked[: max(0, limit)]
    return ranked


def _candidate_terms(candidate: CandidateProfile) -> set[str]:
    return _terms(
        [
            candidate.headline,
            candidate.current_title,
            candidate.seniority,
            candidate.availability,
            *candidate.skills,
            *candidate.domains,
            *candidate.locations,
            *candidate.preferences.desired_titles,
            *candidate.preferences.preferred_domains,
            *candidate.preferences.preferred_locations,
            candidate.preferences.remote_preference,
        ]
    )


def _position_query_terms(position: Position) -> set[str]:
    return _terms(
        [
            position.title,
            position.seniority,
            position.remote_policy,
            *position.must_have,
            *position.nice_to_have,
            *position.locations,
        ]
    )


def _terms(values: Iterable[str]) -> set[str]:
    output: set[str] = set()
    for value in values:
        for term in _WORD_RE.findall(str(value or "").lower()):
            if len(term) > 1 and term not in _STOP_WORDS:
                output.add(term)
    return output


def _coerce_candidate(value: CandidateProfile | dict[str, Any]) -> CandidateProfile:
    if isinstance(value, CandidateProfile):
        return value
    return CandidateProfile.model_validate(_strip_mongo_id(value))


def _coerce_position(value: Position | dict[str, Any]) -> Position:
    if isinstance(value, Position):
        return value
    return Position.model_validate(_strip_mongo_id(value))


def _strip_mongo_id(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "_id"}
