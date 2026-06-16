from __future__ import annotations

from deal_intel.product_context import retrieve_product_context


def handle(
    *,
    cfg: dict,
    embedding_provider,
    query: str,
    limit: int = 5,
) -> dict:
    return retrieve_product_context(
        cfg,
        embedding_provider=embedding_provider,
        query=query,
        limit=limit,
    )
