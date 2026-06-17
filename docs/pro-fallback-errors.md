# Pro Fallback And Atlas Vector Search Error Notes

English is the source language for this document. Append only real or
reproducible failures here. Do not include secrets, connection strings, raw
customer notes, API keys, OAuth tokens, embeddings, or full stack traces with
private paths.

## Policy

`pro` mode uses `mongodb.vector_search: atlas`. When Atlas Vector Search fails,
the product should not silently fall back to Python cosine. Silent fallback makes
operators think the paid path is working when it is not.

Instead:

1. Return a structured error.
2. Explain the probable setup issue.
3. Offer an explicit temporary workaround: set `mongodb.vector_search` to
   `python_cosine`.
4. Record repeatable failures in this file so future doctor/check tooling can
   learn the edge cases.

## What To Record

Use this shape for future entries:

```text
### YYYY-MM-DD - short failure name

- Profile: pro
- Vector mode: atlas
- Cluster tier: M0 | M10 | unknown
- Index name: deal_summary_vector
- Operation: config doctor | search_deals | future atlas-vector-index check/apply
- Sanitized error: ...
- User-visible symptom: ...
- Diagnosis: ...
- Fix or workaround: ...
- Follow-up automation candidate: ...
```

## Known Failure Classes

### Atlas Vector Search index missing

- Symptom: `search_deals` fails in `atlas` mode.
- Likely cause: `deal_summary_vector` was not created in Atlas Search.
- Fix: create the index from `atlas/vector_indexes/deal_summary_vector.v1.json`.
- Workaround: set `mongodb.vector_search: python_cosine`.
- Automation candidate: future `deal-intel atlas-vector-index check`.

### Free-tier cluster does not support Atlas Vector Search

- Symptom: index creation or query fails on M0/free cluster.
- Likely cause: Pro requires Atlas M10+ for the vector-search path.
- Fix: upgrade the cluster or use `full`/`python_cosine`.
- Workaround: set `mongodb.vector_search: python_cosine`.
- Automation candidate: future doctor check that distinguishes M0 from missing
  index when Atlas admin verification is available.

### Vector dimensions mismatch

- Symptom: index creation succeeds with one dimension count, but
  `search_deals` fails in `atlas` mode or returns no usable vector matches.
- Likely cause: the Atlas index `numDimensions` does not match the embedding
  provider output length.
- Expected static contract: `deal_summary_vector` uses
  `summary_embedding`, `numDimensions: 384`, and cosine similarity unless the
  operator explicitly creates a compatible custom index.
- Fix: recreate the Atlas index with dimensions matching the configured
  embedding provider, or use the default local embedding model and the bundled
  `atlas/vector_indexes/deal_summary_vector.v1.json` spec.
- Workaround: set `mongodb.vector_search: python_cosine` until the index and
  embeddings are aligned.

### Embeddings missing on existing deals

- Symptom: index exists, but semantic search returns no useful results.
- Likely cause: deals do not have `summary_embedding` values yet.
- Fix: run or build an embedding backfill path after the LLM/embedding provider
  is ready.
- Workaround: newly scored interactions should populate embeddings.
- Automation candidate: future `backfill-embeddings --dry-run/--apply`.

### Missing Atlas Search permissions

- Symptom: `deal-intel mongo apply-vector-index --apply --json` fails even on
  M10+.
- Likely cause: the configured MongoDB user can read/write data but cannot
  create Atlas Search indexes.
- Fix: grant the required Atlas Search/index management role or create the
  index manually in the Atlas UI from the bundled spec.
- Workaround: set `mongodb.vector_search: python_cosine`.
