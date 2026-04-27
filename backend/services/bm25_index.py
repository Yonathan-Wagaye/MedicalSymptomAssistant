"""
BM25 keyword index built from document_chunks.

Unlike Postgres tsvector (always in sync), BM25 lives in-memory and
must be rebuilt after ingestion.  The trade-off: BM25Okapi is the
standard scoring function in IR literature and gives you explicit
control over tokenisation/stemming.

Workflow:
    build_index(db)          → construct from current DB rows
    save(path) / load(path)  → persist to / restore from disk
    search(query, top_k)     → ranked keyword results

The index is serialised with pickle to the path in
``config.BM25_INDEX_PATH`` (default ``./bm25_index.pkl``).
"""

from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass, field
from pathlib import Path

import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from rank_bm25 import BM25Okapi
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.services.vector_store import SearchResult

logger = logging.getLogger(__name__)

_STEMMER = PorterStemmer()
_STOP_WORDS: set[str] | None = None


def _ensure_nltk_data() -> None:
    """Download NLTK tokeniser and stopword data if missing."""
    for resource in ("punkt_tab", "stopwords"):
        try:
            nltk.data.find(f"tokenizers/{resource}" if "punkt" in resource else f"corpora/{resource}")
        except LookupError:
            nltk.download(resource, quiet=True)


def _get_stop_words() -> set[str]:
    global _STOP_WORDS
    if _STOP_WORDS is None:
        _ensure_nltk_data()
        _STOP_WORDS = set(stopwords.words("english"))
    return _STOP_WORDS


def tokenize(text_: str) -> list[str]:
    """Lowercase → word-tokenise → drop stopwords → stem."""
    _ensure_nltk_data()
    stops = _get_stop_words()
    tokens = word_tokenize(text_.lower())
    return [_STEMMER.stem(t) for t in tokens if t.isalnum() and t not in stops]


@dataclass
class BM25Index:
    """Wrapper around a BM25Okapi index with chunk metadata."""

    bm25: BM25Okapi
    chunk_ids: list[str]
    chunk_texts: list[str]
    chunk_metadata: list[dict] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    @classmethod
    def build(cls, db: Session) -> BM25Index:
        """Pull every chunk from the DB and build a BM25 index."""
        logger.info("Loading chunks from document_chunks …")
        rows = db.execute(
            text("SELECT id, content, source_id, title, section, url FROM document_chunks")
        ).fetchall()

        if not rows:
            raise ValueError("No chunks in document_chunks — run ingestion first")

        chunk_ids: list[str] = []
        chunk_texts: list[str] = []
        chunk_metadata: list[dict] = []
        corpus: list[list[str]] = []

        for r in rows:
            chunk_ids.append(str(r.id))
            chunk_texts.append(r.content)
            chunk_metadata.append(
                {"source_id": r.source_id, "title": r.title, "section": r.section, "url": r.url}
            )
            corpus.append(tokenize(r.content))

        logger.info("Building BM25 index over %d documents …", len(corpus))
        bm25 = BM25Okapi(corpus)

        return cls(
            bm25=bm25,
            chunk_ids=chunk_ids,
            chunk_texts=chunk_texts,
            chunk_metadata=chunk_metadata,
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
        size_mb = path.stat().st_size / (1024 * 1024)
        logger.info("BM25 index saved (%.1f MB) → %s", size_mb, path)

    @classmethod
    def load(cls, path: str | Path) -> BM25Index:
        path = Path(path)
        with open(path, "rb") as f:
            idx = pickle.load(f)  # noqa: S301
        logger.info("BM25 index loaded (%d docs) ← %s", len(idx.chunk_ids), path)
        return idx

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 20) -> list[SearchResult]:
        """Tokenise *query* and return the top-k BM25-ranked chunks."""
        tokens = tokenize(query)
        if not tokens:
            return []

        scores = self.bm25.get_scores(tokens)

        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        return [
            SearchResult(
                chunk_id=self.chunk_ids[i],
                text=self.chunk_texts[i],
                score=float(scores[i]),
                metadata=self.chunk_metadata[i],
            )
            for i in ranked_indices
            if scores[i] > 0
        ]


# ------------------------------------------------------------------
# Module-level singleton (lazy-loaded)
# ------------------------------------------------------------------

_index: BM25Index | None = None


def get_index(path: str | Path | None = None) -> BM25Index:
    """Return the cached BM25 index, loading from disk if needed."""
    global _index
    if _index is None:
        if path is None:
            from backend.core.config import config
            path = config.BM25_INDEX_PATH
        _index = BM25Index.load(path)
    return _index


def invalidate() -> None:
    """Clear the cached index so it is reloaded on next access."""
    global _index
    _index = None
