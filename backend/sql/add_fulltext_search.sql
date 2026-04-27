-- Migration: add full-text search support to document_chunks.
--
-- Run this once against an existing database:
--   docker exec -i medical_rag_postgres psql -U appuser -d medical_rag < backend/sql/add_fulltext_search.sql
--
-- For fresh databases this is already included in createTables.sql.

ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS tsv tsvector;

CREATE INDEX IF NOT EXISTS idx_chunks_tsv
    ON document_chunks USING gin(tsv);

CREATE OR REPLACE FUNCTION document_chunks_tsv_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.tsv :=
        setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.content, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_chunks_tsv ON document_chunks;

CREATE TRIGGER trg_chunks_tsv
BEFORE INSERT OR UPDATE ON document_chunks
FOR EACH ROW
EXECUTE FUNCTION document_chunks_tsv_update();

-- Back-fill any rows inserted before the trigger existed
UPDATE document_chunks
SET tsv = setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
          setweight(to_tsvector('english', coalesce(content, '')), 'B')
WHERE tsv IS NULL;
