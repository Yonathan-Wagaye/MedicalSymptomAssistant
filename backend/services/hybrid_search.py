"""
Hybrid search: fuse vector (semantic) and keyword (lexical) results,
then optionally rerank with a cross-encoder.

Every stage is traced to the ``algo`` logger → backend/logs/main_algo.log.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Literal

from sqlalchemy.orm import Session

from backend.services import embeddings, keyword_search, vector_store
from backend.services.vector_store import SearchResult

logger = logging.getLogger(__name__)
algo = logging.getLogger("algo")

RRF_K = 60


def _rrf_fuse(
    *result_lists: list[SearchResult],
) -> list[SearchResult]:
    """Merge ranked lists using Reciprocal Rank Fusion."""
    scores: dict[str, float] = defaultdict(float)
    seen: dict[str, SearchResult] = {}

    for results in result_lists:
        for rank, result in enumerate(results, start=1):
            scores[result.chunk_id] += 1.0 / (RRF_K + rank)
            if result.chunk_id not in seen:
                seen[result.chunk_id] = result

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)

    return [
        SearchResult(
            chunk_id=cid,
            text=seen[cid].text,
            score=score,
            metadata=seen[cid].metadata,
        )
        for cid, score in ranked
    ]


def search(
    db: Session,
    query: str,
    top_k: int = 10,
    keyword_backend: Literal["postgres", "bm25"] = "postgres",
    candidates_per_retriever: int | None = None,
    rerank: bool = True,
    rerank_candidates: int | None = None,
) -> list[SearchResult]:
    n = candidates_per_retriever or top_k * 3

    # ── stage 1: semantic retriever ──
    t1 = time.perf_counter()
    query_emb = embeddings.embed_query(query)
    vector_results = vector_store.search(db, query_emb, top_k=n)
    t1_done = time.perf_counter()

    algo.info("[VECTOR] Candidates: %d  (%.0f ms)", len(vector_results), (t1_done - t1) * 1000)
    if vector_results:
        algo.info("[VECTOR] Top 3:")
        for r in vector_results[:3]:
            algo.info("           • %s (%.4f)", r.metadata.get("title", "?"), r.score)

    # ── stage 2: keyword retriever ──
    t2 = time.perf_counter()
    if keyword_backend == "bm25":
        from backend.services.bm25_index import get_index
        idx = get_index()
        keyword_results = idx.search(query, top_k=n)
    else:
        keyword_results = keyword_search.search(db, query, top_k=n)
    t2_done = time.perf_counter()

    algo.info("[KEYWORD] Backend: %s  Candidates: %d  (%.0f ms)",
              keyword_backend, len(keyword_results), (t2_done - t2) * 1000)
    if keyword_results:
        algo.info("[KEYWORD] Top 3:")
        for r in keyword_results[:3]:
            algo.info("           • %s (%.4f)", r.metadata.get("title", "?"), r.score)

    logger.info(
        "Hybrid retrieval: %d vector + %d keyword candidates (backend=%s)",
        len(vector_results), len(keyword_results), keyword_backend,
    )

    # ── stage 3: RRF fusion ──
    t3 = time.perf_counter()
    fused = _rrf_fuse(vector_results, keyword_results)
    t3_done = time.perf_counter()

    unique_count = len(fused)
    overlap = (len(vector_results) + len(keyword_results)) - unique_count
    algo.info("[RRF] Unique after fusion: %d  (overlap=%d, %.0f ms)",
              unique_count, overlap, (t3_done - t3) * 1000)
    if fused:
        algo.info("[RRF] Top 3:")
        for r in fused[:3]:
            algo.info("           • %s (rrf=%.6f)", r.metadata.get("title", "?"), r.score)

    # ── stage 4: cross-encoder rerank ──
    if rerank:
        from backend.services.reranker import rerank as _rerank

        n_rerank = rerank_candidates or top_k * 3
        shortlist = fused[:n_rerank]

        t4 = time.perf_counter()
        results = _rerank(query, shortlist, top_k=top_k)
        t4_done = time.perf_counter()

        algo.info("[RERANK] Input: %d candidates  Output: %d  (%.0f ms)",
                  len(shortlist), len(results), (t4_done - t4) * 1000)
        if results:
            algo.info("[RERANK] Score range: %.4f → %.4f", results[0].score, results[-1].score)
            algo.info("[RERANK] Top 3:")
            for r in results[:3]:
                algo.info("           • %s (%.4f)", r.metadata.get("title", "?"), r.score)

        logger.info(
            "Rerank complete — top score %.4f, bottom score %.4f",
            results[0].score if results else 0,
            results[-1].score if results else 0,
        )
        return results

    return fused[:top_k]
