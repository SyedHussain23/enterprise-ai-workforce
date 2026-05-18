"""
JWT Token Blocklist — server-side session invalidation.

PROBLEM:
  JWTs are stateless by design. Once issued, they remain valid until expiry even if:
  - The user explicitly logs out
  - The user changes their password
  - An admin deactivates the account

  Without a blocklist, a stolen token (via XSS, network interception, or insider
  threat) can be used for the full token lifetime — up to 8 hours for our config.

SOLUTION:
  A Redis SET keyed by `jti` (JWT ID claim) with TTL equal to the token's remaining
  lifetime. Every protected endpoint checks this set. Blocked JTIs return 401.

  Redis makes this O(1) per request with negligible latency overhead (~0.2ms).
  The blocklist entries self-expire via Redis TTL — no cleanup job needed.

USAGE:
  # On logout or password change:
  from app.core.token_blocklist import block_token
  await block_token(jti, remaining_seconds)

  # In auth dependency (called automatically):
  from app.core.token_blocklist import is_token_blocked
  if await is_token_blocked(jti):
      raise HTTPException(401, "Token has been revoked")

DESIGN NOTES:
  - `jti` is a UUID4 added to every JWT at creation time.
  - The blocklist only stores JTIs, never the token itself — no PII in Redis.
  - If Redis is unavailable, the blocklist check fails-open (logs a warning).
    This is a deliberate trade-off: availability > security for a single-node
    Redis. For true enterprise deployment, use Redis Sentinel or Cluster.
"""
from __future__ import annotations

import redis
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_KEY_PREFIX = "blocked_jti:"
_client: redis.Redis | None = None


def _get_client() -> redis.Redis | None:
    global _client
    if _client is None:
        try:
            _client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            _client.ping()
        except Exception as exc:
            logger.warning("token_blocklist.redis_unavailable", error=str(exc))
            _client = None
    return _client


def block_token(jti: str, ttl_seconds: int) -> None:
    """
    Add a token JTI to the blocklist.

    Args:
        jti:         The JWT ID claim from the token payload.
        ttl_seconds: How long to keep the block (should equal token remaining lifetime).

    Fails silently if Redis is unavailable (logs warning). The token will
    expire naturally when its `exp` claim passes.
    """
    if ttl_seconds <= 0:
        # Token is already expired — no need to block it
        return
    r = _get_client()
    if r is None:
        logger.warning("token_blocklist.block_skipped_no_redis", jti=jti[:8])
        return
    try:
        r.setex(f"{_KEY_PREFIX}{jti}", ttl_seconds, "1")
        logger.info("token_blocklist.blocked", jti=jti[:8], ttl_seconds=ttl_seconds)
    except Exception as exc:
        logger.warning("token_blocklist.block_failed", jti=jti[:8], error=str(exc))


def is_token_blocked(jti: str) -> bool:
    """
    Return True if this token has been explicitly invalidated.

    Fails open (returns False) if Redis is unavailable — we prefer availability
    over blocking all requests when the token store is down.
    """
    r = _get_client()
    if r is None:
        logger.warning("token_blocklist.check_skipped_no_redis", jti=jti[:8])
        return False
    try:
        return bool(r.exists(f"{_KEY_PREFIX}{jti}"))
    except Exception as exc:
        logger.warning("token_blocklist.check_failed", jti=jti[:8], error=str(exc))
        return False  # fail-open
