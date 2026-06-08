"""Process-level lazy singletons. All tool handlers go through here."""
from __future__ import annotations

import threading

from deal_intel import _env
from deal_intel.providers import llm as _llm
from deal_intel.providers.embedding import EmbeddingProvider, make_embedding_provider
from deal_intel.storage.mongodb import MongoDBClient

_config: dict | None = None
_llm_provider: _llm.LLMProvider | None = None
_mongo: MongoDBClient | None = None
_embedding_provider: EmbeddingProvider | None = None
_embedding_initialized: bool = False
_mongo_lock = threading.Lock()
_embedding_lock = threading.Lock()


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


def embedding_provider() -> EmbeddingProvider | None:
    global _embedding_provider, _embedding_initialized
    if not _embedding_initialized:
        with _embedding_lock:
            if not _embedding_initialized:
                _embedding_provider = make_embedding_provider(config())
                _embedding_initialized = True
    return _embedding_provider


def mongo() -> MongoDBClient:
    global _mongo
    if _mongo is None:
        with _mongo_lock:
            if _mongo is None:
                cfg = config()
                db_name = cfg.get("mongodb", {}).get("database", "deal_intel")
                _mongo = MongoDBClient(database=db_name)
    return _mongo
