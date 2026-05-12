import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class WorkflowLog(Base, TimestampMixin):
    """
    Immutable audit record of every agent execution.
    Replaces the flat JSON file in logs/workflow_logs.json.

    Design intent:
    - One row per /ask invocation
    - steps (JSONB) stores the ordered list of workflow steps exactly
      as the UI renders them — no normalization needed
    - execution_metadata (JSONB) captures response_time, rag_used,
      keyword_match — any signal that may drive future analytics
    - Never updated after insert; queries always read forward
    """
    __tablename__ = "workflow_logs"

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
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Agent routing
    department: Mapped[str] = mapped_column(String(50), nullable=False)
    agent: Mapped[str] = mapped_column(String(50), nullable=False)

    # Payload
    user_input: Mapped[str] = mapped_column(Text, nullable=False)
    final_answer: Mapped[str] = mapped_column(Text, nullable=False)

    # Quality signals — indexed so analytics queries can filter/sort
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evaluation_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Flexible JSONB columns
    steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    execution_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="workflow_logs")
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="workflow_logs")
    user: Mapped["User"] = relationship("User", back_populates="workflow_logs")
    actions: Mapped[list["Action"]] = relationship("Action", back_populates="workflow_log", lazy="select")
    feedback: Mapped[list["Feedback"]] = relationship("Feedback", back_populates="workflow_log", lazy="select")

    def __repr__(self) -> str:
        return f"<WorkflowLog id={self.id} agent={self.agent} confidence={self.confidence}>"
