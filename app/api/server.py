"""
FastAPI application entry point.

This file is intentionally thin — it owns only:
  1. App instantiation + lifespan (startup/shutdown hooks)
  2. Middleware registration (CORS, security headers, rate limiting, request-ID)
  3. Router inclusion

All route handlers live in app/api/routes/*.
All business logic lives in app/services/* (to be migrated incrementally).

Previous state: 1379-line monolith (routes + business logic + middleware mixed together).
Current state: ~120 lines — app setup only.
"""
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_db  # re-exported for test conftest.py backward compat  # noqa: F401
from app.core.config import settings
from app.core.logger import clear_request_id, get_logger, set_request_id
from app.core.middleware import error_handling_middleware, security_headers_middleware
from app.rag.client import get_chroma_client
from app.workflows.workflow_graph import build_workflow

logger = get_logger(__name__)

# ── LangSmith tracing ─────────────────────────────────────────────────────────
if settings.LANGCHAIN_TRACING_V2 and settings.LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"]     = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"]     = settings.LANGCHAIN_PROJECT
    logger.info("langsmith.enabled", project=settings.LANGCHAIN_PROJECT)


# ── Startup / shutdown ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup.begin", app=settings.APP_NAME)
    try:
        get_chroma_client()
        logger.info("startup.chroma_ready")
    except Exception as exc:
        logger.error("startup.chroma_failed", error=str(exc))
    app.state.workflow = build_workflow()
    logger.info("startup.workflow_compiled")
    yield
    logger.info("shutdown.begin")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)


# ── CORS ──────────────────────────────────────────────────────────────────────
# DEBUG: allow all (dev convenience — never enabled in production)
# PRODUCTION: explicit whitelist from ALLOWED_ORIGINS env var
#
# Railway setup: Settings → Variables → ALLOWED_ORIGINS=https://your-app.vercel.app
_dev_origins   = ["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"]
_extra_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]

if settings.DEBUG:
    _cors_origins = ["*"]
else:
    _cors_origins = _extra_origins + _dev_origins
    if not _extra_origins:
        logger.warning(
            "cors.no_allowed_origins",
            detail=(
                "ALLOWED_ORIGINS is not set. "
                "Production frontend will be blocked by CORS. "
                "Set ALLOWED_ORIGINS=https://your-vercel-app.vercel.app in Railway."
            ),
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(error_handling_middleware)
app.middleware("http")(security_headers_middleware)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(rid)
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    clear_request_id()
    return response


# ── Routers ───────────────────────────────────────────────────────────────────
from app.api.routes.health        import router as health_router         # noqa: E402
from app.api.routes.auth          import router as auth_router           # noqa: E402
from app.api.routes.ai            import router as ai_router             # noqa: E402
from app.api.routes.actions       import router as actions_router        # noqa: E402
from app.api.routes.admin         import router as admin_router          # noqa: E402
from app.api.routes.conversations import router as conversations_router  # noqa: E402
from app.api.routes.requests      import router as requests_router       # noqa: E402
from app.api.routes.notifications import router as notifications_router  # noqa: E402

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(actions_router)
app.include_router(admin_router)
app.include_router(conversations_router)
app.include_router(requests_router)
app.include_router(notifications_router)
