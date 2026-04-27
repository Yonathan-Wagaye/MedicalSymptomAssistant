"""
Build (or rebuild) the BM25 keyword index from document_chunks.

Run this after every ingestion so the BM25 backend stays current.
The Postgres tsvector backend does NOT need this step — it auto-updates.

Usage (from project root):
    python -m backend.scripts.build_bm25_index
"""

from __future__ import annotations

import logging

from backend.core.config import config
from backend.core.database import SessionLocal
from backend.core.logging import setup_logging
from backend.services.bm25_index import BM25Index, invalidate

setup_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    db = SessionLocal()
    try:
        idx = BM25Index.build(db)
        idx.save(config.BM25_INDEX_PATH)
        invalidate()
        print(f"\nBM25 index built: {len(idx.chunk_ids)} documents → {config.BM25_INDEX_PATH}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
