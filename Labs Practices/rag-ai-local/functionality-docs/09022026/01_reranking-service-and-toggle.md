---
title: Cross-Encoder Reranking Service + Enable/Disable Toggle
date: 2026-09-02
type: functionality
area: rag-pipeline-retrieval
status: implementation-complete
session_id: n/a
duration: ~90min
files: [Labs Practices/session4-rag/rerank-service/app.py, Labs Practices/session4-rag/rerank-service/Dockerfile, Labs Practices/session4-rag/rerank-service/requirements.txt, Labs Practices/session4-rag/docker-compose.yml, Labs Practices/session4-rag/rag_pipeline/config/env_config.py, Labs Practices/session4-rag/rag_pipeline/config/llm_setup.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step6_reranking.py, Labs Practices/session4-rag/rag_pipeline/retrieval/retrieval_runner.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step10_response.py, Labs Practices/session4-rag/rag_pipeline/api/routes_chat.py, Labs Practices/session4-rag/rag_pipeline/ui/index.html]
version: 1
last_updated: 2026-09-02
extraction_method: pair-session
tags: [rag-pipeline, reranking, cross-encoder, docker, ui-toggle]
keywords: [ms-marco-MiniLM-L-6-v2, rerank-service, RERANK_ENABLED, rerank_scores_martin, dataclasses.replace]
related: [rag-ai-local/QandA/09022026_Docker_Restart_Does_Not_Load_New_Env_Vars.md, rag-ai-local/functionality-docs/09022026/01_handoff-reranking-and-ui-toggle.md]
---

## TL;DR
- **What:** Implemented `retrieval/step6_reranking.py` (previously a Lab3+ stub) as a real cross-encoder reranker, served from a new dedicated `rerank-service` Docker container, with both a server-wide `RERANK_ENABLED` env toggle and a per-request UI checkbox override.
- **Why:** The vector-search step (`step4_similarity_search.py`) only ranks by bi-encoder cosine distance; a cross-encoder reranker that jointly scores `(question, chunk)` pairs is more precise, and the user wanted an easy way to A/B compare answers with and without it.
- **Where:** New `session4-rag/rerank-service/` container; `rag_pipeline/config/`, `retrieval/`, `api/routes_chat.py`, `ui/index.html`.
- **Impact:** Confirmed working end-to-end through `/chat` (after a `docker compose up -d`/full stack recreation was needed to pick up new env vars — see the Docker-restart QandA doc), including the per-request toggle round-tripping correctly and the retrieval-scores debug panel added afterward. See Update below.

**Update (later same day):** end-to-end verification landed successfully — `docker compose down && docker compose up -d` picked up `RERANK_HOST`/`RERANK_HOST_PORT`/`RERANK_ENABLED`, and `/chat` confirmed working with both `rerank: true` and `rerank: false`, correct `"reranked"` flag each time, and visibly different `sources` between the two modes. See the Verification section below for the actual commands/output, and `03_metadata-filtering-problems-and-tradeoffs.md` for what was discovered *using* this reranker (it turned out to have real accuracy problems on adversarial content, fixed separately via metadata filtering).

## What it does

Reranking sits between the vector-search step and context assembly in the `/chat` retrieval pipeline. Instead of trusting `step4_similarity_search.py`'s cosine-distance ordering directly, `retrieval_runner.py` now pulls a larger candidate pool (20 chunks instead of the final 5) from step4, and `step6_reranking.py:rerank_chunks_martin` re-scores all 20 against the question using a cross-encoder, then truncates to the best 5. This can be turned off two ways: a server-wide `RERANK_ENABLED` env var (default `true`), or a per-request `{"rerank": true|false}` field on `POST /chat` that overrides the server default just for that call — surfaced in the UI as a "Rerank" checkbox next to the chat input.

## How it works

**The reranker itself** is a new, separate container (`session4-rag/rerank-service/`) — a minimal FastAPI app (`app.py`) wrapping `sentence_transformers.CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")`, exposing `POST /rerank {"query": str, "documents": list[str]} -> {"scores": list[float]}`. The model loads once at process start (not lazily per-request) and its weights are baked into the Docker image at build time via a `RUN python -c "...CrossEncoder(...)"` step in the `Dockerfile` — the same "pre-pull at build time" pattern already used by `llm-llama-3-8b`/`llm-nomic-embed-text`'s `ollama pull` steps, so the container never needs internet access at runtime and doesn't re-download after every restart.

**Why a separate container instead of embedding it in `rag-app`:** `sentence-transformers` pulls in `torch`, which is ~2GB even with the CPU-only wheel index (`--extra-index-url https://download.pytorch.org/whl/cpu`). Every other model call in this codebase (`embed_text_martin`, `chat_martin`) is a thin `requests`-based HTTP client hitting a dedicated model-serving container — bundling a heavy ML dependency directly into `rag-app`'s otherwise-minimal `python:3.12-slim` image would have broken that pattern and bloated the one image that gets rebuilt/iterated on most often.

**`config/llm_setup.py:rerank_scores_martin(config, query, documents)`** follows the exact same thin-client shape as `embed_text_martin` — POST to `http://{rerank_host}:{rerank_port}/rerank`, `raise_for_status()`, return `response.json()["scores"]`. `step6_reranking.py:rerank_chunks_martin` calls it, zips scores back onto the original `RetrievedChunk` dicts (replacing the old cosine-distance-derived `score` with the cross-encoder's score), sorts descending, and returns the top `top_n`.

**The enable/disable toggle** exists at two levels. `RagConfig.rerank_enabled` (from `RERANK_ENABLED` env var, default `true`) is the server-wide default, read once at `load_config_martin()` time. `api/routes_chat.py`'s `ChatRequest` gained an optional `rerank: bool | None` field; when a request sets it explicitly, the route does `config = dataclasses.replace(config, rerank_enabled=request.rerank)` — producing a per-request copy of the config with just that one field overridden, with zero changes needed to `retrieval_runner.py`'s branching logic (it already just reads `config.rerank_enabled`). The response now includes an additive `"reranked": bool` field (beyond the lab's fixed `{"answer", "sources"}` contract) reporting whether reranking actually ran for that specific request, so the UI checkbox's effect is visibly confirmable per-message instead of only inferable from `docker logs`.

**Per-request debug logging:** `retrieval_runner.py` logs the top-5 `(source_path, score)` ordering twice per request — once right after vector search (`"vector-search ranking"`) and once after reranking if it ran (`"reranked ranking"`) — via `shared/logger.py:get_logger_martin`. This is the primary way to visually confirm reranking actually changed the ordering, since with only 2-3 documents indexed so far the UI-visible `sources` list often looks the same either way.

## Key decisions and why

- **A per-request override via `dataclasses.replace`, not a new function parameter threaded through `retrieval_runner.py`.** Rejected alternative: add an explicit `rerank_override: bool | None` parameter to `run_retrieval_martin` and thread it down to where `config.rerank_enabled` is read — rejected because `RagConfig` is a plain dataclass, so overriding one field for one request's config object needed no changes at all to the already-implemented `config.rerank_enabled` branching logic in `retrieval_runner.py`.
- **Made `RERANK_HOST`/`RERANK_HOST_PORT` unconditionally required in `load_config_martin`**, even though `RERANK_ENABLED` can be `false`. Rejected alternative (the original implementation): only require them when `RERANK_ENABLED=true`. Rejected once the per-request override was added — a request can force `rerank: true` even when the server default is `false`, and that would otherwise hit an empty `rerank_host`/`rerank_port` at call time instead of failing fast at startup.
- **`"reranked": bool` added to the `/chat` response** even though `rag-structure.md`'s API contract table fixes it to `{"answer": str, "sources": list[str]}`. Treated as an acceptable additive field (existing consumers reading only known keys are unaffected) rather than a contract violation, since the user's explicit goal was being able to *validate* reranking is doing something — an extra field is the simplest way to make that visible in the UI itself instead of requiring a `docker logs` check every time.

## Configuration

- `RERANK_ENABLED` (`rag_pipeline/.env`, `session4-rag/.env.rag`) — server-wide default when a `/chat` request doesn't specify `rerank` explicitly. Accepts `true`/`false`/`1`/`0`/`yes`/`no`/`on`/`off` (case-insensitive), defaults to `true` if unset.
- `RERANK_HOST` / `RERANK_HOST_PORT` — where to reach the rerank-service. Must be `host.docker.internal` (container context, `.env.rag`) or `localhost` (local `py main.py` context, `rag_pipeline/.env`) — same host-resolution split already established for `OLLAMA_LLAMA31_HOST`/`OLLAMA_NOMIC_EMBED_TEXT_HOST`.
- `RERANK_HOST_PORT` in the root `session4-rag/.env` (a *different* file from `.env.rag`!) is what `docker-compose.yml`'s `${RERANK_HOST_PORT}:8080` port mapping actually resolves against — Compose's own `${...}` substitution only reads the shell environment or a root `.env` in the compose project directory, never a service's `env_file:` list. Set to `8088`.
- `retrieval_runner.py`'s `_RERANK_CANDIDATE_POOL = 20` / `_RERANK_TOP_N = 5` — hardcoded module constants, not env vars, matching the existing precedent of `step3_chunking_strategy.py`'s `CHUNK_SIZE_TOKENS`/`CHUNK_OVERLAP_TOKENS` (fixed algorithmic constants vs. runtime infra config).

## Gotchas

- **`docker restart` does not inject newly-added `env_file` variables into an already-created container** — only recreating it (`docker compose up -d <service>`) re-reads the compose file's `env_file:` list against the container's environment. This bit us directly: `RERANK_HOST`/`RERANK_HOST_PORT`/`RERANK_ENABLED` were added to `.env.rag` after `rag-app`'s container already existed, so `docker restart rag-app` left them entirely absent from the container's real environment — see the paired QandA doc for the full trace of how this manifested and was diagnosed.
- **A missing env var can be silently "filled in" from the wrong source.** `main.py` calls `load_dotenv()` (default `override=False`), which only skips a var if it's *already present* in `os.environ` — if Docker's `env_file` injection never happened for a var (per the gotcha above), `load_dotenv()` will happily set it from the volume-mounted `rag_pipeline/.env` instead, which has `localhost`-flavored values meant for a *local, non-Docker* run. The failure this produces (`Connection refused` to `localhost:8088`) looks like a networking bug, not a stale-container bug.
- **Reranking needs a genuinely larger candidate pool to matter.** Reranking the same top-5 that vector search already picked barely changes anything; `retrieval_runner.py` requests 20 candidates specifically so the cross-encoder has real alternatives to promote/demote.

## Verification

Confirmed so far (rerank-service in isolation, direct HTTP call, bypassing rag-app):
```
curl -s -X POST http://localhost:8088/rerank -H "Content-Type: application/json" \
  -d '{"query": "What is Playwright used for?", "documents": ["Playwright is a browser automation framework for end-to-end testing.", "The capital of France is Paris.", "Postgres is a relational database."]}'
→ {"scores":[6.196985244750977,-11.20549201965332,-11.033203125]}
```
Clear separation between the relevant document (+6.2) and irrelevant ones (-11), confirming the cross-encoder model itself works correctly.

**End-to-end, confirmed after the container-recreation fix (`docker compose down && docker compose up -d`):**
```
curl -s -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"question": "What is this test document about?"}'
→ HTTP 200, "reranked": true

curl -s -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"question": "What is this test document about?", "rerank": false}'
→ HTTP 200, "reranked": false, different (unreranked) sources
```
`docker logs rag-app` showed the `"vector-search ranking"` / `"reranked ranking"` lines disagreeing substantially in order, confirming the cross-encoder is genuinely doing something, not passing through unchanged.
