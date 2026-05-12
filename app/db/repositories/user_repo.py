import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.core.logger import get_logger

logger = get_logger(__name__)


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_username(self, username: str, company_id: uuid.UUID | None = None) -> User | None:
        stmt = select(User).where(
            User.username == username,
            User.is_active == True,
            User.deleted_at == None,
        )
        if company_id:
            stmt = stmt.where(User.company_id == company_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id, User.deleted_at == None)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        company_id: uuid.UUID,
        email: str,
        username: str,
        hashed_password: str,
        role: str,
        department: str | None = None,
    ) -> User:
        user = User(
            company_id=company_id,
            email=email,
            username=username,
            hashed_password=hashed_password,
            role=role,
            department=department,
        )
        self._db.add(user)
        await self._db.flush()  # gets the generated id without committing
        logger.info("user_repo.created", user_id=str(user.id), username=username)
        return user
