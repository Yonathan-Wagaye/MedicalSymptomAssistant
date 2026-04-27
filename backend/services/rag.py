"""
RAG orchestrator — ties query classification, hybrid search, LLM, and
conversation history into a single ``answer_query`` call.

Every decision is traced to the ``algo`` logger → backend/logs/main_algo.log
so you can follow the full pipeline for any query.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.messages import Message
from backend.services import hybrid_search, llm
from backend.services.query_classifier import QueryUrgency, classify_query

logger = logging.getLogger(__name__)
algo = logging.getLogger("algo")

MAX_HISTORY_MESSAGES = 10
_SEPARATOR = "=" * 60


@dataclass
class RAGResponse:
    """Structured output from the RAG pipeline."""

    answer: str
    urgency: str = "normal"
    follow_up_questions: list[str] = field(default_factory=list)
    related_conditions: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)


def _load_history(db: Session, session_id: UUID) -> list[dict]:
    """Fetch the last N messages for this session, oldest first."""
    rows = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )
    rows.reverse()
    return [{"role": r.role, "content": r.content} for r in rows]


def answer_query(
    db: Session,
    query: str,
    session_id: UUID,
    *,
    top_k: int = 10,
    rerank: bool = True,
) -> RAGResponse:
    """
    Full RAG pipeline: classify → retrieve → prompt → generate → parse.
    """
    t0 = time.perf_counter()
    algo.info(_SEPARATOR)
    algo.info("QUERY: %r", query)
    algo.info(_SEPARATOR)

    # ── 1. classify ──
    t_cls = time.perf_counter()
    classification = classify_query(query)
    algo.info("[CLASSIFY] Urgency       : %s", classification.urgency.value)
    algo.info("[CLASSIFY] Red flags     : %s", classification.red_flags or "none")
    algo.info("[CLASSIFY] Symptom count : %d", classification.symptom_count)
    if classification.urgency == QueryUrgency.VAGUE:
        algo.info("[CLASSIFY] Decision      : SKIP retrieval → ask follow-up questions")
    elif classification.urgency == QueryUrgency.RED_FLAG:
        algo.info("[CLASSIFY] Decision      : Retrieval WITH red-flag safety preamble")
    else:
        algo.info("[CLASSIFY] Decision      : Normal retrieval + generation")
    algo.info("[CLASSIFY] Time          : %.1f ms", (time.perf_counter() - t_cls) * 1000)
    algo.info("-" * 40)

    logger.info(
        "Query classified: urgency=%s, red_flags=%s, symptom_count=%d",
        classification.urgency.value,
        classification.red_flags,
        classification.symptom_count,
    )

    # ── 2. retrieve (skip for vague queries) ──
    source_dicts: list[dict] = []

    if classification.urgency != QueryUrgency.VAGUE:
        t_ret = time.perf_counter()
        search_results = hybrid_search.search(
            db, query=query, top_k=top_k, rerank=rerank,
        )
        source_dicts = [
            {
                "id": sr.chunk_id,
                "title": sr.metadata.get("title", ""),
                "url": sr.metadata.get("url", ""),
                "text": sr.text,
                "score": sr.score,
            }
            for sr in search_results
        ]
        algo.info("[RETRIEVE] Sources returned : %d", len(source_dicts))
        if source_dicts:
            algo.info("[RETRIEVE] Top 3 titles     :")
            for s in source_dicts[:3]:
                algo.info("             • %s (score=%.4f)", s["title"], s["score"])
        algo.info("[RETRIEVE] Total time       : %.1f ms", (time.perf_counter() - t_ret) * 1000)
    else:
        algo.info("[RETRIEVE] SKIPPED — query classified as VAGUE")

    algo.info("-" * 40)

    context_block = llm.build_context_block(source_dicts)

    # ── 3. build classification hint ──
    classification_hint = _build_classification_hint(classification)
    algo.info("[PROMPT] Directive      : %s", classification.urgency.value)

    # ── 4. build messages ──
    history = _load_history(db, session_id)
    algo.info("[PROMPT] History msgs   : %d", len(history))
    algo.info("[PROMPT] Context sources: %d", len(source_dicts))

    messages: list[dict[str, str]] = [
        {"role": "system", "content": llm.SYSTEM_PROMPT},
        *history,
        {
            "role": "user",
            "content": (
                f"{classification_hint}\n\n"
                f"Context from medical knowledge base:\n"
                f"---\n{context_block}\n---\n\n"
                f"User question: {query}"
            ),
        },
    ]

    algo.info("[PROMPT] Total messages  : %d", len(messages))
    algo.info("-" * 40)

    # ── 5. call LLM ──
    t_llm = time.perf_counter()
    raw = llm.chat_completion(messages, json_mode=True)
    t_llm_done = time.perf_counter()
    parsed = llm.parse_llm_json(raw)

    answer = parsed.get("answer", raw)
    urgency = parsed.get("urgency", "normal")
    follow_ups = parsed.get("follow_up_questions", [])
    related = parsed.get("related_conditions", [])

    algo.info("[LLM] Model             : %s", llm.config.LLM_MODEL)
    algo.info("[LLM] Time              : %.1f ms", (t_llm_done - t_llm) * 1000)
    algo.info("[LLM] Response urgency  : %s", urgency)
    algo.info("[LLM] Answer length     : %d chars", len(answer))
    algo.info("[LLM] Related conditions: %d", len(related))
    for c in related:
        algo.info("             • %s (confidence=%s)", c.get("name"), c.get("confidence", "?"))
    algo.info("[LLM] Follow-up Qs      : %d", len(follow_ups))
    for q in follow_ups:
        algo.info("             • %s", q)
    algo.info("-" * 40)

    total_ms = (time.perf_counter() - t0) * 1000
    algo.info("[TOTAL] Pipeline time: %.0f ms", total_ms)
    algo.info(_SEPARATOR + "\n")

    logger.info(
        "RAG complete: urgency=%s, %d sources, %d conditions, %d follow-ups, %d chars (%.0f ms)",
        urgency, len(source_dicts), len(related), len(follow_ups), len(answer), total_ms,
    )

    return RAGResponse(
        answer=answer,
        urgency=urgency,
        follow_up_questions=follow_ups,
        related_conditions=related,
        sources=source_dicts,
    )


def _build_classification_hint(classification) -> str:
    if classification.urgency == QueryUrgency.VAGUE:
        return (
            "[SYSTEM DIRECTIVE: The query is VAGUE — it lacks specific "
            "symptoms.  Follow POLICY 1: ask clarifying follow-up questions.  "
            "Do NOT list diseases.  Set urgency to 'clarification_needed'.]"
        )

    if classification.urgency == QueryUrgency.RED_FLAG:
        flags = ", ".join(classification.red_flags)
        return (
            f"[SYSTEM DIRECTIVE: RED-FLAG symptoms detected: {flags}.  "
            f"Follow POLICY 2: lead with urgent-care guidance.  "
            f"Set urgency to 'emergency'.]"
        )

    return (
        "[SYSTEM DIRECTIVE: The query contains identifiable symptoms.  "
        "Follow POLICY 3: provide cautious, evidence-grounded information.  "
        "Set urgency to 'normal'.]"
    )
