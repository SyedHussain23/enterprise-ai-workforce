"""
Shared FastAPI dependencies used across route modules.

Having a single canonical get_db here lets tests override it in one place
(conftest.py's app.dependency_overrides[get_db] = ...) and have the override
apply across all routes.

If each route module defines its own get_db, tests would need to patch each
module separately — brittle and error-prone.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
