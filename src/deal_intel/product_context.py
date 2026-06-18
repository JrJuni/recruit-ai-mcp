from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from deal_intel.errors import ErrorCode, MCPError, Stage
from deal_intel.user_memory import detect_secret_patterns

CACHE_SCHEMA_VERSION = 1
PARSER_VERSION = "product_context_v1"
DEFAULT_SOURCE_DIR = "~/.deal-intel/product-context/sources"
DEFAULT_CACHE_DIR = "~/.deal-intel/product-context/cache"
MANIFEST_FILE = "manifest.json"
CHUNKS_FILE = "chunks.json"
SUPPORTED_FILE_TYPES = frozenset({"txt", "md", "json", "csv", "pdf", "docx"})
UNSUPPORTED_FILE_TYPES = frozenset({"pptx", "xlsx"})
DEFAULT_MAX_SOURCE_FILE_MB = 100
DEFAULT_MAX_NOTE_MB = 5
BYTES_PER_MB = 1024 * 1024
MAX_SOURCE_FILE_BYTES = DEFAULT_MAX_SOURCE_FILE_MB * BYTES_PER_MB
MAX_NOTE_BYTES = DEFAULT_MAX_NOTE_MB * BYTES_PER_MB
MAX_FILES_PER_RUN = 200
DEFAULT_MAX_CHUNKS_PER_FILE = 2000
DEFAULT_MAX_CHUNKS_PER_RUN = 8000
CHUNK_TARGET_CHARS = 1200
SNIPPET_CHARS = 900
MANAGED_NOTES_DIR = "managed-notes"
_SAFE_FILENAME_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class ProductContextSettings:
    enabled: bool
    source_dirs: tuple[Path, ...]
    cache_dir: Path
    file_types: frozenset[str]
    top_k: int
    max_context_chars: int
    max_source_file_bytes: int
    max_note_bytes: int
    max_chunks_per_file: int
    max_chunks_per_run: int


def resolve_product_context_settings(
    cfg: dict[str, Any] | None,
    *,
    source_dir: str | None = None,
) -> ProductContextSettings:
    section = cfg.get("product_context") if isinstance(cfg, dict) else None
    if not isinstance(section, dict):
        section = {}

    enabled = bool(section.get("enabled", True))
    source_values: Any
    if source_dir and str(source_dir).strip():
        source_values = [source_dir]
    else:
        source_values = section.get("source_dirs") or [DEFAULT_SOURCE_DIR]
    if isinstance(source_values, str):
        source_values = [source_values]
    if not isinstance(source_values, list):
        source_values = [DEFAULT_SOURCE_DIR]

    file_types = section.get("file_types") or list(SUPPORTED_FILE_TYPES)
    if isinstance(file_types, str):
        file_types = [file_types]
    normalized_types = {
        str(item).strip().lower().removeprefix(".")
        for item in file_types
        if str(item).strip()
    }
    allowed_types = frozenset(normalized_types & SUPPORTED_FILE_TYPES)
    if not allowed_types:
        allowed_types = SUPPORTED_FILE_TYPES

    retrieval = section.get("retrieval")
    if not isinstance(retrieval, dict):
        retrieval = {}

    return ProductContextSettings(
        enabled=enabled,
        source_dirs=tuple(_resolve_path(value) for value in source_values),
        cache_dir=_resolve_path(section.get("cache_dir") or DEFAULT_CACHE_DIR),
        file_types=allowed_types,
        top_k=_bounded_int(retrieval.get("top_k"), default=5, minimum=1, maximum=20),
        max_context_chars=_bounded_int(
            retrieval.get("max_context_chars"),
            default=6000,
            minimum=1000,
            maximum=20000,
        ),
        max_source_file_bytes=_bounded_mb(
            section.get("max_source_file_mb"),
            default=DEFAULT_MAX_SOURCE_FILE_MB,
            minimum=1,
            maximum=500,
        ),
        max_note_bytes=_bounded_mb(
            section.get("max_note_mb"),
            default=DEFAULT_MAX_NOTE_MB,
            minimum=1,
            maximum=20,
        ),
        max_chunks_per_file=_bounded_int(
            section.get("max_chunks_per_file"),
            default=DEFAULT_MAX_CHUNKS_PER_FILE,
            minimum=10,
            maximum=20000,
        ),
        max_chunks_per_run=_bounded_int(
            section.get("max_chunks_per_run"),
            default=DEFAULT_MAX_CHUNKS_PER_RUN,
            minimum=10,
            maximum=50000,
        ),
    )


def index_product_context(
    cfg: dict[str, Any],
    *,
    embedding_provider=None,
    source_dir: str = "",
    force_rebuild: bool = False,
    dry_run: bool = True,
) -> dict[str, Any]:
    settings = resolve_product_context_settings(cfg, source_dir=source_dir or None)
    warnings: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    counts = {
        "scanned": 0,
        "indexed": 0,
        "would_index": 0,
        "unchanged": 0,
        "skipped": 0,
        "errors": 0,
        "partial_indexed": 0,
        "indexed_chunks": 0,
    }
    indexed_chunks_this_run = 0

    if not settings.enabled:
        return _index_payload(
            settings=settings,
            dry_run=dry_run,
            counts=counts,
            warnings=[_warning("product_context_disabled", "product_context is disabled.")],
            errors=[],
        )

    if not dry_run and embedding_provider is None:
        raise MCPError(
            error_code=ErrorCode.CONFIG_ERROR,
            stage=Stage.PREFLIGHT,
            message="Embedding provider is required to build product context cache.",
            hint={"fix": 'Install embeddings with pip install -e ".[embedding]".'},
            retryable=False,
        )

    manifest, old_chunks = _load_cache(settings.cache_dir)
    old_docs = manifest.get("documents", {}) if isinstance(manifest, dict) else {}
    chunks_by_doc = _chunks_by_doc(old_chunks)
    next_docs: dict[str, dict[str, Any]] = {}
    next_chunks: list[dict[str, Any]] = []
    now = datetime.now(UTC).isoformat()

    files = list(_iter_source_files(settings, warnings))
    for path in files[:MAX_FILES_PER_RUN]:
        counts["scanned"] += 1
        ext = _extension(path)
        if ext in UNSUPPORTED_FILE_TYPES:
            counts["skipped"] += 1
            warnings.append(
                _warning(
                    "unsupported_file_type",
                    f"{ext} parsing is not supported in this release.",
                    source_path=str(path),
                    file_type=ext,
                )
            )
            continue
        if ext not in settings.file_types:
            counts["skipped"] += 1
            continue

        try:
            stat = path.stat()
        except OSError as exc:
            counts["errors"] += 1
            errors.append(_file_error(path, "stat_failed", str(exc)))
            continue
        if stat.st_size > settings.max_source_file_bytes:
            counts["skipped"] += 1
            warnings.append(
                _warning(
                    "file_too_large",
                    "File exceeded the product-context max file size.",
                    source_path=str(path),
                    bytes=stat.st_size,
                    max_bytes=settings.max_source_file_bytes,
                )
            )
            continue

        doc_id = _doc_id(path)
        sha256 = _sha256_file(path)
        old_doc = old_docs.get(doc_id) if isinstance(old_docs, dict) else None
        if (
            not force_rebuild
            and isinstance(old_doc, dict)
            and old_doc.get("sha256") == sha256
            and old_doc.get("parser_version") == PARSER_VERSION
            and old_doc.get("status") == "indexed"
        ):
            counts["unchanged"] += 1
            next_docs[doc_id] = old_doc
            next_chunks.extend(chunks_by_doc.get(doc_id, []))
            continue

        parsed = _parse_file(path, ext)
        warnings.extend(parsed["warnings"])
        if parsed["error"]:
            counts["errors"] += 1
            errors.append(_file_error(path, parsed["error"], parsed["message"]))
            continue

        text = str(parsed["text"] or "").strip()
        secret_hits = detect_secret_patterns(text)
        if secret_hits:
            counts["skipped"] += 1
            warnings.append(
                _warning(
                    "secret_like_content_skipped",
                    "File appears to contain secrets and was not indexed.",
                    source_path=str(path),
                    secret_patterns=secret_hits,
                )
            )
            continue

        chunks = _chunk_text(
            text,
            doc_id=doc_id,
            source_path=path,
            source_name=path.name,
            metadata=parsed["metadata"],
        )
        if not chunks:
            counts["skipped"] += 1
            warnings.append(
                _warning(
                    "empty_document_skipped",
                    "No indexable text was extracted from this file.",
                    source_path=str(path),
                )
            )
            continue

        if dry_run:
            counts["would_index"] += 1
            continue

        partial_reason = ""
        original_chunk_count = len(chunks)
        if len(chunks) > settings.max_chunks_per_file:
            chunks = chunks[: settings.max_chunks_per_file]
            partial_reason = "max_chunks_per_file"
            warnings.append(
                _warning(
                    "max_chunks_per_file_reached",
                    "Only the first product-context chunks from this file were indexed.",
                    source_path=str(path),
                    indexed_chunks=len(chunks),
                    discovered_chunks=original_chunk_count,
                    max_chunks_per_file=settings.max_chunks_per_file,
                )
            )

        remaining_run_chunks = settings.max_chunks_per_run - indexed_chunks_this_run
        if remaining_run_chunks <= 0:
            counts["skipped"] += 1
            warnings.append(
                _warning(
                    "max_chunks_per_run_reached",
                    "Product-context run chunk budget was exhausted before this file.",
                    source_path=str(path),
                    max_chunks_per_run=settings.max_chunks_per_run,
                )
            )
            continue
        if len(chunks) > remaining_run_chunks:
            chunks = chunks[:remaining_run_chunks]
            partial_reason = partial_reason or "max_chunks_per_run"
            warnings.append(
                _warning(
                    "max_chunks_per_run_reached",
                    "Only the first product-context chunks from this file were "
                    "indexed because the run budget was reached.",
                    source_path=str(path),
                    indexed_chunks=len(chunks),
                    discovered_chunks=original_chunk_count,
                    max_chunks_per_run=settings.max_chunks_per_run,
                )
            )

        embedded_chunks = []
        for chunk in chunks:
            embedded = dict(chunk)
            embedded["embedding"] = embedding_provider.embed(chunk["text"])
            embedded_chunks.append(embedded)

        next_docs[doc_id] = {
            "doc_id": doc_id,
            "source_path": str(path),
            "source_name": path.name,
            "file_type": ext,
            "sha256": sha256,
            "size_bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "parser_version": PARSER_VERSION,
            "status": "indexed",
            "chunk_count": len(embedded_chunks),
            "partial_indexed": bool(partial_reason),
            "partial_reason": partial_reason or None,
            "discovered_chunk_count": original_chunk_count,
            "embedding_dimensions": (
                embedding_provider.dimensions
                if hasattr(embedding_provider, "dimensions")
                else len(embedded_chunks[0].get("embedding", []))
            ),
            "indexed_at": now,
        }
        next_chunks.extend(embedded_chunks)
        counts["indexed"] += 1
        counts["indexed_chunks"] += len(embedded_chunks)
        indexed_chunks_this_run += len(embedded_chunks)
        if partial_reason:
            counts["partial_indexed"] += 1

    if len(files) > MAX_FILES_PER_RUN:
        warnings.append(
            _warning(
                "max_files_per_run_reached",
                "Only the first product-context files were considered.",
                scanned_limit=MAX_FILES_PER_RUN,
                discovered=len(files),
            )
        )

    if not dry_run:
        _write_cache(
            settings.cache_dir,
            {
                "schema_version": CACHE_SCHEMA_VERSION,
                "parser_version": PARSER_VERSION,
                "generated_at": now,
                "source_dirs": [str(path) for path in settings.source_dirs],
                "documents": next_docs,
            },
            next_chunks,
        )

    return _index_payload(
        settings=settings,
        dry_run=dry_run,
        counts=counts,
        warnings=warnings,
        errors=errors,
    )


def add_product_context_note(
    cfg: dict[str, Any],
    *,
    title: str,
    content: str,
    source_name: str = "",
    dry_run: bool = True,
    confirmed_by_user: bool = False,
) -> dict[str, Any]:
    settings = resolve_product_context_settings(cfg)
    cleaned_title = _clean_required_text(title, "title")
    cleaned_content = _clean_required_text(content, "content")
    cleaned_source_name = str(source_name or "").strip()
    warnings: list[dict[str, Any]] = []

    if not dry_run and not confirmed_by_user:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=(
                "confirmed_by_user=true is required when dry_run=false for "
                "add_product_context_note."
            ),
            retryable=False,
        )

    if not settings.enabled:
        warnings.append(
            _warning(
                "product_context_disabled",
                "product_context is disabled; the note can be saved but will not "
                "be used until product context is enabled and indexed.",
            )
        )

    secret_hits = detect_secret_patterns(
        "\n".join([cleaned_title, cleaned_source_name, cleaned_content])
    )
    if secret_hits:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message="product context note appears to contain a secret and was not written.",
            hint={
                "secret_patterns": secret_hits,
                "fix": (
                    "Remove API keys, OAuth tokens, MongoDB URIs, private keys, "
                    "or credential-like values before saving product context."
                ),
            },
            retryable=False,
        )

    content_bytes = len(cleaned_content.encode("utf-8"))
    if content_bytes > settings.max_note_bytes:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message="product context note exceeds the max file size.",
            hint={"max_bytes": settings.max_note_bytes, "actual_bytes": content_bytes},
            retryable=False,
        )

    source_root = settings.source_dirs[0]
    notes_dir = (source_root / MANAGED_NOTES_DIR).resolve()
    note_path = _managed_note_path(notes_dir, cleaned_title)
    _assert_child_path(notes_dir, note_path)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    body = _format_managed_note(
        title=cleaned_title,
        source_name=cleaned_source_name,
        created_at=now,
        content=cleaned_content,
    )

    if not dry_run:
        notes_dir.mkdir(parents=True, exist_ok=True)
        note_path.write_text(body, encoding="utf-8", newline="\n")

    return {
        "ok": True,
        "dry_run": dry_run,
        "enabled": settings.enabled,
        "source_dir": str(source_root),
        "managed_notes_dir": str(notes_dir),
        "source_path": str(note_path),
        "source_name": note_path.name,
        "title": cleaned_title,
        "bytes": len(body.encode("utf-8")),
        "secret_scan": {"checked": True, "hits": []},
        "storage_written": not dry_run,
        "warnings": warnings,
        "next_actions": [
            {
                "tool": "index_product_context",
                "hint": (
                    "Run index_product_context after saving this note so it can "
                    "be used as seller-side retrieval context."
                ),
            },
            {
                "tool": "get_product_context",
                "hint": (
                    "After indexing, query get_product_context to verify the note "
                    "is retrievable before relying on it in add_interaction."
                ),
            },
        ],
    }


def retrieve_product_context(
    cfg: dict[str, Any],
    *,
    embedding_provider,
    query: str,
    limit: int | None = None,
) -> dict[str, Any]:
    settings = resolve_product_context_settings(cfg)
    cleaned_query = str(query or "").strip()
    if not cleaned_query:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message="query must not be empty.",
            retryable=False,
        )
    if not settings.enabled:
        return _retrieval_payload(
            settings=settings,
            query=cleaned_query,
            results=[],
            warnings=[_warning("product_context_disabled", "product_context is disabled.")],
            product_context_status={
                "state": "disabled",
                "message": "Product context is disabled in config.",
            },
            embedding_status=embedding_readiness_status(embedding_provider),
            next_actions=[
                {
                    "tool": "update_config",
                    "hint": (
                        "Enable product_context before indexing or retrieving "
                        "seller-side context."
                    ),
                }
            ],
        )
    if embedding_provider is None:
        raise MCPError(
            error_code=ErrorCode.CONFIG_ERROR,
            stage=Stage.PREFLIGHT,
            message="Embedding provider is required for product context retrieval.",
            hint={
                "fix": 'Install embeddings with pip install -e ".[embedding]".',
                "embedding_status": embedding_readiness_status(embedding_provider),
            },
            retryable=False,
        )

    embedding_status = embedding_readiness_status(embedding_provider)
    _manifest, chunks = _load_cache(settings.cache_dir)
    embedded_chunks = [
        chunk
        for chunk in chunks
        if isinstance(chunk.get("embedding"), list) and chunk.get("embedding")
    ]
    if not embedded_chunks:
        return _retrieval_payload(
            settings=settings,
            query=cleaned_query,
            results=[],
            warnings=[
                _warning(
                    "product_context_index_empty_or_unembedded",
                    "No embedded product context chunks are available. "
                    "Run index_product_context first.",
                )
            ],
            product_context_status={
                "state": "not_indexed",
                "embedded_chunk_count": 0,
                "message": "No indexed product-context chunks were found.",
            },
            embedding_status=embedding_status,
            next_actions=[
                {
                    "tool": "index_product_context",
                    "hint": (
                        "Run index_product_context after adding product docs "
                        "or saving a managed note."
                    ),
                }
            ],
        )

    query_embedding = embedding_provider.embed(cleaned_query)
    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in embedded_chunks:
        emb = chunk.get("embedding") or []
        score = sum(q * d for q, d in zip(query_embedding, emb))
        scored.append((score, chunk))
    scored.sort(key=lambda item: -item[0])

    max_results = _bounded_int(limit, default=settings.top_k, minimum=1, maximum=20)
    results = []
    used_chars = 0
    for score, chunk in scored[:max_results]:
        snippet = _snippet(chunk.get("text", ""))
        if used_chars + len(snippet) > settings.max_context_chars and results:
            break
        used_chars += len(snippet)
        results.append(
            {
                "doc_id": chunk["doc_id"],
                "chunk_id": chunk["chunk_id"],
                "source_name": chunk["source_name"],
                "source_path": chunk["source_path"],
                "file_type": chunk.get("file_type"),
                "section": chunk.get("section"),
                "score": round(score, 4),
                "snippet": snippet,
            }
        )

    return _retrieval_payload(
        settings=settings,
        query=cleaned_query,
        results=results,
        warnings=[],
        product_context_status={
            "state": "ready",
            "embedded_chunk_count": len(embedded_chunks),
            "message": "Product-context cache is indexed and searchable.",
        },
        embedding_status=embedding_status,
        next_actions=[],
    )


def embedding_readiness_status(embedding_provider) -> dict[str, Any]:
    if embedding_provider is None:
        return {
            "state": "not_installed",
            "phase": "missing_provider",
            "retryable": False,
            "next_action": 'Install embeddings with pip install -e ".[embedding]".',
        }
    load_error = getattr(embedding_provider, "load_error", None)
    if load_error:
        return {
            "state": "failed",
            "phase": "failed",
            "retryable": False,
            "error": str(load_error),
            "next_action": "Restart the MCP server and check stderr for warmup errors.",
        }
    if not getattr(embedding_provider, "is_ready", False):
        warmup = getattr(embedding_provider, "warmup_status", {}) or {}
        phase = str(warmup.get("phase") or "loading")
        state = "not_started" if phase == "not_started" else "loading"
        return {
            "state": state,
            "phase": phase,
            "elapsed_seconds": warmup.get("elapsed_seconds"),
            "retryable": True,
            "retry_after_seconds": 5,
            "next_action": "The local embedding model is loading; retry shortly.",
        }
    warmup = getattr(embedding_provider, "warmup_status", {}) or {}
    return {
        "state": "ready",
        "phase": warmup.get("phase", "ready"),
        "elapsed_seconds": warmup.get("elapsed_seconds"),
        "retryable": False,
    }


def render_product_context_prompt_block(payload: dict[str, Any]) -> str:
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list) or not results:
        return ""
    lines = [
        "Seller/product context:",
        "- This is seller-side product knowledge.",
        "- Do not treat it as customer-stated evidence.",
        "- Use it only to understand product fit, terminology, possible value props,",
        "  disqualifiers, and strategy interpretation.",
        "",
        "Relevant product snippets:",
    ]
    for index, item in enumerate(results, start=1):
        source = item.get("source_name") or item.get("doc_id") or "product-context"
        snippet = str(item.get("snippet") or "").strip()
        if not snippet:
            continue
        lines.append(f"[{index}] {source} (score={item.get('score')}): {snippet}")
    return "\n".join(lines)


def product_context_refs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return []
    refs = []
    for item in results:
        refs.append(
            {
                "doc_id": str(item.get("doc_id") or ""),
                "chunk_id": str(item.get("chunk_id") or ""),
                "source_name": str(item.get("source_name") or ""),
                "score": item.get("score"),
            }
        )
    return refs


def _index_payload(
    *,
    settings: ProductContextSettings,
    dry_run: bool,
    counts: dict[str, int],
    warnings: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "ok": not errors,
        "dry_run": dry_run,
        "enabled": settings.enabled,
        "source_dirs": [str(path) for path in settings.source_dirs],
        "cache_dir": str(settings.cache_dir),
        "manifest_path": str(settings.cache_dir / MANIFEST_FILE),
        "chunks_path": str(settings.cache_dir / CHUNKS_FILE),
        "parser_version": PARSER_VERSION,
        "file_types": sorted(settings.file_types),
        "limits": {
            "max_source_file_bytes": settings.max_source_file_bytes,
            "max_note_bytes": settings.max_note_bytes,
            "max_chunks_per_file": settings.max_chunks_per_file,
            "max_chunks_per_run": settings.max_chunks_per_run,
        },
        "counts": counts,
        "warnings": warnings,
        "errors": errors,
        "storage_written": not dry_run and not errors,
    }


def _retrieval_payload(
    *,
    settings: ProductContextSettings,
    query: str,
    results: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    product_context_status: dict[str, Any] | None = None,
    embedding_status: dict[str, Any] | None = None,
    next_actions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "query": query,
        "cache_dir": str(settings.cache_dir),
        "result_count": len(results),
        "results": results,
        "warnings": warnings,
        "product_context_status": product_context_status
        or {"state": "unknown", "message": "Product-context status was not evaluated."},
        "embedding_status": embedding_status,
        "next_actions": next_actions or [],
    }


def _iter_source_files(
    settings: ProductContextSettings,
    warnings: list[dict[str, Any]],
) -> Iterable[Path]:
    seen: set[Path] = set()
    default_root = _resolve_path(DEFAULT_SOURCE_DIR)
    for root in settings.source_dirs:
        if not root.exists():
            if root == default_root:
                # First-run, unconfigured state: guide the user instead of
                # raising what looks like an error.
                warnings.append(
                    _warning(
                        "product_context_not_configured",
                        "No product context is set up yet. Add product, solution, "
                        "ICP, pricing, or positioning documents to the default "
                        "folder shown below, or point to your own folder, then "
                        "index again.",
                        source_dir=str(root),
                        how_to_configure=(
                            "Put files in the folder above, or set "
                            "product_context.source_dirs via update_config "
                            "(or the DEAL_INTEL_PRODUCT_CONTEXT_SOURCE_DIRS env)."
                        ),
                    )
                )
            else:
                # A folder the user explicitly configured is genuinely missing.
                warnings.append(
                    _warning(
                        "source_dir_missing",
                        "Product context source directory does not exist.",
                        source_dir=str(root),
                    )
                )
            continue
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield resolved


def _parse_file(path: Path, ext: str) -> dict[str, Any]:
    warnings: list[dict[str, Any]] = []
    try:
        if ext in {"txt", "md"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            return _parse_result(text=text, warnings=warnings)
        if ext == "json":
            raw = path.read_text(encoding="utf-8", errors="replace")
            try:
                text = json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                text = raw
                warnings.append(
                    _warning(
                        "json_parse_failed_used_raw_text",
                        "JSON parsing failed; indexed raw text instead.",
                        source_path=str(path),
                    )
                )
            return _parse_result(text=text, warnings=warnings)
        if ext == "csv":
            raw = path.read_text(encoding="utf-8-sig", errors="replace")
            rows = []
            for row in csv.reader(raw.splitlines()):
                rows.append(" | ".join(cell.strip() for cell in row if cell.strip()))
            return _parse_result(text="\n".join(row for row in rows if row), warnings=warnings)
        if ext == "pdf":
            return _parse_pdf(path)
        if ext == "docx":
            return _parse_docx(path)
    except OSError as exc:
        return _parse_result(error="read_failed", message=str(exc), warnings=warnings)
    return _parse_result(
        error="unsupported_file_type",
        message=f"{ext} parsing is not supported.",
        warnings=warnings,
    )


def _parse_pdf(path: Path) -> dict[str, Any]:
    warnings: list[dict[str, Any]] = []
    try:
        from pypdf import PdfReader
    except ImportError:
        return _parse_result(
            error="pdf_parser_unavailable",
            message="pypdf is required to index PDF product context files.",
            warnings=warnings,
        )
    try:
        reader = PdfReader(str(path))
        pages = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"[page {index}]\n{text.strip()}")
        return _parse_result(
            text="\n\n".join(pages),
            warnings=warnings,
            metadata={"page_count": len(reader.pages)},
        )
    except Exception as exc:
        return _parse_result(
            error="pdf_parse_failed",
            message=f"{type(exc).__name__}: {exc}",
            warnings=warnings,
        )


def _parse_docx(path: Path) -> dict[str, Any]:
    warnings: list[dict[str, Any]] = []
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    try:
        with zipfile.ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml")
        root = ET.fromstring(document_xml)
        paragraphs = []
        for paragraph in root.findall(".//w:p", namespace):
            texts = [
                node.text or ""
                for node in paragraph.findall(".//w:t", namespace)
                if node.text
            ]
            text = "".join(texts).strip()
            if text:
                paragraphs.append(text)
        return _parse_result(
            text="\n\n".join(paragraphs),
            warnings=warnings,
            metadata={"paragraph_count": len(paragraphs)},
        )
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError) as exc:
        return _parse_result(
            error="docx_parse_failed",
            message=f"{type(exc).__name__}: {exc}",
            warnings=warnings,
        )


def _parse_result(
    *,
    text: str = "",
    warnings: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
    error: str = "",
    message: str = "",
) -> dict[str, Any]:
    return {
        "text": text,
        "warnings": warnings,
        "metadata": metadata or {},
        "error": error,
        "message": message,
    }


def _chunk_text(
    text: str,
    *,
    doc_id: str,
    source_path: Path,
    source_name: str,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    chunks: list[str] = []
    current = ""
    for paragraph in _paragraphs(text):
        if len(paragraph) > CHUNK_TARGET_CHARS:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(_split_long_text(paragraph, CHUNK_TARGET_CHARS))
            continue
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) > CHUNK_TARGET_CHARS and current:
            chunks.append(current.strip())
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current.strip())

    file_type = _extension(source_path)
    return [
        {
            "doc_id": doc_id,
            "chunk_id": f"{doc_id}:{index}",
            "source_path": str(source_path),
            "source_name": source_name,
            "file_type": file_type,
            "section": _section_label(chunk, index),
            "text": chunk,
            "metadata": metadata,
        }
        for index, chunk in enumerate(chunks)
        if chunk.strip()
    ]


def _paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_parts = [part.strip() for part in normalized.split("\n\n")]
    parts: list[str] = []
    for part in raw_parts:
        if not part:
            continue
        if len(part) < CHUNK_TARGET_CHARS:
            parts.append(part)
        else:
            parts.extend(line.strip() for line in part.splitlines() if line.strip())
    return parts


def _split_long_text(text: str, size: int) -> list[str]:
    return [text[index : index + size].strip() for index in range(0, len(text), size)]


def _section_label(text: str, index: int) -> str:
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if first_line.startswith("#"):
        return first_line[:120]
    return f"chunk-{index}"


def _load_cache(cache_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest_path = cache_dir / MANIFEST_FILE
    chunks_path = cache_dir / CHUNKS_FILE
    manifest: dict[str, Any] = {"schema_version": CACHE_SCHEMA_VERSION, "documents": {}}
    chunks: list[dict[str, Any]] = []
    if manifest_path.exists():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                manifest = loaded
        except json.JSONDecodeError:
            manifest = {"schema_version": CACHE_SCHEMA_VERSION, "documents": {}}
    if chunks_path.exists():
        try:
            loaded_chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
            if isinstance(loaded_chunks, list):
                chunks = [item for item in loaded_chunks if isinstance(item, dict)]
        except json.JSONDecodeError:
            chunks = []
    return manifest, chunks


def _write_cache(
    cache_dir: Path,
    manifest: dict[str, Any],
    chunks: list[dict[str, Any]],
) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(cache_dir / MANIFEST_FILE, manifest)
    _write_json_atomic(cache_dir / CHUNKS_FILE, chunks)


def _write_json_atomic(path: Path, payload: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )
    tmp.replace(path)


def _chunks_by_doc(chunks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        doc_id = str(chunk.get("doc_id") or "")
        if not doc_id:
            continue
        grouped.setdefault(doc_id, []).append(chunk)
    return grouped


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _doc_id(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()[:16]


def _extension(path: Path) -> str:
    return path.suffix.lower().removeprefix(".")


def _resolve_path(value: Any) -> Path:
    raw = os.path.expandvars(str(value or "").strip())
    path = Path(raw or DEFAULT_SOURCE_DIR).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _bounded_int(
    value: Any,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _bounded_mb(
    value: Any,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    return _bounded_int(
        value,
        default=default,
        minimum=minimum,
        maximum=maximum,
    ) * BYTES_PER_MB


def _snippet(text: Any) -> str:
    compact = " ".join(str(text or "").split())
    return compact[:SNIPPET_CHARS]


def _warning(code: str, message: str, **details: Any) -> dict[str, Any]:
    payload = {"code": code, "message": message}
    if details:
        payload["details"] = details
    return payload


def _file_error(path: Path, code: str, message: str) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "source_path": str(path),
    }


def _clean_required_text(value: Any, field_name: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message=f"{field_name} must not be empty.",
            retryable=False,
        )
    return cleaned


def _managed_note_path(notes_dir: Path, title: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    slug = _slugify(title)
    base = f"{timestamp}-{slug}"
    candidate = notes_dir / f"{base}.md"
    index = 2
    while candidate.exists():
        candidate = notes_dir / f"{base}-{index}.md"
        index += 1
    return candidate.resolve()


def _slugify(value: str) -> str:
    normalized = _SAFE_FILENAME_RE.sub("-", value.strip().lower()).strip("-")
    if not normalized:
        return "note"
    return normalized[:80].strip("-") or "note"


def _assert_child_path(parent: Path, child: Path) -> None:
    try:
        child.relative_to(parent)
    except ValueError as exc:
        raise MCPError(
            error_code=ErrorCode.INVALID_INPUT,
            stage=Stage.PREFLIGHT,
            message="managed product context note must stay inside managed-notes.",
            retryable=False,
        ) from exc


def _format_managed_note(
    *,
    title: str,
    source_name: str,
    created_at: str,
    content: str,
) -> str:
    return "\n".join(
        [
            "---",
            "deal_intel_managed: true",
            f"title: {json.dumps(title, ensure_ascii=False)}",
            f"source_name: {json.dumps(source_name, ensure_ascii=False)}",
            f"created_at: {json.dumps(created_at)}",
            "---",
            "",
            content,
            "",
        ]
    )
