"""
Notification repository — single source for writing + reading the inbox.

Common access patterns are kept here so the API layer never builds queries
ad-hoc:
  - emit(...)       — write a notification (used by approval/lifecycle hooks)
  - list_for_user() — paginated inbox
  - unread_count()  — for the bell badge
  - mark_read()     — single
  - mark_all_read() — bulk
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.db.models.notification import Notification

logger = get_logger(__name__)


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def emit(
        self,
        *,
        company_id: uuid.UUID,
        recipient_id: uuid.UUID,
        kind: str,
        title: str,
        message: str,
        actor_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        payload: dict | None = None,
    ) -> Notification:
        notif = Notification(
            company_id=company_id,
            recipient_id=recipient_id,
            actor_id=actor_id,
            kind=kind,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
        )
        self._db.add(notif)
        await self._db.flush()
        logger.info(
            "notification.emitted",
            notification_id=str(notif.id),
            kind=kind,
            recipient=str(recipient_id),
        )
        return notif

    async def list_for_user(
        self,
        *,
        recipient_id: uuid.UUID,
        company_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(
                Notification.recipient_id == recipient_id,
                Notification.company_id == company_id,
            )
            .order_by(Notification.created_at.desc())
            .limit(min(limit, 200))
            .offset(offset)
        )
        if unread_only:
            stmt = stmt.where(Notification.is_read == False)  # noqa: E712
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def unread_count(
        self,
        *,
        recipient_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> int:
        stmt = select(func.count()).where(
            Notification.recipient_id == recipient_id,
            Notification.company_id == company_id,
            Notification.is_read == False,  # noqa: E712
        )
        return (await self._db.execute(stmt)).scalar() or 0

    async def mark_read(
        self,
        *,
        notification_id: uuid.UUID,
        recipient_id: uuid.UUID,
    ) -> Notification | None:
        # Ownership check is baked into the update — no one can mark another
        # user's notification as read.
        stmt = (
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.recipient_id == recipient_id,
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
            .returning(Notification)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_all_read(
        self,
        *,
        recipient_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.recipient_id == recipient_id,
                Notification.company_id == company_id,
                Notification.is_read == False,  # noqa: E712
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        result = await self._db.execute(stmt)
        return result.rowcount or 0
