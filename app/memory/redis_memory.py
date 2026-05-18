"""
Redis multi-turn conversation memory with context-window management.

IMPROVEMENTS over original:
  H6: Added conversation summarization for long sessions.
      When session exceeds SUMMARIZE_THRESHOLD turns, older history is
      compressed into a single summary turn using an LLM call. This prevents
      context window overflow and keeps the planner prompt lean.

  Architecture:
  - Active window:  last MAX_ACTIVE_TURNS turns (verbatim, sent to planner)
  - Summary:        compressed older history (single system message)
  - Combined:       [summary (if exists)] + [active turns]

  Redis keys:
  - memory:{session_id}         → LPUSH list of recent turns (newest first)
  - memory:{session_id}:summary → STRING summary of older context
"""
from __future__ import annotations

import json

import redis

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

MAX_ACTIVE_TURNS    = 8     # verbatim turns kept per session
SUMMARIZE_THRESHOLD = 12    # trigger summarization after this many turns
TTL_SECONDS         = 86_400  # 24h, reset on each write

_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _client


def _key(session_id: str) -> str:
    return f"memory:{session_id}"


def _summary_key(session_id: str) -> str:
    return f"memory:{session_id}:summary"


def _summarize(turns: list[dict]) -> str:
    """
    Compress a list of conversation turns into a concise summary.
    Uses gpt-4o-mini (cheap, fast) — summary is ~50–100 tokens.
    Uses resilient_chat_completion for retry + circuit-breaker protection.
    """
    convo = "\n".join(
        f"{t['role'].upper()}: {t['content'][:300]}"
        for t in turns
    )
    try:
        from app.core.openai_client import resilient_chat_completion
        resp = resilient_chat_completion(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": (
                    f"Summarise this enterprise chat conversation in 2–3 sentences. "
                    f"Keep key topics, decisions, and requests mentioned.\n\n{convo}"
                ),
            }],
            max_tokens=150,
            temperature=0,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("memory.summarize_failed", error=str(exc))
        # Fallback: just truncate to last 500 chars of the raw conversation
        return f"[Earlier context summarized] {convo[-500:]}"


def save_turn(session_id: str, user_input: str, assistant_reply: str) -> None:
    """Save one full turn (user + assistant) to session memory."""
    try:
        r = _get_client()
        k = _key(session_id)
        pipe = r.pipeline()
        # LPUSH newest first — list[0] is always most recent
        pipe.lpush(k, json.dumps({"role": "assistant", "content": assistant_reply[:1000]}))
        pipe.lpush(k, json.dumps({"role": "user",      "content": user_input[:500]}))
        # Cap at SUMMARIZE_THRESHOLD * 2 messages (messages not turns)
        pipe.ltrim(k, 0, SUMMARIZE_THRESHOLD * 2 - 1)
        pipe.expire(k, TTL_SECONDS)
        pipe.execute()

        # Check if we should summarize older turns
        total = r.llen(k)
        if total > MAX_ACTIVE_TURNS * 2:
            _maybe_summarize(session_id, r, k)

        logger.info("memory.saved", session_id=session_id[:8])
    except Exception as exc:
        logger.error("memory.save_failed", session_id=session_id[:8], error=str(exc))


def _maybe_summarize(session_id: str, r: redis.Redis, k: str) -> None:
    """
    If history is long, summarize older turns and trim the list.
    Called inline after save — adds ~500ms on the summarization turn.
    """
    try:
        all_raw = r.lrange(k, 0, -1)
        if not all_raw:
            return

        # all_raw is newest-first; reverse to get chronological order
        messages = [json.loads(m) for m in reversed(all_raw)]
        older = messages[: -MAX_ACTIVE_TURNS * 2]   # everything before the active window

        if not older:
            return

        summary = _summarize(older)
        pipe = r.pipeline()
        # Store summary
        pipe.set(_summary_key(session_id), summary)
        pipe.expire(_summary_key(session_id), TTL_SECONDS)
        # Keep only active window in the list (trim older turns out)
        pipe.ltrim(k, 0, MAX_ACTIVE_TURNS * 2 - 1)
        pipe.execute()
        logger.info("memory.summarized", session_id=session_id[:8], older_turns=len(older) // 2)
    except Exception as exc:
        logger.warning("memory.summarize_error", error=str(exc))


def get_history(session_id: str) -> list[dict]:
    """
    Return conversation history oldest-first for the planner prompt.

    Returns: [summary_system_msg (if exists)] + [active_turns]
    """
    try:
        r = _get_client()
        messages: list[dict] = []

        # Prepend summary if it exists
        summary = r.get(_summary_key(session_id))
        if summary:
            messages.append({
                "role":    "system",
                "content": f"[Earlier conversation summary]: {summary}",
            })

        # Active turns (newest-first from Redis → reverse for chronological)
        raw = r.lrange(_key(session_id), 0, MAX_ACTIVE_TURNS * 2 - 1)
        if raw:
            messages += [json.loads(item) for item in reversed(raw)]

        logger.info(
            "memory.fetched",
            session_id=session_id[:8],
            messages=len(messages),
            has_summary=bool(summary),
        )
        return messages
    except Exception as exc:
        logger.error("memory.fetch_failed", session_id=session_id[:8], error=str(exc))
        return []


def clear_session(session_id: str) -> None:
    """Delete all memory for a session (e.g. on logout or new conversation)."""
    try:
        r = _get_client()
        r.delete(_key(session_id), _summary_key(session_id))
        logger.info("memory.cleared", session_id=session_id[:8])
    except Exception as exc:
        logger.error("memory.clear_failed", session_id=session_id[:8], error=str(exc))
