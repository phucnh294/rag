---
title: Upload/Indexing Pipeline — Lab1 Implementation
date: 2026-08-26
type: functionality
area: rag-pipeline-indexing
status: implementation-complete
session_id: n/a
duration: ~90min
files: [Labs Practices/session4-rag/rag_pipeline/api/routes_upload.py, Labs Practices/session4-rag/rag_pipeline/indexing/index_runner.py, Labs Practices/session4-rag/rag_pipeline/indexing/step1_load_input.py, Labs Practices/session4-rag/rag_pipeline/indexing/step2_document_parsing.py, Labs Practices/session4-rag/rag_pipeline/indexing/step3_chunking_strategy.py, Labs Practices/session4-rag/rag_pipeline/indexing/step4_preprocessing.py, Labs Practices/session4-rag/rag_pipeline/indexing/step6_embedding_gen.py, Labs Practices/session4-rag/rag_pipeline/indexing/step7_store_documents.py, Labs Practices/session4-rag/rag_pipeline/indexing/step8_store_chunks.py, Labs Practices/session4-rag/rag_pipeline/config/env_config.py, Labs Practices/session4-rag/rag_pipeline/config/db_connection.py, Labs Practices/session4-rag/rag_pipeline/config/llm_setup.py, Labs Practices/session4-rag/rag_pipeline/shared/file_utils.py, Labs Practices/session4-rag/rag_pipeline/shared/md_frontmatter.py, Labs Practices/session4-rag/rag_pipeline/shared/logger.py]
version: 1
last_updated: 2026-08-26
extraction_method: pair-session
tags: [rag-pipeline, indexing, upload, pgvector, tiktoken, ollama]
keywords: [chunks_indexed, cl100k_base, nomic-embed-text, vector_dims, ON CONFLICT, register_vector]
related: [rag-ai-local/functionality-docs/08262026/01_rag-pipeline-local-dev-setup-fixes.md]
---

## TL;DR
- **What:** Implemented the full Lab1 upload → chunk → embed → store pipeline for `rag_pipeline`, replacing every `NotImplementedError` stub on that path with a working implementation.
- **Why:** `POST /upload` was crashing with an unhandled `NotImplementedError`, which FastAPI surfaces as a plain-text 500 that breaks the UI's `response.json()` call — the whole vertical (route, file save, 8 indexing steps, DB/LLM config) was unimplemented lab scaffolding.
- **Where:** `Labs Practices/session4-rag/rag_pipeline/` — `api/routes_upload.py`, `indexing/*`, `config/*`, `shared/*`.
- **Impact:** `POST /upload` now saves the file, chunks it, embeds each chunk via `nomic-embed-text`, and stores rows in `rag_documents`/`rag_chunks`/`rag_embeddings`. Verified end-to-end through the running `rag-app` container against the real `pgvector` and `nomic-embed-text` containers.

## What it does

The upload/indexing pipeline takes one uploaded `.md` file and turns it into searchable, embedded chunks in Postgres. `POST /upload` (`api/routes_upload.py`) accepts a multipart file, saves it under `input/` via `shared/file_utils.py`, then hands the saved path to `indexing/index_runner.py:run_indexing_martin`, which orchestrates: load the raw file text → split off any YAML frontmatter → chunk the body on a fixed token window → clean each chunk → embed each chunk via Ollama's `nomic-embed-text` model → upsert the parent document row → upsert each chunk and its embedding. The route returns `{"chunks_indexed": <int>}` per the lab's API contract.

## How it works

`chunk_body_martin` (`indexing/step3_chunking_strategy.py`) uses `tiktoken`'s `cl100k_base` encoding — already a project dependency used elsewhere for chat token budgeting — to tokenize the body text, then slides an 800-token window with 120-token overlap across the token array, decoding each window back to text. This gives token-accurate chunk boundaries rather than character- or word-based approximations.

`generate_embeddings_martin` (`indexing/step6_embedding_gen.py`) calls `embed_text_martin` (`config/llm_setup.py`) once per chunk, which POSTs directly to Ollama's REST API (`http://<nomic_host>:<nomic_port>/api/embeddings`) with `{"model": "nomic-embed-text", "prompt": <chunk>}` and reads back `response.json()["embedding"]` — no LangChain wrapper, since the lab allows either raw REST or LangChain and REST needed no new dependency.

`store_chunks_martin` (`indexing/step8_store_chunks.py`) writes the embedding into the `vector` column by formatting the Python `list[float]` as a pgvector text literal (`"[0.1,0.2,...]"`) and casting it in SQL with `%s::vector`, rather than using the separate `pgvector` Python package's `register_vector()` adapter. Both document and chunk/embedding writes use `INSERT ... ON CONFLICT ... DO UPDATE` so re-uploading the same `source_path` (or re-indexing the same `document_id`/`chunk_index` pair) updates in place instead of raising a unique-constraint violation.

## Key decisions and why

- **Format the embedding as a `::vector` text-literal cast instead of adding the `pgvector` PyPI package.** Rejected alternative: `pip install pgvector` and call `register_vector(conn)` so psycopg2 adapts Python lists to `vector` automatically — rejected to avoid a new dependency for what a one-line string format + SQL cast already solves cleanly.
- **Reused `tiktoken` (`cl100k_base`) for both chunk-boundary tokenization (step 3) and per-chunk `token_count` (step 8)** instead of a word/character-based splitter — rejected alternative: `len(text.split())` as a token approximation — rejected because the lab spec calls for token-based chunking specifically (800/120 tokens), and an approximate count would drift from what the embedding/chat models actually see.
- **Left `config/llm_setup.py:chat_martin`, `indexing/step5_metadata_extraction.py`, and the entire `retrieval/` package untouched (still `NotImplementedError` or Lab2/3 stubs).** These belong to `POST /chat`, not `POST /upload` — out of scope for this fix. `step5_metadata_extraction.py` is explicitly marked `[Lab2] stub: return {}` in `rag-structure.md` and is intentionally not wired into `index_runner.py` yet.
- **Added the missing `EMBEDDING_DIM`, `OLLAMA_NOMIC_EMBED_TEXT_HOST`/`_MODEL`, `OLLAMA_LLAMA31_HOST`/`_MODEL` vars to the local `rag_pipeline/.env`** (previously only `_HOST_PORT`/`_PORT` were present) rather than inventing new var names — matched the naming already used in `session4-rag/.env.rag` so local and containerized configs read the same keys, just with `localhost` instead of `host.docker.internal` for the host values.

## Configuration

- `EMBEDDING_DIM` — must equal the actual embedding model's output dimension (768 for `nomic-embed-text`); the `rag_embeddings.embedding` column is created as `vector({{EMBEDDING_DIM}})` by `sql/migrations.py`, so a mismatch here would only surface as a Postgres error on insert (dimension mismatch), not at config-load time — `load_config_martin` does not cross-check it against what the model actually returns.
- `OLLAMA_NOMIC_EMBED_TEXT_HOST` / `_HOST_PORT` / `_MODEL` — target and model name for `embed_text_martin`'s REST call. Wrong host/port surfaces as a `requests` connection error; wrong model name surfaces as a 404-style Ollama error inside `response.raise_for_status()`.
- `shared/file_utils.py:save_upload_martin` sanitizes the filename to `[A-Za-z0-9._-]` and forces a `.md` extension — an uploaded filename with path separators (e.g. `../../x.md`) is reduced to just its basename before being written under `input/`.

## Gotchas

- **FastAPI's default error handler for an unhandled Python exception (any exception, not just `NotImplementedError`) returns plain text `"Internal Server Error"` with a 500 status, not JSON.** Any client code that unconditionally calls `response.json()` on the result (as `ui/index.html`'s `upload()` does) will throw a confusing `SyntaxError: Unexpected token 'I', "Internal S"... is not valid JSON` instead of surfacing the real error. This will resurface for any *other* uncaught exception in the upload path (e.g. Postgres or Ollama being down) — the route currently has no explicit try/except turning failures into a structured JSON error response.
- **The `rag-app` Docker container mounts `./rag_pipeline:/app` as a live volume**, so editing source files takes effect without rebuilding the image — but `main.py` has no `--reload` flag, so a plain `docker restart rag-app` is required to pick up code changes; editing files alone does nothing until the process restarts.
- **Re-running the indexing pipeline on the same file is idempotent** (`ON CONFLICT` on both `rag_documents.source_path` and `rag_chunks (document_id, chunk_index)`), but only as long as the chunk count doesn't shrink between runs — if a smaller edit produces fewer chunks, higher-numbered leftover `chunk_index` rows from the previous version are not deleted, since `store_chunks_martin` only upserts, never deletes stale chunk rows for a document.

## Verification

Upload a file directly against the running `rag-app` container and confirm the JSON contract:
```
curl.exe -s -X POST http://localhost:8000/upload -F "file=@upload_test.md"
```
Expected:
```
{"chunks_indexed":1}
```

Confirm the rows actually landed with the right shape:
```
docker exec pgvector psql -U ai_user -d ai_db -c "SELECT source_path, length(raw_content) FROM rag_documents ORDER BY created_at DESC LIMIT 3;" -c "SELECT document_id, chunk_index, token_count, length(content) FROM rag_chunks ORDER BY chunk_index DESC LIMIT 3;" -c "SELECT chunk_id, model, vector_dims(embedding) FROM rag_embeddings ORDER BY id DESC LIMIT 3;"
```
Expected: one `rag_documents` row for the uploaded path, one `rag_chunks` row with a non-zero `token_count`, and one `rag_embeddings` row with `vector_dims = 768` and `model = nomic-embed-text`. Re-running the same `curl` command against the same file should return the same `chunks_indexed` count without error (upsert path), not a unique-constraint failure.
