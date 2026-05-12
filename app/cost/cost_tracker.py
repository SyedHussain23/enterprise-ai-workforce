"""
Token cost tracker using Redis.

Stores daily and lifetime token usage per company in Redis hashes.
Each LLM call increments atomic counters — no file I/O, no locks.

Key schema:
  cost:daily:{company_id}:{YYYY-MM-DD}  — hash, TTL 30 days
  cost:lifetime:{company_id}            — hash, no TTL

GPT-4o pricing (as of 2025):
  Input:  $0.005 / 1K tokens
  Output: $0.015 / 1K tokens
"""
from datetime import date

import redis

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

INPUT_COST_PER_1K  = 0.005
OUTPUT_COST_PER_1K = 0.015
DAILY_TTL = 60 * 60 * 24 * 30   # 30 days

_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def track_cost(
    prompt_tokens: int,
    completion_tokens: int,
    company_id: str = "global",
) -> None:
    """Atomically increment token counters and estimated cost in Redis."""
    try:
        r = _get_client()
        today = date.today().isoformat()
        daily_key    = f"cost:daily:{company_id}:{today}"
        lifetime_key = f"cost:lifetime:{company_id}"

        cost = (prompt_tokens / 1000 * INPUT_COST_PER_1K) + \
               (completion_tokens / 1000 * OUTPUT_COST_PER_1K)
        total_tokens = prompt_tokens + completion_tokens

        pipe = r.pipeline()
        for key in (daily_key, lifetime_key):
            pipe.hincrbyfloat(key, "prompt_tokens",     prompt_tokens)
            pipe.hincrbyfloat(key, "completion_tokens", completion_tokens)
            pipe.hincrbyfloat(key, "total_tokens",      total_tokens)
            pipe.hincrbyfloat(key, "estimated_cost_usd", cost)
        pipe.expire(daily_key, DAILY_TTL)
        pipe.execute()

        logger.info(
            "cost.tracked",
            company_id=company_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=round(cost, 6),
        )
    except Exception as exc:
        logger.error("cost.track_failed", error=str(exc))


def get_daily_cost(company_id: str = "global", day: str | None = None) -> dict:
    """Return token usage and cost for a specific day (default: today)."""
    try:
        r = _get_client()
        key = f"cost:daily:{company_id}:{day or date.today().isoformat()}"
        data = r.hgetall(key)
        return {k: float(v) for k, v in data.items()} if data else {}
    except Exception as exc:
        logger.error("cost.get_daily_failed", error=str(exc))
        return {}


def get_lifetime_cost(company_id: str = "global") -> dict:
    """Return all-time token usage and cost for the company."""
    try:
        r = _get_client()
        data = r.hgetall(f"cost:lifetime:{company_id}")
        return {k: float(v) for k, v in data.items()} if data else {}
    except Exception as exc:
        logger.error("cost.get_lifetime_failed", error=str(exc))
        return {}
