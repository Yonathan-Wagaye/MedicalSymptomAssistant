from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: str | None = Field(None, max_length=255)


class SessionResponse(BaseModel):
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SessionDetail(SessionResponse):
    """Session with its full message history."""
    messages: list["MessageResponse"] = []


from backend.schemas.messages import MessageResponse  # noqa: E402

SessionDetail.model_rebuild()
