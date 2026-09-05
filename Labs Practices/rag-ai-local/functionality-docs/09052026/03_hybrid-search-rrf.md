---
title: Hybrid Search — Vector + Full-Text, Fused via Reciprocal Rank Fusion
date: 2026-09-05
type: functionality
area: rag-pipeline-retrieval
status: implementation-complete
session_id: n/a
duration: ~90min
files: [Labs Practices/session4-rag/rag_pipeline/sql/03_hybrid_search.sql, Labs Practices/session4-rag/rag_pipeline/sql/migrations.py, Labs Practices/session4-rag/rag_pipeline/retrieval/hybrid/query_builder.py, Labs Practices/session4-rag/rag_pipeline/retrieval/hybrid/lexical.py, Labs Practices/session4-rag/rag_pipeline/retrieval/hybrid/fusion.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step4_similarity_search.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step6_reranking.py, Labs Practices/session4-rag/rag_pipeline/retrieval/retrieval_runner.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step10_response.py, Labs Practices/session4-rag/rag_pipeline/config/env_config.py, Labs Practices/session4-rag/rag_pipeline/api/routes_chat.py, Labs Practices/session4-rag/rag_pipeline/ui/index.html]
version: 1
last_updated: 2026-09-05
extraction_method: pair-session
tags: [rag-pipeline, hybrid-search, full-text-search, rrf, reranking, tsvector]
keywords: [content_tsv, ts_rank, websearch_to_tsquery, reciprocal_rank_fusion_martin, found_by, chunk_id, HYBRID_SEARCH_ENABLED, schema_migrations]
related: [rag-ai-local/functionality-docs/09052026/02_structure-aware-chunking.md, rag-ai-local/functionality-docs/09022026/03_metadata-filtering-problems-and-tradeoffs.md, rag-ai-local/functionality-docs/09022026/01_reranking-service-and-toggle.md]
---

## TL;DR
- **What:** Added a hybrid retrieval stage — Postgres full-text search fused with the existing pgvector cosine-similarity search via Reciprocal Rank Fusion (RRF) — as an opt-in stage alongside reranking.
- **Why:** Pure vector search misses exact-keyword/acronym/rare-term matches that don't embed distinctively but that full-text search catches directly; the project's `rag_chunks.content_tsv tsvector` column already existed in the schema but was completely dead (no trigger, no index, never populated).
- **Where:** New `retrieval/hybrid/` package (`query_builder.py`, `lexical.py`, `fusion.py`); `sql/03_hybrid_search.sql` (new) + `sql/migrations.py` (generalized to run multiple files); `RetrievedChunk` (`chunk_id`/`found_by` fields); `retrieval_runner.py`, `config/env_config.py`, `api/routes_chat.py`, `step10_response.py`, `ui/index.html`.
- **Impact:** Verified end-to-end — migration applied cleanly, `content_tsv` backfilled for all existing rows, hybrid-off regression matches prior behavior exactly, hybrid-on shows a real lexical match fused correctly (`found_by: "both"`) and composing cleanly with the pre-existing metadata filter.

## What it does

Hybrid search sits between vector search and metadata filtering in the `/chat` retrieval pipeline. When enabled, `retrieval_runner.py` runs `step4_similarity_search.py`'s existing vector query AND a new `retrieval/hybrid/lexical.py` full-text query against the same question, then fuses both ranked lists into one via Reciprocal Rank Fusion before anything downstream (metadata filtering, reranking) ever sees the candidates. Toggleable per-request (`{"hybrid": true}`) or via a server-wide default (`HYBRID_SEARCH_ENABLED`), exactly mirroring how reranking is toggled.

## How it works

**Lexical search** (`retrieval/hybrid/lexical.py:lexical_search_martin`) runs:
```sql
SELECT c.id, c.content, d.source_path, d.status, d.area,
       ts_rank(c.content_tsv, websearch_to_tsquery('english', %s)) AS score
FROM rag_chunks c JOIN rag_documents d ON d.id = c.document_id
WHERE c.content_tsv @@ websearch_to_tsquery('english', %s)
ORDER BY score DESC LIMIT %s
```
`websearch_to_tsquery` parses natural-language question text safely as a bind parameter — no manual tsquery-syntax construction needed. `query_builder.py:build_tsquery_text_martin` only does light whitespace normalization before that.

**Fusion** (`retrieval/hybrid/fusion.py:reciprocal_rank_fusion_martin`) takes `[vector_candidates, lexical_candidates]` and, for each chunk at rank `r` (1-indexed) in a ranking, adds `1/(k+r)` (k=60) to that chunk's running score, keyed by `chunk_id` — a field that didn't exist on `RetrievedChunk` before this feature (the vector query never selected `c.id`). A chunk appearing in both rankings accumulates score from both, naturally outranking a chunk found by only one method, without needing cosine-distance and `ts_rank` to be on comparable scales (they aren't). The result is sorted descending and truncated to `top_k`, with `found_by` set to `"vector"`, `"lexical"`, or `"both"` depending on which ranking(s) contained that `chunk_id`.

**Bringing `content_tsv` to life** — the column was declared in `init_rag_db.sql` since Lab1 but had no trigger and no index. `sql/03_hybrid_search.sql` (new file) adds a `BEFORE INSERT OR UPDATE OF content` trigger that populates `content_tsv := to_tsvector('english', NEW.content)`, backfills every existing row (`UPDATE ... WHERE content_tsv IS NULL`), and adds a GIN index for `ts_rank`/`@@` performance. Nothing is dropped — purely additive.

**Running two migration files** — `sql/migrations.py` previously hashed and conditionally re-applied exactly one file (`init_rag_db.sql`). It's now generalized to iterate `_MIGRATION_FILES = ["init_rag_db.sql", "03_hybrid_search.sql"]`, tracking each file's hash independently via a new `filename` column on `schema_migrations` (existing rows default to `'init_rag_db.sql'`, which is accurate — every pre-existing row's hash *was* for that file).

## Key decisions and why

- **No new orchestration framework.** The feature was originally sketched (by the user) with a `retrieval/graph.py` file and "2 nodes" — potentially implying a LangGraph-style architecture. Asked directly via `AskUserQuestion` before planning: confirmed the codebase has no graph/node abstraction anywhere (retrieval is a flat `step1..step10` sequence of plain function calls), and the user chose to extend `retrieval_runner.py` with a conditional branch — the same pattern already used for `config.rerank_enabled` — rather than introduce a new architecture alongside the existing one.
- **Multi-file migrations over folding into `init_rag_db.sql`.** Also asked directly. The user's own proposed filename (`sql/03_hybrid_search.sql`) implied a separate file; generalizing `migrations.py` to support that (rather than just appending statements to the base schema file) scales cleanly to future migrations without re-touching `init_rag_db.sql` each time.
- **RRF over combining raw scores.** Cosine distance (bounded, typically 0-1-ish) and `ts_rank` (unbounded, corpus-dependent) are not on comparable scales — averaging or weighting them directly would require tuning a corpus-specific normalization. RRF sidesteps this entirely by only using rank position, not raw score magnitude — the standard reason RRF is used for this exact fusion problem in IR.
- **`chunk_id` added to `RetrievedChunk` specifically for fusion**, not for any other reason — it's the only reliable way to recognize "the same chunk" across two independently-ordered rankings. This required updating both `step4_similarity_search.py`'s SELECT and `step6_reranking.py`'s rebuild (which previously would have silently dropped it, the same class of bug `status`/`area` field-dropping already had to be fixed once for reranking).
- **`HYBRID_SEARCH_ENABLED` defaults to `false`**, unlike `RERANK_ENABLED` (`true`). This is a judgment call, not something the user was asked about: hybrid search is new and hasn't yet been proven against content that actually needs it (see Gotchas), so shipping opt-in was chosen as the safer default.

## Configuration

- `HYBRID_SEARCH_ENABLED` (optional, default `false`) — server-wide default for whether `/chat` runs the fusion path.
- `{"hybrid": bool}` on `POST /chat` — per-request override, `None` (omitted) means "use the server default", identical semantics to the existing `rerank` field.
- `_HYBRID_CANDIDATE_POOL = 20` (module constant, `retrieval_runner.py`) — how many lexical candidates to pull before fusion; not an env var, matching the existing precedent of hardcoded pipeline-size constants (`CHUNK_SIZE_TOKENS`, `_RERANK_CANDIDATE_POOL`).
- `_RRF_K = 60` (module constant) — the standard IR default for RRF's damping constant; not exposed as configuration since there was no reason found to tune it for this corpus.

## Gotchas

- **A lexical match doesn't necessarily survive to the final answer** — it's still subject to `step5_metadata_filter.py`'s existing `status=current` restriction, which runs *after* fusion. Live-tested: a direct `psql` full-text query for the PTO-days question found `01_keyword_distractor.md` as a strong match (`ts_rank ≈ 1.0`), and it did get fused in (`found_by: "both"`) — but the default `/chat` response (no `include_reference`) never shows it, because the metadata filter correctly excludes it downstream (it's untagged, and a `status=current` document exists for that topic). This is the metadata filter working as designed, not a hybrid-search bug — add `{"include_reference": true}` to see the full fused pool before that filter trims it.
- **No live case has yet shown `found_by="lexical"` alone surviving into a final answer.** Every test this session against the 7-doc PTO corpus produced either `found_by="both"` (lexical agreeing with vector) or a lexical-only hit that the metadata filter removed. Hybrid search's core value-add — rescuing a chunk vector search would have missed outright — is implemented and its RRF math is verified by unit test, but not yet demonstrated end-to-end with content that actually needs it (e.g. an exact policy code or acronym).
- **The vector connection is now held open longer.** Previously `retrieval_runner.py` closed its DB connection immediately after the vector-search call; now, when hybrid is enabled, the same connection stays open through the lexical-search call too (simpler than opening a second connection) — a longer-held connection per request, which matters only if this pipeline is ever put under real concurrent load (currently single-request-at-a-time in practice).

## Verification

```bash
# Migration: init_rag_db.sql skipped (unchanged), new file applied
docker restart rag-app && docker logs rag-app --tail 10
# -> "init_rag_db.sql up to date ... skipping"
# -> "03_hybrid_search.sql changed ... applying migration"
# -> "03_hybrid_search.sql applied successfully."

# Backfill + index confirmed
docker exec pgvector psql -U ai_user -d ai_db -c \
  "SELECT count(*) AS total, count(content_tsv) AS has_tsv FROM rag_chunks;"
# -> 7 | 7
docker exec pgvector psql -U ai_user -d ai_db -c "\d rag_chunks"
# -> shows idx_rag_chunks_content_tsv (GIN) and trg_rag_chunks_tsv trigger

# Regression: hybrid omitted (default false) - unchanged from before this feature
curl -X POST http://localhost:8000/chat -d '{"question": "How many PTO days...?"}'
# -> same answer/sources as before, "hybrid": false

# Hybrid on + include_reference (see full fused pool, unfiltered)
curl -X POST http://localhost:8000/chat \
  -d '{"question": "How many PTO days...?", "hybrid": true, "include_reference": true}'
# -> 01_keyword_distractor.md: found_by="both", highest RRF score (0.0328)
#    matches hand-computed RRF unit test (rank-1-in-both = 1/61 + 1/62)
```
