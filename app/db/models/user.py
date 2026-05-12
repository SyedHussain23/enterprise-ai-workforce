import uuid
from enum import Enum as PyEnum

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class UserRole(str, PyEnum):
    ADMIN = "admin"        # full platform access
    MANAGER = "manager"    # can approve actions, view team analytics
    EMPLOYEE = "employee"  # standard query + self-service workflows


class User(Base, TimestampMixin, SoftDeleteMixin):
    """
    Replaces the in-memory USERS_DB dict.
    Scoped to a company — same email can exist across two tenants.
    Passwords are stored hashed (bcrypt on Day 33 integration).
    """
    __tablename__ = "users"

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
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.EMPLOYEE.value,
    )
    # department allows routing — HR users only need HR answers surfaced first
    department: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="users")
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="user", lazy="select")
    workflow_logs: Mapped[list["WorkflowLog"]] = relationship("WorkflowLog", back_populates="user", lazy="select")
    feedback: Mapped[list["Feedback"]] = relationship("Feedback", back_populates="user", lazy="select")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user", lazy="select")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
