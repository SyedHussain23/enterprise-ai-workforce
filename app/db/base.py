import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """
    Project-wide declarative base.
    All models inherit from this — gives Alembic a single metadata object
    to diff against and generate migrations from.
    """
    pass


class TimestampMixin:
    """
    Adds created_at / updated_at to any model.
    server_default keeps DB and app clocks consistent.
    onupdate fires automatically on every UPDATE — no manual touch needed.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """
    Soft delete: set deleted_at instead of running DELETE.
    Enterprise systems almost never hard-delete rows — audit trails,
    foreign key integrity, and GDPR right-to-erasure all require this.
    Filter with `.where(Model.deleted_at.is_(None))` in every query.
    """
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
