from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.schema.recruiting import (
    CandidateProfile,
    ClientCompany,
    CompensationExpectation,
    Position,
)
from deal_intel.storage.identifiers import suggest_slug


def create_candidate(
    mongo: Any,
    *,
    name: str,
    candidate_id: str | None = None,
    headline: str = "",
    current_company: str = "",
    current_title: str = "",
    skills: list[str] | None = None,
    domains: list[str] | None = None,
    seniority: str = "",
    locations: list[str] | None = None,
    work_authorization: str = "",
    availability: str = "",
) -> dict[str, Any]:
    candidate = _validate_model(
        CandidateProfile,
        {
            "candidate_id": candidate_id or _generated_id("cand", name),
            "name": name,
            "headline": headline,
            "current_company": current_company,
            "current_title": current_title,
            "skills": skills or [],
            "domains": domains or [],
            "seniority": seniority,
            "locations": locations or [],
            "work_authorization": work_authorization,
            "availability": availability,
        },
        entity="candidate",
    )
    _store_or_raise(mongo.upsert_candidate, candidate, entity="candidate")
    record = mongo.get_candidate(candidate.candidate_id) or candidate.model_dump(mode="json")
    return _create_response(
        entity="candidate",
        id_field="candidate_id",
        record=record,
        warnings=[],
    )


def create_client_company(
    mongo: Any,
    *,
    name: str,
    client_company_id: str | None = None,
    industry: str = "",
    stage: str = "",
    locations: list[str] | None = None,
    hiring_preferences: list[str] | None = None,
    risk_notes: list[str] | None = None,
) -> dict[str, Any]:
    client_company = _validate_model(
        ClientCompany,
        {
            "client_company_id": client_company_id or _generated_id("client", name),
            "name": name,
            "industry": industry,
            "stage": stage,
            "locations": locations or [],
            "hiring_preferences": hiring_preferences or [],
            "risk_notes": risk_notes or [],
        },
        entity="client_company",
    )
    _store_or_raise(
        mongo.upsert_client_company,
        client_company,
        entity="client_company",
    )
    record = (
        mongo.get_client_company(client_company.client_company_id)
        or client_company.model_dump(mode="json")
    )
    return _create_response(
        entity="client_company",
        id_field="client_company_id",
        record=record,
        warnings=[],
    )


def create_position(
    mongo: Any,
    *,
    client_company_id: str,
    title: str,
    position_id: str | None = None,
    status: str = "draft",
    seniority: str = "",
    must_have: list[str] | None = None,
    nice_to_have: list[str] | None = None,
    target_compensation: dict[str, Any] | None = None,
    locations: list[str] | None = None,
    remote_policy: str = "",
    ideal_candidate_examples: list[str] | None = None,
) -> dict[str, Any]:
    position = _validate_model(
        Position,
        {
            "position_id": position_id or _generated_id("pos", title),
            "client_company_id": client_company_id,
            "title": title,
            "status": status,
            "seniority": seniority,
            "must_have": must_have or [],
            "nice_to_have": nice_to_have or [],
            "target_compensation": _compensation(target_compensation),
            "locations": locations or [],
            "remote_policy": remote_policy,
            "ideal_candidate_examples": ideal_candidate_examples or [],
        },
        entity="position",
    )
    _store_or_raise(mongo.upsert_position, position, entity="position")
    record = mongo.get_position(position.position_id) or position.model_dump(mode="json")
    return _create_response(
        entity="position",
        id_field="position_id",
        record=record,
        warnings=[],
    )


def _generated_id(prefix: str, source: str) -> str:
    base = suggest_slug(source).lower().replace("-", "_")
    base = base.strip("_") or prefix
    max_base_len = 80 - len(prefix) - 1
    return f"{prefix}_{base[:max_base_len]}".rstrip("_")


def _compensation(value: dict[str, Any] | None) -> CompensationExpectation | None:
    if value is None:
        return None
    return _validate_model(CompensationExpectation, value, entity="target_compensation")


def _validate_model(model_cls: type[Any], payload: dict[str, Any], *, entity: str) -> Any:
    try:
        return model_cls.model_validate(payload)
    except ValidationError as exc:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=f"invalid {entity} input",
            hint={
                "entity": entity,
                "errors": exc.errors(include_input=False),
            },
            retryable=False,
        ) from exc


def _store_or_raise(store_fn: Any, model: Any, *, entity: str) -> None:
    try:
        store_fn(model)
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=f"failed to store {entity}: {type(exc).__name__}",
            hint="Check MongoDB connectivity and the recruiting collection contract.",
            retryable=True,
        ) from exc


def _create_response(
    *,
    entity: str,
    id_field: str,
    record: dict[str, Any],
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "ok": True,
        "entity": entity,
        id_field: record[id_field],
        "record": record,
        "warnings": warnings,
    }
