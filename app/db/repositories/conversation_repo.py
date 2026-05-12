import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation, Message
from app.core.logger import get_logger

logger = get_logger(__name__)


class ConversationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_or_create_by_session(
        self,
        *,
        session_id: str,
        company_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        department: str | None = None,
    ) -> Conversation:
        stmt = select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.company_id == company_id,
        )
        result = await self._db.execute(stmt)
        convo = result.scalar_one_or_none()

        if convo is None:
            convo = Conversation(
                company_id=company_id,
                user_id=user_id,
                session_id=session_id,
                department=department,
                status="active",
            )
            self._db.add(convo)
            await self._db.flush()
            logger.info("conversation_repo.created", session_id=session_id)

        return convo

    async def add_message(
        self,
        *,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        agent: str | None = None,
        confidence: int | None = None,
        source: str | None = None,
        response_time: float | None = None,
        evaluation_score: float | None = None,
        extra: dict | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            agent=agent,
            confidence=confidence,
            source=source,
            response_time=response_time,
            evaluation_score=evaluation_score,
            extra=extra,
        )
        self._db.add(msg)
        await self._db.flush()
        return msg
