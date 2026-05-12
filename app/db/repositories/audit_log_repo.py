import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog
from app.core.logger import get_logger

logger = get_logger(__name__)


class AuditLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def log(
        self,
        event_type: str,
        *,
        company_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        payload: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            company_id=company_id,
            user_id=user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=user_agent,
            payload=payload,
        )
        self._db.add(entry)
        await self._db.flush()
        logger.info("audit.logged", event_type=event_type, user_id=str(user_id) if user_id else None)
        return entry
