---
title: "Handoff: RAG Pipeline Lab1 (Upload + Retrieval) Complete"
date: 2026-08-26
type: session-handoff
area: rag-pipeline
status: superseded
session_id: n/a
next_action: "Superseded — see rag-ai-local/functionality-docs/08292026/01_handoff-gemini-provider-and-reliability-fixes.md"
tags: [rag-pipeline, lab1, upload, retrieval, chat, handoff]
keywords: [chunks_indexed, POST /chat, POST /upload, psycopg2-binary, ai_user, llama3.1:8b]
related: [rag-ai-local/functionality-docs/08262026/01_rag-pipeline-local-dev-setup-fixes.md, rag-ai-local/functionality-docs/08262026/02_upload-indexing-pipeline-lab1-implementation.md, rag-ai-local/functionality-docs/08262026/03_retrieval-chat-pipeline-lab1-implementation.md, rag-ai-local/QandA/08262026_Rag_Pipeline_Local_Run_Failures.md, rag-ai-local/QandA/08262026_Chat_Endpoint_Timeout_And_Vector_Search.md]
---

## TL;DR
- **What:** Got `Labs Practices/session4-rag/rag_pipeline` fully working end-to-end for Lab1 — local dev environment, `POST /upload` (index a `.md` file), and `POST /chat` (ask a question, get an answer + sources).
- **Why:** The entire pipeline was lab scaffolding with every non-trivial function raising `NotImplementedError`; the user's original ask was "the upload doesn't work," which traced back to the whole pipeline being unimplemented, then extended to "make retrieval work" too.
- **Where:** Nearly every file under `rag_pipeline/config/`, `rag_pipeline/indexing/`, `rag_pipeline/retrieval/`, `rag_pipeline/shared/`, `rag_pipeline/api/`, plus `rag_pipeline/.env` and `rag_pipeline/requirements.txt`.
- **Impact:** Both `POST /upload` and `POST /chat` verified working against the live Docker stack (`rag-app`, `pgvector`, `llama31-8b`, `nomic-embed-text`) — see Current Status for the exact commands and results.

## Current Status

Both Lab1 API endpoints work end-to-end against the real running stack:
- `POST /upload` → `{"chunks_indexed":1}` (verified twice — one fresh insert, one re-upload exercising the `ON CONFLICT` upsert path).
- `POST /chat` → real answer + correct de-duplicated sources, ~66s latency (CPU-only `llama3.1:8b`).
- 2 documents / 2 chunks / 2 embeddings confirmed present in Postgres (`rag_documents`, `rag_chunks`, `rag_embeddings` — verified via direct `psql` query).
- Local (`py main.py`, outside Docker) run path also confirmed working after the Python 3.14 dependency and env-loading fixes (see doc `01_`).

Everything in this handoff has been executed and its output observed in this session — none of it is untested code.

## COMPLETED

- **Local dev environment fixed** — `py main.py` runs clean outside Docker. Confirmed by: `py main.py` → `Uvicorn running on http://0.0.0.0:8000`. Details in `01_rag-pipeline-local-dev-setup-fixes.md`.
- **Upload/indexing pipeline (Lab1) fully implemented** — `api/routes_upload.py`, `shared/file_utils.py`, `shared/md_frontmatter.py`, `shared/logger.py`, `config/env_config.py`, `config/db_connection.py`, `config/llm_setup.py:embed_text_martin`, `indexing/step1` through `step4`, `step6`–`step8`, `index_runner.py`. Confirmed by: `curl -X POST http://localhost:8000/upload -F "file=@upload_test.md"` → `{"chunks_indexed":1}`, then verified via `psql` that `rag_documents`/`rag_chunks`/`rag_embeddings` rows exist with `vector_dims(embedding) = 768`. Details in `02_upload-indexing-pipeline-lab1-implementation.md`.
- **Retrieval/chat pipeline (Lab1) fully implemented** — `api/routes_chat.py`, `retrieval/retrieval_runner.py`, `step1`–`step4`, `step7`–`step10`, `config/llm_setup.py:chat_martin`, new `shared/pgvector_utils.py`. Confirmed by: `curl -X POST http://localhost:8000/chat -d '{"question": "What is this test document about?"}'` → correct answer + sources. Details in `03_retrieval-chat-pipeline-lab1-implementation.md`.

## NOT DONE / STILL OPEN

- `retrieval/step5_metadata_filter.py` and `retrieval/step6_reranking.py` — still Lab2/Lab3 pass-through stubs, **intentionally** not implemented (per `rag-structure.md`, not a bug).
- `indexing/step5_metadata_extraction.py` — still Lab2 stub returning `{}`, **intentionally** not implemented.
- `api/routes_upload.py` has **no try/except at all** — any failure (Postgres down, Ollama down, bad file) surfaces as FastAPI's default plain-text 500, which the UI's `response.json()` cannot parse (the exact bug pattern that started this whole session). `api/routes_chat.py` only catches `ValueError` from question validation — a `ReadTimeout` or DB error there still hits the same plain-text-500 trap.
- Port collision between local `py main.py` and the `rag-app` Docker container (both bind host port `8000`) — documented as an operational rule ("stop one before running the other"), not fixed in code.
- `Labs Practices/session4-rag/.env.pgvector` on disk still says `POSTGRES_USER=postgres`/`POSTGRES_PASSWORD=vbpass12#`, but the **live** `pgvector` container is actually running on `ai_user`/`ai_pass` (baked in at first init, before `.env.pgvector` was edited). `rag_pipeline/.env` was updated to match the live container, but the source-of-truth `.env.pgvector` file itself was never reconciled — if that container/volume is ever recreated from scratch, it will pick up `.env.pgvector`'s current values and `rag_pipeline/.env` would need to change again.
- No automated test suite (pytest or otherwise) exists anywhere in `rag_pipeline/` — every verification in this session was a manual `curl` + `psql` check, not a repeatable test.

## NEXT ACTION

Two reasonable next steps, pick one:
1. **Implement Lab2** — `indexing/step5_metadata_extraction.py` (parse frontmatter into title/date/area/status/tags/summary) and `retrieval/step5_metadata_filter.py` (scope candidates by those fields before vector search). This directly addresses the "unrelated document shows up as a source" behavior documented in `08262026_Chat_Endpoint_Timeout_And_Vector_Search.md` Q3.
2. **Harden error handling** — wrap `api/routes_upload.py:upload_martin` and the non-`ValueError` paths of `api/routes_chat.py:chat_martin` so failures return structured JSON (e.g. `HTTPException` with a real status code) instead of FastAPI's default plain-text 500 that breaks the UI's `response.json()` call.

To resume and re-verify the current state:
```
docker restart rag-app
curl -s -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"question": "What is this test document about?"}'
```

## CONTEXT THE NEXT SESSION CANNOT DERIVE FROM CODE

- **Decision:** Used Ollama's `POST /api/generate` (not `/api/chat`) for `chat_martin`. **Reason:** the user had already manually verified `/api/generate` works against this exact Ollama setup earlier in the project (a raw `curl` test with `model`, `prompt`, `stream: false`), and `step8_prompt_building.py` produces one flat prompt string, which `/api/generate` consumes directly. **Rejected alternative:** `/api/chat`'s messages-array format — would have needed extra shaping for no benefit here.
- **Decision:** pgvector embeddings are inserted/queried via a hand-built `"[0.1,0.2,...]"` string literal cast with `::vector` (`shared/pgvector_utils.py:to_vector_literal_martin`), not the `pgvector` PyPI package's `register_vector()` adapter. **Reason:** avoids adding a new dependency for a one-line formatting need. **Rejected alternative:** `pip install pgvector` + `register_vector(conn)`.
- **Trap:** A slow LLM response and a crashed endpoint look **identical** to the client — both `NotImplementedError` and `requests.exceptions.ReadTimeout` become FastAPI's plain-text `"Internal Server Error"`, which breaks `ui/index.html`'s unconditional `response.json()` call the same way. **What actually happens:** the very first `/chat` test failed this way at a 120s timeout; raising `chat_martin`'s `requests.post(timeout=...)` to 300s fixed it, since `llama31-8b` runs CPU-only (no GPU passthrough) and reliably takes 60-90+ seconds per answer.
- **Ground truth:** the running `pgvector` container's actual live credentials are `ai_user`/`ai_pass`, not whatever `session4-rag/.env.pgvector` currently says on disk. **Verified where:** `docker inspect pgvector --format '{{range .Config.Env}}{{println .}}{{end}}'` — Postgres only applies `POSTGRES_*` env vars on first init against an empty data volume, so editing the env file after the fact does nothing to a container whose volume already has data.
- **Ground truth:** `docker-compose.yml`'s `rag-app` service mounts `./rag_pipeline:/app` live, so source edits take effect without an image rebuild — but `CMD ["python", "main.py"]` has no `--reload`, so `docker restart rag-app` is required after every code change; editing files alone does nothing to the running process. **Verified where:** `Labs Practices/session4-rag/rag_pipeline/Dockerfile:10` and `Labs Practices/session4-rag/docker-compose.yml:32-33`.
