---
title: RAG Pipeline Local Dev Setup Fixes
date: 2026-08-26
type: functionality
area: rag-pipeline-setup
status: implementation-complete
session_id: n/a
duration: ~60min
files: [Labs Practices/session4-rag/rag_pipeline/requirements.txt, Labs Practices/session4-rag/rag_pipeline/main.py, Labs Practices/session4-rag/rag_pipeline/.env]
version: 1
last_updated: 2026-08-26
extraction_method: pair-session
tags: [rag-pipeline, postgres, dotenv, python, docker, windows]
keywords: [psycopg2-binary, tiktoken, cp314, load_dotenv, pgvector, ai_user, POSTGRES_HOST_PORT]
related: [rag-ai-local/QandA/08262026_Rag_Pipeline_Local_Run_Failures.md]
---

## TL;DR
- **What:** Made `rag_pipeline/main.py` runnable directly with `py main.py` on Windows (outside Docker), against the already-running `pgvector` container from `session4-rag`'s Compose stack.
- **Why:** The pinned dependency versions predated Python 3.14 wheel support, and the app had no local (non-Docker) `.env`-loading path, so it only ever worked inside the `rag-app` container where Compose's `env_file:` injects vars directly.
- **Where:** `Labs Practices/session4-rag/rag_pipeline/` (`requirements.txt`, `main.py`, `.env`); the running `pgvector`, `rag-app`, `llama31-8b`, `nomic-embed-text` containers from `Labs Practices/session4-rag/docker-compose.yml`.
- **Impact:** `py main.py` now applies schema migrations and starts the API server on port 8000 locally, without needing the `rag-app` container.

## What it does

`rag_pipeline/main.py` is the process entry point for the RAG backend: it applies idempotent schema migrations against Postgres (`sql/migrations.py`), then starts the FastAPI app (`api/main.py`) via `uvicorn` on port 8000. It can run two ways: inside the `rag-app` Docker container (as part of the `session4-rag` Compose stack), or directly on the host with `py main.py` for faster local iteration.

## How it works

The Compose stack (`Labs Practices/session4-rag/docker-compose.yml`) defines four services: `pgvector` (Postgres + pgvector extension, host port `6024` → container `5432`), `llama31-8b` and `nomic-embed-text` (Ollama models), and `rag-app` (this pipeline, host port `8000`). Each service gets its env vars from `env_file:` entries (e.g. `rag-app` reads `.env.common` + `.env.rag`), which Docker Compose injects directly into the container's process environment at start.

When running `rag_pipeline` locally instead (`py main.py` from a Windows shell), there is no Compose `env_file:` mechanism — the process only sees vars that are actually set in its environment. `main.py` now calls `load_dotenv()` (from `python-dotenv`) at import time to read `rag_pipeline/.env` into `os.environ` before anything reads `POSTGRES_*`/`OLLAMA_*` vars, making the local run path equivalent to the Docker one.

For a local run to reach the `pgvector` container, `rag_pipeline/.env` uses `POSTGRES_HOST=localhost` + `POSTGRES_HOST_PORT=6024` (the container's host-published port), whereas the container-to-container path (`rag-app` → `pgvector`) would instead need the container/service name and internal port (e.g. `POSTGRES_HOST=pgvector`, port `5432`), since containers on the same Docker network resolve each other by service name and don't need the host port mapping at all.

## Key decisions and why

- **Bumped `psycopg2-binary` 2.9.9 → 2.9.12 and `tiktoken` 0.8.0 → 0.14.0** instead of pinning an older Python version or installing build toolchains (MSVC linker fix / Rust compiler). Rejected alternative: install a C/Rust toolchain to build the old pins from source — rejected because it adds a heavyweight, machine-specific setup step for a problem that a version bump solves for free (both newer versions ship prebuilt `cp314` Windows wheels).
- **Added `load_dotenv()` directly in `main.py`** rather than implementing the (currently `NotImplementedError`-stubbed) `config/env_config.py:load_config_martin`. Rejected alternative: implement `load_config_martin` fully as part of this fix — rejected as out of scope; that function is a separate, larger lab task (typed `RagConfig` bundling all env vars), while the immediate bug was simply that no code anywhere called `load_dotenv()`.
- **Pointed `rag_pipeline/.env` at the container's actual live credentials (`ai_user`/`ai_pass`)** rather than recreating the `pgvector` container to match `.env.pgvector`'s newer values (`postgres`/`vbpass12#`). Rejected alternative: drop the `pgvector_data` volume and let Postgres re-init with `.env.pgvector`'s credentials — rejected because it would destroy any data already stored in that volume; matching the app config to the live DB is non-destructive.

## Configuration

- `rag_pipeline/.env` → `POSTGRES_HOST` / `POSTGRES_HOST_PORT`: which host and port `psycopg2.connect()` targets. For a local (non-Docker) run against the Compose-managed `pgvector` container, this must be `localhost` + the **host-published** port (`6024`), not the container-internal port (`5432`).
- `rag_pipeline/.env` → `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB`: must match whatever the `pgvector` container was **actually initialized with** (see Gotchas) — not necessarily whatever is currently written in `session4-rag/.env.pgvector`.
- `session4-rag/docker-compose.yml` → `rag-app` service `ports: ["8000:8000"]`: binds host port 8000. Running `py main.py` locally binds the same host port independently; both can bind without either raising an error, but the network stack (Docker Desktop's WSL2/Hyper-V proxy vs a native Windows socket) makes it non-deterministic which process actually answers a given client depending on which "localhost" resolution path the client takes.

## Gotchas

- **A `.env` file is not read by the OS or by Python automatically.** It only takes effect when something explicitly loads it — Docker Compose's `env_file:` directive for containers, or an explicit `load_dotenv()` call for a local process. Editing `.env` and expecting a plain `py main.py` run to pick it up (with no loader in the code) silently fails with `KeyError`, not a clear "env file not loaded" message.
- **Postgres only applies `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` on the very first start against an empty data directory.** Once the named volume (`pgvector_data`) has data, editing `.env.pgvector` and restarting the container does *nothing* to existing credentials — `docker inspect <container> --format '{{range .Config.Env}}{{println .}}{{end}}'` shows what the container was actually launched with, which can silently diverge from what's currently written in the env file on disk.
- **Two processes can both bind host port 8000 without either erroring**, at least under Docker Desktop on Windows — the `rag-app` container's published port and a locally-run `py main.py` both reported success. This does not mean there's no conflict; it means the failure mode is silent (wrong process answers requests) rather than a bind error, so don't rely on "it started without an error" as proof there's no port collision.

## Verification

Run locally after the fixes:
```
cd "Labs Practices/session4-rag/rag_pipeline"
py main.py
```
Expected output:
```
INFO:__main__:Applying schema migrations...
INFO:sql.migrations:Schema up to date (hash <hash>); skipping migration.
INFO:__main__:Starting API server on :8000
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

To confirm what credentials a running Postgres container actually holds (vs. what an env file currently says):
```
docker inspect pgvector --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -i postgres
```
