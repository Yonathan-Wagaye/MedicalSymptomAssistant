"""
Table: chat_sessions
   Column   |           Type           | Collation | Nullable |      Default      
------------+--------------------------+-----------+----------+-------------------
 id         | uuid                     |           | not null | gen_random_uuid()
 title      | character varying(255)   |           |          | 
 created_at | timestamp with time zone |           | not null | now()
 updated_at | timestamp with time zone |           | not null | now()
Indexes:
    "chat_sessions_pkey" PRIMARY KEY, btree (id)
Referenced by:
    TABLE "messages" CONSTRAINT "fk_messages_session" FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
    TABLE "symptom_queries" CONSTRAINT "fk_symptom_queries_session" FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
Triggers:
    trg_chat_sessions_updated_at BEFORE UPDATE ON chat_sessions FOR EACH ROW EXECUTE FUNCTION set_updated_at()
"""

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from backend.core.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
