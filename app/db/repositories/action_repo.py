import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.action import Action, ActionStatus
from app.core.logger import get_logger

logger = get_logger(__name__)


# Terminal states — no further transitions allowed from these.
TERMINAL_STATUSES = {
    ActionStatus.APPROVED.value,
    ActionStatus.REJECTED.value,
    ActionStatus.COMPLETED.value,
    ActionStatus.FAILED.value,
    "cancelled",
}


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

    async def complete(self, action_id: uuid.UUID, result_payload: dict | None = None) -> Action | None:
        action = await self.get_by_id(action_id)
        if not action:
            return None
        action.status = ActionStatus.COMPLETED.value
        if result_payload:
            action.payload = {**(action.payload or {}), "execution_result": result_payload}
        await self._db.flush()
        logger.info("action.completed", action_id=str(action_id))
        return action

    # ── Cancel (employee-side) ────────────────────────────────────────────────
    async def cancel(
        self,
        *,
        action_id: uuid.UUID,
        canceller_id: uuid.UUID,
        reason: str | None = None,
    ) -> Action | None:
        """Employee cancels their own pending request.

        Returns None if the action does not exist OR is already in a
        terminal state (cannot cancel approved/rejected/completed).
        """
        action = await self.get_by_id(action_id)
        if not action:
            return None
        if action.user_id != canceller_id:
            # Caller must verify ownership before invoking — defensive only
            return None
        if action.status in TERMINAL_STATUSES:
            return None
        action.status = "cancelled"
        action.notes = reason
        action.approved_at = datetime.now(timezone.utc)
        await self._db.flush()
        logger.info("action.cancelled", action_id=str(action_id), by=str(canceller_id))
        return action

    # ── Listing for approvers & users ─────────────────────────────────────────
    async def list_pending_for_approvers(
        self,
        *,
        company_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
        department: str | None = None,
    ) -> list[Action]:
        stmt = (
            select(Action)
            .where(
                Action.company_id == company_id,
                Action.status == ActionStatus.PENDING.value,
                Action.requires_approval == True,  # noqa: E712
            )
            .order_by(Action.created_at.desc())
            .limit(min(limit, 200))
            .offset(offset)
        )
        if department:
            stmt = stmt.where(Action.department == department)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def list_for_user_paginated(
        self,
        *,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
    ) -> tuple[list[Action], int]:
        base = select(Action).where(Action.user_id == user_id)
        if status:
            base = base.where(Action.status == status)
        stmt = base.order_by(Action.created_at.desc()).limit(min(limit, 200)).offset(offset)
        rows = (await self._db.execute(stmt)).scalars().all()

        count_stmt = select(func.count()).where(Action.user_id == user_id)
        if status:
            count_stmt = count_stmt.where(Action.status == status)
        total = (await self._db.execute(count_stmt)).scalar() or 0
        return list(rows), int(total)

    async def count_pending_for_company(self, company_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            Action.company_id == company_id,
            Action.status == ActionStatus.PENDING.value,
            Action.requires_approval == True,  # noqa: E712
        )
        return (await self._db.execute(stmt)).scalar() or 0
