"""
Table: symptom_queries
       Column        |           Type           | Collation | Nullable |      Default      
---------------------+--------------------------+-----------+----------+-------------------
 id                  | uuid                     |           | not null | gen_random_uuid()
 session_id          | uuid                     |           | not null | 
 raw_query           | text                     |           | not null | 
 normalized_query    | text                     |           |          | 
 response_summary    | text                     |           |          | 
 possible_conditions | jsonb                    |           |          | 
 retrieved_docs      | jsonb                    |           |          | 
 created_at          | timestamp with time zone |           | not null | now()
Indexes:
    "symptom_queries_pkey" PRIMARY KEY, btree (id)
    "idx_symptom_queries_created_at" btree (created_at)
    "idx_symptom_queries_session_id" btree (session_id)
Foreign-key constraints:
    "fk_symptom_queries_session" FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
Referenced by:
    TABLE "feedback" CONSTRAINT "fk_feedback_symptom_query" FOREIGN KEY (symptom_query_id) REFERENCES symptom_queries(id) ON DELETE CASCADE
"""

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from backend.core.database import Base


class SymptomQuery(Base):
    __tablename__ = "symptom_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_query = Column(Text, nullable=False)
    normalized_query = Column(Text, nullable=True)
    response_summary = Column(Text, nullable=True)
    possible_conditions = Column(JSONB, nullable=True)
    retrieved_docs = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
