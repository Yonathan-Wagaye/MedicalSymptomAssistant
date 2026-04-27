from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FeedbackCreate(BaseModel):
    symptom_query_id: UUID
    helpful: bool
    comment: str | None = None


class FeedbackResponse(BaseModel):
    id: UUID
    symptom_query_id: UUID
    helpful: bool
    comment: str | None
    created_at: datetime

    class Config:
        from_attributes = True
