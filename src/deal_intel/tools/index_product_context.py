from __future__ import annotations

from deal_intel.product_context import index_product_context


def handle(
    *,
    cfg: dict,
    embedding_provider=None,
    source_dir: str = "",
    force_rebuild: bool = False,
    dry_run: bool = True,
) -> dict:
    return index_product_context(
        cfg,
        embedding_provider=embedding_provider,
        source_dir=source_dir,
        force_rebuild=force_rebuild,
        dry_run=dry_run,
    )
