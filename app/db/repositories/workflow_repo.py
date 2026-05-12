import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workflow_log import WorkflowLog
from app.core.logger import get_logger

logger = get_logger(__name__)


class WorkflowLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        *,
        company_id: uuid.UUID,
        session_id: str,
        department: str,
        agent: str,
        user_input: str,
        final_answer: str,
        confidence: int,
        evaluation_score: float | None,
        steps: list,
        execution_metadata: dict,
        conversation_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
    ) -> WorkflowLog:
        log = WorkflowLog(
            company_id=company_id,
            conversation_id=conversation_id,
            user_id=user_id,
            session_id=session_id,
            department=department,
            agent=agent,
            user_input=user_input,
            final_answer=final_answer,
            confidence=confidence,
            evaluation_score=evaluation_score,
            steps=steps,
            execution_metadata=execution_metadata,
        )
        self._db.add(log)
        await self._db.flush()
        logger.info(
            "workflow_repo.created",
            log_id=str(log.id),
            agent=agent,
            confidence=confidence,
        )
        return log

    async def get_recent(
        self,
        company_id: uuid.UUID,
        limit: int = 20,
    ) -> list[WorkflowLog]:
        stmt = (
            select(WorkflowLog)
            .where(WorkflowLog.company_id == company_id)
            .order_by(WorkflowLog.created_at.desc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())
