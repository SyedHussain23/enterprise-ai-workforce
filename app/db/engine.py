from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ── Engine ───────────────────────────────────────────────────────────────────
# pool_pre_ping=True: sends a lightweight SELECT 1 before handing a connection
# from the pool. Prevents "connection closed" errors after DB restart or idle
# timeout — critical for long-running production services.
#
# pool_recycle: forces connections to recycle every hour, preventing stale
# connections from sitting in the pool past the server's idle-timeout limit.
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE,
)

# ── Session factory ───────────────────────────────────────────────────────────
# expire_on_commit=False: after commit(), objects remain accessible without
# triggering lazy-load queries. Critical for async — there's no implicit I/O
# allowed outside an active session.
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
