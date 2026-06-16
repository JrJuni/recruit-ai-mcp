from __future__ import annotations

from deal_intel.product_context import add_product_context_note


def handle(
    *,
    cfg: dict,
    title: str,
    content: str,
    source_name: str = "",
    dry_run: bool = True,
    confirmed_by_user: bool = False,
) -> dict:
    return add_product_context_note(
        cfg,
        title=title,
        content=content,
        source_name=source_name,
        dry_run=dry_run,
        confirmed_by_user=confirmed_by_user,
    )
