---
title: Gemini Chat Provider Reliability Issues (429/503/404/Timeout)
date: 2026-08-29
type: qanda
area: rag-pipeline-retrieval
status: implementation-complete
session_id: n/a
duration: ~90min
issue_type: bug
severity: medium
resolution_date: 2026-08-29
tags: [rag-pipeline, gemini, ollama, chat-provider, reliability]
keywords: [CHAT_PROVIDER, gemini-flash-lite-latest, 429, 503, 404, ReadTimeout, generativelanguage.googleapis.com, _CHAT_BACKENDS]
related: [rag-ai-local/functionality-docs/08292026/01_handoff-gemini-provider-and-reliability-fixes.md, rag-ai-local/QandA/08262026_Chat_Endpoint_Timeout_And_Vector_Search.md]
---

## TL;DR
- **What:** After switching `POST /chat`'s answer generation from Ollama to Google AI Studio's Gemini, three separate Gemini-side failure modes surfaced one after another during verification: intermittent `503`s on a preview model, `404` model-deprecation errors on two different models in a row, and an uncaught client-side timeout.
- **Why:** Each fix exposed the next problem — switching models to dodge one failure revealed the next, until the model *and* the retry logic were both correct.
- **Where:** `Labs Practices/session4-rag/rag_pipeline/config/llm_setup.py:_chat_gemini_martin`, `.env` / `.env.rag` (`GEMINI_MODEL`).
- **Impact:** Settled on `GEMINI_MODEL=gemini-flash-lite-latest` with a retry loop covering `429`/`503`/`Timeout`; confirmed stable across repeated spaced-out `/chat` calls.

## Q1: Why did `/chat` intermittently return `Bad Gateway` with `503 Service Unavailable` from `generativelanguage.googleapis.com` right after switching to `gemini-3.6-flash`?

**Answer:** `gemini-3.6-flash` was a very recently released preview-tier model at the time (per `GET /v1beta/models`, version `3.6-flash-07-2026`), and Google's own backend was intermittently returning `503` for it — transient capacity limits on Google's side, not a problem with the app, the API key, or local infrastructure (`pgvector`/`nomic-embed-text`/`rag-app` were all healthy throughout).

**Evidence:**
```
{"detail":"LLM request failed: 503 Server Error: Service Unavailable for url: https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?..."}
HTTP 502
```
A 5-request burst reproduced it directly: 3/5 succeeded, 2/5 failed with this exact `503`.

**Root cause:** Transient Google-side capacity limits on a newly released model.
**Fix:** `config/llm_setup.py:_chat_gemini_martin` — added a retry loop (up to 3 attempts, 2s/4s backoff) for `429`/`503` responses. Improved the burst success rate from 3/5 to 4/5, but did not fully eliminate failures (see Q2).

## Q2: Why did `_chat_gemini_martin` still fail with `404 Client Error: Not Found` after retries were added, first for `gemini-2.5-flash` and then again for `gemini-2.5-flash-lite`?

**Answer:** Both models had been deprecated for new users by the time of this session — Google's Generative Language API returns `HTTP 404` with `status: "NOT_FOUND"` (not `400`/`401`/`403`) for this case, and the error message explicitly names the recommended replacement model. This is not a retryable error (no amount of backoff fixes a permanently retired model), so it needed a model change, not a retry-logic change.

**Evidence:**
```json
{
  "error": {
    "code": 404,
    "message": "This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.6-flash for the latest features and improvements.",
    "status": "NOT_FOUND"
  }
}
```
Then, after switching to `gemini-2.5-flash-lite`, the identical pattern recurred:
```json
{
  "error": {
    "code": 404,
    "message": "This model models/gemini-2.5-flash-lite is no longer available to new users. Please update your code to use models/gemini-3.5-flash-lite for the latest features and improvements.",
    "status": "NOT_FOUND"
  }
}
```

**Root cause:** Both `gemini-2.5-flash` and `gemini-2.5-flash-lite` were retired for new users as of 2026-08-29; a pinned model name has no protection against this.
**Fix:** `GEMINI_MODEL=gemini-flash-lite-latest` in both `rag_pipeline/.env` and `session4-rag/.env.rag` — an alias Google resolves server-side to its current cheapest Flash-Lite model, so future retirements of the underlying pinned version don't require another manual model-name change.

## Q3: Was the Google AI Studio API key (`AQ.Ab8RN6LQ...`) actually invalid, given how different it looks from the classic `AIzaSy...` Google API key format?

**Answer:** No — the key was valid throughout. A key starting with `"AQ."` doesn't match the older, commonly-documented `"AIzaSy..."` Google API key shape, which made it a reasonable first suspect when `generateContent` calls failed. It was ruled out by calling `GET /v1beta/models?key=<key>` directly: it returned a full, large list of available models (200 OK), proving the key authenticates correctly — the actual failures (Q1, Q2) were unrelated to the key.

**Evidence:**
```
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=AQ.Ab8RN6LQ..."
→ HTTP 200, {"models": [...50+ entries including "models/gemini-2.5-flash", "models/gemini-flash-lite-latest", ...]}
```

**Root cause:** N/A — key was never the problem; documented so a future session doesn't re-waste time suspecting it.
**Fix:** N/A.

## Q4: Why did 2 of 3 spaced-out `/chat` test calls fail with a plain `requests.exceptions.Timeout` even after the `429`/`503` retry logic was in place?

**Answer:** `_chat_gemini_martin`'s retry loop only branched on `response.status_code in {429, 503}` — but a `requests.exceptions.Timeout` is raised by `requests.post()` itself, before any `response` object exists at all. The retry condition never had a `response` to inspect, so a timeout propagated immediately on the very first attempt with zero retries, regardless of `_MAX_ATTEMPTS`.

**Evidence:**
```
{"detail":"LLM request timed out: HTTPSConnectionPool(host='generativelanguage.googleapis.com', port=443): Read timed out. (read timeout=60)"}
HTTP 504
```
2 of 3 spaced (8s apart) requests failed this way against `gemini-flash-lite-latest`, which otherwise had no `429`/`503`/`404` issues.

**Root cause:** The retry loop's only branch condition (`response.status_code`) can't fire for an exception that occurs before a response exists.
**Fix:** `config/llm_setup.py:_chat_gemini_martin` — wrapped the `requests.post()` call itself in `try/except requests.exceptions.Timeout` inside the same attempt loop, so a timeout is now retried exactly like a `429`/`503` would be. Confirmed by: 3/3 subsequent spaced test calls succeeded.
