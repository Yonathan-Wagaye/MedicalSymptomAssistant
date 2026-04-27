from __future__ import annotations

import logging

from sentence_transformers import CrossEncoder

from backend.core.config import config
from backend.services.vector_store import SearchResult

logger = logging.getLogger(__name__)

_model: CrossEncoder | None = None


# lazy load the cross-encoder model
def _get_model() -> CrossEncoder:
    global _model
    if _model is None:
        logger.info("Loading reranker model: %s …", config.RERANKER_MODEL)
        _model = CrossEncoder(config.RERANKER_MODEL)
        logger.info("Reranker model ready")
    return _model


# rerank the candidates with the cross-encoder and return the top-k
def rerank(
    query: str,
    candidates: list[SearchResult],
    top_k: int = 10,
) -> list[SearchResult]:
    if not candidates:
        return []

    model = _get_model()

    pairs = [(query, c.text) for c in candidates]
    scores = model.predict(pairs, show_progress_bar=False)

    scored = sorted(
        zip(candidates, scores),
        key=lambda cs: cs[1],
        reverse=True,
    )

    return [
        SearchResult(
            chunk_id=candidate.chunk_id,
            text=candidate.text,
            score=float(score),
            metadata=candidate.metadata,
        )
        for candidate, score in scored[:top_k]
    ]
