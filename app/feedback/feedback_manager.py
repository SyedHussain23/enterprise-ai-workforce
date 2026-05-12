"""
Feedback repository — replaces the old JSON-file stub.

Writes thumbs-up/down (1–5 rating) against a WorkflowLog row so
admins can track response quality over time and feed data into
offline RAGAS evaluation runs (Day 39).
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.feedback import Feedback
from app.core.logger import get_logger

logger = get_logger(__name__)


class FeedbackRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        *,
        company_id: uuid.UUID,
        workflow_log_id: uuid.UUID,
        rating: int,
        user_id: uuid.UUID | None = None,
        comment: str | None = None,
    ) -> Feedback:
        fb = Feedback(
            company_id=company_id,
            workflow_log_id=workflow_log_id,
            user_id=user_id,
            rating=rating,
            comment=comment,
        )
        self._db.add(fb)
        await self._db.flush()
        logger.info("feedback.created", feedback_id=str(fb.id), rating=rating)
        return fb

    async def get_recent(
        self,
        company_id: uuid.UUID,
        limit: int = 50,
    ) -> list[Feedback]:
        stmt = (
            select(Feedback)
            .where(Feedback.company_id == company_id)
            .order_by(Feedback.created_at.desc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())
