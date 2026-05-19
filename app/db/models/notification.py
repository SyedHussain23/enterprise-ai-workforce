"""
In-app notification model.

A Notification represents an event that requires a user's attention:
  - their request was approved/rejected
  - a request was assigned to them for approval
  - their request received a comment
  - workflow status changed

Notifications are:
  - per-user (recipient_id)
  - scoped to a company (tenant isolation)
  - linked to an originating entity (action / workflow / etc.) so the
    frontend can deep-link to the source

This is intentionally lightweight — heavy-weight delivery (email, push, SMS)
is *not* in scope here. The frontend polls /notifications and renders the
unread badge. Add a transport layer later without changing this shape.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class NotificationKind(str, PyEnum):
    """High-level category — drives icon and routing target on the client."""
    REQUEST_SUBMITTED   = "request_submitted"   # to approvers: new pending request
    REQUEST_APPROVED    = "request_approved"    # to requester: yours was approved
    REQUEST_REJECTED    = "request_rejected"    # to requester: yours was rejected
    REQUEST_COMMENTED   = "request_commented"   # comment added to a request
    REQUEST_COMPLETED   = "request_completed"   # request executed downstream
    REQUEST_ESCALATED   = "request_escalated"   # SLA breached / escalated
    SYSTEM              = "system"              # generic platform notice


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    kind:    Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title:   Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(String(800), nullable=False)

    # Deep-link target — typically an action ID, workflow log ID, etc.
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id:   Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    # Extra context — e.g. {"action_type": "apply_leave", "days": 3}
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True,
    )
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    # Relationships
    recipient: Mapped["User"] = relationship("User", foreign_keys=[recipient_id])
    actor:     Mapped["User"] = relationship("User", foreign_keys=[actor_id])

    def __repr__(self) -> str:
        return f"<Notification id={self.id} kind={self.kind} read={self.is_read}>"
