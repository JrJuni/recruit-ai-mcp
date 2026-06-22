from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

EXPECTED_CONTRACT = {
    "ok": True,
    "question_count": 13,
    "candidate_count": 8,
    "written_record_count": 27,
    "reloaded_record_count": 27,
    "guardrail_candidate_count": 4,
    "open_position_count": 2,
    "positions_with_shortlist": 2,
}


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    questions = {item["id"]: item for item in payload["questions"]}
    metrics = questions["rq01_recruiting_pipeline_metrics"]["payload"]["summary"]
    persistence = questions["rq11_local_recruiting_persistence"]["payload"]["summary"]
    guardrails = questions["rq12_recommendation_guardrails"]["payload"]["summary"]
    shortlist = questions["rq13_client_shortlist_readiness"]["payload"]["summary"]
    actual = {
        "ok": payload["ok"],
        "question_count": payload["question_count"],
        "candidate_count": metrics["candidate_count"],
        "written_record_count": persistence["written_record_count"],
        "reloaded_record_count": persistence["reloaded_record_count"],
        "guardrail_candidate_count": guardrails["guardrail_candidate_count"],
        "open_position_count": shortlist["open_position_count"],
        "positions_with_shortlist": shortlist["positions_with_shortlist"],
    }
    if actual != EXPECTED_CONTRACT:
        raise ValueError(
            "Recruiting natural-question smoke contract mismatch: "
            f"expected={EXPECTED_CONTRACT!r}, actual={actual!r}"
        )
    return actual


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
