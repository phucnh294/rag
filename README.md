# rag

Personal lab work from an AI/RAG practice course: a full local RAG (Retrieval-Augmented
Generation) pipeline with cross-encoder reranking and metadata filtering, plus an
earlier Ollama Docker setup exercise.

## Projects

### [`Labs Practices/session4-rag/`](Labs%20Practices/session4-rag/) — RAG pipeline (main project)

A document upload → indexing → retrieval → chat pipeline, containerized end to end.

**Stack:** FastAPI, Postgres + `pgvector`, Ollama (local LLM/embeddings) or Google
Gemini (switchable), a dedicated cross-encoder reranking microservice.

**Services** (`docker-compose.yml`):
| Service | Role |
|---|---|
| `rag-app` | FastAPI app — `/upload` (index a `.md` doc) and `/chat` (ask a question), plus a minimal chat UI |
| `pgvector` | Postgres with the `pgvector` extension for embedding storage/similarity search |
| `llama31-8b` / `nomic-embed-text` | Local Ollama containers for chat / embeddings (optional — Gemini can be used instead) |
| `rerank-service` | Standalone FastAPI service wrapping a `sentence-transformers` cross-encoder, used to re-score retrieved chunks before they're sent to the LLM |

**Key features:**
- Pluggable chat backend — `CHAT_PROVIDER=ollama` or `gemini`, switchable via env var, no code changes.
- Cross-encoder reranking, toggleable per-request (UI checkbox / `{"rerank": bool}`) or via server default (`RERANK_ENABLED`).
- Metadata-driven retrieval filtering — documents can be tagged `status`/`area` (via YAML frontmatter or upload-time form fields) so a designated "authoritative" document for a topic is preferred over similar-but-wrong content, with an `include_reference` override to see the unfiltered pool.
- A debug panel in the UI showing the full candidate pool before/after reranking and metadata filtering, for inspecting *why* a given answer was produced.

**Docs:** `Labs Practices/rag-ai-local/` holds the running knowledge base for this
project — `QandA/` (investigated bugs/questions) and `functionality-docs/` (design
notes, decisions, session handoffs), each dated and tagged for future retrieval.

**Running it:**
```bash
cd "Labs Practices/session4-rag"
cp .env.example .env
cp .env.common.example .env.common
cp .env.rag.example .env.rag
cp .env.pgvector.example .env.pgvector
cp .env.nomic.embed.text.example .env.nomic.embed.text
cp .env.ollama.llama3.8b.example .env.ollama.llama3.8b
cp rag_pipeline/.env.example rag_pipeline/.env
# fill in real values (DB password, GEMINI_API_KEY if using Gemini) in the copies above
docker compose up -d
```
Then open `http://localhost:8000`.

### [`module2/`](module2/) — Ollama Docker setup exercise

An earlier, standalone exercise: running Ollama models (`gemma:2b`, `llama3:8b`) in
Docker, tested via `curl`/Postman. Unrelated to the RAG pipeline above.

## Secrets

No real `.env` files are committed (see `.gitignore`) — only `*.env.*.example`
templates with placeholder values. Copy the templates you need and fill in real
credentials/API keys locally before running anything.
