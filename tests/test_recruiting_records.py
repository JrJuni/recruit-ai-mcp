from __future__ import annotations

from datetime import UTC, datetime

import pytest

from deal_intel.schema.recruiting import CandidateProfile, EvidenceReference
from deal_intel.storage.recruiting_collections import CANDIDATES, INTERACTIONS
from deal_intel.storage.recruiting_records import normalize_recruiting_record


def _fixed_now() -> datetime:
    return datetime(2026, 6, 22, 12, 34, 56, tzinfo=UTC)


def test_normalize_recruiting_record_accepts_pydantic_model() -> None:
    candidate = CandidateProfile(
        candidate_id="cand_avery_chen",
        name="Avery Chen",
        skills=["Python"],
        evidence=[
            EvidenceReference(
                evidence_id="ev_screen_1",
                source_type="interaction",
                source_id="int_screen_1",
                summary="Recent backend leadership.",
            )
        ],
    )

    record = normalize_recruiting_record(CANDIDATES, candidate, now=_fixed_now())

    assert record["candidate_id"] == "cand_avery_chen"
    assert record["preferences"] == {
        "desired_titles": [],
        "preferred_domains": [],
        "preferred_locations": [],
        "remote_preference": "",
        "excluded_companies": [],
        "notes": "",
    }
    assert record["evidence"][0]["source_id"] == "int_screen_1"
    assert record["created_at"] == "2026-06-22T12:34:56+00:00"
    assert record["updated_at"] == "2026-06-22T12:34:56+00:00"


def test_normalize_recruiting_record_strips_mongo_id_and_converts_nested_models() -> None:
    record = normalize_recruiting_record(
        INTERACTIONS,
        {
            "_id": "internal",
            "interaction_id": "int_screen_1",
            "subject_type": "candidate",
            "subject_id": "cand_avery_chen",
            "interaction_type": "candidate_screen",
            "evidence_refs": [
                EvidenceReference(
                    evidence_id="ev_screen_1",
                    source_type="interaction",
                    source_id="int_screen_1",
                )
            ],
            "created_at": "2026-06-01T00:00:00+00:00",
        },
        now=_fixed_now(),
    )

    assert "_id" not in record
    assert record["evidence_refs"][0]["evidence_id"] == "ev_screen_1"
    assert record["created_at"] == "2026-06-01T00:00:00+00:00"
    assert record["updated_at"] == "2026-06-22T12:34:56+00:00"


def test_normalize_recruiting_record_requires_known_collection_id() -> None:
    with pytest.raises(ValueError, match="candidate_id"):
        normalize_recruiting_record(CANDIDATES, {"name": "Missing ID"}, now=_fixed_now())


def test_normalize_recruiting_record_rejects_non_mapping_payload() -> None:
    with pytest.raises(TypeError, match="mapping or Pydantic model"):
        normalize_recruiting_record(CANDIDATES, ["not", "a", "record"], now=_fixed_now())
