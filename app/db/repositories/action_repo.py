import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.action import Action, ActionStatus
from app.core.logger import get_logger

logger = get_logger(__name__)


class ActionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        *,
        company_id: uuid.UUID,
        action_type: str,
        department: str,
        payload: dict,
        requires_approval: bool = True,
        user_id: uuid.UUID | None = None,
        workflow_log_id: uuid.UUID | None = None,
    ) -> Action:
        action = Action(
            company_id=company_id,
            user_id=user_id,
            workflow_log_id=workflow_log_id,
            action_type=action_type,
            department=department,
            status=ActionStatus.PENDING.value,
            requires_approval=requires_approval,
            payload=payload,
        )
        self._db.add(action)
        await self._db.flush()
        logger.info("action.created", action_id=str(action.id), action_type=action_type)
        return action

    async def get_pending(self, company_id: uuid.UUID) -> list[Action]:
        stmt = (
            select(Action)
            .where(
                Action.company_id == company_id,
                Action.status == ActionStatus.PENDING.value,
            )
            .order_by(Action.created_at.desc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user(self, user_id: uuid.UUID, limit: int = 20) -> list[Action]:
        stmt = (
            select(Action)
            .where(Action.user_id == user_id)
            .order_by(Action.created_at.desc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, action_id: uuid.UUID) -> Action | None:
        stmt = select(Action).where(Action.id == action_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def approve(self, action_id: uuid.UUID, approver_id: uuid.UUID, notes: str | None = None) -> Action | None:
        action = await self.get_by_id(action_id)
        if not action:
            return None
        action.status = ActionStatus.APPROVED.value
        action.approved_by_id = approver_id
        action.approved_at = datetime.now(timezone.utc)
        action.notes = notes
        await self._db.flush()
        logger.info("action.approved", action_id=str(action_id), approver=str(approver_id))
        return action

    async def reject(self, action_id: uuid.UUID, approver_id: uuid.UUID, notes: str | None = None) -> Action | None:
        action = await self.get_by_id(action_id)
        if not action:
            return None
        action.status = ActionStatus.REJECTED.value
        action.approved_by_id = approver_id
        action.approved_at = datetime.now(timezone.utc)
        action.notes = notes
        await self._db.flush()
        logger.info("action.rejected", action_id=str(action_id))
        return action
