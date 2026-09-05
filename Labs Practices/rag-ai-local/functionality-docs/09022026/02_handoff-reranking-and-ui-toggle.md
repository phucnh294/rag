---
title: "Handoff: Reranking Service + UI Toggle (blocked on container recreation)"
date: 2026-09-02
type: session-handoff
area: rag-pipeline-retrieval
status: superseded
session_id: n/a
next_action: "Superseded — see rag-ai-local/functionality-docs/09022026/04_handoff-metadata-filtering-complete.md"
supersedes: rag-ai-local/functionality-docs/08292026/01_handoff-gemini-provider-and-reliability-fixes.md
tags: [rag-pipeline, reranking, cross-encoder, docker, ui-toggle, handoff]
keywords: [rerank-service, RERANK_ENABLED, RERANK_HOST, docker compose up, dataclasses.replace, reranked]
related: [rag-ai-local/functionality-docs/09022026/01_reranking-service-and-toggle.md, rag-ai-local/QandA/09022026_Docker_Restart_Does_Not_Load_New_Env_Vars.md]
---

## TL;DR
- **What:** Implemented cross-encoder reranking for `/chat` as a new `rerank-service` Docker container, plus a server-wide `RERANK_ENABLED` env toggle and a per-request UI checkbox override — all code is written, but end-to-end verification through `rag-app` is currently blocked.
- **Why:** The user wanted reranking added to improve retrieval quality, then asked specifically for an enable/disable toggle in the UI (not just an env var) so they could interactively A/B test whether reranking actually helps.
- **Where:** New `session4-rag/rerank-service/`; `rag_pipeline/config/env_config.py`, `config/llm_setup.py`, `retrieval/step6_reranking.py`, `retrieval/retrieval_runner.py`, `retrieval/step10_response.py`, `api/routes_chat.py`, `ui/index.html`.
- **Impact:** `rerank-service` itself is built, running, and verified correct in isolation. `rag-app`'s actual container is missing the new `RERANK_*` env vars (needs recreation, not just restart) — `/chat` will currently fail with a `KeyError` on `RERANK_HOST` until that's done.

## Current Status

- **`rerank-service` container:** built (`docker images` shows `session4-rag-rerank-service:latest`, 2.09GB), running, `/health` returns `{"status":"ok","model":"cross-encoder/ms-marco-MiniLM-L-6-v2"}`. Direct `/rerank` call confirmed correct scoring: a Playwright-relevant document scored `+6.2` vs. `-11` for two irrelevant documents on a test query.
- **`rag-app` container:** still running on its *old* environment (created before this session's `.env.rag` changes). Confirmed via `docker exec rag-app printenv | grep -i rerank` → **no output** — `RERANK_HOST`/`RERANK_HOST_PORT`/`RERANK_ENABLED` are entirely absent from its real environment.
- **Code:** fully written and not yet exercised end-to-end through `rag-app` — `RERANK_HOST`/`RERANK_HOST_PORT` were just made *unconditionally* required in `load_config_martin()` (see decision below), so **`/chat` will currently fail outright** (`KeyError: 'RERANK_HOST'` inside `Missing required env var`) until the container is recreated.
- This is a genuinely incomplete state, not a "small thing left to verify" — the very next `/chat` call, if made without fixing the container first, will fail.

## COMPLETED

- **`rerank-service`** — new FastAPI + `sentence-transformers` CrossEncoder container (`cross-encoder/ms-marco-MiniLM-L-6-v2`), model weights baked into the image at build time. Confirmed working via direct `curl` to `/health` and `/rerank` (see Current Status).
- **`retrieval/step6_reranking.py`** — implemented (was a Lab3+ stub): scores all candidates via `config/llm_setup.py:rerank_scores_martin`, sorts, truncates to `top_n`.
- **`retrieval/retrieval_runner.py`** — requests a larger candidate pool (20) before reranking down to 5; logs both the pre-rerank ("vector-search ranking") and post-rerank ("reranked ranking") top-5 orderings for visual before/after comparison via `docker logs rag-app`.
- **Server-wide toggle** — `RERANK_ENABLED` env var (`RagConfig.rerank_enabled`), default `true`.
- **Per-request UI toggle** — `ChatRequest.rerank: bool | None` on `POST /chat`; when set, `api/routes_chat.py` does `config = dataclasses.replace(config, rerank_enabled=request.rerank)` before calling the retrieval runner — no changes needed to the runner's existing branch logic. `ui/index.html` has a "Rerank" checkbox next to the chat input wired into the request body.
- **Response now reports whether reranking ran** — `step10_response.py:build_response_martin` returns an additive `"reranked": bool` field (beyond the lab's `{"answer", "sources"}` contract). The UI shows this next to each RAG message (`· reranked` / `· no rerank`) so the toggle's effect is visible per-message, not just in logs.
- **Made `RERANK_HOST`/`RERANK_HOST_PORT` unconditionally required** in `load_config_martin()` (previously conditional on `RERANK_ENABLED`) — necessary once a per-request override could force reranking on even when the server default is off; the connection info needs to be loaded and ready regardless of the default.

## NOT DONE / STILL OPEN

- **Blocking:** `rag-app`'s container needs to be recreated (not restarted) to pick up `RERANK_HOST`/`RERANK_HOST_PORT`/`RERANK_ENABLED` from `.env.rag`. Attempted once via `docker compose up -d rag-app`, but the user interrupted that specific tool call and asked to pivot to the UI-toggle feature instead — the container recreation itself was never actually vetoed, just not yet re-confirmed after the UI work. **Ask before running it.**
- No end-to-end `/chat` test has been run since the reranking code was written — everything in "Completed" for the app-side code is verified by *reading*, not by *running*, except `rerank-service` itself.
- All the "NOT DONE" items from the previous handoff (`08292026/01_`) are still open and untouched this session: Lab2 metadata filtering (`step5_metadata_extraction.py`/`step5_metadata_filter.py`), the local-`py main.py`-vs-`rag-app` port-8000 collision, the `.env.pgvector` vs. live-container credential mismatch, no automated test suite, no chat-UI loading indicator, and Gemini free-tier `429` risk under sustained real usage.
- **New:** with only 2-3 documents currently indexed, reranking's actual quality impact hasn't been demonstrated yet in a real `/chat` answer — only the raw cross-encoder scoring was validated directly against `rerank-service`. A convincing before/after comparison needs either more indexed documents with genuinely competing candidates, or a deliberately ambiguous test question.

## NEXT ACTION

1. **Ask the user how to apply the container fix**, then recreate `rag-app`:
   ```
   docker compose up -d rag-app
   ```
   (run from `Labs Practices/session4-rag/`). This should recreate only `rag-app`, leaving `pgvector`/`llama31-8b`/`nomic-embed-text`/`rerank-service` untouched.
2. Confirm the vars landed: `docker exec rag-app printenv | grep -i rerank` should show all three.
3. Test end-to-end with reranking on (default): `curl -s -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"question": "What is this test document about?"}'` → expect `HTTP 200` with a `"reranked": true` field in the response.
4. Test the override off: same call with `"rerank": false` added to the body → expect `"reranked": false`.
5. Check `docker logs rag-app` for the `"vector-search ranking"` / `"reranked ranking"` log lines to confirm the cross-encoder actually reordered something (not just passed through unchanged).
6. Try the UI checkbox directly in the browser at `http://localhost:8000/` to confirm the toggle + `· reranked`/`· no rerank` label round-trip correctly.

## CONTEXT THE NEXT SESSION CANNOT DERIVE FROM CODE

- **Decision:** Reranking runs as its own Docker container (`rerank-service`), not a library embedded in `rag-app`. **Reason:** `sentence-transformers` pulls in `torch` (~2GB even CPU-only), and every other model call in this codebase is a thin `requests` client to a dedicated container (`llama31-8b`, `nomic-embed-text`) — bundling a heavy ML dependency into `rag-app`'s minimal image would have broken that pattern. **Rejected alternative:** install `sentence-transformers`/`torch` directly into `rag_pipeline/requirements.txt` — this was the original plan-mode design before the user explicitly redirected to "add new rerank model to docker" as its own service.
- **Decision:** the enable/disable toggle is per-request (`ChatRequest.rerank`, overriding config via `dataclasses.replace`), not just a static env var. **Reason:** the user explicitly asked to move it into the UI "instead" of only an env-var toggle, specifically so they could validate reranking's effect interactively without editing `.env` + recreating containers for every test.
- **Trap:** `docker restart` does **not** pick up newly-added `env_file` variables for an already-existing container — this is what's currently blocking verification. Recreating (`docker compose up -d <service>`) is required for any *new* variable (not just a changed value of an existing one) added to a service's `env_file` list. Full trace in `rag-ai-local/QandA/09022026_Docker_Restart_Does_Not_Load_New_Env_Vars.md`.
- **Trap:** when a required env var is missing from a container's real environment, `main.py`'s `load_dotenv()` (default `override=False`) can silently backfill it from the volume-mounted `rag_pipeline/.env` — which holds values meant for a *local, non-Docker* run (`localhost` instead of `host.docker.internal`). The resulting failure looks like a networking/config bug in the app, not a stale-container symptom. Always check `docker exec <container> printenv | grep <VAR>` first.
- **Ground truth:** the cross-encoder model itself works correctly — confirmed via a direct `curl` to `rerank-service` with one relevant and two irrelevant documents, scoring `+6.2` vs. `-11`/`-11`. Any failure encountered when resuming this work is almost certainly the container-env issue above, not a problem with the reranker or the model choice.
