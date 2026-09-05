---
title: "Handoff: Gemini Chat Provider + Reliability Fixes"
date: 2026-08-29
type: session-handoff
area: rag-pipeline-retrieval
status: superseded
session_id: n/a
next_action: "Superseded — see rag-ai-local/functionality-docs/09022026/01_handoff-reranking-and-ui-toggle.md"
supersedes: rag-ai-local/functionality-docs/08262026/04_handoff-rag-pipeline-lab1-complete.md
tags: [rag-pipeline, gemini, ollama, chat-provider, reliability, handoff]
keywords: [CHAT_PROVIDER, gemini-flash-lite-latest, 429, 503, ReadTimeout, _CHAT_BACKENDS]
related: [rag-ai-local/functionality-docs/08262026/03_retrieval-chat-pipeline-lab1-implementation.md, rag-ai-local/QandA/08262026_Chat_Endpoint_Timeout_And_Vector_Search.md]
---

## TL;DR
- **What:** Added a pluggable `CHAT_PROVIDER` (Ollama or Gemini) to `chat_martin`, switched the running stack to Google AI Studio's Gemini for answer generation, hardened `/upload` and `/chat` error handling, then found and fixed three separate Gemini reliability bugs surfaced one after another by real testing.
- **Why:** CPU-only `llama3.1:8b` via Ollama took 60-90+ seconds (once over 7 minutes) per answer; the user wanted a faster/cheaper alternative via Google AI Studio, switchable without code changes.
- **Where:** `rag_pipeline/config/env_config.py`, `rag_pipeline/config/llm_setup.py`, `rag_pipeline/api/routes_chat.py`, `rag_pipeline/api/routes_upload.py`, `rag_pipeline/.env`, `session4-rag/.env.rag`.
- **Impact:** `/chat` now answers via Gemini in a few seconds instead of minutes, confirmed via 3/3 successful spaced-out requests after the final fix.

## Current Status

- `CHAT_PROVIDER=gemini` in both `rag_pipeline/.env` and `session4-rag/.env.rag`; `GEMINI_MODEL=gemini-flash-lite-latest` in both.
- `config/llm_setup.py:_chat_gemini_martin` retries up to 3 attempts (2s/4s backoff) on `429`, `503`, **and** network-level `Timeout`.
- `api/routes_chat.py` and `api/routes_upload.py` both catch `requests.exceptions.Timeout` / `RequestException` / `psycopg2.Error` and return a proper `HTTPException` (`400`/`502`/`504`) instead of letting FastAPI's default plain-text 500 reach the client.
- Verified: 3 consecutive `/chat` calls, 8 seconds apart, all `HTTP 200` with correct answers + sources, using `gemini-flash-lite-latest`.
- `llama31-8b` Ollama container is still running but no longer used for chat generation (only `nomic-embed-text` embeddings still route through Ollama).

## COMPLETED

- **Dynamic chat-provider dispatch** — `RagConfig.chat_provider` + `config/llm_setup.py:_CHAT_BACKENDS` (a `dict[str, Callable]` registry: `"ollama"` → `_chat_ollama_martin`, `"gemini"` → `_chat_gemini_martin`). Confirmed by: changing `CHAT_PROVIDER` in `.env` + `docker restart rag-app` is the only step needed to switch backends — no code change. Adding a third provider is one function + one registry entry.
- **Error handling hardened on both routes** — this was an explicit "NOT DONE" item in the previous handoff (`08262026/04_`). Confirmed by: a request against a bad/placeholder Gemini key returned `{"detail": "LLM request failed: ..."}` with `HTTP 502`, not a plain-text crash.
- **Bug 1 — `gemini-3.6-flash` intermittent `503`** — a very-new preview model hitting Google-side capacity limits. Fixed by adding retry-with-backoff for `429`/`503` responses. Confirmed by: burst-test success rate went from 3/5 to 4/5.
- **Bug 2 — model deprecation (`404`)** — `gemini-2.5-flash` and then `gemini-2.5-flash-lite` both returned `404 NOT_FOUND` with `"This model ... is no longer available to new users. Please update your code to use models/<replacement>"`. Fixed by switching to `gemini-flash-lite-latest`, an alias Google resolves to its current cheapest Flash-Lite model. Confirmed by: `GET /v1beta/models?key=...` listed it, and a direct `generateContent` call against it succeeded.
- **Bug 3 — uncaught client-side timeout** — `gemini-flash-lite-latest` itself worked, but 2 of 3 spaced test calls hit a bare `requests.exceptions.Timeout` (60s) that the existing retry loop never saw, because a `Timeout` fires before any `response` object exists, and the loop's retry condition only checked `response.status_code`. Fixed by wrapping the `requests.post()` call itself in `try/except requests.exceptions.Timeout` inside the same retry loop. Confirmed by: 3/3 spaced calls succeeded after this fix.

## NOT DONE / STILL OPEN

- `retrieval/step5_metadata_filter.py`, `retrieval/step6_reranking.py`, `indexing/step5_metadata_extraction.py` — still Lab2/Lab3 stubs, **intentionally** not implemented (carried over from the previous handoff, unchanged this session).
- Port collision between local `py main.py` and the `rag-app` Docker container (both bind host `8000`) — still not fixed in code, still just an operational rule (carried over, unchanged).
- `session4-rag/.env.pgvector` still doesn't match the `pgvector` container's actual live credentials (`ai_user`/`ai_pass`) — still not reconciled at the source-of-truth file level (carried over, unchanged).
- No automated test suite exists anywhere in `rag_pipeline/` (carried over, unchanged).
- **New:** `ui/index.html`'s chat form still has no loading indicator. This mattered less as a UX issue with Gemini (a few seconds) than it did with Ollama (minutes), but it's still a real gap — a user has no way to tell "still working" from "silently failed" while a request is in flight.
- **New:** Gemini free-tier `429` rate limits are real and were reproduced directly (rapid-fire testing hit them). The retry loop's 2-4s backoff smooths over a single transient blip but cannot clear a per-minute quota window — sustained real usage faster than the free tier's RPM limit will still surface as a `502` to the user.
- **New:** `GEMINI_API_KEY` is stored in plaintext in two `.env` files with no secrets management — consistent with how `POSTGRES_PASSWORD` is already handled in this lab, but worth flagging since this key is tied to real (if free-tier) Google quota/billing, unlike a throwaway local Postgres password.
- **New:** `llama31-8b` container is running idle (no longer called for chat) — not stopped, since removing/stopping infrastructure wasn't asked for.

## NEXT ACTION

If `429`s resurface under real usage (not just burst-testing): either enable billing on the Google AI Studio project backing this key for a higher quota, or make `_chat_gemini_martin` respect a `Retry-After` response header if Google sends one, instead of the current fixed 2s/4s backoff.

Otherwise, the next open work is unchanged from before: **implement Lab2** — `indexing/step5_metadata_extraction.py` (parse frontmatter fields) + `retrieval/step5_metadata_filter.py` (scope vector search candidates by them).

To resume and re-verify current state:
```
docker restart rag-app
curl -s -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"question": "What is this test document about?"}'
```

## CONTEXT THE NEXT SESSION CANNOT DERIVE FROM CODE

- **Decision:** `CHAT_PROVIDER` dispatch is a registry `dict[str, Callable]` (`_CHAT_BACKENDS`) rather than a hard-coded single implementation. **Reason:** the user explicitly rejected an initial hard swap-to-Gemini edit with "make it dynamic to switch to gemini or ollama or any model." **Rejected alternative:** the hard replacement I wrote first, which deleted the Ollama chat path entirely — reverted before ever being applied.
- **Trap:** Google's Generative Language API returns `HTTP 404` with `status: "NOT_FOUND"` — not `400`/`401`/`403` — when an API key is valid but the requested **model** has been deprecated for new users. The error body itself names the exact replacement model (e.g. *"Please update your code to use models/gemini-3.6-flash"*). This looked at first like a bad-key problem; `GET /v1beta/models?key=...` returning a full model list is what proved the key was fine and isolated the problem to the model name.
- **Trap:** as of this session's date (2026-08-29), **both** `gemini-2.5-flash` and `gemini-2.5-flash-lite` are deprecated for new users. Do not suggest either as a default for new Gemini integrations — check `GET /v1beta/models` or use an alias like `gemini-flash-lite-latest` instead of a pinned version.
- **Ground truth:** the API key `AQ.Ab8RN6LQ...` (starting with `"AQ."`) is a **valid** Google AI Studio key, despite not matching the classic `"AIzaSy..."` Google API key shape from older documentation. Verified via a successful `GET /v1beta/models` call. Don't assume a key is malformed just because its prefix looks unfamiliar — test it against the API directly.
- **Ground truth:** `gemini-flash-lite-latest` is a live alias Google's API resolves server-side to whatever its current cheapest/smallest Flash-Lite model is. Verified present in `GET /v1beta/models` and working via a direct `generateContent` call. Preferring "-latest"-style alias names over pinned versions for provider model config is what avoids the exact 404-deprecation break hit twice in this session.
- **Trap:** `requests.exceptions.Timeout` is raised **before** any `response` object exists — a retry loop that only branches on `response.status_code` (e.g. checking for `429`/`503`) will never see it and will let it propagate on the very first attempt. It has to be caught in its own `try/except` wrapped directly around the `requests.post()` call, inside the same attempt loop, to actually get retried.
