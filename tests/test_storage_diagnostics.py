from __future__ import annotations

import pytest

from deal_intel.storage.diagnostics import (
    classify_storage_error,
    local_sample_mode_hint,
    mongodb_atlas_setup_hint,
    storage_error_hint,
)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("MONGODB_URI is not set for storage.backend=mongo", "missing_mongodb_uri"),
        ("AuthenticationFailed: bad auth", "authentication_or_authorization"),
        ("ReplicaSetNoPrimary: No primary available", "atlas_failover_or_cluster_unavailable"),
        ("ServerSelectionTimeoutError: getaddrinfo failed", "dns_or_network"),
        ("socket timeout while connecting", "dns_or_network"),
        ("unknown storage read failure", "storage_access"),
    ],
)
def test_classify_storage_error(message: str, expected: str) -> None:
    assert classify_storage_error(RuntimeError(message)) == expected


def test_storage_error_hint_is_actionable_and_secret_safe() -> None:
    exc = RuntimeError(
        "ServerSelectionTimeoutError: mongodb+srv://user:super-secret@example.mongodb.net timed out"
    )

    hint = storage_error_hint(exc, operation="export_report.weekly_pipeline.read_deals")

    assert hint["operation"] == "export_report.weekly_pipeline.read_deals"
    assert hint["diagnostic_command"] == "recruit-ai config doctor"
    assert hint["next_actions"]
    serialized = str(hint)
    assert "mongodb+srv" not in serialized
    assert "super-secret" not in serialized


def test_atlas_setup_hint_is_recruiting_first() -> None:
    hint = mongodb_atlas_setup_hint()

    assert "real recruiting/team data" in hint["purpose"]
    assert "real deal data" not in hint["purpose"]


def test_local_sample_hint_mentions_recruiting_records() -> None:
    hint = local_sample_mode_hint()

    assert "recruiting records" in hint["purpose"]
    assert "compatibility deal records" in hint["purpose"]
    assert "user-created local personal deals are stored" not in hint["purpose"]
    assert hint["temporary_env"] == "RECRUIT_AI_STORAGE_BACKEND=local_sample"
    assert hint["user_config_path"] == "~/.recruit-ai/config.yaml"
