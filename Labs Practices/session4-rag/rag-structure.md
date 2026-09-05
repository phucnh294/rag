# rag_pipeline/ — File-by-File Task Breakdown

Companion doc to `02_module4-rag-lab.html`. Scope: build only the `[Lab1]`
steps below. `[Lab2]`/`[Lab3]` steps are stubbed (pass-through / return
empty) so the pipeline runs end-to-end now and gets extended in later labs.

API contract these files must satisfy:

| Endpoint | Request | Response |
|---|---|---|
| `POST /upload` | multipart `file` (.md) | `{"chunks_indexed": <int>}` |
| `POST /chat` | json `{"question": "<str>"}` | `{"answer": "<str>", "sources": ["<filename>", ...]}` |
| `GET /` | — | `ui/index.html` |

---

## main.py

**[Lab1]** Entry point. Calls `run_migrations_martin()` (from
`sql/migrations.py`) to bring the schema up to date, then starts the FastAPI
app (`uvicorn`) defined in `api/`.

---

## config/

- **env_config.py** — **[Lab1]** Load and validate all env vars from
  `.env.rag` (DB creds, `OLLAMA_NOMIC_EMBED_TEXT_HOST`/`_PORT`,
  `OLLAMA_LLAMA31_HOST`/`_PORT`, `EMBEDDING_DIM`) into one typed config
  object. Fail fast (raise) on a missing required var.
- **db_connection.py** — **[Lab1]** Provide a helper that opens a Postgres
  connection (or a small pool) using the config above. Used by
  `indexing/step7`, `step8`, and `retrieval/step4`.
- **llm_setup.py** — **[Lab1]** Build the clients used to talk to the two
  Ollama models — either raw REST calls (`POST /api/embeddings`,
  `POST /api/chat`) or LangChain's `OllamaEmbeddings`/`ChatOllama`. One
  function per model call: embed(text) -> list[float], chat(prompt) -> str.

---

## indexing/ — PROCESS 1 (upload → indexed)

| Step | File | Task | Lab |
|---|---|---|---|
| 1 | `step1_load_input.py` | Read one `.md` file's raw text given its path (the file `/upload` just saved into `input/`). Return `(source_path, raw_text)`. | Lab1 |
| 2 | `step2_document_parsing.py` | Split `raw_text` into `(frontmatter_block, body_text)` by finding the `---`...`---` delimiters. Lab1 only needs the split, not field parsing. | Lab1 |
| 3 | `step3_chunking_strategy.py` | Fixed-token chunking of `body_text`: 800 tokens per chunk, 120 token overlap. Return `list[str]` chunks in order. | Lab1 |
| 4 | `step4_preprocessing.py` | Clean each chunk before embedding — strip control chars, collapse excess whitespace. Return `list[str]`. | Lab1 |
| 5 | `step5_metadata_extraction.py` | Parse `frontmatter_block` into title/date/area/status/tags/summary. | **Lab2 — stub: return `{}`** |
| 6 | `step6_embedding_gen.py` | Call `llm_setup`'s embed function on each cleaned chunk. Return `list[list[float]]` (768-dim each). | Lab1 |
| 7 | `step7_store_documents.py` | Upsert one row into `rag_documents` (`source_path`, `raw_content`) — `ON CONFLICT (source_path) DO UPDATE`. Return the `document_id`. | Lab1 |
| 8 | `step8_store_chunks.py` | For each `(chunk_text, embedding)` pair: insert into `rag_chunks` (`document_id`, `chunk_index`, `content`, `token_count`), then insert the matching `rag_embeddings` row (`chunk_id`, `embedding`, `model`). | Lab1 |
| — | `index_runner.py` | Orchestrate steps 1→8 for one file path. Return `chunks_indexed: int` for the API response. | Lab1 |

**Depends on:** `config/db_connection.py`, `config/llm_setup.py`, `shared/md_frontmatter.py`.

---

## retrieval/ — PROCESS 2 (question → answer)

| Step | File | Task | Lab |
|---|---|---|---|
| 1-3 | receive / normalize / embed question | Take `{"question": str}`, trim/validate it, embed it via `llm_setup`. Return the question vector. | Lab1 |
| 4 | `step4_similarity_search.py` | Cosine top-k against `rag_embeddings` (`ORDER BY embedding <=> %s LIMIT k`). Join back to `rag_chunks`/`rag_documents` for content + `source_path`. Return the top-k rows. | Lab1 |
| 5 | `step5_metadata_filter.py` | Pre-filter candidates by `area`/`status`/`tags` before the vector search. | **Lab2 — stub: pass through unfiltered** |
| 6 | `step6_reranking.py` | Cross-encoder rerank of the top-k. | **Lab3+ — stub: pass through unchanged** |
| 7-9 | context assembly / prompt building / LLM call | Concatenate the retrieved chunk texts into a context block, build the final prompt (system + context + question), call `llm_setup`'s chat function. | Lab1 |
| 10 | `step10_response.py` | Shape the final `{"answer": str, "sources": list[str]}` — `sources` = de-duplicated `source_path`/filenames of the chunks actually used. | Lab1 |
| — | `retrieval_runner.py` | Orchestrate steps 1→10 for one question. Return the shaped response dict. | Lab1 |

**Depends on:** `config/db_connection.py`, `config/llm_setup.py`.

---

## api/

- **main.py** — **[Lab1]** FastAPI app instance, mounts `routes_upload` and
  `routes_chat`, serves `ui/index.html` (static) at `GET /`.
- **routes_upload.py** — **[Lab1]** `POST /upload`: accept multipart `file`,
  write it into `input/`, call `indexing.index_runner`, return
  `{"chunks_indexed": N}`.
- **routes_chat.py** — **[Lab1]** `POST /chat`: accept `{"question": str}`,
  call `retrieval.retrieval_runner`, return its `{"answer", "sources"}` dict
  directly.

---

## shared/

- **md_frontmatter.py** — **[Lab1]** Parse/strip a YAML frontmatter block
  from a markdown string. Used by `indexing/step2`.
- **file_utils.py** — **[Lab1]** Filesystem helpers: list `.md` files under
  `input/`, safely write an uploaded file into `input/` (sanitize the
  filename).
- **logger.py** — **[Lab1]** One place that configures the `logging` module
  (level from env, consistent format) — imported by every other module
  instead of each one configuring logging itself.

---

## ui/

- **index.html** — Given/copied as-is (see lab tab ⑤). Calls `POST /upload`
  and `POST /chat` on the same origin (`:8000`). No backend work needed here.
