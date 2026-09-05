---
title: Retrieval/Chat Pipeline — Lab1 Implementation
date: 2026-08-26
type: functionality
area: rag-pipeline-retrieval
status: implementation-complete
session_id: n/a
duration: ~45min
files: [Labs Practices/session4-rag/rag_pipeline/api/routes_chat.py, Labs Practices/session4-rag/rag_pipeline/retrieval/retrieval_runner.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step1_receive_question.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step2_normalize_question.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step3_embed_question.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step4_similarity_search.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step7_context_assembly.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step8_prompt_building.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step9_llm_call.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step10_response.py, Labs Practices/session4-rag/rag_pipeline/config/llm_setup.py, Labs Practices/session4-rag/rag_pipeline/shared/pgvector_utils.py, Labs Practices/session4-rag/rag_pipeline/indexing/step8_store_chunks.py]
version: 1
last_updated: 2026-08-26
extraction_method: pair-session
tags: [rag-pipeline, retrieval, chat, pgvector, ollama, llama3.1]
keywords: [POST /chat, cosine distance, embedding <=>, api/generate, ReadTimeout, host.docker.internal]
related: [rag-ai-local/functionality-docs/08262026/02_upload-indexing-pipeline-lab1-implementation.md]
---

## TL;DR
- **What:** Implemented the full Lab1 retrieval pipeline (question → embed → vector search → prompt → LLM answer) so `POST /chat` returns a real `{"answer", "sources"}` instead of crashing on `NotImplementedError`.
- **Why:** Every step in `retrieval/` and the `/chat` route were unimplemented lab stubs, same pattern as the upload pipeline fixed earlier the same day.
- **Where:** `Labs Practices/session4-rag/rag_pipeline/` — `api/routes_chat.py`, `retrieval/*`, `config/llm_setup.py:chat_martin`, plus a new shared helper `shared/pgvector_utils.py`.
- **Impact:** `POST /chat` verified end-to-end against the running `rag-app`/`pgvector`/`llama31-8b` containers — correct answer, correct de-duplicated sources, ~66 seconds total latency (CPU-only `llama3.1:8b` generation).

## What it does

The retrieval pipeline answers a natural-language question against whatever `.md` files have already been indexed by the upload pipeline. `POST /chat` (`api/routes_chat.py`) accepts `{"question": str}` and calls `retrieval/retrieval_runner.py:run_retrieval_martin`, which: validates and normalizes the question, embeds it via the same `nomic-embed-text` model used at index time, runs a cosine-distance top-k search against `rag_embeddings` joined back to `rag_chunks`/`rag_documents`, assembles the retrieved chunk text into one context block, builds a final prompt, calls `llama3.1:8b` for the answer, and shapes the response as `{"answer": str, "sources": list[str]}` with de-duplicated `source_path`s.

## How it works

`similarity_search_martin` (`retrieval/step4_similarity_search.py`) runs `ORDER BY embedding <=> %s::vector LIMIT %s` — pgvector's `<=>` operator is cosine *distance* (0 = identical), so the function converts it to a similarity `score = 1.0 - distance` before returning `RetrievedChunk` rows, joined against `rag_chunks` and `rag_documents` in the same query so no second round-trip is needed for `content`/`source_path`.

The embedding literal formatting (`"[0.1,0.2,...]"` cast with `::vector`) was pulled out of `indexing/step8_store_chunks.py` into a new `shared/pgvector_utils.py:to_vector_literal_martin`, since retrieval's similarity search needed the exact same encoding for the *question* embedding that indexing already used for chunk embeddings — keeping one implementation avoids the two drifting apart if the literal format ever needs to change.

`call_llm_martin` → `config/llm_setup.py:chat_martin` calls Ollama's `POST /api/generate` (not `/api/chat`) with `{"model": "llama3.1:8b", "prompt": <built prompt>, "stream": false}` — the same endpoint shape already confirmed working via a manual `curl` test earlier in this project. `step5_metadata_filter.py` and `step6_reranking.py` remain Lab2/Lab3 pass-through stubs per `rag-structure.md` and were not touched; `retrieval_runner.py` still calls them so the pipeline shape matches the eventual Lab2/Lab3 version without needing to be rewired later.

## Key decisions and why

- **Used `POST /api/generate` for `chat_martin`, not `POST /api/chat`.** Rejected alternative: Ollama's chat-style endpoint (`/api/chat` with a messages array) — rejected because the already-verified manual test against this exact setup (`curl .../api/generate -d '{"model": "llama3.1:latest", "prompt": ..., "stream": false}'`) used `/api/generate`, and `step8_prompt_building.py` already produces one flat prompt string rather than a structured messages list, so `/api/generate` needed no extra shaping.
- **Raised `chat_martin`'s request timeout from 120s to 300s.** The first end-to-end test against `llama31-8b` (CPU-only — the GPU `deploy:` block in `docker-compose.yml` is commented out) hit `requests.exceptions.ReadTimeout` at 120s and surfaced as the same generic "Internal Server Error" text-body problem documented for the upload path. Rejected alternative: leave it at 120s and treat slow answers as a hard failure — rejected because the model reliably takes ~60-90s to answer on this hardware, so 120s left no margin.
- **Extracted `to_vector_literal_martin` into `shared/pgvector_utils.py`** instead of duplicating the embedding-formatting logic a second time in `retrieval/step4_similarity_search.py`. Rejected alternative: copy the private `_to_vector_literal` helper from `indexing/step8_store_chunks.py` again — rejected as needless duplication of a non-trivial formatting/casting detail now used by two independent pipelines.
- **`routes_chat.py` catches `ValueError` from `receive_question_martin` and converts it to `HTTPException(400, ...)`**, unlike the upload route which lets any exception fall through to FastAPI's default plain-text 500. This was added because "reject empty/missing input" is `step1_receive_question.py`'s explicit, expected job per `rag-structure.md` — a genuinely empty question is a normal validation case, not a system failure, so it gets a proper 400 JSON error instead of the same "Internal Server Error"-is-not-JSON trap documented for `/upload`.

## Configuration

- `chat_martin`'s `timeout=300` (`config/llm_setup.py`) — the ceiling on how long `/chat` will wait for `llama3.1:8b` before raising `ReadTimeout` (which still surfaces as an unhandled 500, since only the question-validation `ValueError` is caught in the route). On faster hardware or with GPU passthrough enabled this could be lowered; on this CPU-only setup, raising it further may be needed for longer prompts/contexts.
- `similarity_search_martin`'s `top_k` (default `5`, in `retrieval/step4_similarity_search.py`) — how many chunks get pulled into the context window before prompt building; not currently exposed as an env var or request parameter.

## Gotchas

- **A slow LLM response looks identical to a crashed one from the client's point of view** — both a `NotImplementedError` and a `requests.exceptions.ReadTimeout` inside `chat_martin` propagate up as FastAPI's plain-text 500 "Internal Server Error", which `ui/index.html`'s unconditional `response.json()` call turns into the same confusing `SyntaxError` reported for `/upload`. There is currently no distinct timeout-specific error message returned to the UI.
- **`similarity_search_martin` will happily return chunks from *any* previously indexed document**, not just ones related to the current session's testing — a `/chat` call during this verification returned sources from both a deliberately uploaded test file and a QandA markdown file uploaded independently through the browser UI. This is correct top-k-across-the-whole-corpus behavior, not a bug, but it means answers can pull in unexpected sources once more than one document has been indexed. `step5_metadata_filter.py` (Lab2) is where per-document/area scoping would eventually get added.
- **`docker restart rag-app` is required after every code change**, same as for the upload pipeline — the container has no `--reload`, so editing `retrieval/*.py` files alone has no effect on an already-running process.

## Verification

```
curl -s -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"question": "What is this test document about?"}'
```
Actual result observed:
```
{"answer":"This test document is about verifying that the /upload endpoint works correctly, including saving the file, chunking it, generating embeddings, and storing everything in Postgres.","sources":["/app/input/upload_test.md","/app/input/08262026_Rag_Pipeline_Local_Run_Failures.md"]}
```
Latency: ~66 seconds wall-clock (CPU-only `llama3.1:8b` generation dominates).

Confirm the underlying documents an answer's sources point to:
```
docker exec pgvector psql -U ai_user -d ai_db -c "SELECT source_path, created_at FROM rag_documents ORDER BY created_at;"
```
