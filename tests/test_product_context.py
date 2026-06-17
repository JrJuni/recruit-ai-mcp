from __future__ import annotations

import json
import zipfile
from xml.sax.saxutils import escape

import pytest

import deal_intel.product_context as product_context
from deal_intel import _context, mcp_server
from deal_intel.errors import ErrorCode, MCPError
from deal_intel.product_context import (
    CHUNKS_FILE,
    MANIFEST_FILE,
    add_product_context_note,
    index_product_context,
    retrieve_product_context,
)


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
            1.0 if any(word in lowered for word in ("security", "soc2", "hipaa")) else 0.0,
            1.0 if any(word in lowered for word in ("pricing", "budget", "package")) else 0.0,
            1.0
            if any(word in lowered for word in ("workflow", "automation", "efficiency"))
            else 0.0,
        ]


def _cfg(tmp_path) -> dict:
    return {
        "product_context": {
            "source_dirs": [str(tmp_path / "sources")],
            "cache_dir": str(tmp_path / "cache"),
            "retrieval": {"top_k": 2, "max_context_chars": 2000},
        }
    }


def _write_docx(path, paragraphs: list[str]) -> None:
    body = "".join(
        "<w:p><w:r><w:t>"
        + escape(paragraph)
        + "</w:t></w:r></w:p>"
        for paragraph in paragraphs
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body>"
        "</w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document)


def test_index_product_context_writes_cache_and_reuses_unchanged_file(tmp_path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "security.md").write_text(
        "# Security\nSupports SOC2 and HIPAA deployment reviews.",
        encoding="utf-8",
    )
    cfg = _cfg(tmp_path)

    first_embedding = KeywordEmbedding()
    first = index_product_context(
        cfg,
        embedding_provider=first_embedding,
        dry_run=False,
    )

    assert first["ok"] is True
    assert first["counts"]["indexed"] == 1
    assert first["storage_written"] is True
    assert first_embedding.calls

    second_embedding = KeywordEmbedding()
    second = index_product_context(
        cfg,
        embedding_provider=second_embedding,
        dry_run=False,
    )

    assert second["ok"] is True
    assert second["counts"]["unchanged"] == 1
    assert second["counts"]["indexed"] == 0
    assert second_embedding.calls == []
    assert (tmp_path / "cache" / MANIFEST_FILE).exists()
    assert (tmp_path / "cache" / CHUNKS_FILE).exists()


def test_add_product_context_note_dry_run_does_not_write(tmp_path) -> None:
    result = add_product_context_note(
        _cfg(tmp_path),
        title="ICP notes",
        content="Target small B2B teams with audit-heavy workflows.",
        source_name="paste",
        dry_run=True,
    )

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["storage_written"] is False
    assert result["source_name"].endswith("-icp-notes.md")
    assert not (tmp_path / "sources" / "managed-notes").exists()
    assert "Target small" not in json.dumps(result, ensure_ascii=False)


def test_add_product_context_note_apply_requires_confirmation(tmp_path) -> None:
    with pytest.raises(MCPError) as exc_info:
        add_product_context_note(
            _cfg(tmp_path),
            title="Pricing",
            content="Pricing packages support annual budgets.",
            dry_run=False,
        )

    assert exc_info.value.error_code == ErrorCode.INVALID_INPUT
    assert "confirmed_by_user" in exc_info.value.message


def test_add_product_context_note_writes_managed_markdown_and_unique_names(
    tmp_path,
) -> None:
    cfg = _cfg(tmp_path)

    first = add_product_context_note(
        cfg,
        title="Pricing / Packaging",
        content="Annual budget packages include security review support.",
        source_name="host paste",
        dry_run=False,
        confirmed_by_user=True,
    )
    second = add_product_context_note(
        cfg,
        title="Pricing / Packaging",
        content="Expansion packages include workflow automation support.",
        source_name="host paste",
        dry_run=False,
        confirmed_by_user=True,
    )

    first_path = tmp_path / "sources" / "managed-notes" / first["source_name"]
    second_path = tmp_path / "sources" / "managed-notes" / second["source_name"]
    assert first_path.exists()
    assert second_path.exists()
    assert first_path != second_path
    text = first_path.read_text(encoding="utf-8")
    assert "deal_intel_managed: true" in text
    assert 'title: "Pricing / Packaging"' in text
    assert "Annual budget packages" in text
    assert "Annual budget packages" not in json.dumps(first, ensure_ascii=False)


def test_add_product_context_note_rejects_secret_empty_and_oversized_content(
    tmp_path,
) -> None:
    with pytest.raises(MCPError) as empty_exc:
        add_product_context_note(_cfg(tmp_path), title="Empty", content=" ")
    assert empty_exc.value.error_code == ErrorCode.INVALID_INPUT

    with pytest.raises(MCPError) as secret_exc:
        add_product_context_note(
            _cfg(tmp_path),
            title="Secret",
            content="OPENAI_API_KEY=sk-abcdefghijklmnop",
        )
    assert secret_exc.value.error_code == ErrorCode.INVALID_INPUT
    assert "openai_key" in secret_exc.value.hint["secret_patterns"]

    with pytest.raises(MCPError) as too_large_exc:
        add_product_context_note(
            _cfg(tmp_path),
            title="Huge",
            content="x" * (product_context.MAX_NOTE_BYTES + 1),
        )
    assert too_large_exc.value.error_code == ErrorCode.INVALID_INPUT


def test_index_product_context_allows_source_larger_than_note_limit(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(product_context, "MAX_NOTE_BYTES", 32)
    monkeypatch.setattr(product_context, "MAX_SOURCE_FILE_BYTES", 4096)
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "large-source.md").write_text(
        "Workflow automation and security positioning. " * 20,
        encoding="utf-8",
    )

    result = product_context.index_product_context(
        _cfg(tmp_path),
        embedding_provider=KeywordEmbedding(),
        dry_run=False,
    )

    assert result["ok"] is True
    assert result["counts"]["indexed"] == 1
    assert result["counts"]["skipped"] == 0


def test_index_product_context_partial_indexes_when_chunk_budget_is_reached(
    tmp_path,
) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    paragraphs = [
        f"Security workflow paragraph {index}. " + ("controls " * 260)
        for index in range(20)
    ]
    (sources / "large-catalog.md").write_text(
        "\n\n".join(paragraphs),
        encoding="utf-8",
    )
    cfg = _cfg(tmp_path)
    cfg["product_context"]["max_chunks_per_file"] = 10

    result = product_context.index_product_context(
        cfg,
        embedding_provider=KeywordEmbedding(),
        dry_run=False,
    )

    assert result["ok"] is True
    assert result["counts"]["indexed"] == 1
    assert result["counts"]["partial_indexed"] == 1
    assert result["counts"]["indexed_chunks"] == 10
    assert result["limits"]["max_chunks_per_file"] == 10
    assert "max_chunks_per_file_reached" in {
        warning["code"] for warning in result["warnings"]
    }
    manifest = json.loads((tmp_path / "cache" / MANIFEST_FILE).read_text())
    doc = next(iter(manifest["documents"].values()))
    assert doc["partial_indexed"] is True
    assert doc["partial_reason"] == "max_chunks_per_file"
    assert doc["chunk_count"] == 10
    assert doc["discovered_chunk_count"] > 10


def test_add_product_context_note_path_traversal_title_stays_in_managed_notes(
    tmp_path,
) -> None:
    result = add_product_context_note(
        _cfg(tmp_path),
        title="../../outside",
        content="Workflow automation context.",
        dry_run=False,
        confirmed_by_user=True,
    )

    note_path = (tmp_path / "sources" / "managed-notes" / result["source_name"]).resolve()
    assert note_path.exists()
    assert note_path.parent == (tmp_path / "sources" / "managed-notes").resolve()
    assert ".." not in result["source_name"]


def test_add_product_context_note_can_be_indexed_and_retrieved(tmp_path) -> None:
    cfg = _cfg(tmp_path)
    add_product_context_note(
        cfg,
        title="Healthcare security positioning",
        content="Healthcare customers care about HIPAA and audit-log security.",
        dry_run=False,
        confirmed_by_user=True,
    )

    index_result = index_product_context(
        cfg,
        embedding_provider=KeywordEmbedding(),
        dry_run=False,
    )
    result = retrieve_product_context(
        cfg,
        embedding_provider=KeywordEmbedding(),
        query="HIPAA security",
        limit=1,
    )

    assert index_result["counts"]["indexed"] == 1
    assert result["ok"] is True
    assert result["result_count"] == 1
    assert result["results"][0]["source_name"].endswith(
        "-healthcare-security-positioning.md"
    )
    assert "HIPAA" in result["results"][0]["snippet"]


def test_index_product_context_dry_run_does_not_embed_or_write(tmp_path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "positioning.txt").write_text(
        "Workflow automation for small teams.",
        encoding="utf-8",
    )
    embedding = KeywordEmbedding()

    result = index_product_context(
        _cfg(tmp_path),
        embedding_provider=embedding,
        dry_run=True,
    )

    assert result["ok"] is True
    assert result["counts"]["would_index"] == 1
    assert result["storage_written"] is False
    assert embedding.calls == []
    assert not (tmp_path / "cache" / MANIFEST_FILE).exists()


def test_index_product_context_parses_docx_and_retrieves_content(tmp_path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    _write_docx(
        sources / "healthcare-security.docx",
        [
            "Healthcare security positioning supports HIPAA audit readiness.",
            "Budget owners care about workflow automation and evidence exports.",
        ],
    )
    cfg = _cfg(tmp_path)

    index_result = index_product_context(
        cfg,
        embedding_provider=KeywordEmbedding(),
        dry_run=False,
    )
    result = retrieve_product_context(
        cfg,
        embedding_provider=KeywordEmbedding(),
        query="HIPAA security",
        limit=1,
    )

    assert index_result["ok"] is True
    assert index_result["counts"]["indexed"] == 1
    assert index_result["file_types"] == ["csv", "docx", "json", "md", "pdf", "txt"]
    assert result["ok"] is True
    assert result["result_count"] == 1
    assert result["results"][0]["source_name"] == "healthcare-security.docx"
    assert result["results"][0]["file_type"] == "docx"
    assert "HIPAA audit readiness" in result["results"][0]["snippet"]


def test_index_product_context_skips_secret_and_unsupported_office(tmp_path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "secret.md").write_text(
        "OPENAI_API_KEY=sk-abcdefghijklmnop",
        encoding="utf-8",
    )
    (sources / "deck.pptx").write_bytes(b"placeholder")

    result = index_product_context(
        _cfg(tmp_path),
        embedding_provider=KeywordEmbedding(),
        dry_run=False,
    )

    assert result["ok"] is True
    assert result["counts"]["skipped"] == 2
    codes = {warning["code"] for warning in result["warnings"]}
    assert "secret_like_content_skipped" in codes
    assert "unsupported_file_type" in codes
    chunks = json.loads((tmp_path / "cache" / CHUNKS_FILE).read_text(encoding="utf-8"))
    assert chunks == []


def test_retrieve_product_context_returns_relevant_bounded_snippet(tmp_path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "security.md").write_text(
        "Security posture: SOC2, HIPAA, and audit-log support.",
        encoding="utf-8",
    )
    (sources / "pricing.md").write_text(
        "Pricing packages support annual budget planning.",
        encoding="utf-8",
    )
    cfg = _cfg(tmp_path)
    index_product_context(cfg, embedding_provider=KeywordEmbedding(), dry_run=False)

    result = retrieve_product_context(
        cfg,
        embedding_provider=KeywordEmbedding(),
        query="HIPAA security review",
        limit=1,
    )

    assert result["ok"] is True
    assert result["result_count"] == 1
    assert result["results"][0]["source_name"] == "security.md"
    assert "HIPAA" in result["results"][0]["snippet"]
    assert len(result["results"][0]["snippet"]) <= 900


def test_retrieve_product_context_requires_embedding_provider(tmp_path) -> None:
    with pytest.raises(MCPError) as exc_info:
        retrieve_product_context(_cfg(tmp_path), embedding_provider=None, query="security")

    assert exc_info.value.error_code == ErrorCode.CONFIG_ERROR


def test_mcp_get_product_context_reports_missing_embedding_dependency(monkeypatch) -> None:
    monkeypatch.setattr(_context, "embedding_provider", lambda: None)

    result = mcp_server.get_product_context("security")

    assert result["ok"] is False
    assert result["error_code"] == "CONFIG_ERROR"
    assert result["warming_up"] is False


def test_index_product_context_guides_when_default_source_dir_absent(
    tmp_path, monkeypatch
) -> None:
    missing_default = tmp_path / "default-product-context" / "sources"
    monkeypatch.setattr(product_context, "DEFAULT_SOURCE_DIR", str(missing_default))
    cfg = {"product_context": {"cache_dir": str(tmp_path / "cache")}}

    result = index_product_context(cfg, embedding_provider=None, dry_run=True)

    codes = {warning["code"] for warning in result["warnings"]}
    assert "product_context_not_configured" in codes
    assert "source_dir_missing" not in codes


def test_index_product_context_warns_when_configured_source_dir_absent(
    tmp_path,
) -> None:
    cfg = {
        "product_context": {
            "source_dirs": [str(tmp_path / "does-not-exist")],
            "cache_dir": str(tmp_path / "cache"),
        }
    }

    result = index_product_context(cfg, embedding_provider=None, dry_run=True)

    codes = {warning["code"] for warning in result["warnings"]}
    assert "source_dir_missing" in codes
    assert "product_context_not_configured" not in codes
