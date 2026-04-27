"""
Ingestion service — embeds documents and stores them in pgvector.

HOW INGESTION WORKS:

Data sources (Kaggle CSV, MedlinePlus scraper, etc.) prepare their data
into a standard list of dicts:

    [
        {"content": "text to embed", "source_id": "unique_id", "title": "...", ...},
        ...
    ]

This service then:
1. Optionally clears old chunks from the same source (idempotent re-runs)
2. Embeds the text in batches (batch_size controls memory vs speed)
3. Inserts into pgvector via the vector_store service
4. Optionally rebuilds the BM25 keyword index

The Postgres tsvector column updates automatically via a trigger, so
keyword search through the ``postgres`` backend works with no extra step.
The BM25 in-memory index must be rebuilt explicitly (step 4).

WHY BATCH:
The embedding model processes multiple texts faster in a batch than one
at a time (GPU/CPU SIMD parallelism). But too large a batch can OOM.
64 is a safe default for the ~420MB all-mpnet-base-v2 model on CPU.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.services import embeddings, vector_store

logger = logging.getLogger(__name__)


def ingest_documents(
    db: Session,
    documents: list[dict],
    batch_size: int = 64,
    clear_source: str | None = None,
    rebuild_bm25: bool = True,
) -> int:
    """
    Embed and store documents in pgvector.

    Args:
        db: database session
        documents: dicts with keys content, source_id, title
                   (optional: section, url)
        batch_size: texts per embedding call
        clear_source: if set, DELETE existing chunks whose source_id
                      starts with this prefix before inserting
        rebuild_bm25: rebuild the BM25 in-memory index after inserting
                      (Postgres tsvector updates automatically via trigger)
    Returns:
        number of chunks inserted
    """
    if clear_source:
        deleted = db.execute(
            text("DELETE FROM document_chunks WHERE source_id LIKE :prefix"),
            {"prefix": f"{clear_source}%"},
        ).rowcount
        db.commit()
        logger.info("Cleared %d existing chunks (prefix='%s')", deleted, clear_source)

    total_batches = (len(documents) + batch_size - 1) // batch_size
    total_inserted = 0

    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        texts = [doc["content"] for doc in batch]

        logger.info(
            "Embedding batch %d/%d (%d texts)…",
            i // batch_size + 1,
            total_batches,
            len(texts),
        )

        embs = embeddings.embed_texts(texts)
        vector_store.add_documents(db, batch, embs)
        total_inserted += len(batch)

    logger.info("Ingestion complete: %d chunks stored", total_inserted)

    if rebuild_bm25 and total_inserted > 0:
        try:
            from backend.core.config import config
            from backend.services.bm25_index import BM25Index, invalidate

            logger.info("Rebuilding BM25 index …")
            idx = BM25Index.build(db)
            idx.save(config.BM25_INDEX_PATH)
            invalidate()
            logger.info("BM25 index rebuilt (%d docs)", len(idx.chunk_ids))
        except Exception:
            logger.warning("BM25 rebuild failed (non-fatal) — run build_bm25_index manually", exc_info=True)

    return total_inserted
