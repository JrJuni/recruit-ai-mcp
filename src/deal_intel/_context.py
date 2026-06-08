"""Process-level lazy singletons. All tool handlers go through here."""
from __future__ import annotations

from deal_intel import _env
from deal_intel.providers import llm as _llm
from deal_intel.storage.mongodb import MongoDBClient

_config: dict | None = None
_llm_provider: _llm.LLMProvider | None = None
_mongo: MongoDBClient | None = None


def config() -> dict:
    global _config
    if _config is None:
        _config = _env.load_config()
    return _config


def llm_provider() -> _llm.LLMProvider:
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = _llm.make_llm_provider(config())
    return _llm_provider


def mongo() -> MongoDBClient:
    global _mongo
    if _mongo is None:
        cfg = config()
        db_name = cfg.get("mongodb", {}).get("database", "deal_intel")
        _mongo = MongoDBClient(database=db_name)
    return _mongo
