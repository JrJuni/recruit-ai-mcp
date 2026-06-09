from __future__ import annotations

from deal_intel import _env


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
