from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from importlib import resources
from pathlib import Path
from typing import Any

DEAL_SUMMARY_VECTOR_INDEX = "deal_summary_vector"
DEAL_SUMMARY_VECTOR_INDEX_FILE = "deal_summary_vector.v1.json"
MIN_VECTOR_DIMENSIONS = 1
MAX_VECTOR_DIMENSIONS = 4096
DEFAULT_DEAL_SUMMARY_VECTOR_INDEX_SPEC = (
    Path(__file__).resolve().parents[2]
    / "atlas"
    / "vector_indexes"
    / DEAL_SUMMARY_VECTOR_INDEX_FILE
)


def load_deal_summary_vector_index_spec(path: str | Path | None = None) -> dict[str, Any]:
    """Load the version-managed Atlas Vector Search index spec."""
    if path is not None:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    if DEFAULT_DEAL_SUMMARY_VECTOR_INDEX_SPEC.exists():
        return json.loads(
            DEFAULT_DEAL_SUMMARY_VECTOR_INDEX_SPEC.read_text(encoding="utf-8")
        )
    return json.loads(_vector_index_resource_text())


def deal_summary_vector_index_name() -> str:
    return str(load_deal_summary_vector_index_spec()["create_search_index"]["name"])


def deal_summary_vector_search_settings() -> dict[str, int]:
    spec = load_deal_summary_vector_index_spec()
    _raise_if_invalid_spec(spec)
    settings = spec["search"]
    return {
        "num_candidates_multiplier": int(settings["numCandidatesMultiplier"]),
        "minimum_num_candidates": int(settings["minimumNumCandidates"]),
        "max_limit": int(settings["maxLimit"]),
    }


def deal_summary_vector_index_summary(
    *,
    dimensions: int | None = None,
) -> dict[str, Any]:
    """Return a compact, secret-safe summary of the expected Atlas index."""
    spec = load_deal_summary_vector_index_spec()
    _raise_if_invalid_spec(spec)
    field = _vector_field(spec)
    effective_dimensions = field["numDimensions"]
    if dimensions is not None:
        effective_dimensions = _validated_dimensions(dimensions)
    return {
        "index_name": spec["create_search_index"]["name"],
        "collection": spec["collection"],
        "embedding_path": spec["embedding"]["path"],
        "num_dimensions": effective_dimensions,
        "similarity": spec["embedding"]["similarity"],
        "minimum_cluster_tier": spec["minimum_cluster_tier"],
    }


def validate_deal_summary_vector_index_spec(
    spec: Mapping[str, Any],
) -> list[str]:
    """Validate the static Atlas Vector Search spec without calling Atlas."""
    errors: list[str] = []

    if spec.get("id") != DEAL_SUMMARY_VECTOR_INDEX:
        errors.append("id must be deal_summary_vector")
    if spec.get("collection") != "deals":
        errors.append("collection must be deals")
    if spec.get("minimum_cluster_tier") != "M10":
        errors.append("minimum_cluster_tier must be M10")

    embedding = spec.get("embedding")
    if not isinstance(embedding, Mapping):
        errors.append("embedding must be an object")
        embedding = {}
    embedding_path = embedding.get("path")
    embedding_dimensions = embedding.get("numDimensions")
    embedding_similarity = embedding.get("similarity")

    if embedding_path != "summary_embedding":
        errors.append("embedding.path must be summary_embedding")
    errors.extend(_dimension_errors(embedding_dimensions, "embedding.numDimensions"))
    if embedding_similarity != "cosine":
        errors.append("embedding.similarity must be cosine")

    create_index = spec.get("create_search_index")
    if not isinstance(create_index, Mapping):
        errors.append("create_search_index must be an object")
        create_index = {}
    if create_index.get("name") != DEAL_SUMMARY_VECTOR_INDEX:
        errors.append("create_search_index.name must be deal_summary_vector")
    if create_index.get("type") != "vectorSearch":
        errors.append("create_search_index.type must be vectorSearch")

    try:
        field = _vector_field(spec)
    except ValueError as exc:
        errors.append(str(exc))
        field = {}

    if field:
        if field.get("type") != "vector":
            errors.append("vector field type must be vector")
        if field.get("path") != embedding_path:
            errors.append("vector field path must match embedding.path")
        if field.get("numDimensions") != embedding_dimensions:
            errors.append("vector field dimensions must match embedding.numDimensions")
        if field.get("similarity") != embedding_similarity:
            errors.append("vector field similarity must match embedding.similarity")
        errors.extend(
            _dimension_errors(
                field.get("numDimensions"),
                "create_search_index.definition.fields[].numDimensions",
            )
        )

    search = spec.get("search")
    if not isinstance(search, Mapping):
        errors.append("search must be an object")
        search = {}
    for key in ("numCandidatesMultiplier", "minimumNumCandidates", "maxLimit"):
        value = search.get(key)
        if not isinstance(value, int) or value <= 0:
            errors.append(f"search.{key} must be a positive integer")

    return errors


def build_create_search_index_command(
    *,
    dimensions: int | None = None,
) -> dict[str, Any]:
    spec = load_deal_summary_vector_index_spec()
    _raise_if_invalid_spec(spec)
    index = deepcopy(spec["create_search_index"])
    if dimensions is not None:
        dimensions = _validated_dimensions(dimensions)
        for field in index["definition"]["fields"]:
            if field.get("path") == spec["embedding"]["path"]:
                field["numDimensions"] = dimensions
    return {
        "createSearchIndexes": spec["collection"],
        "indexes": [index],
    }


def _vector_index_resource_text() -> str:
    return (
        resources.files("deal_intel.resources")
        .joinpath("atlas", "vector_indexes", DEAL_SUMMARY_VECTOR_INDEX_FILE)
        .read_text(encoding="utf-8")
    )


def _raise_if_invalid_spec(spec: Mapping[str, Any]) -> None:
    errors = validate_deal_summary_vector_index_spec(spec)
    if errors:
        raise ValueError(
            "Invalid deal_summary_vector Atlas index spec: " + "; ".join(errors)
        )


def _vector_field(spec: Mapping[str, Any]) -> Mapping[str, Any]:
    create_index = spec.get("create_search_index", {})
    if not isinstance(create_index, Mapping):
        raise ValueError("create_search_index must be an object")
    definition = create_index.get("definition", {})
    if not isinstance(definition, Mapping):
        raise ValueError("create_search_index.definition must be an object")
    fields = definition.get("fields", [])
    if not isinstance(fields, list):
        raise ValueError("create_search_index.definition.fields must be an array")
    embedding = spec.get("embedding", {})
    if not isinstance(embedding, Mapping):
        raise ValueError("embedding must be an object")
    candidates = [
        field
        for field in fields
        if isinstance(field, Mapping)
        and field.get("path") == embedding.get("path")
    ]
    if len(candidates) != 1:
        raise ValueError("exactly one vector field must match embedding.path")
    return candidates[0]


def _validated_dimensions(dimensions: int) -> int:
    errors = _dimension_errors(dimensions, "dimensions")
    if errors:
        raise ValueError(errors[0])
    return dimensions


def _dimension_errors(value: Any, label: str) -> list[str]:
    if not isinstance(value, int):
        return [f"{label} must be an integer"]
    if value < MIN_VECTOR_DIMENSIONS or value > MAX_VECTOR_DIMENSIONS:
        return [
            f"{label} must be between {MIN_VECTOR_DIMENSIONS} and "
            f"{MAX_VECTOR_DIMENSIONS}"
        ]
    return []
