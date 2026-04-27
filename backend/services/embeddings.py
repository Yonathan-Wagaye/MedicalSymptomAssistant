from __future__ import annotations

import logging

from sentence_transformers import SentenceTransformer

from backend.core.config import config

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


 # lazy-load the embedding model on first use
def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s …", config.EMBEDDING_MODEL)
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
        logger.info(
            "Embedding model ready (dim=%d)",
            _model.get_sentence_embedding_dimension(),
        )
    return _model

# encode a batch of strings into float vectors
def embed_texts(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    embeddings = model.encode(texts, show_progress_bar=len(texts) > 50)
    return embeddings.tolist()

# encode a single query string
def embed_query(query: str) -> list[float]:
    return embed_texts([query])[0]
