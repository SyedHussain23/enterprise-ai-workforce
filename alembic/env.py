import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# ── Project imports ───────────────────────────────────────────────────────────
# Import settings before models so DATABASE_URL is available.
from app.core.config import settings

# Import all models via the models __init__.py so that Base.metadata contains
# every table. If a model is not imported here, Alembic will not detect it
# in autogenerate and will silently miss its table.
from app.db.base import Base
import app.db.models  # noqa: F401 — side-effect import registers all models

# ── Alembic config ────────────────────────────────────────────────────────────
config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ── Offline migration (generates SQL without a live DB connection) ─────────────
def run_migrations_offline() -> None:
    """
    Emit raw SQL to stdout — useful for DBAs who apply migrations manually
    or for generating migration scripts for review before applying.
    Run with: alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online migration (connects to DB and applies changes) ─────────────────────
def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Alembic CLI is synchronous but our engine is async.
    create_async_engine + run_sync bridges the gap — Alembic gets a sync
    connection handle, while the underlying driver stays asyncpg.
    NullPool is used here because migration runs are short-lived CLI processes;
    connection pooling is unnecessary and wastes resources.
    """
    connectable = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
