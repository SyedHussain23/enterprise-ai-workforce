"""
Health check endpoints.

GET /health      — shallow, used by Railway healthcheck probe (fast)
GET /health/deep — deep connectivity check for monitoring dashboards
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.api.deps import get_db
from app.core.config import settings
from app.core.logger import get_logger
from app.rag.client import get_chroma_client

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health")
async def health():
    """Shallow health check — used by Railway healthcheck probe."""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@router.get("/health/deep")
async def health_deep(db: AsyncSession = Depends(get_db)):
    """
    Deep health check — verifies connectivity to all downstream dependencies.
    Returns degraded (not 500) so Railway doesn't restart on partial failure.
    """
    import redis as _redis_lib

    checks: dict[str, str] = {}

    # PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {str(exc)[:80]}"

    # Redis
    try:
        r = _redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {str(exc)[:80]}"

    # ChromaDB — verify via document count
    try:
        chroma = get_chroma_client()
        count = chroma._collection.count()
        checks["chromadb"] = f"ok ({count} documents)"
    except Exception as exc:
        checks["chromadb"] = f"error: {str(exc)[:80]}"

    # OpenAI key validity (cheap list-models call)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=3.0)
        client.models.list()
        checks["openai"] = "ok"
    except Exception as exc:
        checks["openai"] = f"error: {str(exc)[:80]}"

    # Circuit breaker state
    from app.core.openai_client import get_circuit_state
    cb = get_circuit_state()
    checks["circuit_breaker"] = cb["state"]

    overall = "ok" if all(
        v.startswith("ok") or v == "closed"
        for v in checks.values()
    ) else "degraded"

    return {
        "status":          overall,
        "app":             settings.APP_NAME,
        "version":         settings.APP_VERSION,
        "checks":          checks,
        "circuit_breaker": cb,
    }
