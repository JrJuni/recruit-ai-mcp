"""Slug sanitization + validation + suggestion — ported from event-intel-mcp.

    sanitize_slug(s)  -> str    # raises MCPError(INVALID_INPUT) with suggested_slug on failure
    validate_slug(s)  -> bool   # pure boolean predicate, no raise
    suggest_slug(s)   -> str    # best-effort ASCII transliteration; hash-suffix fallback

The slug grammar is `^[a-zA-Z0-9_-]{1,64}$`. Gate for deal_id inputs entering the system.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

from deal_intel.errors import ErrorCode, MCPError, Stage

_SLUG_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
_SLUG_MAX_LEN = 64
_FALLBACK_PREFIX = "deal-"


def validate_slug(s: str) -> bool:
    """True iff `s` matches `^[a-zA-Z0-9_-]{1,64}$`. Never raises."""
    return bool(s) and isinstance(s, str) and bool(_SLUG_RE.match(s))


def suggest_slug(s: str) -> str:
    """Best-effort ASCII-safe slug derivation. Always returns a valid slug."""
    raw = s if isinstance(s, str) else str(s or "")

    nfkd = unicodedata.normalize("NFKD", raw)
    stripped = "".join(ch for ch in nfkd if not unicodedata.combining(ch))

    out_chars: list[str] = []
    for ch in stripped:
        if ch.isascii() and (ch.isalnum() or ch in "_-"):
            out_chars.append(ch.lower())
        else:
            out_chars.append("-")
    collapsed = re.sub(r"-+", "-", "".join(out_chars)).strip("-_")

    if collapsed:
        return collapsed[:_SLUG_MAX_LEN]

    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
    return f"{_FALLBACK_PREFIX}{digest}"


def sanitize_slug(s: str, *, field_name: str = "slug") -> str:
    """Return `s` if already valid. Otherwise raise MCPError(INVALID_INPUT) with suggested_slug hint."""
    if validate_slug(s):
        return s
    suggested = suggest_slug(s if isinstance(s, str) else "")
    raise MCPError(
        error_code=ErrorCode.INVALID_INPUT,
        stage=Stage.PREFLIGHT,
        message=(
            f"{field_name} {s!r} violates [a-zA-Z0-9_-]{{1,64}}"
            if isinstance(s, str) and s
            else f"{field_name} is empty or not a string"
        ),
        hint={
            "rule": "^[a-zA-Z0-9_-]{1,64}$",
            "suggested_slug": suggested,
            "field": field_name,
        },
        retryable=False,
    )
