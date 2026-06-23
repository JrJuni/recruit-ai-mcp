from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

EXPECTED_CONTRACT = {
    "ok": True,
    "question_count": 17,
    "candidate_count": 13,
    "written_record_count": 33,
    "reloaded_record_count": 33,
    "guardrail_candidate_count": 9,
    "guardrails_with_risk_flags": 9,
    "guardrails_with_next_questions": 9,
    "guardrail_risk_row_count": 9,
    "guardrail_next_question_row_count": 9,
    "guardrail_dimension_score_row_count": 9,
    "guardrail_required_risk_flags": ["skill_gap"],
    "candidate_position_available_count": 2,
    "candidate_position_excluded_count": 1,
    "open_position_count": 2,
    "positions_with_shortlist": 2,
    "positions_with_review_risks": 2,
    "positions_with_next_questions": 2,
    "shortlist_risk_row_count": 4,
    "shortlist_next_question_row_count": 5,
    "shortlist_dimension_score_row_count": 6,
    "shortlist_required_risk_flags": ["skill_gap"],
    "saved_run_result_count": 3,
    "saved_run_feedback_adjustment_row_count": 2,
    "saved_run_risk_row_count": 2,
    "saved_run_next_question_row_count": 2,
    "trace_written": True,
    "trace_enabled": True,
    "trace_exists": True,
    "trace_event_count": 1,
    "trace_invalid_event_count": 0,
    "trace_max_events": 3,
    "trace_recent_event_count": 1,
    "trace_recent_tool_names": ["add_recruiting_interaction"],
    "trace_redacted_marker_count": 3,
    "trace_forbidden_value_present": False,
    "report_export_artifact_count": 2,
    "report_export_csv_exists": True,
    "report_export_markdown_exists": True,
    "report_export_csv_row_count": 49,
    "report_export_markdown_line_count": 40,
    "report_export_row_count": 48,
    "report_export_briefing": "2 open positions, 3 active submissions, 1 placements.",
    "report_export_forbidden_term_present": False,
    "candidate_exclusion_result_count": 2,
    "candidate_exclusion_top_position_id": "pos_orbitpay_payments_lead",
    "candidate_exclusion_flagged_count": 1,
    "candidate_exclusion_question_count": 1,
}
_REQUIRED_QUESTIONS = (
    "rq01_recruiting_pipeline_metrics",
    "rq03_positions_for_avery",
    "rq11_local_recruiting_persistence",
    "rq12_recommendation_guardrails",
    "rq13_client_shortlist_readiness",
    "rq14_recommendation_run_review",
    "rq15_workflow_trace_safety",
    "rq16_recruiting_report_export",
    "rq17_candidate_exclusion_position_guardrail",
)
_REQUIRED_FIT_DIMENSIONS = (
    "skill_fit",
    "domain_fit",
    "seniority_fit",
    "compensation_fit",
    "location_fit",
    "availability_fit",
    "client_preference_fit",
    "risk",
)
_CANDIDATE_EXCLUSION_TARGET_ID = "pos_northstar_backend_lead"
_CANDIDATE_EXCLUSION_REQUIRED_RISK_FLAGS = ("client_exclusion",)
_CANDIDATE_EXCLUSION_REQUIRED_NEXT_QUESTION = (
    "Confirm whether the candidate exclusion can be revisited."
)
_SAVED_RUN_TOP_TARGET_ID = "cand_avery_chen"
_SAVED_RUN_TOP_FEEDBACK_ADJUSTMENTS = (
    ("fb_avery_northstar_advance", "domain_fit"),
    ("fb_avery_northstar_advance", "client_preference_fit"),
)
_SAVED_RUN_REQUIRED_RISK_TARGET_ID = "cand_jordan_lee"
_SAVED_RUN_REQUIRED_RISK_FLAGS = ("skill_gap", "client_exclusion")
_SAVED_RUN_REQUIRED_NEXT_QUESTION = "Confirm required skill: Python"


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    questions = _questions_by_id(payload)
    metrics = _summary(questions, "rq01_recruiting_pipeline_metrics")
    candidate_positions = _summary(questions, "rq03_positions_for_avery")
    persistence = _summary(questions, "rq11_local_recruiting_persistence")
    guardrail_payload = _question_payload(questions, "rq12_recommendation_guardrails")
    guardrails = _summary_from_payload(
        guardrail_payload,
        question_id="rq12_recommendation_guardrails",
    )
    shortlist_payload = _question_payload(questions, "rq13_client_shortlist_readiness")
    shortlist = _summary_from_payload(
        shortlist_payload,
        question_id="rq13_client_shortlist_readiness",
    )
    saved_run_payload = _question_payload(questions, "rq14_recommendation_run_review")
    saved_run = _summary_from_payload(
        saved_run_payload,
        question_id="rq14_recommendation_run_review",
    )
    _validate_saved_recommendation_run(saved_run_payload)
    trace_safety = _summary(questions, "rq15_workflow_trace_safety")
    report_export = _summary(questions, "rq16_recruiting_report_export")
    candidate_exclusion_payload = _question_payload(
        questions, "rq17_candidate_exclusion_position_guardrail"
    )
    candidate_exclusion = _summary_from_payload(
        candidate_exclusion_payload,
        question_id="rq17_candidate_exclusion_position_guardrail",
    )
    _validate_candidate_exclusion_run(candidate_exclusion_payload)
    actual = {
        "ok": _required_key(payload, "ok", scope="top-level payload"),
        "question_count": _required_key(
            payload,
            "question_count",
            scope="top-level payload",
        ),
        "candidate_count": _required_key(
            metrics,
            "candidate_count",
            scope="rq01_recruiting_pipeline_metrics summary",
        ),
        "written_record_count": _required_key(
            persistence,
            "written_record_count",
            scope="rq11_local_recruiting_persistence summary",
        ),
        "reloaded_record_count": _required_key(
            persistence,
            "reloaded_record_count",
            scope="rq11_local_recruiting_persistence summary",
        ),
        "guardrail_candidate_count": _required_key(
            guardrails,
            "guardrail_candidate_count",
            scope="rq12_recommendation_guardrails summary",
        ),
        "guardrails_with_risk_flags": _required_key(
            guardrails,
            "guardrails_with_risk_flags",
            scope="rq12_recommendation_guardrails summary",
        ),
        "guardrails_with_next_questions": _required_key(
            guardrails,
            "guardrails_with_next_questions",
            scope="rq12_recommendation_guardrails summary",
        ),
        "guardrail_risk_row_count": _guardrail_row_count(
            guardrail_payload,
            field="guardrail_risk_flags",
        ),
        "guardrail_next_question_row_count": _guardrail_row_count(
            guardrail_payload,
            field="guardrail_next_questions",
        ),
        "guardrail_dimension_score_row_count": _guardrail_dimension_score_row_count(
            guardrail_payload
        ),
        "guardrail_required_risk_flags": _required_guardrail_risk_flags(
            guardrail_payload,
            flags=EXPECTED_CONTRACT["guardrail_required_risk_flags"],
        ),
        "candidate_position_available_count": _required_key(
            candidate_positions,
            "available_position_count",
            scope="rq03_positions_for_avery summary",
        ),
        "candidate_position_excluded_count": _required_key(
            candidate_positions,
            "excluded_position_count",
            scope="rq03_positions_for_avery summary",
        ),
        "open_position_count": _required_key(
            shortlist,
            "open_position_count",
            scope="rq13_client_shortlist_readiness summary",
        ),
        "positions_with_shortlist": _required_key(
            shortlist,
            "positions_with_shortlist",
            scope="rq13_client_shortlist_readiness summary",
        ),
        "positions_with_review_risks": _required_key(
            shortlist,
            "positions_with_review_risks",
            scope="rq13_client_shortlist_readiness summary",
        ),
        "positions_with_next_questions": _required_key(
            shortlist,
            "positions_with_next_questions",
            scope="rq13_client_shortlist_readiness summary",
        ),
        "shortlist_risk_row_count": _shortlist_row_count(
            shortlist_payload,
            field="risk_flags",
        ),
        "shortlist_next_question_row_count": _shortlist_row_count(
            shortlist_payload,
            field="next_questions",
        ),
        "shortlist_dimension_score_row_count": _shortlist_dimension_score_row_count(
            shortlist_payload
        ),
        "shortlist_required_risk_flags": _required_shortlist_risk_flags(
            shortlist_payload,
            flags=EXPECTED_CONTRACT["shortlist_required_risk_flags"],
        ),
        "saved_run_result_count": _required_key(
            saved_run,
            "result_count",
            scope="rq14_recommendation_run_review summary",
        ),
        "saved_run_feedback_adjustment_row_count": _required_key(
            saved_run,
            "feedback_adjustment_row_count",
            scope="rq14_recommendation_run_review summary",
        ),
        "saved_run_risk_row_count": _required_key(
            saved_run,
            "risk_row_count",
            scope="rq14_recommendation_run_review summary",
        ),
        "saved_run_next_question_row_count": _required_key(
            saved_run,
            "next_question_row_count",
            scope="rq14_recommendation_run_review summary",
        ),
        "trace_event_count": _required_key(
            trace_safety,
            "event_count",
            scope="rq15_workflow_trace_safety summary",
        ),
        "trace_written": _required_key(
            trace_safety,
            "trace_written",
            scope="rq15_workflow_trace_safety summary",
        ),
        "trace_enabled": _required_key(
            trace_safety,
            "enabled",
            scope="rq15_workflow_trace_safety summary",
        ),
        "trace_exists": _required_key(
            trace_safety,
            "trace_exists",
            scope="rq15_workflow_trace_safety summary",
        ),
        "trace_invalid_event_count": _required_key(
            trace_safety,
            "invalid_event_count",
            scope="rq15_workflow_trace_safety summary",
        ),
        "trace_max_events": _required_key(
            trace_safety,
            "max_events",
            scope="rq15_workflow_trace_safety summary",
        ),
        "trace_recent_event_count": _required_key(
            trace_safety,
            "recent_event_count",
            scope="rq15_workflow_trace_safety summary",
        ),
        "trace_recent_tool_names": _required_key(
            trace_safety,
            "recent_tool_names",
            scope="rq15_workflow_trace_safety summary",
        ),
        "trace_redacted_marker_count": _required_key(
            trace_safety,
            "redacted_marker_count",
            scope="rq15_workflow_trace_safety summary",
        ),
        "trace_forbidden_value_present": _required_key(
            trace_safety,
            "forbidden_value_present",
            scope="rq15_workflow_trace_safety summary",
        ),
        "report_export_artifact_count": _required_key(
            report_export,
            "artifact_count",
            scope="rq16_recruiting_report_export summary",
        ),
        "report_export_csv_exists": _required_key(
            report_export,
            "csv_exists",
            scope="rq16_recruiting_report_export summary",
        ),
        "report_export_markdown_exists": _required_key(
            report_export,
            "markdown_exists",
            scope="rq16_recruiting_report_export summary",
        ),
        "report_export_csv_row_count": _required_key(
            report_export,
            "csv_row_count",
            scope="rq16_recruiting_report_export summary",
        ),
        "report_export_markdown_line_count": _required_key(
            report_export,
            "markdown_line_count",
            scope="rq16_recruiting_report_export summary",
        ),
        "report_export_row_count": _required_key(
            report_export,
            "row_count",
            scope="rq16_recruiting_report_export summary",
        ),
        "report_export_briefing": _required_key(
            report_export,
            "briefing",
            scope="rq16_recruiting_report_export summary",
        ),
        "report_export_forbidden_term_present": _required_key(
            report_export,
            "forbidden_term_present",
            scope="rq16_recruiting_report_export summary",
        ),
        "candidate_exclusion_result_count": _required_key(
            candidate_exclusion,
            "result_count",
            scope="rq17_candidate_exclusion_position_guardrail summary",
        ),
        "candidate_exclusion_top_position_id": _required_key(
            candidate_exclusion,
            "top_position_id",
            scope="rq17_candidate_exclusion_position_guardrail summary",
        ),
        "candidate_exclusion_flagged_count": _required_key(
            candidate_exclusion,
            "excluded_client_flagged_count",
            scope="rq17_candidate_exclusion_position_guardrail summary",
        ),
        "candidate_exclusion_question_count": _required_key(
            candidate_exclusion,
            "excluded_client_question_count",
            scope="rq17_candidate_exclusion_position_guardrail summary",
        ),
    }
    if actual != EXPECTED_CONTRACT:
        raise ValueError(
            "Recruiting natural-question smoke contract mismatch: "
            f"expected={EXPECTED_CONTRACT!r}, actual={actual!r}"
        )
    return actual


def _questions_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_questions = _required_key(payload, "questions", scope="top-level payload")
    if not isinstance(raw_questions, list):
        raise ValueError("Recruiting smoke payload field 'questions' must be a list.")
    questions = {
        item.get("id"): item
        for item in raw_questions
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    missing = [question_id for question_id in _REQUIRED_QUESTIONS if question_id not in questions]
    if missing:
        raise ValueError(
            "Recruiting smoke payload missing required question ids: "
            + ", ".join(missing)
        )
    return questions


def _summary(questions: dict[str, dict[str, Any]], question_id: str) -> dict[str, Any]:
    payload = _question_payload(questions, question_id)
    return _summary_from_payload(payload, question_id=question_id)


def _question_payload(
    questions: dict[str, dict[str, Any]],
    question_id: str,
) -> dict[str, Any]:
    payload = _required_key(questions[question_id], "payload", scope=question_id)
    if not isinstance(payload, dict):
        raise ValueError(f"Recruiting smoke question {question_id} payload must be a mapping.")
    return payload


def _summary_from_payload(payload: dict[str, Any], *, question_id: str) -> dict[str, Any]:
    summary = _required_key(payload, "summary", scope=f"{question_id} payload")
    if not isinstance(summary, dict):
        raise ValueError(f"Recruiting smoke question {question_id} summary must be a mapping.")
    return summary


def _shortlist_row_count(payload: dict[str, Any], *, field: str) -> int:
    shortlists = _required_key(
        payload,
        "shortlists",
        scope="rq13_client_shortlist_readiness payload",
    )
    if not isinstance(shortlists, list):
        raise ValueError("Recruiting smoke rq13 shortlists must be a list.")
    count = 0
    for shortlist_index, shortlist in enumerate(shortlists):
        if not isinstance(shortlist, dict):
            raise ValueError(
                "Recruiting smoke rq13 shortlist rows must be mappings."
            )
        candidates = _required_key(
            shortlist,
            "candidates",
            scope=f"rq13_client_shortlist_readiness shortlist {shortlist_index}",
        )
        if not isinstance(candidates, list):
            raise ValueError(
                "Recruiting smoke rq13 shortlist candidates must be a list."
            )
        for candidate_index, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                raise ValueError(
                    "Recruiting smoke rq13 candidate rows must be mappings."
                )
            values = _required_key(
                candidate,
                field,
                scope=(
                    "rq13_client_shortlist_readiness "
                    f"candidate {candidate_index}"
                ),
            )
            if not isinstance(values, list):
                raise ValueError(
                    "Recruiting smoke rq13 candidate "
                    f"field {field!r} must be a list."
                )
            if values:
                count += 1
    return count


def _shortlist_dimension_score_row_count(payload: dict[str, Any]) -> int:
    shortlists = _required_key(
        payload,
        "shortlists",
        scope="rq13_client_shortlist_readiness payload",
    )
    if not isinstance(shortlists, list):
        raise ValueError("Recruiting smoke rq13 shortlists must be a list.")
    count = 0
    for shortlist_index, shortlist in enumerate(shortlists):
        if not isinstance(shortlist, dict):
            raise ValueError(
                "Recruiting smoke rq13 shortlist rows must be mappings."
            )
        candidates = _required_key(
            shortlist,
            "candidates",
            scope=f"rq13_client_shortlist_readiness shortlist {shortlist_index}",
        )
        if not isinstance(candidates, list):
            raise ValueError(
                "Recruiting smoke rq13 shortlist candidates must be a list."
            )
        for candidate_index, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                raise ValueError(
                    "Recruiting smoke rq13 candidate rows must be mappings."
                )
            scores = _required_key(
                candidate,
                "dimension_scores",
                scope=(
                    "rq13_client_shortlist_readiness "
                    f"candidate {candidate_index}"
                ),
            )
            if not isinstance(scores, dict):
                raise ValueError(
                    "Recruiting smoke rq13 dimension_scores must be a mapping."
                )
            missing = [
                dimension
                for dimension in _REQUIRED_FIT_DIMENSIONS
                if dimension not in scores
            ]
            if missing:
                raise ValueError(
                    "Recruiting smoke rq13 dimension_scores missing "
                    + ", ".join(missing)
                )
            count += 1
    return count


def _required_shortlist_risk_flags(
    payload: dict[str, Any],
    *,
    flags: list[str],
) -> list[str]:
    shortlists = _required_key(
        payload,
        "shortlists",
        scope="rq13_client_shortlist_readiness payload",
    )
    if not isinstance(shortlists, list):
        raise ValueError("Recruiting smoke rq13 shortlists must be a list.")
    observed: set[str] = set()
    for shortlist_index, shortlist in enumerate(shortlists):
        if not isinstance(shortlist, dict):
            raise ValueError(
                "Recruiting smoke rq13 shortlist rows must be mappings."
            )
        candidates = _required_key(
            shortlist,
            "candidates",
            scope=f"rq13_client_shortlist_readiness shortlist {shortlist_index}",
        )
        if not isinstance(candidates, list):
            raise ValueError(
                "Recruiting smoke rq13 shortlist candidates must be a list."
            )
        for candidate_index, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                raise ValueError(
                    "Recruiting smoke rq13 candidate rows must be mappings."
                )
            values = _required_key(
                candidate,
                "risk_flags",
                scope=(
                    "rq13_client_shortlist_readiness "
                    f"candidate {candidate_index}"
                ),
            )
            if not isinstance(values, list):
                raise ValueError(
                    "Recruiting smoke rq13 candidate field 'risk_flags' "
                    "must be a list."
                )
            observed.update(item for item in values if isinstance(item, str))
    missing = [flag for flag in flags if flag not in observed]
    if missing:
        raise ValueError(
            "Recruiting smoke rq13 missing required risk flags: "
            + ", ".join(missing)
        )
    return [flag for flag in flags if flag in observed]


def _guardrail_row_count(payload: dict[str, Any], *, field: str) -> int:
    guardrails = _required_key(
        payload,
        "guardrails",
        scope="rq12_recommendation_guardrails payload",
    )
    if not isinstance(guardrails, list):
        raise ValueError("Recruiting smoke rq12 guardrails must be a list.")
    count = 0
    for guardrail_index, guardrail in enumerate(guardrails):
        if not isinstance(guardrail, dict):
            raise ValueError("Recruiting smoke rq12 guardrail rows must be mappings.")
        values = _required_key(
            guardrail,
            field,
            scope=f"rq12_recommendation_guardrails guardrail {guardrail_index}",
        )
        if not isinstance(values, list):
            raise ValueError(
                "Recruiting smoke rq12 guardrail "
                f"field {field!r} must be a list."
            )
        if values:
            count += 1
    return count


def _required_guardrail_risk_flags(
    payload: dict[str, Any],
    *,
    flags: list[str],
) -> list[str]:
    guardrails = _required_key(
        payload,
        "guardrails",
        scope="rq12_recommendation_guardrails payload",
    )
    if not isinstance(guardrails, list):
        raise ValueError("Recruiting smoke rq12 guardrails must be a list.")
    observed: set[str] = set()
    for guardrail_index, guardrail in enumerate(guardrails):
        if not isinstance(guardrail, dict):
            raise ValueError("Recruiting smoke rq12 guardrail rows must be mappings.")
        values = _required_key(
            guardrail,
            "guardrail_risk_flags",
            scope=f"rq12_recommendation_guardrails guardrail {guardrail_index}",
        )
        if not isinstance(values, list):
            raise ValueError(
                "Recruiting smoke rq12 guardrail field "
                "'guardrail_risk_flags' must be a list."
            )
        observed.update(item for item in values if isinstance(item, str))
    missing = [flag for flag in flags if flag not in observed]
    if missing:
        raise ValueError(
            "Recruiting smoke rq12 missing required risk flags: "
            + ", ".join(missing)
        )
    return [flag for flag in flags if flag in observed]


def _validate_candidate_exclusion_run(payload: dict[str, Any]) -> None:
    run = _required_key(
        payload,
        "run",
        scope="rq17_candidate_exclusion_position_guardrail payload",
    )
    if not isinstance(run, dict):
        raise ValueError("Recruiting smoke rq17 run must be a mapping.")
    results = _required_key(
        run,
        "results",
        scope="rq17_candidate_exclusion_position_guardrail run",
    )
    if not isinstance(results, list):
        raise ValueError("Recruiting smoke rq17 run results must be a list.")
    excluded = None
    for result_index, row in enumerate(results):
        if not isinstance(row, dict):
            raise ValueError("Recruiting smoke rq17 result rows must be mappings.")
        if row.get("target_id") == _CANDIDATE_EXCLUSION_TARGET_ID:
            excluded = row
            break
    if excluded is None:
        raise ValueError(
            "Recruiting smoke rq17 missing excluded client result row "
            f"{_CANDIDATE_EXCLUSION_TARGET_ID!r}."
        )
    risk_flags = _required_key(
        excluded,
        "risk_flags",
        scope="rq17_candidate_exclusion_position_guardrail excluded result",
    )
    if not isinstance(risk_flags, list):
        raise ValueError("Recruiting smoke rq17 excluded result risk_flags must be a list.")
    missing_flags = [
        flag
        for flag in _CANDIDATE_EXCLUSION_REQUIRED_RISK_FLAGS
        if flag not in risk_flags
    ]
    if missing_flags:
        raise ValueError(
            "Recruiting smoke rq17 excluded result missing required risk flags: "
            + ", ".join(missing_flags)
        )
    next_questions = _required_key(
        excluded,
        "next_questions",
        scope="rq17_candidate_exclusion_position_guardrail excluded result",
    )
    if not isinstance(next_questions, list):
        raise ValueError(
            "Recruiting smoke rq17 excluded result next_questions must be a list."
        )
    if _CANDIDATE_EXCLUSION_REQUIRED_NEXT_QUESTION not in next_questions:
        raise ValueError(
            "Recruiting smoke rq17 excluded result missing exclusion next question."
        )


def _validate_saved_recommendation_run(payload: dict[str, Any]) -> None:
    review = _required_key(
        payload,
        "review",
        scope="rq14_recommendation_run_review payload",
    )
    if not isinstance(review, dict):
        raise ValueError("Recruiting smoke rq14 review must be a mapping.")
    record = _required_key(
        review,
        "record",
        scope="rq14_recommendation_run_review review",
    )
    if not isinstance(record, dict):
        raise ValueError("Recruiting smoke rq14 review record must be a mapping.")
    results = _required_key(
        record,
        "results",
        scope="rq14_recommendation_run_review record",
    )
    if not isinstance(results, list):
        raise ValueError("Recruiting smoke rq14 record results must be a list.")
    top_row = _find_result_row(
        results,
        target_id=_SAVED_RUN_TOP_TARGET_ID,
        scope="rq14",
    )
    feedback_adjustments = _required_key(
        top_row,
        "feedback_adjustments",
        scope="rq14_recommendation_run_review top result",
    )
    if not isinstance(feedback_adjustments, list):
        raise ValueError(
            "Recruiting smoke rq14 top result feedback_adjustments must be a list."
        )
    observed_adjustments = {
        (row.get("feedback_id"), row.get("dimension"))
        for row in feedback_adjustments
        if isinstance(row, dict)
    }
    missing_adjustments = [
        adjustment
        for adjustment in _SAVED_RUN_TOP_FEEDBACK_ADJUSTMENTS
        if adjustment not in observed_adjustments
    ]
    if missing_adjustments:
        raise ValueError(
            "Recruiting smoke rq14 top result missing feedback adjustments: "
            + ", ".join(f"{fid}:{dimension}" for fid, dimension in missing_adjustments)
        )
    risk_row = _find_result_row(
        results,
        target_id=_SAVED_RUN_REQUIRED_RISK_TARGET_ID,
        scope="rq14",
    )
    risk_flags = _required_key(
        risk_row,
        "risk_flags",
        scope="rq14_recommendation_run_review risk result",
    )
    if not isinstance(risk_flags, list):
        raise ValueError("Recruiting smoke rq14 risk result risk_flags must be a list.")
    missing_flags = [
        flag for flag in _SAVED_RUN_REQUIRED_RISK_FLAGS if flag not in risk_flags
    ]
    if missing_flags:
        raise ValueError(
            "Recruiting smoke rq14 risk result missing required risk flags: "
            + ", ".join(missing_flags)
        )
    next_questions = _required_key(
        risk_row,
        "next_questions",
        scope="rq14_recommendation_run_review risk result",
    )
    if not isinstance(next_questions, list):
        raise ValueError(
            "Recruiting smoke rq14 risk result next_questions must be a list."
        )
    if _SAVED_RUN_REQUIRED_NEXT_QUESTION not in next_questions:
        raise ValueError(
            "Recruiting smoke rq14 risk result missing required next question."
        )


def _find_result_row(
    results: list[Any],
    *,
    target_id: str,
    scope: str,
) -> dict[str, Any]:
    for row in results:
        if not isinstance(row, dict):
            raise ValueError(f"Recruiting smoke {scope} result rows must be mappings.")
        if row.get("target_id") == target_id:
            return row
    raise ValueError(
        f"Recruiting smoke {scope} missing required result row {target_id!r}."
    )


def _guardrail_dimension_score_row_count(payload: dict[str, Any]) -> int:
    guardrails = _required_key(
        payload,
        "guardrails",
        scope="rq12_recommendation_guardrails payload",
    )
    if not isinstance(guardrails, list):
        raise ValueError("Recruiting smoke rq12 guardrails must be a list.")
    count = 0
    for guardrail_index, guardrail in enumerate(guardrails):
        if not isinstance(guardrail, dict):
            raise ValueError("Recruiting smoke rq12 guardrail rows must be mappings.")
        scores = _required_key(
            guardrail,
            "guardrail_dimension_scores",
            scope=f"rq12_recommendation_guardrails guardrail {guardrail_index}",
        )
        if not isinstance(scores, dict):
            raise ValueError(
                "Recruiting smoke rq12 guardrail_dimension_scores must be a mapping."
            )
        missing = [
            dimension
            for dimension in _REQUIRED_FIT_DIMENSIONS
            if dimension not in scores
        ]
        if missing:
            raise ValueError(
                "Recruiting smoke rq12 guardrail_dimension_scores missing "
                + ", ".join(missing)
            )
        count += 1
    return count


def _required_key(mapping: dict[str, Any], key: str, *, scope: str) -> Any:
    if key not in mapping:
        raise ValueError(f"Recruiting smoke {scope} missing required field {key!r}.")
    return mapping[key]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the Recruit AI natural-question smoke contract."
    )
    parser.add_argument("payload", type=Path)
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.payload.read_text(encoding="utf-8"))
        actual = validate_payload(payload)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps({"ok": True, "contract": actual}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
