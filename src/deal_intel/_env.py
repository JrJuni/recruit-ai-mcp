from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]  # src/deal_intel → src → repo root
load_dotenv(_ROOT / ".env", override=False)

_USER_CONFIG_PATH = Path.home() / ".deal-intel" / "config.yaml"


def load_config() -> dict:
    import yaml

    defaults_path = _ROOT / "config" / "defaults.yaml"
    config: dict = {}
    if defaults_path.exists():
        with open(defaults_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    if _USER_CONFIG_PATH.exists():
        with open(_USER_CONFIG_PATH, encoding="utf-8") as f:
            user = yaml.safe_load(f) or {}
        _deep_merge(config, user)

    return config


def _deep_merge(base: dict, override: dict) -> None:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
