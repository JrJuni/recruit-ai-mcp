from __future__ import annotations

from deal_intel.schema.recruiting import (
    DEFAULT_RECRUITING_FIT_RUBRIC,
    EvidenceReference,
    FitSignal,
)
from deal_intel.schema.recruiting_fit import (
    build_fit_snapshot,
    calculate_overall_score,
)


def _evidence() -> EvidenceReference:
    return EvidenceReference(
        evidence_id="ev_screen_1",
        source_type="interaction",
        source_id="int_screen_1",
        summary="Candidate described recent Python platform ownership.",
        confidence="candidate_stated",
    )


def _complete_signals(score: int = 4, *, risk: int = 1) -> dict[str, FitSignal]:
    return {
        key: FitSignal(score=risk if key == "risk" else score, evidence_refs=[_evidence()])
        for key in DEFAULT_RECRUITING_FIT_RUBRIC.dimensions
    }


def test_build_fit_snapshot_calculates_weighted_score_with_risk_inversion() -> None:
    result = build_fit_snapshot(
        dimensions=_complete_signals(score=4, risk=1),
        summary="Strong fit with low risk.",
        risk_summary="No major risk identified.",
    )

    assert result.snapshot.overall_score == 80.0
    assert result.dimension_scores["skill_fit"] == 80.0
    assert result.dimension_scores["risk"] == 80.0
    assert result.snapshot.summary == "Strong fit with low risk."
    assert result.snapshot.risk_summary == "No major risk identified."
    assert result.warnings == []


def test_calculate_overall_score_uses_dimension_weights() -> None:
    signals = _complete_signals(score=0, risk=5)
    signals["skill_fit"] = FitSignal(score=5, evidence_refs=[_evidence()])

    score = calculate_overall_score(dimensions=signals)

    assert score == 17.14


def test_calculate_overall_score_honors_custom_rubric_weights() -> None:
    rubric = DEFAULT_RECRUITING_FIT_RUBRIC.model_copy(deep=True)
    rubric.dimensions["skill_fit"] = rubric.dimensions["skill_fit"].model_copy(
        update={"weight": 10.0}
    )
    signals = _complete_signals(score=0, risk=5)
    signals["skill_fit"] = FitSignal(score=5, evidence_refs=[_evidence()])

    score = calculate_overall_score(dimensions=signals, rubric=rubric)

    assert score == 57.97


def test_missing_dimensions_are_penalized_and_warned() -> None:
    result = build_fit_snapshot(
        dimensions={
            "skill_fit": FitSignal(score=5, evidence_refs=[_evidence()]),
            "risk": FitSignal(score=0, evidence_refs=[_evidence()]),
        }
    )

    assert result.snapshot.overall_score == 28.57
    assert result.dimension_scores["skill_fit"] == 100.0
    assert result.dimension_scores["risk"] == 100.0
    missing = [warning for warning in result.warnings if warning["code"] == "missing_dimension"]
    assert {warning["dimension"] for warning in missing} == {
        "domain_fit",
        "seniority_fit",
        "compensation_fit",
        "location_fit",
        "availability_fit",
        "client_preference_fit",
    }


def test_missing_evidence_missing_info_and_low_scores_emit_warnings() -> None:
    result = build_fit_snapshot(
        dimensions={
            "skill_fit": FitSignal(
                score=2,
                rationale="Plausible but not proven.",
                missing_info=["Need recent work sample."],
            ),
            "risk": FitSignal(score=4),
        }
    )

    warnings = {(warning["code"], warning["dimension"]) for warning in result.warnings}
    assert ("missing_evidence", "skill_fit") in warnings
    assert ("missing_info", "skill_fit") in warnings
    assert ("low_dimension_score", "skill_fit") in warnings
    assert ("missing_evidence", "risk") in warnings
    assert ("low_dimension_score", "risk") in warnings


def test_build_fit_snapshot_accepts_plain_dict_signals() -> None:
    result = build_fit_snapshot(
        dimensions={
            "skill_fit": {"score": 3, "rationale": "Partial evidence."},
            "risk": {"score": 2, "rationale": "Some process risk."},
        },
        missing_info=["Confirm compensation."],
    )

    assert result.snapshot.dimensions["skill_fit"].score == 3
    assert result.snapshot.missing_info == ["Confirm compensation."]
