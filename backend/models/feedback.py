"""
Table: feedback
      Column      |           Type           | Collation | Nullable |      Default      
------------------+--------------------------+-----------+----------+-------------------
 id               | uuid                     |           | not null | gen_random_uuid()
 symptom_query_id | uuid                     |           | not null | 
 helpful          | boolean                  |           | not null | 
 comment          | text                     |           |          | 
 created_at       | timestamp with time zone |           | not null | now()
Indexes:
    "feedback_pkey" PRIMARY KEY, btree (id)
    "idx_feedback_symptom_query_id" btree (symptom_query_id)
Foreign-key constraints:
    "fk_feedback_symptom_query" FOREIGN KEY (symptom_query_id) REFERENCES symptom_queries(id) ON DELETE CASCADE
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from backend.core.database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    symptom_query_id = Column(UUID(as_uuid=True), ForeignKey("symptom_queries.id", ondelete="CASCADE"), nullable=False, index=True)
    helpful = Column(Boolean, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
