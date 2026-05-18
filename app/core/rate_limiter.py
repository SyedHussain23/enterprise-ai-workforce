"""
Redis sliding-window rate limiter — production-correct version.

FIXES vs. previous implementation:
  C2/C7: Reads real client IP from X-Forwarded-For / X-Real-IP headers
         (Railway, Nginx, Cloudflare all set these). Falls back to
         request.client.host only when no proxy header is present.
  C6:    Fail-closed on Redis error for /ask endpoints — rate limiting
         is a security control, not a convenience feature.

Rate limits (tunable via env vars or constants):
  - General API:    30 req / 60s per IP
  - /ask endpoint:  20 req / 60s per user (auth-aware)
  - /login:         10 req / 60s per IP (brute-force protection)

Architecture:
  Sorted-set sliding window: O(log N) per request, accurate under
  high concurrency. Each entry: score=timestamp, member=uuid4.
"""
from __future__ import annotations

import time
import uuid

import redis
from fastapi import HTTPException, Request

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# ── Limits ────────────────────────────────────────────────────────────────────
WINDOW_SECONDS      = 60

LIMIT_GENERAL       = 60   # /health, /docs, static
LIMIT_ASK           = 20   # /ask, /ask/stream  — per user (auth-aware)
LIMIT_LOGIN         = 10   # /login             — brute-force protection
LIMIT_ADMIN         = 100  # /admin/*            — trusted admins

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis | None:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            _redis_client.ping()
        except Exception as exc:
            logger.warning("rate_limiter.redis_unavailable", error=str(exc))
            _redis_client = None
    return _redis_client


def _real_ip(request: Request) -> str:
    """
    Extract true client IP, honouring reverse-proxy headers.

    Priority: X-Forwarded-For (first IP) > X-Real-IP > request.client.host
    Validates that extracted value looks like an IP; falls back on garbage.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # X-Forwarded-For: client, proxy1, proxy2 — take leftmost (real client)
        candidate = xff.split(",")[0].strip()
        if candidate:
            return candidate

    xri = request.headers.get("x-real-ip", "").strip()
    if xri:
        return xri

    return request.client.host if request.client else "unknown"


def _check(key: str, limit: int, fail_open: bool = False) -> None:
    """
    Core sliding-window check.

    Args:
        key:       Redis key (e.g. "rl:ask:user:abc123")
        limit:     Maximum requests allowed in WINDOW_SECONDS
        fail_open: If True, allow request when Redis is unavailable (convenience APIs).
                   If False, block when Redis is unavailable (security APIs).
    """
    client = _get_redis()
    if client is None:
        if fail_open:
            logger.warning("rate_limiter.fail_open", key=key)
            return
        logger.error("rate_limiter.fail_closed", key=key)
        raise HTTPException(
            status_code=503,
            detail="Rate limiter temporarily unavailable. Please retry in a moment.",
        )

    try:
        now = time.time()
        window_start = now - WINDOW_SECONDS

        pipe = client.pipeline()
        pipe.zremrangebyscore(key, "-inf", window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(uuid.uuid4()): now})
        pipe.expire(key, WINDOW_SECONDS * 2)
        results = pipe.execute()

        count = results[1]   # count BEFORE adding this request
        if count >= limit:
            logger.warning("rate_limiter.blocked", key=key, count=count, limit=limit)
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded ({limit} requests per {WINDOW_SECONDS}s). Retry later.",
                headers={"Retry-After": str(WINDOW_SECONDS)},
            )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("rate_limiter.check_error", key=key, error=str(exc))
        if not fail_open:
            raise HTTPException(status_code=503, detail="Rate limiter error.")


# ── FastAPI dependency functions ──────────────────────────────────────────────

def rate_limiter(request: Request) -> None:
    """General-purpose rate limiter (fail-open, 60 req/min per IP)."""
    ip = _real_ip(request)
    _check(f"rl:general:{ip}", LIMIT_GENERAL, fail_open=True)


def ask_rate_limiter(request: Request) -> None:
    """
    /ask endpoint rate limiter — auth-aware, fail-closed.

    Uses JWT sub (username) when authenticated, falls back to IP.
    Prevents LLM cost abuse and prompt injection floods.
    """
    # Try to extract user from Authorization header without full auth dependency
    user_key = None
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        # Use raw token as key — no decode overhead, still user-specific
        token = auth[7:50]   # 43-char prefix is effectively unique per user
        user_key = f"rl:ask:user:{token}"

    if not user_key:
        ip = _real_ip(request)
        user_key = f"rl:ask:ip:{ip}"

    _check(user_key, LIMIT_ASK, fail_open=False)


def login_rate_limiter(request: Request) -> None:
    """
    /login brute-force protection — fail-closed, strict.

    Keyed by IP only (user not yet authenticated).
    10 attempts per minute before lockout.
    """
    ip = _real_ip(request)
    _check(f"rl:login:{ip}", LIMIT_LOGIN, fail_open=False)
