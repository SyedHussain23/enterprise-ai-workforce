import uuid
from enum import Enum as PyEnum

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class CompanyPlan(str, PyEnum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Company(Base, TimestampMixin, SoftDeleteMixin):
    """
    Tenant root.  Every other table carries a company_id FK pointing here.
    Scoping all queries by company_id is what makes the system multi-tenant.
    """
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # slug is used as the URL-safe tenant identifier: acme-corp.enterprise-ai.com
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    plan: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CompanyPlan.FREE.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships — back-populated so ORM can traverse both directions
    users: Mapped[list["User"]] = relationship("User", back_populates="company", lazy="select")
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="company", lazy="select")
    workflow_logs: Mapped[list["WorkflowLog"]] = relationship("WorkflowLog", back_populates="company", lazy="select")
    actions: Mapped[list["Action"]] = relationship("Action", back_populates="company", lazy="select")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="company", lazy="select")

    def __repr__(self) -> str:
        return f"<Company id={self.id} slug={self.slug} plan={self.plan}>"
