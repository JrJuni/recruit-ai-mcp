from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.schema.recruiting_recommendation import (
    build_candidate_position_recommendation_run,
    build_position_candidate_recommendation_run,
)
from deal_intel.storage.identifiers import suggest_slug


def recommend_candidates_for_position(
    mongo: Any,
    *,
    position_id: str,
    candidate_query: dict[str, Any] | None = None,
    candidate_limit: int = 50,
    result_limit: int = 10,
    feedback_limit: int = 200,
    recommendation_run_id: str | None = None,
    save_run: bool = False,
) -> dict[str, Any]:
    position = _read_one_or_raise(
        mongo.get_position,
        position_id,
        entity="position",
    )
    candidates = _read_many_or_raise(
        mongo.list_candidates,
        entity="candidate",
        query=candidate_query or {},
        limit=candidate_limit,
    )
    feedback = _read_many_or_raise(
        mongo.list_feedback,
        entity="feedback",
        position_id=position_id,
        limit=feedback_limit,
    )
    run = _build_or_raise(
        build_position_candidate_recommendation_run,
        position=position,
        candidates=candidates,
        client_feedback=feedback,
        recommendation_run_id=recommendation_run_id
        or _generated_run_id("rec_candidates_for", position_id),
        query={
            "candidate_query": candidate_query or {},
            "candidate_limit": candidate_limit,
            "result_limit": result_limit,
            "feedback_limit": feedback_limit,
        },
        limit=result_limit,
    )
    stored = _save_if_requested(mongo, run, save_run=save_run)
    return _recommendation_response(
        run=run,
        storage_written=stored,
        warnings=[] if candidates else [_warning("no_candidates", "No candidates were available.")],
    )


def recommend_positions_for_candidate(
    mongo: Any,
    *,
    candidate_id: str,
    client_company_id: str | None = None,
    position_status: str | None = "open",
    position_limit: int = 50,
    result_limit: int = 10,
    feedback_limit: int = 200,
    recommendation_run_id: str | None = None,
    save_run: bool = False,
) -> dict[str, Any]:
    candidate = _read_one_or_raise(
        mongo.get_candidate,
        candidate_id,
        entity="candidate",
    )
    positions = _read_many_or_raise(
        mongo.list_positions,
        entity="position",
        client_company_id=client_company_id,
        status=position_status,
        limit=position_limit,
    )
    feedback = _read_many_or_raise(
        mongo.list_feedback,
        entity="feedback",
        candidate_id=candidate_id,
        limit=feedback_limit,
    )
    run = _build_or_raise(
        build_candidate_position_recommendation_run,
        candidate=candidate,
        positions=positions,
        client_feedback=feedback,
        recommendation_run_id=recommendation_run_id
        or _generated_run_id("rec_positions_for", candidate_id),
        query={
            "client_company_id": client_company_id,
            "position_status": position_status,
            "position_limit": position_limit,
            "result_limit": result_limit,
            "feedback_limit": feedback_limit,
        },
        limit=result_limit,
    )
    stored = _save_if_requested(mongo, run, save_run=save_run)
    return _recommendation_response(
        run=run,
        storage_written=stored,
        warnings=[] if positions else [_warning("no_positions", "No positions were available.")],
    )


def _read_one_or_raise(read_fn: Any, entity_id: str, *, entity: str) -> dict[str, Any]:
    try:
        record = read_fn(entity_id)
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=f"failed to read {entity}: {type(exc).__name__}",
            hint="Check MongoDB connectivity and the recruiting collection contract.",
            retryable=True,
        ) from exc
    if record is None:
        raise MCPError(
            error_code=ErrorCode.NOT_FOUND,
            stage=Stage.STORAGE,
            message=f"{entity} not found",
            hint={f"{entity}_id": entity_id},
            retryable=False,
        )
    return record


def _read_many_or_raise(read_fn: Any, *, entity: str, **kwargs: Any) -> list[dict[str, Any]]:
    try:
        return list(read_fn(**kwargs))
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=f"failed to list {entity}: {type(exc).__name__}",
            hint="Check MongoDB connectivity and the recruiting collection contract.",
            retryable=True,
        ) from exc


def _build_or_raise(build_fn: Any, **kwargs: Any) -> Any:
    try:
        return build_fn(**kwargs)
    except ValidationError as exc:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message="invalid recommendation input",
            hint={"errors": exc.errors(include_input=False)},
            retryable=False,
        ) from exc


def _save_if_requested(mongo: Any, run: Any, *, save_run: bool) -> bool:
    if not save_run:
        return False
    try:
        return bool(mongo.save_recommendation_run(run))
    except Exception as exc:
        raise MCPError(
            error_code=ErrorCode.STORAGE_ERROR,
            stage=Stage.STORAGE,
            message=f"failed to save recommendation run: {type(exc).__name__}",
            hint="Check MongoDB connectivity and the recruiting collection contract.",
            retryable=True,
        ) from exc


def _recommendation_response(
    *,
    run: Any,
    storage_written: bool,
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "ok": True,
        "entity": "recommendation_run",
        "recommendation_run_id": run.recommendation_run_id,
        "mode": run.mode,
        "anchor_type": run.anchor_type,
        "anchor_id": run.anchor_id,
        "result_count": len(run.results),
        "storage_written": storage_written,
        "record": run.model_dump(mode="json"),
        "warnings": warnings,
    }


def _generated_run_id(prefix: str, source: str) -> str:
    base = suggest_slug(source).lower().replace("-", "_")
    base = base.strip("_") or "run"
    max_base_len = 80 - len(prefix) - 1
    return f"{prefix}_{base[:max_base_len]}".rstrip("_")


def _warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}
