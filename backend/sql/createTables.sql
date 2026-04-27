-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable vector similarity search (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- =========================================================
-- 1. chat_sessions
-- =========================================================
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================================
-- 2. messages
-- =========================================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_messages_session
        FOREIGN KEY (session_id)
        REFERENCES chat_sessions(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_session_id
    ON messages(session_id);

CREATE INDEX IF NOT EXISTS idx_messages_created_at
    ON messages(created_at);

-- =========================================================
-- 3. symptom_queries
-- =========================================================
CREATE TABLE IF NOT EXISTS symptom_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    raw_query TEXT NOT NULL,
    normalized_query TEXT,
    response_summary TEXT,
    possible_conditions JSONB,
    retrieved_docs JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_symptom_queries_session
        FOREIGN KEY (session_id)
        REFERENCES chat_sessions(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_symptom_queries_session_id
    ON symptom_queries(session_id);

CREATE INDEX IF NOT EXISTS idx_symptom_queries_created_at
    ON symptom_queries(created_at);

-- =========================================================
-- 4. feedback
-- =========================================================
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symptom_query_id UUID NOT NULL,
    helpful BOOLEAN NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_feedback_symptom_query
        FOREIGN KEY (symptom_query_id)
        REFERENCES symptom_queries(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_feedback_symptom_query_id
    ON feedback(symptom_query_id);

-- =========================================================
-- 5. document_chunks (pgvector)
--
-- Stores text chunks alongside their vector embeddings.
-- vector(768) matches the output of all-mpnet-base-v2.
--
-- The HNSW index enables approximate nearest-neighbor search.
-- Without it pgvector does a brute-force scan of every row --
-- fine under ~10k chunks, but the index keeps queries O(log n).
-- =========================================================
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT NOT NULL,
    title TEXT NOT NULL,
    section TEXT,
    url TEXT,
    content TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_source_id
    ON document_chunks(source_id);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
    ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- =========================================================
-- 5b. Full-text search for hybrid retrieval
--
-- A tsvector column lets Postgres do keyword search natively.
-- Title words get weight 'A' (highest); content gets 'B'.
-- A BEFORE INSERT trigger auto-populates the column so the
-- existing INSERT code in vector_store.add_documents works
-- without changes.
-- =========================================================
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

-- =========================================================
-- 6. Trigger: auto-update updated_at on chat_sessions
-- =========================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_chat_sessions_updated_at ON chat_sessions;

CREATE TRIGGER trg_chat_sessions_updated_at
BEFORE UPDATE ON chat_sessions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
