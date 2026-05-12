import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ActionType(str, PyEnum):
    # HR
    APPLY_LEAVE = "apply_leave"
    UPDATE_PROFILE = "update_profile"
    REQUEST_CERTIFICATE = "request_certificate"
    # IT
    CREATE_TICKET = "create_ticket"
    RESET_PASSWORD = "reset_password"
    REQUEST_ACCESS = "request_access"
    # Finance
    SUBMIT_EXPENSE = "submit_expense"
    REQUEST_ADVANCE = "request_advance"
    QUERY_PAYSLIP = "query_payslip"


class ActionStatus(str, PyEnum):
    PENDING = "pending"        # submitted, awaiting approval
    APPROVED = "approved"      # manager approved
    REJECTED = "rejected"      # manager rejected
    COMPLETED = "completed"    # executed and confirmed
    FAILED = "failed"          # execution attempted but errored


class Action(Base, TimestampMixin):
    """
    Represents a real-world operation triggered by an agent (Day 36).
    Carries its own approval lifecycle so managers can approve/reject
    without the AI needing to re-run the workflow.

    approved_by_id is nullable because not all actions need approval —
    the requires_approval flag controls which ones block on human sign-off.
    """
    __tablename__ = "actions"

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
    workflow_log_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_logs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ActionStatus.PENDING.value,
        index=True,
    )
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Structured payload — specific to action_type schema
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Approval metadata
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="actions")
    workflow_log: Mapped["WorkflowLog"] = relationship("WorkflowLog", back_populates="actions")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    approved_by: Mapped["User"] = relationship("User", foreign_keys=[approved_by_id])

    def __repr__(self) -> str:
        return f"<Action id={self.id} type={self.action_type} status={self.status}>"
