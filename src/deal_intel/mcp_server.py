from __future__ import annotations

import deal_intel._env  # noqa: F401 — triggers dotenv load at import time
from fastmcp import FastMCP

app = FastMCP("deal-intel")


@app.tool()
def create_deal(company: str, industry: str = "", deal_size_krw: int = 0) -> dict:
    """Create a new deal for a prospect company."""
    from deal_intel import _context
    from deal_intel.tools import create_deal as _t

    return _t.handle(
        mongo=_context.mongo(),
        company=company,
        industry=industry or None,
        deal_size_krw=deal_size_krw or None,
    )


@app.tool()
def add_meeting(deal_id: str, date: str, raw_notes: str) -> dict:
    """Add meeting notes to an existing deal and extract MEDDPICC signals via LLM."""
    from deal_intel import _context
    from deal_intel.tools import add_meeting as _t

    return _t.handle(
        mongo=_context.mongo(),
        llm=_context.llm_provider(),
        deal_id=deal_id,
        date=date,
        raw_notes=raw_notes,
    )


@app.tool()
def get_deal(deal_id: str) -> dict:
    """Retrieve a deal with full meeting history and MEDDPICC scores."""
    from deal_intel import _context
    from deal_intel.tools import get_deal as _t

    return _t.handle(mongo=_context.mongo(), deal_id=deal_id)


@app.tool()
def list_deals(stage: str = "", limit: int = 20) -> dict:
    """List deals, optionally filtered by stage (discovery/qualification/proposal/negotiation/won/lost/stalled)."""
    from deal_intel import _context
    from deal_intel.tools import list_deals as _t

    return _t.handle(mongo=_context.mongo(), stage=stage or None, limit=limit)


@app.tool()
def analyze_deal(deal_id: str) -> dict:
    """Analyze a deal's MEDDPICC gaps and generate BD strategy recommendations."""
    from deal_intel import _context
    from deal_intel.tools import analyze_deal as _t

    return _t.handle(
        mongo=_context.mongo(),
        llm=_context.llm_provider(),
        deal_id=deal_id,
    )


def main() -> None:
    # Pre-import heavy deps on main thread to avoid FastMCP worker-thread deadlock.
    # (Lesson from event-intel-mcp: first pymongo import inside a worker thread can hang.)
    try:
        import pymongo  # noqa: F401
    except ImportError:
        pass
    app.run()


if __name__ == "__main__":
    main()
