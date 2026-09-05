---
title: docker restart Doesn't Load New env_file Variables
date: 2026-09-02
type: qanda
area: rag-pipeline-retrieval
status: implementation-complete
session_id: n/a
duration: ~20min
issue_type: bug
severity: medium
resolution_date: 2026-09-02
tags: [docker, docker-compose, env-vars, rerank-service]
keywords: [docker restart, docker compose up, env_file, load_dotenv, RERANK_HOST, Connection refused]
related: [rag-ai-local/functionality-docs/09022026/01_reranking-service-and-toggle.md]
---

## TL;DR
- **What:** After adding `RERANK_HOST`/`RERANK_HOST_PORT`/`RERANK_ENABLED` to `session4-rag/.env.rag` and running `docker restart rag-app`, `/chat` failed with `Connection refused` to `localhost:8088` instead of reaching the `rerank-service` container.
- **Why:** `docker restart` reuses an already-created container's existing environment; it does not re-read `docker-compose.yml`'s `env_file:` list for newly-added variables. Only recreating the container does.
- **Where:** `Labs Practices/session4-rag/rag_pipeline/config/llm_setup.py:rerank_scores_martin`, `main.py`'s `load_dotenv()` call.
- **Impact:** Diagnosed via `docker exec rag-app printenv`; fix is to recreate the container (`docker compose up -d rag-app`), not just restart it, whenever a *new* env var is added to a service's `env_file`.

## Q1: Why did `/chat` fail with `Connection refused` to `localhost:8088` when `RERANK_HOST` was set to `host.docker.internal` in `.env.rag`, not `localhost`?

**Answer:** `docker restart <container>` restarts the existing container process in place — it does **not** re-read `docker-compose.yml`'s `env_file:` entries. A container's environment variables are fixed at creation time (`docker create`/`docker compose up`, including the initial `docker compose up` that first brought the stack up). Since `RERANK_HOST`/`RERANK_HOST_PORT`/`RERANK_ENABLED` were added to `.env.rag` *after* the `rag-app` container already existed, `docker restart rag-app` left the running container's actual OS environment with **no `RERANK_*` variables at all** — confirmed directly.

**Evidence:**
```
$ docker exec rag-app printenv | grep -i rerank
(no output)
```

**Root cause:** `docker restart` doesn't recreate the container, so newly-added `env_file` variables never reach it.
**Fix:** Recreate the container instead of restarting it: `docker compose up -d rag-app` (Compose detects the config/env change and recreates only that service, leaving the rest of the stack running).

## Q2: Given `RERANK_HOST` was completely absent from the container's environment, why did the app use `localhost` (from `rag_pipeline/.env`) instead of immediately raising `KeyError: 'RERANK_HOST'`?

**Answer:** `main.py` calls `load_dotenv()` with its default `override=False` behavior, meaning it only *skips* setting a variable if that variable is **already present** in `os.environ`. Since `env_file` injection for `RERANK_HOST` never happened (per Q1), `os.environ` had no `RERANK_HOST` key at all when `load_dotenv()` ran — so `load_dotenv()` set it from whatever it found first in the volume-mounted `/app/.env` (which is `rag_pipeline/.env` on the host, containing `RERANK_HOST=localhost` — the value meant for a local, non-Docker `py main.py` run, not for a container). The app then proceeded normally with a value that's wrong in a container context, rather than failing fast.

**Evidence:**
```
{"detail":"LLM request failed: HTTPConnectionPool(host='localhost', port=8088): Max retries exceeded with url: /rerank (Caused by NewConnectionError(\"...Connection refused\"))"}
HTTP 502
```
No `KeyError`/`Missing required env var` message appeared, because a value *was* found — just from the wrong file, silently.

**Root cause:** `load_dotenv()`'s "don't override existing vars" semantics only protect against overwriting a var that's already set — they provide no protection against a var being *entirely absent* from the real container environment and getting silently backfilled from a file meant for a different run context.
**Fix:** N/A code-level fix; the actual fix is the Q1 container-recreation step. Documented here so a future "wrong host value used" symptom is recognized as this same class of bug rather than re-debugged from scratch — check `docker exec <container> printenv | grep <VAR>` first to see what the container *actually* has before suspecting the application code.
