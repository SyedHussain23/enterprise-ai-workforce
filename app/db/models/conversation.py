import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ConversationStatus(str):
    ACTIVE = "active"
    CLOSED = "closed"


class Conversation(Base, TimestampMixin):
    """
    A logical thread between a user and the AI workforce.
    One session_id maps to one Conversation — but a user can have many.
    This is the anchor for the Redis memory system built on Day 34.
    """
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # session_id comes from the frontend — indexed so we can look up by it fast
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    department: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="conversations")
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="select",
    )
    workflow_logs: Mapped[list["WorkflowLog"]] = relationship("WorkflowLog", back_populates="conversation", lazy="select")

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} session={self.session_id} dept={self.department}>"


class Message(Base, TimestampMixin):
    """
    Individual turn in a conversation (user message or assistant reply).
    Carries the full AI response metadata so the UI can re-render
    any historical message exactly as it appeared originally.
    This is the persistent layer that Redis memory (Day 34) is seeded from.
    """
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # role: "user" or "assistant" — mirrors LangChain message convention
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # AI-specific fields — null for user messages
    agent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[int | None] = mapped_column(nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    response_time: Mapped[float | None] = mapped_column(nullable=True)
    evaluation_score: Mapped[float | None] = mapped_column(nullable=True)

    # Flexible bag for extra metadata without schema changes
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message id={self.id} role={self.role} agent={self.agent}>"
