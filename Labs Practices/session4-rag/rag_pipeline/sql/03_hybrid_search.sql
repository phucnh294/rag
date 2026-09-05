-- Lab3+ hybrid search: bring the already-declared rag_chunks.content_tsv
-- column to life (trigger + backfill + GIN index). Purely additive — never
-- drops a table, column, or row of data. Idempotent: safe to re-run.

CREATE OR REPLACE FUNCTION rag_chunks_tsv_trigger_martin() RETURNS trigger AS $$
BEGIN
  NEW.content_tsv := to_tsvector('english', COALESCE(NEW.content, ''));
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_rag_chunks_tsv ON rag_chunks;
CREATE TRIGGER trg_rag_chunks_tsv
  BEFORE INSERT OR UPDATE OF content ON rag_chunks
  FOR EACH ROW EXECUTE FUNCTION rag_chunks_tsv_trigger_martin();

-- Backfill rows written before this trigger existed.
UPDATE rag_chunks SET content_tsv = to_tsvector('english', content) WHERE content_tsv IS NULL;

CREATE INDEX IF NOT EXISTS idx_rag_chunks_content_tsv ON rag_chunks USING GIN (content_tsv);
