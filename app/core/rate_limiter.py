"""
Redis sliding-window rate limiter.

The previous implementation used a module-level dict `request_log = {}`.
Problems:
  1. Reset on every process restart — ineffective as a real limiter
  2. Not shared across Gunicorn workers — each worker has its own counter
  3. Memory leak — IPs accumulate without cleanup

This implementation uses Redis sorted sets:
  - Key:   `ratelimit:{ip}`
  - Value: sorted set of timestamps (score = timestamp, member = uuid)
  - TTL:   WINDOW_SECONDS on the key — auto-cleaned by Redis

Sliding window is more accurate than fixed-window (no boundary burst).
Falls back silently if Redis is unavailable — prefer availability over strict enforcement.
"""
import time
import uuid

import redis
from fastapi import HTTPException, Request

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

MAX_REQUESTS = 30          # per window per IP
WINDOW_SECONDS = 60        # rolling window duration

_redis: redis.Redis | None = None


def _get_redis() -> redis.Redis | None:
    global _redis
    if _redis is None:
        try:
            _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            _redis.ping()
        except Exception as exc:
            logger.warning("rate_limiter.redis_unavailable", error=str(exc))
            _redis = None
    return _redis


def rate_limiter(request: Request) -> None:
    """FastAPI dependency — raises 429 if client exceeds rate limit."""
    client = _get_redis()
    ip = request.client.host if request.client else "unknown"

    if client is None:
        # Redis unavailable — skip enforcement rather than blocking all traffic
        return

    try:
        key = f"ratelimit:{ip}"
        now = time.time()
        window_start = now - WINDOW_SECONDS

        pipe = client.pipeline()
        # Remove timestamps outside the window
        pipe.zremrangebyscore(key, "-inf", window_start)
        # Count remaining
        pipe.zcard(key)
        # Add this request
        pipe.zadd(key, {str(uuid.uuid4()): now})
        # Ensure TTL (cleans up keys for inactive IPs)
        pipe.expire(key, WINDOW_SECONDS * 2)
        results = pipe.execute()

        request_count = results[1]  # zcard result before this request
        if request_count >= MAX_REQUESTS:
            logger.warning("rate_limiter.blocked", ip=ip, count=request_count)
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {MAX_REQUESTS} requests per {WINDOW_SECONDS}s.",
            )

    except HTTPException:
        raise
    except Exception as exc:
        # Redis error during check — fail open
        logger.error("rate_limiter.error", ip=ip, error=str(exc))
