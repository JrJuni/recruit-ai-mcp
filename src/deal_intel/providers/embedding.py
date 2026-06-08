from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from importlib.util import find_spec


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]: ...

    @property
    @abstractmethod
    def dimensions(self) -> int: ...

    @property
    def is_ready(self) -> bool:
        """True once the model is loaded and embed() will return immediately."""
        return True

    @property
    def load_error(self) -> str | None:
        """Background warmup failure, if any."""
        return None

    @property
    def warmup_status(self) -> dict:
        return {"phase": "ready", "elapsed_seconds": 0.0}

    def warmup(self) -> None:
        """Pre-load model so the first embed() call is fast. Safe to call from any thread."""
        self.embed("warmup")


class SentenceTransformerProvider(EmbeddingProvider):
    """Local embedding via sentence-transformers — no API key required."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model = None
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._load_error: str | None = None
        self._created_at = time.monotonic()
        self._warmup_started_at: float | None = None
        self._warmup_phase = "not_started"

    @property
    def is_ready(self) -> bool:
        return self._ready.is_set()

    @property
    def load_error(self) -> str | None:
        return self._load_error

    @property
    def warmup_status(self) -> dict:
        started_at = self._warmup_started_at or self._created_at
        elapsed = time.monotonic() - started_at
        return {
            "phase": self._warmup_phase,
            "elapsed_seconds": round(elapsed, 1),
        }

    def _get_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:  # double-checked locking
                    self._warmup_phase = "importing_sentence_transformers"
                    from sentence_transformers import SentenceTransformer
                    self._warmup_phase = "loading_model"
                    self._model = SentenceTransformer(self._model_name, device="cpu")
                    self._warmup_phase = "model_loaded"
        return self._model

    def warmup(self) -> None:
        self._warmup_started_at = time.monotonic()
        self._warmup_phase = "starting"
        try:
            super().warmup()
        except Exception as exc:
            self._warmup_phase = "failed"
            self._load_error = f"{type(exc).__name__}: {exc}"
            raise

    def embed(self, text: str) -> list[float]:
        model = self._get_model()
        self._warmup_phase = "encoding"
        vec = model.encode(text, normalize_embeddings=True)
        self._warmup_phase = "ready"
        self._ready.set()
        return vec.tolist()

    @property
    def dimensions(self) -> int:
        return 384  # all-MiniLM-L6-v2


def make_embedding_provider(cfg: dict) -> EmbeddingProvider | None:
    """Return embedding provider, or None if sentence-transformers not installed."""
    if find_spec("sentence_transformers") is None:
        return None
    model = cfg.get("embedding", {}).get("model", "all-MiniLM-L6-v2")
    return SentenceTransformerProvider(model)
