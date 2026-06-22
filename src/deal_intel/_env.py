from __future__ import annotations

import os
from importlib import resources
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]  # src/deal_intel → src → repo root
load_dotenv(_ROOT / ".env", override=False)

_USER_CONFIG_PATH = Path.home() / ".recruit-ai" / "config.yaml"
_VALID_STORAGE_BACKENDS = {"mongo", "local_sample"}
_VALID_TOOL_SURFACES = {"auto", "sample", "standard", "developer"}
_VALID_REPORT_LANGUAGES = {"en", "ko"}


def user_config_path() -> Path:
    return _USER_CONFIG_PATH


def load_config() -> dict:
    import yaml

    config: dict = {}
    defaults_path = _ROOT / "config" / "defaults.yaml"
    if defaults_path.exists():
        with open(defaults_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    else:
        defaults_text = (
            resources.files("deal_intel.resources")
            .joinpath("defaults.yaml")
            .read_text(encoding="utf-8")
        )
        config = yaml.safe_load(defaults_text) or {}

    if _USER_CONFIG_PATH.exists():
        with open(_USER_CONFIG_PATH, encoding="utf-8") as f:
            user = yaml.safe_load(f) or {}
        _deep_merge(config, user)

    # mcpb user_config env override. RECRUIT_AI_* is the primary prefix;
    # DEAL_INTEL_* remains a compatibility fallback for older bundles.
    provider_env = _env_value("RECRUIT_AI_LLM_PROVIDER", "DEAL_INTEL_LLM_PROVIDER")
    if provider_env in {"chatgpt_oauth", "anthropic", "openai_api"}:
        config.setdefault("llm", {})["provider"] = provider_env
    else:
        # "true"/"1" -> chatgpt_oauth, "false"/"0" -> anthropic.
        _oauth_env = _env_value(
            "RECRUIT_AI_USE_CHATGPT_OAUTH",
            "DEAL_INTEL_USE_CHATGPT_OAUTH",
        ).lower()
        if _oauth_env in ("true", "1"):
            config.setdefault("llm", {})["provider"] = "chatgpt_oauth"
        elif _oauth_env in ("false", "0"):
            config.setdefault("llm", {})["provider"] = "anthropic"

    storage_backend_env = _env_value(
        "RECRUIT_AI_STORAGE_BACKEND",
        "DEAL_INTEL_STORAGE_BACKEND",
    )
    if storage_backend_env in _VALID_STORAGE_BACKENDS:
        config.setdefault("storage", {})["backend"] = storage_backend_env

    tool_surface_env = _env_value("RECRUIT_AI_TOOLS_SURFACE", "DEAL_INTEL_TOOLS_SURFACE")
    if tool_surface_env in _VALID_TOOL_SURFACES:
        config.setdefault("tools", {})["surface"] = tool_surface_env

    reporting_language_env = _env_value(
        "RECRUIT_AI_REPORTING_LANGUAGE",
        "DEAL_INTEL_REPORTING_LANGUAGE",
    )
    if reporting_language_env in _VALID_REPORT_LANGUAGES:
        config.setdefault("reporting", {})["language"] = reporting_language_env

    source_dirs_env = _env_value(
        "RECRUIT_AI_PRODUCT_CONTEXT_SOURCE_DIRS",
        "DEAL_INTEL_PRODUCT_CONTEXT_SOURCE_DIRS",
    )
    if source_dirs_env:
        source_dirs = [
            item.strip()
            for item in source_dirs_env.split(";")
            if item.strip() and not _looks_secret_like(item.strip())
        ]
        if source_dirs:
            config.setdefault("product_context", {})["source_dirs"] = source_dirs

    _apply_product_context_int_env(
        config,
        "RECRUIT_AI_PRODUCT_CONTEXT_MAX_SOURCE_FILE_MB",
        "DEAL_INTEL_PRODUCT_CONTEXT_MAX_SOURCE_FILE_MB",
        "max_source_file_mb",
        minimum=1,
        maximum=500,
    )
    _apply_product_context_int_env(
        config,
        "RECRUIT_AI_PRODUCT_CONTEXT_MAX_NOTE_MB",
        "DEAL_INTEL_PRODUCT_CONTEXT_MAX_NOTE_MB",
        "max_note_mb",
        minimum=1,
        maximum=20,
    )
    _apply_product_context_int_env(
        config,
        "RECRUIT_AI_PRODUCT_CONTEXT_MAX_CHUNKS_PER_FILE",
        "DEAL_INTEL_PRODUCT_CONTEXT_MAX_CHUNKS_PER_FILE",
        "max_chunks_per_file",
        minimum=10,
        maximum=20000,
    )
    _apply_product_context_int_env(
        config,
        "RECRUIT_AI_PRODUCT_CONTEXT_MAX_CHUNKS_PER_RUN",
        "DEAL_INTEL_PRODUCT_CONTEXT_MAX_CHUNKS_PER_RUN",
        "max_chunks_per_run",
        minimum=10,
        maximum=50000,
    )

    return config


def _env_value(primary: str, legacy: str) -> str:
    value = os.environ.get(primary, "").strip()
    if value:
        return value
    return os.environ.get(legacy, "").strip()


def _deep_merge(base: dict, override: dict) -> None:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def _looks_secret_like(value: str) -> bool:
    lowered = value.lower()
    return (
        "mongodb://" in lowered
        or "mongodb+srv://" in lowered
        or value.startswith(("sk-", "sk_", "xoxb-", "ghp_"))
    )


def _apply_product_context_int_env(
    config: dict,
    primary_env_name: str,
    env_name: str,
    field: str,
    *,
    minimum: int,
    maximum: int,
) -> None:
    raw = _env_value(primary_env_name, env_name)
    if not raw:
        return
    try:
        value = int(raw)
    except ValueError:
        return
    if minimum <= value <= maximum:
        config.setdefault("product_context", {})[field] = value
