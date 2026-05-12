from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields an async DB session per request.

    Usage in endpoint:
        @app.post("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...

    The session is committed and closed in the finally block regardless of
    whether the handler succeeded or raised. SQLAlchemy rolls back
    automatically on exceptions via the context manager protocol.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
