from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# dataclass to store the search result
@dataclass
class SearchResult:
    chunk_id: str
    text: str
    score: float
    metadata: dict = field(default_factory=dict)


def search(
    db: Session,
    query_embedding: list[float],
    top_k: int = 10,
) -> list[SearchResult]:
    emb_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"

    rows = db.execute(
        text("""
            SELECT id, content, source_id, title, section, url,
                   1 - (embedding <=> CAST(:emb AS vector)) AS similarity
            FROM document_chunks
            ORDER BY embedding <=> CAST(:emb AS vector)
            LIMIT :k
        """),
        {"emb": emb_literal, "k": top_k},
    ).fetchall()

    return [
        SearchResult(
            chunk_id=str(r.id),
            text=r.content,
            score=float(r.similarity),
            metadata={
                "source_id": r.source_id,
                "title": r.title,
                "section": r.section,
                "url": r.url,
            },
        )
        for r in rows
    ]


def add_documents(
    db: Session,
    chunks: list[dict],
    embeddings: list[list[float]],
) -> int:
    for chunk, emb in zip(chunks, embeddings):
        emb_literal = "[" + ",".join(str(v) for v in emb) + "]"
        db.execute(
            text("""
                INSERT INTO document_chunks
                    (content, source_id, title, section, url, embedding)
                VALUES
                    (:content, :source_id, :title, :section, :url, CAST(:emb AS vector))
            """),
            {
                "content": chunk["content"],
                "source_id": chunk["source_id"],
                "title": chunk["title"],
                "section": chunk.get("section"),
                "url": chunk.get("url"),
                "emb": emb_literal,
            },
        )

    db.commit()
    logger.info("Inserted %d chunks into document_chunks", len(chunks))
    return len(chunks)


def count_chunks(db: Session) -> int:
    return db.execute(text("SELECT count(*) FROM document_chunks")).scalar() or 0
