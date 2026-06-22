from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from deal_intel.user_memory import detect_secret_patterns

SubjectType = Literal["candidate", "client_company", "position", "submission"]
InteractionType = Literal[
    "candidate_screen",
    "client_intake",
    "interview",
    "email_thread",
    "call_summary",
    "internal_note",
]
InteractionDirection = Literal["inbound", "outbound", "mixed", "internal"]
SourceConfidence = Literal[
    "candidate_stated",
    "client_stated",
    "mixed",
    "internal",
    "outbound_unconfirmed",
    "unknown",
]
SubmissionStatus = Literal[
    "draft",
    "submitted",
    "client_review",
    "interviewing",
    "offer",
    "placed",
    "rejected",
    "withdrawn",
    "paused",
]
PositionStatus = Literal["draft", "open", "paused", "filled", "closed", "cancelled"]
RecommendationMode = Literal["position_to_candidates", "candidate_to_positions"]
AnchorType = Literal["position", "candidate"]
FeedbackSentiment = Literal["positive", "mixed", "negative", "neutral"]
DecisionSignal = Literal[
    "advance",
    "reject",
    "hold",
    "needs_more_info",
    "preference_update",
]

FIT_DIMENSION_KEYS = (
    "skill_fit",
    "domain_fit",
    "seniority_fit",
    "compensation_fit",
    "location_fit",
    "availability_fit",
    "client_preference_fit",
    "risk",
)
_FIT_DIMENSION_SET = frozenset(FIT_DIMENSION_KEYS)
_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{1,79}$")
_DIMENSION_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


class RecruitingModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceReference(RecruitingModel):
    evidence_id: str
    source_type: Literal["interaction", "document", "profile", "feedback", "manual_note"]
    source_id: str
    quote: str = ""
    summary: str = ""
    confidence: SourceConfidence = "unknown"

    @field_validator("evidence_id", "source_id")
    @classmethod
    def _valid_id(cls, value: str) -> str:
        return _clean_id(value)

    @field_validator("quote", "summary")
    @classmethod
    def _safe_optional_text(cls, value: str) -> str:
        return _clean_optional_text(value, max_length=1200)


class FitRubricDimension(RecruitingModel):
    key: str
    label: str
    description: str
    weight: float = 1.0
    gap_threshold: int = 2
    higher_is_better: bool = True
    suggested_questions: list[str] = Field(default_factory=list)

    @field_validator("key")
    @classmethod
    def _valid_dimension_key(cls, value: str) -> str:
        normalized = _clean_required_text(value, max_length=64)
        if not _DIMENSION_RE.fullmatch(normalized):
            raise ValueError("dimension key must be snake_case")
        return normalized

    @field_validator("label", "description")
    @classmethod
    def _safe_required_text(cls, value: str) -> str:
        return _clean_required_text(value, max_length=500)

    @field_validator("weight", mode="before")
    @classmethod
    def _positive_weight(cls, value: float) -> float:
        if isinstance(value, bool):
            raise ValueError("weight must be greater than 0")
        parsed = float(value)
        if parsed <= 0:
            raise ValueError("weight must be greater than 0")
        return parsed

    @field_validator("gap_threshold", mode="before")
    @classmethod
    def _valid_gap_threshold(cls, value: int) -> int:
        if isinstance(value, bool):
            raise ValueError("gap_threshold must be an integer from 0 to 5")
        parsed = int(value)
        if parsed < 0 or parsed > 5:
            raise ValueError("gap_threshold must be an integer from 0 to 5")
        return parsed

    @field_validator("suggested_questions")
    @classmethod
    def _safe_questions(cls, value: list[str]) -> list[str]:
        return _clean_text_list(value, max_items=10, max_length=300)


class RecruitingFitRubric(RecruitingModel):
    key: str = "recruiting_fit"
    display_name: str = "Recruiting Fit"
    score_min: int = 0
    score_max: int = 5
    dimensions: dict[str, FitRubricDimension]

    @field_validator("key")
    @classmethod
    def _safe_key(cls, value: str) -> str:
        return _clean_id(value)

    @field_validator("display_name")
    @classmethod
    def _safe_display_name(cls, value: str) -> str:
        return _clean_required_text(value, max_length=120)

    @model_validator(mode="after")
    def _valid_scale_and_dimensions(self) -> RecruitingFitRubric:
        if self.score_min != 0 or self.score_max != 5:
            raise ValueError("recruiting fit score scale must be fixed at 0-5")
        if set(self.dimensions) != _FIT_DIMENSION_SET:
            missing = sorted(_FIT_DIMENSION_SET - set(self.dimensions))
            extra = sorted(set(self.dimensions) - _FIT_DIMENSION_SET)
            raise ValueError(
                "rubric dimensions must match default recruiting fit keys; "
                f"missing={missing}, extra={extra}"
            )
        for key, dimension in self.dimensions.items():
            if dimension.key != key:
                raise ValueError(f"dimension key mismatch for {key}")
        return self


class FitSignal(RecruitingModel):
    score: int = Field(ge=0, le=5)
    rationale: str = ""
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)

    @field_validator("rationale")
    @classmethod
    def _safe_rationale(cls, value: str) -> str:
        return _clean_optional_text(value, max_length=1200)

    @field_validator("missing_info")
    @classmethod
    def _safe_missing_info(cls, value: list[str]) -> list[str]:
        return _clean_text_list(value, max_items=12, max_length=300)


class FitSnapshot(RecruitingModel):
    rubric_key: str = "recruiting_fit"
    dimensions: dict[str, FitSignal]
    overall_score: float = Field(ge=0, le=100)
    summary: str = ""
    risk_summary: str = ""
    missing_info: list[str] = Field(default_factory=list)

    @field_validator("rubric_key")
    @classmethod
    def _safe_rubric_key(cls, value: str) -> str:
        return _clean_id(value)

    @field_validator("summary", "risk_summary")
    @classmethod
    def _safe_optional_text(cls, value: str) -> str:
        return _clean_optional_text(value, max_length=1600)

    @field_validator("missing_info")
    @classmethod
    def _safe_missing_info(cls, value: list[str]) -> list[str]:
        return _clean_text_list(value, max_items=20, max_length=300)

    @model_validator(mode="after")
    def _known_dimensions(self) -> FitSnapshot:
        unknown = sorted(set(self.dimensions) - _FIT_DIMENSION_SET)
        if unknown:
            raise ValueError("unknown fit dimensions: " + ", ".join(unknown))
        return self


class CompensationExpectation(RecruitingModel):
    currency: str = "USD"
    minimum: int | None = Field(default=None, ge=0)
    target: int | None = Field(default=None, ge=0)
    maximum: int | None = Field(default=None, ge=0)
    period: Literal["annual", "monthly", "hourly", "contract_total"] = "annual"
    note: str = ""

    @field_validator("currency")
    @classmethod
    def _currency_code(cls, value: str) -> str:
        normalized = _clean_required_text(value, max_length=3).upper()
        if not re.fullmatch(r"[A-Z]{3}", normalized):
            raise ValueError("currency must be a three-letter ISO-style code")
        return normalized

    @field_validator("note")
    @classmethod
    def _safe_note(cls, value: str) -> str:
        return _clean_optional_text(value, max_length=500)


class CandidatePreferences(RecruitingModel):
    desired_titles: list[str] = Field(default_factory=list)
    preferred_domains: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    remote_preference: str = ""
    excluded_companies: list[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator(
        "desired_titles",
        "preferred_domains",
        "preferred_locations",
        "excluded_companies",
    )
    @classmethod
    def _safe_lists(cls, value: list[str]) -> list[str]:
        return _clean_text_list(value, max_items=50, max_length=120)

    @field_validator("remote_preference", "notes")
    @classmethod
    def _safe_text(cls, value: str) -> str:
        return _clean_optional_text(value, max_length=800)


class CandidateProfile(RecruitingModel):
    candidate_id: str
    name: str
    headline: str = ""
    current_company: str = ""
    current_title: str = ""
    skills: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    seniority: str = ""
    compensation_expectation: CompensationExpectation | None = None
    locations: list[str] = Field(default_factory=list)
    work_authorization: str = ""
    availability: str = ""
    preferences: CandidatePreferences = Field(default_factory=CandidatePreferences)
    risk_flags: list[str] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    @field_validator("candidate_id")
    @classmethod
    def _candidate_id(cls, value: str) -> str:
        return _clean_id(value)

    @field_validator(
        "name",
        "headline",
        "current_company",
        "current_title",
        "seniority",
        "work_authorization",
        "availability",
        "created_at",
        "updated_at",
    )
    @classmethod
    def _safe_text(cls, value: str) -> str:
        return _clean_optional_text(value, max_length=300)

    @field_validator("skills", "domains", "locations", "risk_flags")
    @classmethod
    def _safe_lists(cls, value: list[str]) -> list[str]:
        return _clean_text_list(value, max_items=100, max_length=120)

    @model_validator(mode="after")
    def _name_required(self) -> CandidateProfile:
        if not self.name:
            raise ValueError("candidate name is required")
        return self


class ClientCompany(RecruitingModel):
    client_company_id: str
    name: str
    industry: str = ""
    stage: str = ""
    locations: list[str] = Field(default_factory=list)
    hiring_preferences: list[str] = Field(default_factory=list)
    feedback_patterns: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    @field_validator("client_company_id")
    @classmethod
    def _company_id(cls, value: str) -> str:
        return _clean_id(value)

    @field_validator("name", "industry", "stage", "created_at", "updated_at")
    @classmethod
    def _safe_text(cls, value: str) -> str:
        return _clean_optional_text(value, max_length=300)

    @field_validator("locations", "hiring_preferences", "feedback_patterns", "risk_notes")
    @classmethod
    def _safe_lists(cls, value: list[str]) -> list[str]:
        return _clean_text_list(value, max_items=100, max_length=300)

    @model_validator(mode="after")
    def _name_required(self) -> ClientCompany:
        if not self.name:
            raise ValueError("client company name is required")
        return self


class Position(RecruitingModel):
    position_id: str
    client_company_id: str
    title: str
    status: PositionStatus = "draft"
    seniority: str = ""
    must_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    target_compensation: CompensationExpectation | None = None
    locations: list[str] = Field(default_factory=list)
    remote_policy: str = ""
    ideal_candidate_examples: list[str] = Field(default_factory=list)
    rubric: RecruitingFitRubric = Field(
        default_factory=lambda: DEFAULT_RECRUITING_FIT_RUBRIC.model_copy(deep=True)
    )
    created_at: str = ""
    updated_at: str = ""

    @field_validator("position_id", "client_company_id")
    @classmethod
    def _ids(cls, value: str) -> str:
        return _clean_id(value)

    @field_validator("title", "seniority", "remote_policy", "created_at", "updated_at")
    @classmethod
    def _safe_text(cls, value: str) -> str:
        return _clean_optional_text(value, max_length=300)

    @field_validator("must_have", "nice_to_have", "locations")
    @classmethod
    def _safe_lists(cls, value: list[str]) -> list[str]:
        return _clean_text_list(value, max_items=100, max_length=160)

    @field_validator("ideal_candidate_examples")
    @classmethod
    def _safe_example_ids(cls, value: list[str]) -> list[str]:
        return [_clean_id(item) for item in value[:20]]

    @model_validator(mode="after")
    def _title_required(self) -> Position:
        if not self.title:
            raise ValueError("position title is required")
        return self


class RecruitingInteraction(RecruitingModel):
    interaction_id: str
    subject_type: SubjectType
    subject_id: str
    interaction_type: InteractionType
    direction: InteractionDirection = "mixed"
    source_confidence: SourceConfidence = "unknown"
    participants: list[str] = Field(default_factory=list)
    occurred_at: str = ""
    summary: str = ""
    raw_content: str = ""
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)

    @field_validator("interaction_id", "subject_id")
    @classmethod
    def _ids(cls, value: str) -> str:
        return _clean_id(value)

    @field_validator("participants")
    @classmethod
    def _safe_participants(cls, value: list[str]) -> list[str]:
        return _clean_text_list(value, max_items=30, max_length=120)

    @field_validator("occurred_at", "summary")
    @classmethod
    def _safe_text(cls, value: str) -> str:
        return _clean_optional_text(value, max_length=2000)

    @field_validator("raw_content")
    @classmethod
    def _raw_content(cls, value: str) -> str:
        return str(value or "")


class ClientFeedback(RecruitingModel):
    feedback_id: str
    subject_type: SubjectType
    subject_id: str
    position_id: str | None = None
    candidate_id: str | None = None
    sentiment: FeedbackSentiment = "neutral"
    decision_signal: DecisionSignal = "needs_more_info"
    rubric_deltas: dict[str, int] = Field(default_factory=dict)
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)
    preference_learning: list[str] = Field(default_factory=list)
    summary: str = ""
    created_at: str = ""

    @field_validator("feedback_id", "subject_id")
    @classmethod
    def _ids(cls, value: str) -> str:
        return _clean_id(value)

    @field_validator("position_id", "candidate_id")
    @classmethod
    def _optional_ids(cls, value: str | None) -> str | None:
        return _clean_id(value) if value else None

    @field_validator("rubric_deltas")
    @classmethod
    def _valid_rubric_deltas(cls, value: dict[str, int]) -> dict[str, int]:
        output: dict[str, int] = {}
        for key, delta in value.items():
            if key not in _FIT_DIMENSION_SET:
                raise ValueError("unknown fit dimension: " + str(key))
            parsed = int(delta)
            if parsed < -5 or parsed > 5:
                raise ValueError("rubric delta must be between -5 and 5")
            output[key] = parsed
        return output

    @field_validator("preference_learning")
    @classmethod
    def _safe_preferences(cls, value: list[str]) -> list[str]:
        return _clean_text_list(value, max_items=30, max_length=300)

    @field_validator("summary", "created_at")
    @classmethod
    def _safe_text(cls, value: str) -> str:
        return _clean_optional_text(value, max_length=1200)


class Submission(RecruitingModel):
    submission_id: str
    candidate_id: str
    position_id: str
    status: SubmissionStatus = "draft"
    submitted_at: str = ""
    fit_snapshot: FitSnapshot | None = None
    client_feedback_ids: list[str] = Field(default_factory=list)
    next_step: str = ""

    @field_validator("submission_id", "candidate_id", "position_id")
    @classmethod
    def _ids(cls, value: str) -> str:
        return _clean_id(value)

    @field_validator("client_feedback_ids")
    @classmethod
    def _feedback_ids(cls, value: list[str]) -> list[str]:
        return [_clean_id(item) for item in value[:100]]

    @field_validator("submitted_at", "next_step")
    @classmethod
    def _safe_text(cls, value: str) -> str:
        return _clean_optional_text(value, max_length=500)


class RecommendationResult(RecruitingModel):
    target_id: str
    rank: int = Field(ge=1)
    fit_snapshot: FitSnapshot
    recommendation_reason: str = ""
    risk_flags: list[str] = Field(default_factory=list)
    rejected_reason: str = ""
    next_questions: list[str] = Field(default_factory=list)

    @field_validator("target_id")
    @classmethod
    def _target_id(cls, value: str) -> str:
        return _clean_id(value)

    @field_validator("recommendation_reason", "rejected_reason")
    @classmethod
    def _safe_text(cls, value: str) -> str:
        return _clean_optional_text(value, max_length=1200)

    @field_validator("risk_flags", "next_questions")
    @classmethod
    def _safe_lists(cls, value: list[str]) -> list[str]:
        return _clean_text_list(value, max_items=30, max_length=300)


class RecommendationRun(RecruitingModel):
    recommendation_run_id: str
    mode: RecommendationMode
    anchor_type: AnchorType
    anchor_id: str
    query: dict = Field(default_factory=dict)
    rubric: RecruitingFitRubric = Field(
        default_factory=lambda: DEFAULT_RECRUITING_FIT_RUBRIC.model_copy(deep=True)
    )
    results: list[RecommendationResult] = Field(default_factory=list)
    created_at: str = ""

    @field_validator("recommendation_run_id", "anchor_id")
    @classmethod
    def _ids(cls, value: str) -> str:
        return _clean_id(value)

    @field_validator("created_at")
    @classmethod
    def _safe_created_at(cls, value: str) -> str:
        return _clean_optional_text(value, max_length=120)

    @model_validator(mode="after")
    def _mode_matches_anchor(self) -> RecommendationRun:
        expected = "position" if self.mode == "position_to_candidates" else "candidate"
        if self.anchor_type != expected:
            raise ValueError(f"anchor_type must be {expected!r} for mode {self.mode!r}")
        return self


def default_recruiting_fit_rubric() -> RecruitingFitRubric:
    return RecruitingFitRubric.model_validate(_DEFAULT_RUBRIC_PAYLOAD)


def _clean_id(value: str) -> str:
    normalized = _clean_required_text(value, max_length=80)
    if not _ID_RE.fullmatch(normalized):
        raise ValueError("id must be lowercase slug text")
    return normalized


def _clean_required_text(value: str, *, max_length: int) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("field is required")
    _reject_secret_like(normalized)
    return normalized[:max_length]


def _clean_optional_text(value: str, *, max_length: int) -> str:
    normalized = str(value or "").strip()
    if normalized:
        _reject_secret_like(normalized)
    return normalized[:max_length]


def _clean_text_list(
    values: list[str],
    *,
    max_items: int,
    max_length: int,
) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values[:max_items]:
        item = _clean_optional_text(value, max_length=max_length)
        if not item or item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    return cleaned


def _reject_secret_like(value: str) -> None:
    if detect_secret_patterns(value):
        raise ValueError("field appears to contain a secret")


_DEFAULT_RUBRIC_PAYLOAD = {
    "key": "recruiting_fit",
    "display_name": "Recruiting Fit",
    "dimensions": {
        "skill_fit": {
            "key": "skill_fit",
            "label": "Skill fit",
            "description": "Observed match between required skills and candidate capability.",
            "weight": 1.5,
            "gap_threshold": 3,
            "suggested_questions": [
                "Which required skills are proven by recent work evidence?",
            ],
        },
        "domain_fit": {
            "key": "domain_fit",
            "label": "Domain fit",
            "description": "Similarity of industry, product, customer, or operating context.",
            "weight": 1.0,
            "gap_threshold": 2,
            "suggested_questions": [
                "Has the candidate worked in a comparable domain or customer context?",
            ],
        },
        "seniority_fit": {
            "key": "seniority_fit",
            "label": "Seniority fit",
            "description": "Alignment of scope, ownership, leadership, and role level.",
            "weight": 1.25,
            "gap_threshold": 3,
            "suggested_questions": [
                "What scope has the candidate owned without close supervision?",
            ],
        },
        "compensation_fit": {
            "key": "compensation_fit",
            "label": "Compensation fit",
            "description": "Alignment between role budget and candidate expectations.",
            "weight": 1.0,
            "gap_threshold": 3,
            "suggested_questions": [
                "Are expectations, flexibility, and competing offers known?",
            ],
        },
        "location_fit": {
            "key": "location_fit",
            "label": "Location fit",
            "description": "Location, remote policy, timezone, and authorization alignment.",
            "weight": 1.0,
            "gap_threshold": 3,
            "suggested_questions": [
                "Can the candidate work where and how the client requires?",
            ],
        },
        "availability_fit": {
            "key": "availability_fit",
            "label": "Availability fit",
            "description": "Start-date and process-timing alignment.",
            "weight": 0.75,
            "gap_threshold": 2,
            "suggested_questions": [
                "When can the candidate interview and start?",
            ],
        },
        "client_preference_fit": {
            "key": "client_preference_fit",
            "label": "Client preference fit",
            "description": "Alignment with explicit and learned client preferences.",
            "weight": 1.25,
            "gap_threshold": 3,
            "suggested_questions": [
                "Which client preferences are explicit versus inferred from feedback?",
            ],
        },
        "risk": {
            "key": "risk",
            "label": "Risk",
            "description": "Delivery, retention, credibility, process, or mismatch risk.",
            "weight": 1.0,
            "gap_threshold": 2,
            "higher_is_better": False,
            "suggested_questions": [
                "What could cause this match to fail after submission?",
            ],
        },
    },
}

DEFAULT_RECRUITING_FIT_RUBRIC = default_recruiting_fit_rubric()
