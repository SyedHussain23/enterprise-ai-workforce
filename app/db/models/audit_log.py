import uuid
from enum import Enum as PyEnum

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class AuditEventType(str, PyEnum):
    # Auth
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    TOKEN_REFRESHED = "token_refreshed"
    # Query
    QUERY_SUBMITTED = "query_submitted"
    QUERY_BLOCKED = "query_blocked"          # guardrail triggered
    # Actions
    ACTION_CREATED = "action_created"
    ACTION_APPROVED = "action_approved"
    ACTION_REJECTED = "action_rejected"
    # Admin
    USER_CREATED = "user_created"
    USER_DEACTIVATED = "user_deactivated"
    DOCUMENT_UPLOADED = "document_uploaded"  # KB management Day 44+


class AuditLog(Base, TimestampMixin):
    """
    Append-only compliance log. Never updated, never soft-deleted.
    Every sensitive event in the system writes a row here.

    entity_type + entity_id let you reconstruct "what happened to this
    conversation/action/user" across time without joining to the main tables.

    payload (JSONB) holds event-specific detail (e.g., old vs new value
    for a field change, the blocked query text, the approval decision reason).
    Keep PII out of payload or ensure GDPR-compliant retention policies.
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    # Network context — useful for security investigations
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)   # supports IPv6
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Event detail
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="audit_logs")
    user: Mapped["User"] = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} event={self.event_type} user={self.user_id}>"
