"""
Table: messages
   Column   |           Type           | Collation | Nullable |      Default      
------------+--------------------------+-----------+----------+-------------------
 id         | uuid                     |           | not null | gen_random_uuid()
 session_id | uuid                     |           | not null | 
 role       | character varying(20)    |           | not null | 
 content    | text                     |           | not null | 
 created_at | timestamp with time zone |           | not null | now()
Indexes:
    "messages_pkey" PRIMARY KEY, btree (id)
    "idx_messages_created_at" btree (created_at)
    "idx_messages_session_id" btree (session_id)
Check constraints:
    "messages_role_check" CHECK (role::text = ANY (ARRAY['user'::character varying, 'assistant'::character varying]::text[]))
Foreign-key constraints:
    "fk_messages_session" FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
"""

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from backend.core.database import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="messages_role_check"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
