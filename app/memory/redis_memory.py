"""
Redis multi-turn conversation memory.

Stores per-session chat history as a capped list so the planner agent
has context from previous turns. Each entry is a JSON object with
role ("user" | "assistant") and content.

Key design decisions:
- LPUSH + LTRIM keeps the list bounded (MAX_HISTORY items) — no unbounded growth.
- TTL of 24 hours resets on every write — idle sessions expire automatically.
- Fails silently: if Redis is down the workflow still functions, just without memory.
"""
import json

import redis

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

MAX_HISTORY = 10        # turns kept per session (each turn = 1 message)
TTL_SECONDS = 86400     # 24 hours — reset on every write

_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def _key(session_id: str) -> str:
    return f"memory:{session_id}"


def save_turn(session_id: str, user_input: str, assistant_reply: str) -> None:
    """Save one full turn (user + assistant) to session memory."""
    try:
        r = _get_client()
        k = _key(session_id)
        pipe = r.pipeline()
        # LPUSH user first, then assistant — so after reversal the order is
        # user → assistant (chronological) within each turn.
        pipe.lpush(k, json.dumps({"role": "user", "content": user_input}))
        pipe.lpush(k, json.dumps({"role": "assistant", "content": assistant_reply}))
        pipe.ltrim(k, 0, MAX_HISTORY * 2 - 1)   # cap at MAX_HISTORY turns
        pipe.expire(k, TTL_SECONDS)
        pipe.execute()
        logger.info("memory.saved", session_id=session_id)
    except Exception as exc:
        logger.error("memory.save_failed", session_id=session_id, error=str(exc))


def get_history(session_id: str) -> list[dict]:
    """
    Return conversation history oldest-first for the planner prompt.
    Format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
    """
    try:
        r = _get_client()
        raw = r.lrange(_key(session_id), 0, MAX_HISTORY * 2 - 1)
        if not raw:
            return []
        # list is stored newest-first (LPUSH), reverse to get oldest-first
        messages = [json.loads(item) for item in reversed(raw)]
        logger.info("memory.fetched", session_id=session_id, turns=len(messages))
        return messages
    except Exception as exc:
        logger.error("memory.fetch_failed", session_id=session_id, error=str(exc))
        return []


def clear_session(session_id: str) -> None:
    """Delete all memory for a session (e.g. on logout)."""
    try:
        _get_client().delete(_key(session_id))
        logger.info("memory.cleared", session_id=session_id)
    except Exception as exc:
        logger.error("memory.clear_failed", session_id=session_id, error=str(exc))
