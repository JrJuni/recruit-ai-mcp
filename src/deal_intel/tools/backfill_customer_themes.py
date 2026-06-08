from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from deal_intel.providers.llm import LLMProvider
from deal_intel.schema.customer_themes import rebuild_deal_customer_themes
from deal_intel.storage.mongodb import MongoDBClient
from deal_intel.tools.customer_theme_analysis import extract_customer_themes


def handle(
    mongo: MongoDBClient,
    llm: LLMProvider,
    *,
    limit: int = 0,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    deals = mongo.list_deals_for_theme_backfill(limit=limit)
    stats: dict = {
        "ok": True,
        "dry_run": dry_run,
        "deals_scanned": len(deals),
        "deals_updated": 0,
        "meetings_processed": 0,
        "meetings_skipped": 0,
        "themes_extracted": 0,
        "errors": [],
    }
    theme_counts: Counter[str] = Counter()

    for deal in deals:
        changed = False
        for meeting in deal.get("meetings", []):
            if not force and "customer_themes" in meeting:
                stats["meetings_skipped"] += 1
                continue

            raw_notes = str(meeting.get("raw_notes") or "").strip()
            if not raw_notes:
                meeting["customer_themes"] = []
                stats["meetings_skipped"] += 1
                changed = True
                continue

            try:
                themes, _usage = extract_customer_themes(llm, raw_notes)
            except Exception as exc:
                stats["errors"].append(
                    {
                        "deal_id": deal.get("deal_id"),
                        "meeting_id": meeting.get("meeting_id"),
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                continue

            meeting["customer_themes"] = themes
            stats["meetings_processed"] += 1
            stats["themes_extracted"] += len(themes)
            theme_counts.update(theme["theme_key"] for theme in themes)
            changed = True

        if not changed:
            continue

        deal["customer_themes"] = rebuild_deal_customer_themes(deal)
        deal["updated_at"] = datetime.now(UTC).isoformat()
        if not dry_run:
            mongo.upsert_deal(deal)
        stats["deals_updated"] += 1

    stats["theme_counts"] = dict(theme_counts.most_common())
    return stats
