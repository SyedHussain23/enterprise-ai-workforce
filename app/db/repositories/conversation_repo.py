import uuid

from sqlalchemy import func, select
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

    async def get_user_conversations(
        self,
        *,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        """Return conversations for a user, newest first."""
        stmt = (
            select(Conversation)
            .where(
                Conversation.company_id == company_id,
                Conversation.user_id == user_id,
            )
            .order_by(Conversation.updated_at.desc())
            .limit(min(limit, 200))
            .offset(offset)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def count_user_conversations(
        self,
        *,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> int:
        stmt = select(func.count()).where(
            Conversation.company_id == company_id,
            Conversation.user_id == user_id,
        )
        return (await self._db.execute(stmt)).scalar() or 0

    async def get_messages(
        self,
        *,
        session_id: str,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 100,
    ) -> list[Message]:
        """Return messages for a session, oldest first. Validates ownership."""
        convo_stmt = select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.company_id == company_id,
            Conversation.user_id == user_id,
        )
        convo_result = await self._db.execute(convo_stmt)
        convo = convo_result.scalar_one_or_none()
        if convo is None:
            return []

        msg_stmt = (
            select(Message)
            .where(Message.conversation_id == convo.id)
            .order_by(Message.created_at.asc())
            .limit(min(limit, 500))
        )
        result = await self._db.execute(msg_stmt)
        return list(result.scalars().all())
