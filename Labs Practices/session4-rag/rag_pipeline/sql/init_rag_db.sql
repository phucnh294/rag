-- Idempotent schema for the RAG knowledge base.
-- Designed for the rag-ai-local corpus (QandA + functionality-docs) and
-- evolves across labs: columns for later labs exist now but stay unused
-- until that lab is reached. {{EMBEDDING_DIM}} is substituted by
-- sql/migrations.py at startup.

CREATE EXTENSION IF NOT EXISTS vector;

-- 1) DOCUMENTS — 1 row / .md file
CREATE TABLE IF NOT EXISTS rag_documents (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_path  TEXT NOT NULL UNIQUE,   -- e.g. rag-ai-local/QandA/07042026_....md
  raw_content  TEXT,                   -- [Lab1] full file text
  -- [Lab2] filled from frontmatter + TL;DR:
  doc_type VARCHAR(30), title TEXT, doc_date DATE, area VARCHAR(100),
  status VARCHAR(40), tags TEXT[], description TEXT, summary TEXT,
  metadata JSONB, created_at TIMESTAMP DEFAULT NOW()
);

-- 2) CHUNKS — many fixed-token chunks / document
CREATE TABLE IF NOT EXISTS rag_chunks (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES rag_documents(id) ON DELETE CASCADE,
  chunk_index INT, content TEXT NOT NULL, token_count INT,  -- [Lab1]
  metadata JSONB,                    -- [Lab2]
  content_tsv tsvector,              -- [Lab3] full-text
  UNIQUE (document_id, chunk_index)
);

-- 3) EMBEDDINGS — 1 vector / chunk
CREATE TABLE IF NOT EXISTS rag_embeddings (
  id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chunk_id UUID REFERENCES rag_chunks(id) ON DELETE CASCADE,
  embedding vector({{EMBEDDING_DIM}}) NOT NULL,  -- 768 = nomic
  model VARCHAR(80), UNIQUE (chunk_id)
);

-- Indexes to support the Lab1 access patterns (FK lookups + ordering).
CREATE INDEX IF NOT EXISTS idx_rag_chunks_document_id ON rag_chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_rag_embeddings_chunk_id ON rag_embeddings (chunk_id);

-- NOTE: the lab HTML marks this excerpt as partial ("+ index, trigger
-- updated_at, trigger content_tsv (Lab3). Xem file đầy đủ") but the fuller
-- version was never provided alongside the lab materials. The indexes above
-- cover Lab1's needs; an `updated_at` trigger and the Lab3 `content_tsv`
-- trigger are intentionally left out until those labs are reached.
