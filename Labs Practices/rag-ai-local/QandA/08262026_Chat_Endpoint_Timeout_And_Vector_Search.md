---
title: /chat Endpoint Timeout and pgvector Cosine Search
date: 2026-08-26
type: qanda
area: rag-pipeline-retrieval
status: implementation-complete
session_id: n/a
duration: ~45min
issue_type: bug
severity: medium
resolution_date: 2026-08-26
tags: [rag-pipeline, retrieval, ollama, pgvector, timeout]
keywords: [ReadTimeout, api/generate, embedding <=>, llama3.1:8b, HTTPConnectionPool]
related: [rag-ai-local/QandA/08262026_Rag_Pipeline_Local_Run_Failures.md, rag-ai-local/functionality-docs/08262026/03_retrieval-chat-pipeline-lab1-implementation.md]
---

## TL;DR
- **What:** `POST /chat` failed with the same "Internal Server Error is not valid JSON" symptom as the earlier `/upload` bug, this time caused by a `requests.exceptions.ReadTimeout` against `llama31-8b` rather than a missing implementation.
- **Why:** `llama3.1:8b` runs CPU-only in this environment (no GPU passthrough configured), so a single answer reliably takes 60-90+ seconds — longer than the initial 120s HTTP client timeout in some cases.
- **Where:** `Labs Practices/session4-rag/rag_pipeline/config/llm_setup.py:chat_martin`.
- **Impact:** Raised the timeout to 300s; `/chat` now consistently returns a correct answer with de-duplicated sources in ~66s.

## Q1: Why did `POST /chat` return `Internal Server Error` / a JSON parse error even after `retrieval_runner.py` was fully implemented?

**Answer:** `chat_martin` (`config/llm_setup.py`) called Ollama's `/api/generate` with `requests.post(..., timeout=120)`. On this machine, `llama31-8b` runs without GPU acceleration (the `deploy: resources: reservations: devices: [{capabilities: [gpu]}]` block in `docker-compose.yml` is commented out), so a single generation call took longer than 120 seconds, raising `requests.exceptions.ReadTimeout`. Like any other unhandled exception in a FastAPI route, this became a plain-text 500 response, which the UI's `response.json()` then failed to parse — the exact same failure shape as the earlier `/upload` `NotImplementedError` bug, but with a different root cause underneath.

**Evidence:**
```
File "/app/config/llm_setup.py", line 29, in chat_martin
    response = requests.post(...)
requests.exceptions.ReadTimeout: HTTPConnectionPool(host='host.docker.internal', port=11436): Read timed out. (read timeout=120)
```
Client-side result of that same request:
```
Internal Server Error
```

**Root cause:** CPU-only LLM inference exceeding a too-short HTTP client timeout.
**Fix:** `Labs Practices/session4-rag/rag_pipeline/config/llm_setup.py` — raised `chat_martin`'s `requests.post(..., timeout=...)` from `120` to `300`.

## Q2: How does `similarity_search_martin` rank chunks, and is a lower or higher `score` better?

**Answer:** It orders by pgvector's `<=>` operator, which is **cosine distance** (0 = identical vectors, larger = less similar) — so `ORDER BY embedding <=> %s::vector LIMIT %s` already returns the closest matches first. The function then converts that distance into a similarity score via `score = 1.0 - distance` before returning `RetrievedChunk` rows, so in the returned data, **higher `score` is more relevant** (the reverse of the raw distance value used in the `ORDER BY`).

**Evidence:**
```python
# retrieval/step4_similarity_search.py
SELECT c.content, d.source_path, (e.embedding <=> %s::vector) AS distance
...
ORDER BY e.embedding <=> %s::vector
LIMIT %s
...
RetrievedChunk(content=content, source_path=source_path, score=1.0 - distance)
```

**Root cause:** N/A — design question, not a bug.
**Fix:** N/A — documented for future readers of `retrieval/step4_similarity_search.py:24`.

## Q3: Why do sources from unrelated documents show up in a `/chat` answer even when only one document seems relevant?

**Answer:** `similarity_search_martin` has no per-document or per-session scoping — it searches `rag_embeddings` across every document ever indexed into this Postgres instance, then returns the top-`k` (default 5) closest chunks regardless of source. During verification, a `/chat` call answered correctly using a deliberately-uploaded test file but *also* pulled in a chunk from an unrelated QandA markdown file that had been uploaded independently through the browser UI — this is expected top-k-over-the-whole-corpus behavior, not a bug.

**Evidence:**
```
{"answer":"...", "sources":["/app/input/upload_test.md","/app/input/08262026_Rag_Pipeline_Local_Run_Failures.md"]}
```
```sql
SELECT source_path, created_at FROM rag_documents ORDER BY created_at;
--  /app/input/upload_test.md
--  /app/input/08262026_Rag_Pipeline_Local_Run_Failures.md
```

**Root cause:** `retrieval/step5_metadata_filter.py` is an intentional Lab2 stub (`rag-structure.md`) that passes candidates through unfiltered — there is no scoping by `area`/`status`/`tags` yet.
**Fix:** N/A for Lab1 — implement `filter_by_metadata_martin` when Lab2 is reached to scope candidates before the vector search.
