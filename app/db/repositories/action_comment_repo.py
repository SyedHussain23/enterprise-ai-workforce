"""ActionComment repository — comment thread on a request."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.action_comment import ActionComment


class ActionCommentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(
        self,
        *,
        action_id: uuid.UUID,
        author_id: uuid.UUID,
        body: str,
    ) -> ActionComment:
        comment = ActionComment(action_id=action_id, author_id=author_id, body=body)
        self._db.add(comment)
        await self._db.flush()
        return comment

    async def list_for_action(
        self,
        *,
        action_id: uuid.UUID,
    ) -> list[ActionComment]:
        stmt = (
            select(ActionComment)
            .where(ActionComment.action_id == action_id)
            .order_by(ActionComment.created_at.asc())
            .options(selectinload(ActionComment.author))
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())
