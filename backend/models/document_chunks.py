from sqlalchemy import Column, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from pgvector.sqlalchemy import Vector

from backend.core.database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    source_id = Column(Text, nullable=False, index=True)
    title = Column(Text, nullable=False)
    section = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
