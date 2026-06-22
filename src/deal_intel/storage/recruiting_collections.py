from __future__ import annotations

from typing import Final

CANDIDATES: Final = "candidates"
CLIENT_COMPANIES: Final = "client_companies"
POSITIONS: Final = "positions"
SUBMISSIONS: Final = "submissions"
FEEDBACK: Final = "feedback"
INTERACTIONS: Final = "interactions"
RECOMMENDATION_RUNS: Final = "recommendation_runs"

RECRUITING_COLLECTIONS: Final[tuple[str, ...]] = (
    CANDIDATES,
    CLIENT_COMPANIES,
    POSITIONS,
    SUBMISSIONS,
    FEEDBACK,
    INTERACTIONS,
    RECOMMENDATION_RUNS,
)

RECRUITING_COLLECTION_ID_FIELDS: Final[dict[str, str]] = {
    CANDIDATES: "candidate_id",
    CLIENT_COMPANIES: "client_company_id",
    POSITIONS: "position_id",
    SUBMISSIONS: "submission_id",
    FEEDBACK: "feedback_id",
    INTERACTIONS: "interaction_id",
    RECOMMENDATION_RUNS: "recommendation_run_id",
}

_RECRUITING_SAFE_PROJECTIONS: Final[dict[str, dict[str, int]]] = {
    CANDIDATES: {"_id": 0},
    CLIENT_COMPANIES: {"_id": 0},
    POSITIONS: {"_id": 0},
    SUBMISSIONS: {"_id": 0},
    FEEDBACK: {"_id": 0},
    INTERACTIONS: {"_id": 0, "raw_content": 0},
    RECOMMENDATION_RUNS: {"_id": 0},
}


def recruiting_collections() -> tuple[str, ...]:
    return RECRUITING_COLLECTIONS


def recruiting_id_field(collection: str) -> str:
    _validate_recruiting_collection(collection)
    return RECRUITING_COLLECTION_ID_FIELDS[collection]


def recruiting_safe_projection(collection: str, *, include_raw: bool = False) -> dict[str, int]:
    _validate_recruiting_collection(collection)
    projection = dict(_RECRUITING_SAFE_PROJECTIONS[collection])
    if include_raw:
        projection.pop("raw_content", None)
    return projection


def _validate_recruiting_collection(collection: str) -> None:
    if collection not in RECRUITING_COLLECTION_ID_FIELDS:
        valid = ", ".join(RECRUITING_COLLECTIONS)
        raise ValueError(f"unknown recruiting collection {collection!r}; valid: {valid}")
