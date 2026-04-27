"""
POST /query — the main RAG endpoint.

Accepts a user question + session ID, runs the full pipeline
(classify → retrieve → generate), persists messages and metadata,
and returns a structured response.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.chat_sessions import ChatSession
from backend.models.messages import Message
from backend.models.symptom_queries import SymptomQuery
from backend.schemas.query import QueryRequest, QueryResponse, RelatedTopic, Source
from backend.services.rag import answer_query

logger = logging.getLogger(__name__)

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def submit_query(body: QueryRequest, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == body.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.add(Message(session_id=body.session_id, role="user", content=body.query))
    db.flush()

    try:
        result = answer_query(db, query=body.query, session_id=body.session_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    related_topics = [
        RelatedTopic(
            name=c.get("name", "Unknown"),
            matched_symptoms=c.get("matched_symptoms", []),
            confidence=c.get("confidence", "low"),
            reason=c.get("explanation"),
        )
        for c in result.related_conditions
    ]

    sources = [
        Source(
            id=s["id"],
            title=s.get("title", ""),
            snippet=s.get("text", "")[:300],
        )
        for s in result.sources
    ]

    db.add(Message(session_id=body.session_id, role="assistant", content=result.answer))

    db.add(
        SymptomQuery(
            session_id=body.session_id,
            raw_query=body.query,
            normalized_query=body.query.lower().strip(),
            response_summary=result.answer,
            possible_conditions=[t.model_dump() for t in related_topics],
            retrieved_docs=[s.model_dump() for s in sources],
        )
    )

    db.commit()
    logger.info("Query processed for session %s (urgency=%s)", body.session_id, result.urgency)

    return QueryResponse(
        session_id=body.session_id,
        answer=result.answer,
        urgency=result.urgency,
        follow_up_questions=result.follow_up_questions,
        related_topics=related_topics,
        sources=sources,
    )
