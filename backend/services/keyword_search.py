"""
Postgres full-text search against document_chunks.

Uses the ``tsv`` tsvector column (auto-populated by a BEFORE INSERT
trigger) with cover-density ranking.

IMPORTANT: uses **OR** semantics so that a document matching ANY query
term is returned.  Documents matching more terms rank higher via
``ts_rank_cd``.  The previous AND (``plainto_tsquery``) approach was
too restrictive — most natural-language symptom queries returned 0 hits
because no single chunk contained every query word.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.services.vector_store import SearchResult

logger = logging.getLogger(__name__)

_STOP_WORDS = frozenset({
    "i", "me", "my", "a", "an", "the", "is", "am", "are", "was", "were",
    "be", "been", "do", "does", "did", "have", "has", "had", "and", "or",
    "but", "if", "in", "on", "at", "to", "for", "of", "with", "by",
    "it", "its", "this", "that", "from", "so", "very", "really", "also",
    "just", "not", "no", "all", "both", "each", "been", "being",
    "about", "than", "too", "some", "such", "can", "will", "would",
    "should", "could", "may", "might", "lot", "lots", "much",
})


def _to_or_tsquery(query: str) -> str:
    """
    Convert a natural-language query into an OR-joined tsquery string.

    ``to_tsquery('english', 'fever | cough | chest | pain')`` lets
    Postgres stem each term and match documents containing ANY of them.
    """
    words = re.findall(r"[a-zA-Z]+", query.lower())
    terms = [w for w in words if len(w) > 1 and w not in _STOP_WORDS]
    if not terms:
        return query.lower()
    return " | ".join(terms)


def search(
    db: Session,
    query: str,
    top_k: int = 20,
) -> list[SearchResult]:
    """
    Full-text keyword search using Postgres tsvector with OR semantics.

    Ranking uses ``ts_rank_cd`` (cover-density) which rewards terms
    appearing close together — good for medical phrases like
    "chest pain".  Documents matching more query terms rank higher.
    """
    if not query.strip():
        return []

    or_query = _to_or_tsquery(query)
    logger.debug("tsquery: %s", or_query)

    rows = db.execute(
        text("""
            SELECT id, content, source_id, title, section, url,
                   ts_rank_cd(tsv, q) AS rank
            FROM document_chunks,
                 to_tsquery('english', :q) q
            WHERE tsv @@ q
            ORDER BY rank DESC
            LIMIT :k
        """),
        {"q": or_query, "k": top_k},
    ).fetchall()

    return [
        SearchResult(
            chunk_id=str(r.id),
            text=r.content,
            score=float(r.rank),
            metadata={
                "source_id": r.source_id,
                "title": r.title,
                "section": r.section,
                "url": r.url,
            },
        )
        for r in rows
    ]
