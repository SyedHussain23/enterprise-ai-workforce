"""
Request middleware for the Enterprise AI Workforce API.

Responsibilities:
  1. Request-ID propagation: attach a UUID to every request for log correlation.
     Respects X-Request-ID if the caller provides one (useful for end-to-end tracing).

  2. Error handling: catch unhandled exceptions and return a clean 500 JSON response
     instead of a naked Python traceback.

  3. Security headers: attach production-grade HTTP security headers to every
     response. These complement (not duplicate) the headers set in vercel.json;
     they protect direct API consumers and any non-Vercel deployments.
"""
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.logger import get_logger, set_request_id, clear_request_id

logger = get_logger(__name__)

# ── Security header values ─────────────────────────────────────────────────────
# CSP: allow scripts/styles only from self. Inline eval is blocked.
# Adjusted for API: most restrictive defaults since this is a JSON API, not HTML.
_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options":     "nosniff",
    "X-Frame-Options":            "DENY",
    "X-XSS-Protection":           "0",           # Disabled in favour of CSP (modern standard)
    "Referrer-Policy":            "strict-origin-when-cross-origin",
    "Permissions-Policy":         "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy":    "default-src 'none'; frame-ancestors 'none'",
    # HSTS: 1 year, include sub-domains.  Only send on HTTPS (Railway/Vercel always HTTPS).
    "Strict-Transport-Security":  "max-age=31536000; includeSubDomains; preload",
    "Cache-Control":              "no-store",      # API responses must not be cached
    "Pragma":                     "no-cache",
}


async def request_id_middleware(request: Request, call_next):
    """Attach a unique request ID to every request for log correlation."""
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(rid)
    request.state.request_id = rid
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        clear_request_id()


async def security_headers_middleware(request: Request, call_next):
    """Attach security headers to every response."""
    response = await call_next(request)
    for key, value in _SECURITY_HEADERS.items():
        # Don't override if the handler already set a more specific policy
        if key not in response.headers:
            response.headers[key] = value
    return response


async def error_handling_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception("unhandled_exception", path=request.url.path, method=request.method)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )
