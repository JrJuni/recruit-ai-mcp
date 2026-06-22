from __future__ import annotations


def storage_error_hint(exc: Exception, *, operation: str) -> dict[str, object]:
    """Return a secret-safe, user-actionable hint for Mongo/storage failures."""

    likely_issue = classify_storage_error(exc)
    next_actions = [
        "Run `recruit-ai config doctor` to check profile, storage, and MongoDB readiness.",
        "Verify MONGODB_URI is configured for the environment running this MCP server.",
        "Check MongoDB Atlas Network Access/IP allowlist, credentials, and cluster status.",
        "If Atlas is resuming, upgrading, or selecting a new primary, wait briefly and retry.",
    ]
    if likely_issue == "missing_mongodb_uri":
        next_actions = [
            "Set MONGODB_URI in .env or in the host MCP configuration.",
            "Run `recruit-ai config doctor` to confirm the full/pro MongoDB profile is ready.",
            "Use `recruit-ai config show` to confirm which profile and storage backend are active.",
        ]
    elif likely_issue == "authentication_or_authorization":
        next_actions = [
            "Verify the MongoDB username, password, and database user permissions.",
            "Confirm the URI is being supplied to the same Python runtime used by the MCP server.",
            "Run `recruit-ai config doctor` after updating credentials.",
        ]
    elif likely_issue == "dns_or_network":
        next_actions = [
            "Check internet/VPN/DNS connectivity from this machine.",
            "Verify the Atlas cluster hostname and Network Access/IP allowlist.",
            "Run `recruit-ai config doctor` and retry after transient DNS or network recovery.",
        ]
    elif likely_issue == "atlas_failover_or_cluster_unavailable":
        next_actions = [
            "Wait 30-60 seconds for Atlas resume, upgrade, or failover to finish.",
            "Check the Atlas cluster status page/metrics for primary election or maintenance.",
            "Run `recruit-ai config doctor` and retry the export.",
        ]

    return {
        "operation": operation,
        "likely_issue": likely_issue,
        "diagnostic_command": "recruit-ai config doctor",
        "next_actions": next_actions,
        "safe_detail": (
            "Original storage errors may contain environment-specific details; "
            "this hint intentionally omits URIs, API keys, tokens, and raw credentials."
        ),
    }


def classify_storage_error(exc: Exception) -> str:
    """Classify common storage failures without returning the original message."""

    text = f"{type(exc).__name__}: {exc}".lower()
    if "mongodb_uri" in text and ("not set" in text or "missing" in text):
        return "missing_mongodb_uri"
    if any(
        marker in text
        for marker in (
            "authenticationfailed",
            "auth failed",
            "authentication failed",
            "bad auth",
            "not authorized",
            "unauthorized",
            "permission denied",
            "commandnotfound",
        )
    ):
        return "authentication_or_authorization"
    if any(
        marker in text
        for marker in (
            "replicasetnoprimary",
            "no primary",
            "not primary",
            "node is recovering",
            "interruptedatshutdown",
            "shutdown in progress",
        )
    ):
        return "atlas_failover_or_cluster_unavailable"
    if any(
        marker in text
        for marker in (
            "dns",
            "getaddrinfo",
            "name or service not known",
            "nodename nor servname",
            "connection refused",
            "connection reset",
            "timed out",
            "timeout",
            "network is unreachable",
            "temporary failure in name resolution",
        )
    ):
        return "dns_or_network"
    return "storage_access"


def local_sample_mode_hint() -> dict[str, str]:
    """Return the standard hint for entering MongoDB-free sample mode."""

    return {
        "offer": (
            "MongoDB URI is missing. Ask the user: 'Do you want to continue "
            "in zero-config sample mode for now, or set up MongoDB Atlas for "
            "the normal full mode?'"
        ),
        "purpose": (
            "Use the bundled sample dataset when MongoDB Atlas is not configured "
            "yet. The bundled fixture is immutable; user-created local personal "
            "deals are stored separately under storage.local_data_dir."
        ),
        "temporary_env": "RECRUIT_AI_STORAGE_BACKEND=local_sample",
        "powershell": "$env:RECRUIT_AI_STORAGE_BACKEND='local_sample'",
        "user_config_path": "~/.recruit-ai/config.yaml",
        "user_config": "storage:\n  backend: local_sample",
        "diagnostic_command": "recruit-ai storage-status",
    }


def mongodb_atlas_setup_hint() -> dict[str, object]:
    """Return a secret-safe first-time Atlas setup hint."""

    return {
        "purpose": "Full mode stores real deal data in the user's MongoDB Atlas project.",
        "steps": [
            "Create or sign in to a MongoDB Atlas account.",
            "Create a Free/M0 cluster.",
            "Create a database user with read/write access.",
            "Add the current IP address under Network Access.",
            "Open Connect -> Drivers and copy the connection string.",
            (
                "Replace <password> locally and provide the URI through MCPB, "
                ".env, or a shell environment variable."
            ),
        ],
        "atlas_signup_url": "https://www.mongodb.com/cloud/atlas/register",
        "free_cluster_guide_url": "https://www.mongodb.com/docs/atlas/tutorial/deploy-free-tier-cluster/",
        "secret_handling": (
            "The connection string usually contains a password. Do not paste it "
            "into chat or docs; enter it in the MCPB form, .env, or local shell."
        ),
    }


def missing_mongodb_uri_message() -> str:
    return (
        "MONGODB_URI is not set for storage.backend=mongo. "
        "Set MONGODB_URI in .env for Atlas-backed storage, or switch to "
        "local sample mode with RECRUIT_AI_STORAGE_BACKEND=local_sample."
    )


def missing_mongodb_uri_ping(*, database: str) -> dict:
    return {
        "status": "missing_uri",
        "storage_backend": "mongo",
        "database": database,
        "message": missing_mongodb_uri_message(),
        "fix": "Set MONGODB_URI in .env (see .env.example).",
        "sample_mode_hint": local_sample_mode_hint(),
    }
