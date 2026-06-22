from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from deal_intel.schema.recruiting import (
    FIT_DIMENSION_KEYS,
    CandidateProfile,
    ClientFeedback,
    EvidenceReference,
    FitSignal,
    FitSnapshot,
    Position,
)
from deal_intel.schema.recruiting_fit import build_fit_snapshot

_WORD_RE = re.compile(r"[a-z0-9]+")
_NEGATIVE_PREFERENCE_TERMS = (
    "reject",
    "rejects",
    "rejected",
    "avoid",
    "avoids",
    "without",
    "not enough",
    "heavy role",
    "role-shaping",
    "role shaping",
)
_LOW_SIGNAL_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "before",
        "candidate",
        "candidates",
        "for",
        "heavy",
        "need",
        "needs",
        "not",
        "or",
        "profiles",
        "reject",
        "rejects",
        "rejected",
        "the",
        "this",
        "to",
        "who",
        "with",
    }
)


@dataclass(frozen=True)
class CandidatePositionFitResult:
    snapshot: FitSnapshot
    dimension_scores: dict[str, float]
    warnings: list[dict[str, Any]]
    signals: dict[str, FitSignal]
    feedback_adjustments: list[FeedbackScoreAdjustment]


@dataclass(frozen=True)
class FeedbackScoreAdjustment:
    feedback_id: str
    dimension: str
    delta: int
    original_score: int
    adjusted_score: int
    reason: str


def build_candidate_position_fit(
    *,
    candidate: CandidateProfile | dict[str, Any],
    position: Position | dict[str, Any],
    client_feedback: Iterable[ClientFeedback | dict[str, Any]] | None = None,
) -> CandidatePositionFitResult:
    """Build a deterministic candidate-position fit snapshot.

    This is intentionally a field/rubric heuristic, not RAG or LLM reasoning.
    Recommendation tools can use it as the reproducible scoring layer before
    adding retrieval, ranking, and feedback-learning orchestration.
    """

    candidate_model = _coerce_candidate(candidate)
    position_model = _coerce_position(position)
    feedback_models = _coerce_feedback(client_feedback or ())
    evidence = list(candidate_model.evidence[:5])

    base_signals = {
        "skill_fit": _skill_signal(candidate_model, position_model, evidence),
        "domain_fit": _domain_signal(candidate_model, position_model, feedback_models, evidence),
        "seniority_fit": _seniority_signal(candidate_model, position_model, evidence),
        "compensation_fit": _compensation_signal(candidate_model, position_model, evidence),
        "location_fit": _location_signal(candidate_model, position_model, evidence),
        "availability_fit": _availability_signal(candidate_model, evidence),
        "client_preference_fit": _client_preference_signal(
            candidate_model,
            position_model,
            feedback_models,
            evidence,
        ),
        "risk": _risk_signal(candidate_model, position_model, feedback_models, evidence),
    }
    applicable_feedback = _applicable_feedback(candidate_model, position_model, feedback_models)
    signals, feedback_adjustments = _apply_feedback_adjustments(
        base_signals,
        applicable_feedback,
    )
    missing_info = _collect_missing_info(signals.values())
    result = build_fit_snapshot(
        dimensions=signals,
        rubric=position_model.rubric,
        summary=(
            f"Deterministic fit snapshot for {candidate_model.name} "
            f"against {position_model.title}."
        ),
        risk_summary=signals["risk"].rationale,
        missing_info=missing_info,
    )
    return CandidatePositionFitResult(
        snapshot=result.snapshot,
        dimension_scores=result.dimension_scores,
        warnings=result.warnings,
        signals=signals,
        feedback_adjustments=feedback_adjustments,
    )


def _skill_signal(
    candidate: CandidateProfile,
    position: Position,
    evidence: list[EvidenceReference],
) -> FitSignal:
    requirements = list(position.must_have)
    nice_to_have = list(position.nice_to_have)
    if not requirements and not nice_to_have:
        return FitSignal(
            score=0,
            rationale="Role skills are not defined.",
            evidence_refs=evidence,
            missing_info=["Define required and preferred role skills."],
        )
    if not candidate.skills:
        return FitSignal(
            score=0,
            rationale="Candidate skills are not captured.",
            evidence_refs=evidence,
            missing_info=["Capture candidate skills with source evidence."],
        )

    matched_must = _matched_items(requirements, candidate.skills)
    unmatched_must = [item for item in requirements if item not in matched_must]
    matched_nice = _matched_items(nice_to_have, candidate.skills)

    if requirements:
        coverage = len(matched_must) / len(requirements)
        if coverage >= 1:
            score = 5
        elif coverage >= 0.75:
            score = 4
        elif coverage >= 0.5:
            score = 3
        elif coverage > 0:
            score = 2
        else:
            score = 1
    else:
        coverage = len(matched_nice) / len(nice_to_have) if nice_to_have else 0
        score = 4 if coverage >= 0.75 else 3 if coverage > 0 else 2

    missing_info = [f"Confirm required skill: {item}" for item in unmatched_must]
    rationale = (
        f"Matched {len(matched_must)}/{len(requirements)} must-have skills"
        f" and {len(matched_nice)}/{len(nice_to_have)} nice-to-have skills."
    )
    return FitSignal(
        score=score,
        rationale=rationale,
        evidence_refs=evidence,
        missing_info=missing_info,
    )


def _domain_signal(
    candidate: CandidateProfile,
    position: Position,
    feedback: list[ClientFeedback],
    evidence: list[EvidenceReference],
) -> FitSignal:
    if not candidate.domains:
        return FitSignal(
            score=0,
            rationale="Candidate domain history is not captured.",
            evidence_refs=evidence,
            missing_info=["Capture candidate domain history."],
        )

    role_context = [
        position.title,
        *position.must_have,
        *position.nice_to_have,
        *[item for item in position.ideal_candidate_examples],
        *_feedback_preference_text(feedback),
    ]
    matches = _matched_items(candidate.domains, role_context)
    if matches:
        score = 5 if len(matches) >= 2 or _has_exact_match(candidate.domains, role_context) else 4
        missing_info: list[str] = []
        rationale = "Candidate domain signals overlap role or preference context."
    elif _has_meaningful_text(role_context):
        score = 2
        missing_info = ["Confirm whether candidate domain experience transfers to this role."]
        rationale = "Candidate domains are captured but do not clearly overlap role context."
    else:
        score = 3
        missing_info = ["Capture target role domain or client operating context."]
        rationale = "Candidate domains are known but the role domain is under-specified."

    return FitSignal(
        score=score,
        rationale=rationale,
        evidence_refs=evidence,
        missing_info=missing_info,
    )


def _seniority_signal(
    candidate: CandidateProfile,
    position: Position,
    evidence: list[EvidenceReference],
) -> FitSignal:
    if not candidate.seniority or not position.seniority:
        return FitSignal(
            score=0,
            rationale="Candidate or role seniority is missing.",
            evidence_refs=evidence,
            missing_info=["Confirm candidate seniority and role level."],
        )
    candidate_level = _seniority_level(candidate.seniority)
    position_level = _seniority_level(position.seniority)
    if _normalize_phrase(candidate.seniority) == _normalize_phrase(position.seniority):
        score = 5
    elif candidate_level is not None and position_level is not None:
        gap = abs(candidate_level - position_level)
        score = 5 if gap == 0 else 4 if gap == 1 else 2 if gap == 2 else 1
    elif _token_overlap(candidate.seniority, position.seniority):
        score = 4
    else:
        score = 2

    return FitSignal(
        score=score,
        rationale=(
            f"Candidate seniority '{candidate.seniority}' compared with "
            f"role seniority '{position.seniority}'."
        ),
        evidence_refs=evidence,
    )


def _compensation_signal(
    candidate: CandidateProfile,
    position: Position,
    evidence: list[EvidenceReference],
) -> FitSignal:
    candidate_comp = candidate.compensation_expectation
    role_comp = position.target_compensation
    if candidate_comp is None or role_comp is None:
        return FitSignal(
            score=0,
            rationale="Candidate expectation or role budget is missing.",
            evidence_refs=evidence,
            missing_info=["Confirm candidate compensation expectation and role budget."],
        )
    if candidate_comp.currency != role_comp.currency or candidate_comp.period != role_comp.period:
        return FitSignal(
            score=1,
            rationale="Compensation currency or period does not match.",
            evidence_refs=evidence,
            missing_info=["Normalize compensation currency and period before comparing."],
        )

    candidate_min = _first_amount(
        candidate_comp.minimum,
        candidate_comp.target,
        candidate_comp.maximum,
    )
    candidate_target = _first_amount(
        candidate_comp.target,
        candidate_comp.minimum,
        candidate_comp.maximum,
    )
    role_max = _first_amount(role_comp.maximum, role_comp.target, role_comp.minimum)
    if candidate_min is None or candidate_target is None or role_max is None:
        return FitSignal(
            score=0,
            rationale="Comparable compensation amounts are missing.",
            evidence_refs=evidence,
            missing_info=["Capture comparable compensation amounts."],
        )

    if candidate_target <= role_max:
        score = 5
    elif candidate_min <= role_max:
        score = 4
    else:
        gap_ratio = (candidate_min - role_max) / role_max if role_max else 1.0
        score = 3 if gap_ratio <= 0.10 else 2 if gap_ratio <= 0.25 else 1

    return FitSignal(
        score=score,
        rationale="Compared candidate expectation with the role compensation ceiling.",
        evidence_refs=evidence,
        missing_info=[] if score >= 4 else ["Confirm compensation flexibility."],
    )


def _location_signal(
    candidate: CandidateProfile,
    position: Position,
    evidence: list[EvidenceReference],
) -> FitSignal:
    candidate_locations = [
        *candidate.locations,
        *candidate.preferences.preferred_locations,
        candidate.preferences.remote_preference,
    ]
    role_locations = [*position.locations, position.remote_policy]
    if not _has_meaningful_text(role_locations):
        return FitSignal(
            score=3,
            rationale="Candidate location is known but role location policy is under-specified.",
            evidence_refs=evidence,
            missing_info=["Confirm role location and remote policy."],
        )
    if not _has_meaningful_text(candidate_locations):
        return FitSignal(
            score=0,
            rationale="Candidate location or remote preference is missing.",
            evidence_refs=evidence,
            missing_info=["Confirm candidate location and remote preference."],
        )

    role_remote = _mentions_remote(role_locations)
    candidate_remote = _mentions_remote(candidate_locations)
    if _matched_items(role_locations, candidate_locations):
        score = 5
        rationale = "Candidate location preferences overlap the role location policy."
    elif role_remote and candidate_remote:
        score = 5
        rationale = "Both role and candidate support remote work."
    elif role_remote:
        score = 4
        rationale = "Role supports remote work; candidate has location information."
    elif candidate_remote:
        score = 1
        rationale = "Candidate appears remote-oriented while the role is location-bound."
    else:
        score = 1
        rationale = "No clear location overlap was found."

    missing_info = [] if score >= 4 else ["Confirm location, timezone, or relocation flexibility."]
    return FitSignal(
        score=score,
        rationale=rationale,
        evidence_refs=evidence,
        missing_info=missing_info,
    )


def _availability_signal(
    candidate: CandidateProfile,
    evidence: list[EvidenceReference],
) -> FitSignal:
    if not candidate.availability:
        return FitSignal(
            score=0,
            rationale="Candidate availability is missing.",
            evidence_refs=evidence,
            missing_info=["Confirm interview and start-date availability."],
        )
    availability = candidate.availability.lower()
    if any(term in availability for term in ("immediate", "asap", "now")):
        score = 5
    else:
        days = _first_number(availability)
        if days is None:
            score = 3
        elif days <= 14:
            score = 5
        elif days <= 30:
            score = 4
        elif days <= 60:
            score = 3
        elif days <= 90:
            score = 2
        else:
            score = 1
    return FitSignal(
        score=score,
        rationale=f"Candidate availability is '{candidate.availability}'.",
        evidence_refs=evidence,
        missing_info=[] if score >= 4 else ["Confirm whether timing fits the search plan."],
    )


def _client_preference_signal(
    candidate: CandidateProfile,
    position: Position,
    feedback: list[ClientFeedback],
    evidence: list[EvidenceReference],
) -> FitSignal:
    applicable_feedback = _applicable_feedback(candidate, position, feedback)
    feedback_evidence = [
        ref
        for item in applicable_feedback
        for ref in item.evidence_refs[:3]
    ]
    if _candidate_excludes_position_client(candidate, position):
        return FitSignal(
            score=0,
            rationale="Candidate excluded this client company from target searches.",
            evidence_refs=[*evidence, *feedback_evidence],
            missing_info=["Confirm whether the candidate exclusion can be revisited."],
        )
    if candidate.candidate_id in position.ideal_candidate_examples:
        return FitSignal(
            score=5,
            rationale="Candidate is listed as an ideal-candidate example for this position.",
            evidence_refs=[*evidence, *feedback_evidence],
        )

    preference_text = _feedback_preference_text(feedback)
    candidate_text = [
        candidate.headline,
        candidate.current_title,
        *candidate.skills,
        *candidate.domains,
        *candidate.preferences.desired_titles,
        *candidate.preferences.preferred_domains,
        candidate.preferences.notes,
        *candidate.risk_flags,
    ]
    if _matches_negative_preference(
        _feedback_preference_learning_text(applicable_feedback),
        candidate_text,
    ):
        return FitSignal(
            score=1,
            rationale="Candidate profile overlaps learned negative client preference text.",
            evidence_refs=[*evidence, *feedback_evidence],
            missing_info=["Review client preference conflict before shortlisting."],
        )
    if applicable_feedback:
        preference_score = 3
        for item in applicable_feedback:
            if item.decision_signal in {"advance", "preference_update"}:
                preference_score += 1
            if item.sentiment == "positive":
                preference_score += 1
            if item.sentiment == "negative" or item.decision_signal == "reject":
                preference_score -= 2
        return FitSignal(
            score=_clamp_score(preference_score),
            rationale="Client feedback provides explicit preference signal for this match.",
            evidence_refs=[*evidence, *feedback_evidence],
        )
    if preference_text and _matched_items(preference_text, candidate_text):
        return FitSignal(
            score=4,
            rationale="Candidate profile overlaps learned client preference text.",
            evidence_refs=evidence,
        )
    return FitSignal(
        score=0,
        rationale="No explicit client preference signal is attached to this match.",
        evidence_refs=evidence,
        missing_info=["Capture client preferences or ideal-candidate examples."],
    )


def _risk_signal(
    candidate: CandidateProfile,
    position: Position,
    feedback: list[ClientFeedback],
    evidence: list[EvidenceReference],
) -> FitSignal:
    risk_score = 0
    if len(candidate.risk_flags) == 1:
        risk_score = 2
    elif len(candidate.risk_flags) == 2:
        risk_score = 4
    elif len(candidate.risk_flags) >= 3:
        risk_score = 5

    for item in _applicable_feedback(candidate, position, feedback):
        if item.sentiment == "negative" or item.decision_signal == "reject":
            risk_score += 2
        elif item.sentiment == "mixed" or item.decision_signal == "hold":
            risk_score += 1
    if _candidate_excludes_position_client(candidate, position):
        risk_score += 2

    risk_score = _clamp_score(risk_score)
    if risk_score == 0:
        rationale = "No candidate risk flags or negative feedback are recorded."
    else:
        rationale = "Risk reflects candidate risk flags and applicable feedback signals."
    return FitSignal(
        score=risk_score,
        rationale=rationale,
        evidence_refs=evidence,
        missing_info=[] if candidate.risk_flags else [],
    )


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


def _matched_items(required: Iterable[str], observed: Iterable[str]) -> list[str]:
    observed_phrases = [_normalize_phrase(item) for item in observed if _normalize_phrase(item)]
    observed_token_sets = [_tokens(item) for item in observed if _tokens(item)]
    matched: list[str] = []
    for item in required:
        phrase = _normalize_phrase(item)
        tokens = _tokens(item)
        if not phrase or not tokens:
            continue
        if phrase in observed_phrases:
            matched.append(item)
            continue
        if any(tokens.issubset(observed_tokens) for observed_tokens in observed_token_sets):
            matched.append(item)
            continue
        if any(
            _token_jaccard(tokens, observed_tokens) >= 0.5
            for observed_tokens in observed_token_sets
        ):
            matched.append(item)
    return matched


def _matches_negative_preference(
    preference_text: Iterable[str],
    candidate_text: Iterable[str],
) -> bool:
    candidate_token_sets = []
    for item in candidate_text:
        tokens = _content_tokens(item)
        if len(tokens) >= 2:
            candidate_token_sets.append(tokens)
    for item in preference_text:
        normalized = _normalize_phrase(item)
        if not normalized:
            continue
        if not any(term in normalized for term in _NEGATIVE_PREFERENCE_TERMS):
            continue
        preference_tokens = _content_tokens(item)
        if len(preference_tokens) < 2:
            continue
        for candidate_tokens in candidate_token_sets:
            overlap = preference_tokens & candidate_tokens
            if len(overlap) >= 2:
                return True
    return False


def _candidate_excludes_position_client(
    candidate: CandidateProfile,
    position: Position,
) -> bool:
    excluded = candidate.preferences.excluded_companies
    if not excluded or not position.client_company_id:
        return False
    return bool(_matched_items(excluded, [position.client_company_id]))


def _content_tokens(value: str) -> set[str]:
    return {
        token
        for token in _tokens(value)
        if token not in _LOW_SIGNAL_WORDS and len(token) > 2
    }


def _has_exact_match(left: Iterable[str], right: Iterable[str]) -> bool:
    right_phrases = {_normalize_phrase(item) for item in right if _normalize_phrase(item)}
    return any(_normalize_phrase(item) in right_phrases for item in left if _normalize_phrase(item))


def _applicable_feedback(
    candidate: CandidateProfile,
    position: Position,
    feedback: list[ClientFeedback],
) -> list[ClientFeedback]:
    output: list[ClientFeedback] = []
    for item in feedback:
        candidate_matches = item.candidate_id in {None, candidate.candidate_id}
        position_matches = item.position_id in {None, position.position_id}
        if candidate_matches and position_matches:
            output.append(item)
    return output


def _apply_feedback_adjustments(
    signals: dict[str, FitSignal],
    feedback: list[ClientFeedback],
) -> tuple[dict[str, FitSignal], list[FeedbackScoreAdjustment]]:
    adjusted = dict(signals)
    adjustments: list[FeedbackScoreAdjustment] = []
    for item in feedback:
        for dimension in FIT_DIMENSION_KEYS:
            delta = item.rubric_deltas.get(dimension, 0)
            if delta == 0:
                continue
            signal = adjusted[dimension]
            original_score = signal.score
            adjusted_score = _clamp_score(original_score + delta)
            reason = (
                f"Applied client feedback delta {delta:+d} from "
                f"{item.feedback_id} to {dimension}."
            )
            adjusted[dimension] = signal.model_copy(
                update={
                    "score": adjusted_score,
                    "rationale": _append_rationale(signal.rationale, reason),
                    "evidence_refs": [
                        *signal.evidence_refs,
                        *item.evidence_refs[:3],
                    ],
                }
            )
            adjustments.append(
                FeedbackScoreAdjustment(
                    feedback_id=item.feedback_id,
                    dimension=dimension,
                    delta=delta,
                    original_score=original_score,
                    adjusted_score=adjusted_score,
                    reason=reason,
                )
            )
    return adjusted, adjustments


def _append_rationale(current: str, addition: str) -> str:
    if not current:
        return addition
    return f"{current} {addition}"


def _feedback_preference_text(feedback: list[ClientFeedback]) -> list[str]:
    return [
        text
        for item in feedback
        for text in [*item.preference_learning, item.summary]
        if text
    ]


def _feedback_preference_learning_text(feedback: list[ClientFeedback]) -> list[str]:
    return [
        text
        for item in feedback
        for text in item.preference_learning
        if text
    ]


def _collect_missing_info(signals: Iterable[FitSignal]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for signal in signals:
        for item in signal.missing_info:
            if item not in seen:
                seen.add(item)
                output.append(item)
    return output[:20]


def _seniority_level(value: str) -> int | None:
    text = value.lower()
    if any(term in text for term in ("intern", "trainee")):
        return 0
    if any(term in text for term in ("junior", "associate", "entry")):
        return 1
    if any(term in text for term in ("mid", "intermediate")):
        return 2
    if "senior" in text:
        return 3
    if any(term in text for term in ("staff", "principal", "lead")):
        return 4
    if any(term in text for term in ("manager", "director", "head", "vp", "executive")):
        return 5
    return None


def _first_amount(*values: int | None) -> int | None:
    for value in values:
        if value is not None:
            return value
    return None


def _first_number(value: str) -> int | None:
    match = re.search(r"\d+", value)
    return int(match.group(0)) if match else None


def _mentions_remote(values: Iterable[str]) -> bool:
    return any("remote" in value.lower() or "anywhere" in value.lower() for value in values)


def _has_meaningful_text(values: Iterable[str]) -> bool:
    return any(str(value or "").strip() for value in values)


def _token_overlap(left: str, right: str) -> bool:
    return bool(_tokens(left) & _tokens(right))


def _token_jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _tokens(value: str) -> set[str]:
    return set(_WORD_RE.findall(value.lower()))


def _normalize_phrase(value: str) -> str:
    return " ".join(_WORD_RE.findall(value.lower()))


def _clamp_score(value: int) -> int:
    return max(0, min(5, int(value)))
