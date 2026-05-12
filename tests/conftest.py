"""
Shared pytest fixtures.

Uses a separate test database so tests never touch production data.
Each test gets a fresh transaction that is rolled back after the test —
no cleanup code needed in individual tests.
"""
import asyncio
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.server import app, get_db
from app.auth.auth import hash_password
from app.core.config import settings
from app.db.base import Base
from app.db.models.company import Company, CompanyPlan
from app.db.models.user import User, UserRole

# ── Test DB (same server, separate database) ──────────────────────────────────
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    "/enterprise_ai", "/enterprise_ai_test"
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def create_test_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(create_test_tables):
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def seeded_db(db_session: AsyncSession):
    """Insert a company + admin user, return both objects."""
    company = Company(
        name="Test Co",
        slug="test",
        plan=CompanyPlan.PRO.value,
        is_active=True,
    )
    db_session.add(company)
    await db_session.flush()

    admin = User(
        company_id=company.id,
        email="admin@test.com",
        username="testadmin",
        hashed_password=hash_password("testpass"),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()

    return {"company": company, "admin": admin}


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """AsyncClient with DB dependency overridden to use the test session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
