from __future__ import annotations

from importlib import resources
from pathlib import Path

from deal_intel import _env

ROOT = Path(__file__).resolve().parents[1]


def test_load_config_accepts_explicit_llm_provider_env(monkeypatch, tmp_path) -> None:
    root = tmp_path
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "defaults.yaml").write_text(
        "llm:\n  provider: chatgpt_oauth\n",
        encoding="utf-8",
    )
    missing_user_config = tmp_path / "missing" / "config.yaml"
    monkeypatch.setattr(_env, "_ROOT", root)
    monkeypatch.setattr(_env, "_USER_CONFIG_PATH", missing_user_config)
    monkeypatch.setenv("DEAL_INTEL_LLM_PROVIDER", "openai_api")
    monkeypatch.setenv("DEAL_INTEL_USE_CHATGPT_OAUTH", "true")

    config = _env.load_config()

    assert config["llm"]["provider"] == "openai_api"


def test_load_config_preserves_legacy_oauth_env_override(monkeypatch, tmp_path) -> None:
    root = tmp_path
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "defaults.yaml").write_text(
        "llm:\n  provider: openai_api\n",
        encoding="utf-8",
    )
    missing_user_config = tmp_path / "missing" / "config.yaml"
    monkeypatch.setattr(_env, "_ROOT", root)
    monkeypatch.setattr(_env, "_USER_CONFIG_PATH", missing_user_config)
    monkeypatch.delenv("DEAL_INTEL_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("DEAL_INTEL_USE_CHATGPT_OAUTH", "false")

    config = _env.load_config()

    assert config["llm"]["provider"] == "anthropic"


def test_load_config_accepts_reporting_language_env(monkeypatch, tmp_path) -> None:
    root = tmp_path
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "defaults.yaml").write_text(
        "reporting:\n  language: en\n",
        encoding="utf-8",
    )
    missing_user_config = tmp_path / "missing" / "config.yaml"
    monkeypatch.setattr(_env, "_ROOT", root)
    monkeypatch.setattr(_env, "_USER_CONFIG_PATH", missing_user_config)
    monkeypatch.setenv("DEAL_INTEL_REPORTING_LANGUAGE", "ko")

    config = _env.load_config()

    assert config["reporting"]["language"] == "ko"


def test_load_config_accepts_product_context_source_dirs_env(monkeypatch, tmp_path) -> None:
    root = tmp_path
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "defaults.yaml").write_text(
        "product_context:\n"
        "  source_dirs:\n"
        "    - ~/.deal-intel/product-context/sources\n",
        encoding="utf-8",
    )
    missing_user_config = tmp_path / "missing" / "config.yaml"
    monkeypatch.setattr(_env, "_ROOT", root)
    monkeypatch.setattr(_env, "_USER_CONFIG_PATH", missing_user_config)
    monkeypatch.setenv(
        "DEAL_INTEL_PRODUCT_CONTEXT_SOURCE_DIRS",
        "~/company-docs;~/solution-docs",
    )

    config = _env.load_config()

    assert config["product_context"]["source_dirs"] == [
        "~/company-docs",
        "~/solution-docs",
    ]


def test_load_config_ignores_secret_like_product_context_source_dirs_env(
    monkeypatch,
    tmp_path,
) -> None:
    root = tmp_path
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "defaults.yaml").write_text(
        "product_context:\n"
        "  source_dirs:\n"
        "    - ~/.deal-intel/product-context/sources\n",
        encoding="utf-8",
    )
    missing_user_config = tmp_path / "missing" / "config.yaml"
    monkeypatch.setattr(_env, "_ROOT", root)
    monkeypatch.setattr(_env, "_USER_CONFIG_PATH", missing_user_config)
    monkeypatch.setenv(
        "DEAL_INTEL_PRODUCT_CONTEXT_SOURCE_DIRS",
        "~/company-docs;mongodb+srv://secret.example",
    )

    config = _env.load_config()

    assert config["product_context"]["source_dirs"] == ["~/company-docs"]


def test_load_config_accepts_product_context_limit_env(monkeypatch, tmp_path) -> None:
    root = tmp_path
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "defaults.yaml").write_text(
        "product_context:\n"
        "  max_source_file_mb: 100\n"
        "  max_chunks_per_file: 2000\n"
        "  max_chunks_per_run: 8000\n",
        encoding="utf-8",
    )
    missing_user_config = tmp_path / "missing" / "config.yaml"
    monkeypatch.setattr(_env, "_ROOT", root)
    monkeypatch.setattr(_env, "_USER_CONFIG_PATH", missing_user_config)
    monkeypatch.setenv("DEAL_INTEL_PRODUCT_CONTEXT_MAX_SOURCE_FILE_MB", "250")
    monkeypatch.setenv("DEAL_INTEL_PRODUCT_CONTEXT_MAX_CHUNKS_PER_FILE", "5000")
    monkeypatch.setenv("DEAL_INTEL_PRODUCT_CONTEXT_MAX_CHUNKS_PER_RUN", "12000")

    config = _env.load_config()

    assert config["product_context"]["max_source_file_mb"] == 250
    assert config["product_context"]["max_chunks_per_file"] == 5000
    assert config["product_context"]["max_chunks_per_run"] == 12000


def test_load_config_ignores_invalid_product_context_limit_env(
    monkeypatch,
    tmp_path,
) -> None:
    root = tmp_path
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "defaults.yaml").write_text(
        "product_context:\n"
        "  max_source_file_mb: 100\n",
        encoding="utf-8",
    )
    missing_user_config = tmp_path / "missing" / "config.yaml"
    monkeypatch.setattr(_env, "_ROOT", root)
    monkeypatch.setattr(_env, "_USER_CONFIG_PATH", missing_user_config)
    monkeypatch.setenv("DEAL_INTEL_PRODUCT_CONTEXT_MAX_SOURCE_FILE_MB", "9999")

    config = _env.load_config()

    assert config["product_context"]["max_source_file_mb"] == 100


def test_packaged_defaults_match_repo_defaults() -> None:
    packaged = (
        resources.files("deal_intel.resources")
        .joinpath("defaults.yaml")
        .read_text(encoding="utf-8")
    )
    repo = (ROOT / "config" / "defaults.yaml").read_text(encoding="utf-8")

    assert packaged == repo


def test_load_config_falls_back_to_packaged_defaults(monkeypatch, tmp_path) -> None:
    missing_repo_root = tmp_path / "missing-repo-root"
    missing_user_config = tmp_path / "missing" / "config.yaml"
    monkeypatch.setattr(_env, "_ROOT", missing_repo_root)
    monkeypatch.setattr(_env, "_USER_CONFIG_PATH", missing_user_config)
    monkeypatch.delenv("DEAL_INTEL_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("DEAL_INTEL_USE_CHATGPT_OAUTH", raising=False)
    monkeypatch.delenv("DEAL_INTEL_STORAGE_BACKEND", raising=False)
    monkeypatch.delenv("DEAL_INTEL_TOOLS_SURFACE", raising=False)
    monkeypatch.delenv("DEAL_INTEL_REPORTING_LANGUAGE", raising=False)
    monkeypatch.delenv("DEAL_INTEL_PRODUCT_CONTEXT_SOURCE_DIRS", raising=False)

    config = _env.load_config()

    assert config["llm"]["provider"] == "chatgpt_oauth"
    assert config["storage"]["backend"] == "mongo"
    assert config["mongodb"]["database"] == "deal_intel"
