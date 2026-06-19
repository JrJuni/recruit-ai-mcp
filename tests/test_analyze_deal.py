from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from deal_intel.product_context import index_product_context
from deal_intel.tools import analyze_deal


class FakeLLM:
    def __init__(self, text: str = "Generated BD strategy.") -> None:
        self.text = text
        self.calls: list[dict] = []

    def chat_once(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            text=self.text,
            usage={"input_tokens": 20, "output_tokens": 7},
        )


class FakeMongo:
    def __init__(self, deal: dict) -> None:
        self.deal = deepcopy(deal)
        self.saved: dict | None = None

    def get_deal(self, deal_id: str) -> dict | None:
        if self.deal.get("deal_id") != deal_id:
            return None
        return deepcopy(self.deal)

    def upsert_deal(self, deal: dict) -> None:
        self.saved = deepcopy(deal)
        self.deal = deepcopy(deal)


class KeywordEmbedding:
    dimensions = 3
    is_ready = True
    load_error = None
    warmup_status = {"phase": "ready", "elapsed_seconds": 0.0}

    def __init__(self) -> None:
        self.calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        lowered = text.lower()
        return [
            1.0 if any(word in lowered for word in ("hipaa", "security")) else 0.0,
            1.0 if "pricing" in lowered else 0.0,
            1.0 if "workflow" in lowered else 0.0,
        ]


class LoadingEmbedding:
    dimensions = 3
    is_ready = False
    load_error = None
    warmup_status = {"phase": "loading_model", "elapsed_seconds": 3.0}

    def embed(self, text: str) -> list[float]:
        raise AssertionError("loading embedding must not be used")


def setup_function() -> None:
    analyze_deal.clear_analysis_cache()


def _cfg(tmp_path) -> dict:
    return {
        "llm": {"provider": "chatgpt_oauth"},
        "product_context": {
            "source_dirs": [str(tmp_path / "sources")],
            "cache_dir": str(tmp_path / "cache"),
            "retrieval": {"top_k": 2, "max_context_chars": 2000},
        },
    }


def _deal() -> dict:
    return {
        "deal_id": "deal-1",
        "company": "Acme Health",
        "industry": "Healthcare",
        "customer_segment": "mid_market",
        "deal_stage": "proposal",
        "deal_size_amount": 50_000_000,
        "deal_size_currency": "KRW",
        "customer_themes": [
            {
                "label": "security posture",
                "dimension": "decision_criteria",
                "evidence": "HIPAA audit readiness is part of the buying criteria.",
            }
        ],
        "interactions": [
            {
                "interaction_id": "i-1",
                "date": "2026-06-10",
                "interaction_type": "meeting",
                "direction": "inbound",
                "source_confidence": "customer_stated",
                "summary": "Customer asked how HIPAA security evidence is exported.",
                "meddpicc": {
                    "identify_pain": {
                        "score": 4,
                        "evidence": "HIPAA audit preparation is still manual.",
                    }
                },
            }
        ],
        "meetings": [],
    }


def test_analyze_deal_uses_product_context_without_storing_raw_context(
    tmp_path,
) -> None:
    cfg = _cfg(tmp_path)
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "healthcare-security.md").write_text(
        "Product supports HIPAA security evidence exports and audit-log review.",
        encoding="utf-8",
    )
    index_product_context(cfg, embedding_provider=KeywordEmbedding(), dry_run=False)
    mongo = FakeMongo(_deal())
    llm = FakeLLM()

    result = analyze_deal.handle(
        mongo=mongo,
        llm=llm,
        cfg=cfg,
        embedding_provider=KeywordEmbedding(),
        deal_id="deal-1",
    )

    assert result["ok"] is True
    assert result["product_context_used"] is True
    assert result["product_context_ref_count"] == 1
    assert result["product_context_refs"][0]["source_name"] == "healthcare-security.md"
    prompt = llm.calls[0]["user"]
    assert "Seller/product context:" in prompt
    assert "Do not treat it as customer-stated evidence." in prompt
    assert "HIPAA security evidence exports" in prompt
    assert result["persist_strategy"] is False
    assert result["storage_written"] is False
    assert result["cache_hit"] is False
    assert mongo.saved is None


def test_analyze_deal_without_product_context_keeps_existing_prompt(tmp_path) -> None:
    cfg = _cfg(tmp_path)
    mongo = FakeMongo(_deal())
    llm = FakeLLM()

    result = analyze_deal.handle(
        mongo=mongo,
        llm=llm,
        cfg=cfg,
        embedding_provider=None,
        deal_id="deal-1",
    )

    assert result["ok"] is True
    assert result["product_context_used"] is False
    assert result["product_context_ref_count"] == 0
    assert "Seller/product context:" not in llm.calls[0]["user"]
    assert mongo.saved is None


def test_analyze_deal_skips_product_context_when_embedding_is_loading(
    tmp_path,
) -> None:
    cfg = _cfg(tmp_path)
    mongo = FakeMongo(_deal())
    llm = FakeLLM()

    result = analyze_deal.handle(
        mongo=mongo,
        llm=llm,
        cfg=cfg,
        embedding_provider=LoadingEmbedding(),
        deal_id="deal-1",
    )

    assert result["ok"] is True
    assert result["product_context_used"] is False
    assert result["product_context_ref_count"] == 0
    assert result["embedding_status"]["state"] == "loading"
    assert result["product_context_status"]["state"] == "embedding_loading"
    assert result["warnings"][0]["code"] == "product_context_embedding_not_ready"
    assert "Seller/product context:" not in llm.calls[0]["user"]
    assert mongo.saved is None


def test_analyze_deal_confirmed_persist_writes_strategy(tmp_path) -> None:
    cfg = _cfg(tmp_path)
    mongo = FakeMongo(_deal())
    llm = FakeLLM()

    result = analyze_deal.handle(
        mongo=mongo,
        llm=llm,
        cfg=cfg,
        embedding_provider=None,
        deal_id="deal-1",
        persist_strategy=True,
        confirmed_by_user=True,
    )

    assert result["ok"] is True
    assert result["persist_strategy"] is True
    assert result["storage_written"] is True
    assert result["cache_hit"] is False
    assert mongo.saved is not None
    assert mongo.saved["bd_strategy"] == "Generated BD strategy."
    assert mongo.saved["bd_strategy_usage"]["source_tool"] == "analyze_deal"


def test_analyze_deal_requires_confirmation_before_persist(tmp_path) -> None:
    cfg = _cfg(tmp_path)
    mongo = FakeMongo(_deal())
    llm = FakeLLM()

    with pytest.raises(Exception) as exc_info:
        analyze_deal.handle(
            mongo=mongo,
            llm=llm,
            cfg=cfg,
            embedding_provider=None,
            deal_id="deal-1",
            persist_strategy=True,
        )

    assert getattr(exc_info.value, "error_code") == "INVALID_INPUT"
    assert llm.calls == []
    assert mongo.saved is None


def test_analyze_deal_cache_avoids_repeated_llm_calls(tmp_path) -> None:
    cfg = _cfg(tmp_path)
    mongo = FakeMongo(_deal())
    llm = FakeLLM()

    first = analyze_deal.handle(
        mongo=mongo,
        llm=llm,
        cfg=cfg,
        embedding_provider=None,
        deal_id="deal-1",
    )
    second = analyze_deal.handle(
        mongo=mongo,
        llm=llm,
        cfg=cfg,
        embedding_provider=None,
        deal_id="deal-1",
    )

    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert second["usage_summary"]["totals"]["total_tokens"] == 0
    assert len(llm.calls) == 1
    assert mongo.saved is None


def test_analyze_deal_force_bypasses_cache(tmp_path) -> None:
    cfg = _cfg(tmp_path)
    mongo = FakeMongo(_deal())
    llm = FakeLLM()

    analyze_deal.handle(
        mongo=mongo,
        llm=llm,
        cfg=cfg,
        embedding_provider=None,
        deal_id="deal-1",
    )
    result = analyze_deal.handle(
        mongo=mongo,
        llm=llm,
        cfg=cfg,
        embedding_provider=None,
        deal_id="deal-1",
        force=True,
    )

    assert result["cache_hit"] is False
    assert result["force"] is True
    assert len(llm.calls) == 2


def test_analyze_deal_can_persist_from_cache_without_second_llm_call(tmp_path) -> None:
    cfg = _cfg(tmp_path)
    mongo = FakeMongo(_deal())
    llm = FakeLLM()

    analyze_deal.handle(
        mongo=mongo,
        llm=llm,
        cfg=cfg,
        embedding_provider=None,
        deal_id="deal-1",
    )
    result = analyze_deal.handle(
        mongo=mongo,
        llm=llm,
        cfg=cfg,
        embedding_provider=None,
        deal_id="deal-1",
        persist_strategy=True,
        confirmed_by_user=True,
    )

    assert result["cache_hit"] is True
    assert result["storage_written"] is True
    assert len(llm.calls) == 1
    assert mongo.saved is not None
    assert mongo.saved["bd_strategy"] == "Generated BD strategy."
    assert mongo.saved["bd_strategy_usage"]["source_tool"] == "analyze_deal"


def test_analyze_deal_llm_errors_are_not_retryable(tmp_path) -> None:
    class FailingLLM:
        def chat_once(self, **_kwargs):
            raise RuntimeError("provider unavailable")

    with pytest.raises(Exception) as exc_info:
        analyze_deal.handle(
            mongo=FakeMongo(_deal()),
            llm=FailingLLM(),
            cfg=_cfg(tmp_path),
            embedding_provider=None,
            deal_id="deal-1",
        )

    assert getattr(exc_info.value, "error_code") == "LLM_ERROR"
    assert getattr(exc_info.value, "retryable") is False
