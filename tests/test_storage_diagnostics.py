from __future__ import annotations

import pytest

from deal_intel.storage.diagnostics import classify_storage_error, storage_error_hint


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
    assert hint["diagnostic_command"] == "deal-intel config doctor"
    assert hint["next_actions"]
    serialized = str(hint)
    assert "mongodb+srv" not in serialized
    assert "super-secret" not in serialized
