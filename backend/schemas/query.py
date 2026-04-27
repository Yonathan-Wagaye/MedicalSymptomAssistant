from uuid import UUID

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    session_id: UUID
    query: str = Field(..., min_length=1)


class RelatedTopic(BaseModel):
    name: str
    matched_symptoms: list[str] = []
    confidence: str = "low"
    reason: str | None = None


class Source(BaseModel):
    id: str
    title: str
    snippet: str


class QueryResponse(BaseModel):
    session_id: UUID
    answer: str
    urgency: str = "normal"
    follow_up_questions: list[str] = []
    related_topics: list[RelatedTopic] = []
    sources: list[Source] = []
    disclaimer: str = (
        "This is informational only and not a diagnosis. "
        "Seek professional care for urgent or worsening symptoms."
    )
