---
title: RAG Pipeline Local Run Failures (psycopg2, dotenv, Postgres creds)
date: 2026-08-26
type: qanda
area: rag-pipeline-setup
status: implementation-complete
session_id: n/a
duration: ~60min
issue_type: bug
severity: medium
resolution_date: 2026-08-26
tags: [rag-pipeline, postgres, dotenv, python, docker]
keywords: [psycopg2-binary, tiktoken, POSTGRES_HOST, KeyError, LNK2001, _PyInterpreterState_Get, pgvector, ai_user, ai_pass]
related: []
---

## TL;DR
- **What:** Three chained failures blocked `py main.py` from starting `rag_pipeline` locally on Windows: a Python 3.14 wheel-build failure for `psycopg2-binary`/`tiktoken`, a missing `.env` load causing `KeyError: 'POSTGRES_HOST'`, and a Postgres credential mismatch against the already-initialized `pgvector` container.
- **Why:** `requirements.txt` pinned versions predating Python 3.14 wheel support, `main.py` read `os.environ` directly with no `load_dotenv()` call, and `.env.pgvector` had been edited after the `pgvector` container's data volume was already initialized with different credentials.
- **Where:** `Labs Practices/session4-rag/rag_pipeline/requirements.txt`, `rag_pipeline/main.py`, `rag_pipeline/.env`.
- **Impact:** `py main.py` now runs migrations and starts the API server locally; documented the port-8000 collision risk against the `rag-app` Docker container.

## Q1: Why does `psycopg2-binary==2.9.9` fail to build on Python 3.14 with `LNK2001: unresolved external symbol _PyInterpreterState_Get`?

**Answer:** `psycopg2-binary` 2.9.9 has no prebuilt Windows wheel for `cp314`, so `pip` falls back to compiling the C extension from source. Its C code calls `_PyInterpreterState_Get`, a private CPython API whose ABI changed in 3.14, so the linker can't resolve the symbol and the build fails.

**Evidence:**
```
utils.obj : error LNK2001: unresolved external symbol _PyInterpreterState_Get
build\lib.win-amd64-cpython-314\psycopg2\_psycopg.cp314-win_amd64.pyd : fatal error LNK1120: 1 unresolved externals
error: Command '[...link.exe...]' returned non-zero exit status 1120.
ERROR: Failed building wheel for psycopg2-binary
```

**Root cause:** Version pin predates Python 3.14 wheel/ABI support.
**Fix:** `Labs Practices/session4-rag/rag_pipeline/requirements.txt` — bumped to `psycopg2-binary==2.9.12` (ships a `cp314` wheel, no compiler needed).

## Q2: Why did `tiktoken==0.8.0` also fail to install on Python 3.14 with `error: can't find Rust compiler`?

**Answer:** Same class of problem as Q1 — `tiktoken` 0.8.0 has no `cp314` wheel, so `pip` tries to build its Rust extension from source, which requires a Rust toolchain that isn't installed.

**Evidence:**
```
running build_rust
error: can't find Rust compiler
ERROR: Failed building wheel for tiktoken
```

**Root cause:** Version pin predates Python 3.14 wheel support.
**Fix:** `Labs Practices/session4-rag/rag_pipeline/requirements.txt` — bumped to `tiktoken==0.14.0` (ships a `cp314` wheel).

## Q3: Why does `main.py` raise `KeyError: 'POSTGRES_HOST'` / `MigrationError: Missing required env var` even though `.env` defines `POSTGRES_HOST`?

**Answer:** `.env` files are not loaded by the OS or Python automatically — that only happens when Docker Compose's `env_file:` directive injects them into a container. `main.py` read `os.environ["POSTGRES_HOST"]` directly with no `load_dotenv()` call anywhere in the import chain, so when run locally with `py main.py` (outside Docker), the vars were never populated.

**Evidence:**
```
File ".../sql/migrations.py", line 38, in _get_db_connection_martin
    host=os.environ["POSTGRES_HOST"],
KeyError: 'POSTGRES_HOST'
sql.migrations.MigrationError: Missing required env var: 'POSTGRES_HOST'
```

**Root cause:** No `.env` loader in the local (non-Docker) run path.
**Fix:** `Labs Practices/session4-rag/rag_pipeline/main.py` — added `from dotenv import load_dotenv` + `load_dotenv()` before any env-var reads; added `python-dotenv==1.0.1` to `requirements.txt` (previously only present transitively via `uvicorn[standard]`).

## Q4: Why does connecting to the `pgvector` container fail with `password authentication failed for user "postgres"` even though `.env.pgvector` sets `POSTGRES_PASSWORD=vbpass12#`?

**Answer:** Postgres only applies `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` on the *first* container start, when its data volume (`pgvector_data`) is empty. The running `pgvector` container was originally initialized with `POSTGRES_USER=ai_user` / `POSTGRES_PASSWORD=ai_pass` (matching `.env.rag`, not `.env.pgvector`). `.env.pgvector` was edited afterward to `postgres`/`vbpass12#`, but since the volume already had data, Postgres never re-read those values — the live credentials stayed `ai_user`/`ai_pass`.

**Evidence:**
```
$ docker inspect pgvector --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -i postgres
POSTGRES_PASSWORD=ai_pass
POSTGRES_DB=ai_db
POSTGRES_USER=ai_user
```
```
psycopg2.OperationalError: connection to server at "localhost" (::1), port 6024 failed: FATAL:  password authentication failed for user "postgres"
```

**Root cause:** `.env.pgvector` was edited after `pgvector`'s data volume was already initialized; Postgres ignores `POSTGRES_*` env vars on subsequent starts against a non-empty data directory.
**Fix:** `Labs Practices/session4-rag/rag_pipeline/.env` — changed `POSTGRES_USER`/`POSTGRES_PASSWORD` to `ai_user`/`ai_pass` to match the container's actual live credentials. (To make `.env.pgvector`'s `postgres`/`vbpass12#` take effect instead, the `pgvector_data` volume would need to be dropped and the container re-initialized — not done here since it would destroy existing data.)

## Q5: Can `py main.py` (run locally on Windows) and the `rag-app` Docker container run at the same time without conflict?

**Answer:** No — both bind host port 8000. Running `py main.py` locally while `rag-app`'s container (`0.0.0.0:8000->8000/tcp`) is up creates two listeners on the same port, which leads to unpredictable behavior about which process actually answers a given request depending on the network stack (Docker Desktop's WSL2/Hyper-V proxy vs native Windows bind).

**Evidence:**
```
$ docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}"
rag-app   session4-rag-rag-app   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
```
Local run's own log (started without error despite the container already holding the port):
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Root cause:** Two independent processes configured for the same host port; not mutually exclusive by the app or Compose config.
**Fix:** No code fix — operational rule: stop `rag-app` (`docker stop rag-app`) before running `py main.py` locally, or vice versa. Not enforced in code as of this writing.
