import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.logger import get_logger, set_request_id, clear_request_id

logger = get_logger(__name__)


async def request_id_middleware(request: Request, call_next):
    """Attach a unique request ID to every request for log correlation."""
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(rid)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        clear_request_id()


async def error_handling_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception("unhandled_exception", path=request.url.path, method=request.method)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )
