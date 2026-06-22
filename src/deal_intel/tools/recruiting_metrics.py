from __future__ import annotations

from typing import Any

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.schema.recruiting_metrics import build_recruiting_pipeline_metrics


def get_recruiting_metrics(
    mongo: Any,
    *,
    candidate_limit: int = 500,
    position_limit: int = 500,
    submission_limit: int = 1000,
    feedback_limit: int = 1000,
    position_status: str | None = None,
) -> dict[str, Any]:
    candidates = _read_many_or_raise(
        mongo.list_candidates,
        entity="candidate",
        query={},
        limit=candidate_limit,
    )
    positions = _read_many_or_raise(
        mongo.list_positions,
        entity="position",
        status=position_status,
        limit=position_limit,
    )
    submissions = _read_many_or_raise(
        mongo.list_submissions,
        entity="submission",
        limit=submission_limit,
    )
    feedback = _read_many_or_raise(
        mongo.list_feedback,
        entity="feedback",
        limit=feedback_limit,
    )
    metrics = build_recruiting_pipeline_metrics(
        candidates=candidates,
        positions=positions,
        submissions=submissions,
        feedback=feedback,
    )
    return {
        **metrics,
        "filters": {
            "position_status": position_status,
        },
        "limits": {
            "candidate_limit": candidate_limit,
            "position_limit": position_limit,
            "submission_limit": submission_limit,
            "feedback_limit": feedback_limit,
        },
        "storage_written": False,
    }


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
