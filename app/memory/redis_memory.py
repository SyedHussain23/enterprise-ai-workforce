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
SUMMARIZE_THRESHOLD = 10    # trigger summarization after this many turns (was 12 — fire earlier to avoid hot-path latency)
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


def save_turn(
    session_id: str,
    user_input: str,
    assistant_reply: str,
    background_tasks=None,
) -> None:
    """
    Save one full turn (user + assistant) to session memory.

    Args:
        session_id:        Unique session identifier.
        user_input:        The user's message.
        assistant_reply:   The assistant's response.
        background_tasks:  FastAPI BackgroundTasks instance. When provided,
                           summarization runs off the hot path (non-blocking).
                           When None (e.g., from tests), summarization runs inline.

    DESIGN: Summarization used to run synchronously on turn SUMMARIZE_THRESHOLD,
    causing a 1-3 second latency spike on that specific message. Moving it to a
    background task eliminates the spike entirely — the user sees their response
    immediately while the old turns are compressed in parallel.
    """
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

        # Check if we should summarize — run off the hot path when possible
        total = r.llen(k)
        if total > MAX_ACTIVE_TURNS * 2:
            if background_tasks is not None:
                # Non-blocking: user gets their response immediately
                background_tasks.add_task(_maybe_summarize, session_id, r, k)
            else:
                # Fallback for callers without BackgroundTasks (tests, scripts)
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


# ── Pending-workflow state (multi-turn slot collection) ───────────────────────
# When the AI starts collecting slots for an ACTION request but the user hasn't
# provided all required slots yet, the partial state is stored here so the next
# message can pick up where it left off.

_PENDING_WF_TTL = 30 * 60   # 30 minutes — enough for a normal workflow conversation
_PENDING_WF_PREFIX = "wf_pending"


def _pending_key(session_id: str) -> str:
    return f"{_PENDING_WF_PREFIX}:{session_id}"


def get_pending_workflow(session_id: str) -> dict | None:
    """
    Return the pending workflow state for a session, or None if there is none.

    State shape:
        {
            "workflow_type":    str,           # e.g. "apply_leave"
            "collected_slots":  dict,          # slots we already have
            "missing_slots":    list[str],     # slots still needed
        }
    """
    if not session_id:
        return None
    try:
        r = _get_client()
        raw = r.get(_pending_key(session_id))
        if not raw:
            return None
        state = json.loads(raw)
        logger.info(
            "pending_wf.loaded",
            session_id=session_id[:8],
            workflow_type=state.get("workflow_type"),
            missing=state.get("missing_slots"),
        )
        return state
    except Exception as exc:
        logger.warning("pending_wf.load_failed", session_id=session_id[:8], error=str(exc))
        return None


def save_pending_workflow(session_id: str, state: dict) -> None:
    """
    Persist a partial workflow state so the next message can continue it.
    The state is automatically evicted after _PENDING_WF_TTL seconds.
    """
    if not session_id:
        return
    try:
        r = _get_client()
        r.setex(_pending_key(session_id), _PENDING_WF_TTL, json.dumps(state))
        logger.info(
            "pending_wf.saved",
            session_id=session_id[:8],
            workflow_type=state.get("workflow_type"),
            missing=state.get("missing_slots"),
        )
    except Exception as exc:
        logger.warning("pending_wf.save_failed", session_id=session_id[:8], error=str(exc))


def clear_pending_workflow(session_id: str) -> None:
    """
    Remove pending workflow state once the workflow has been completed
    (all slots collected + action created) or explicitly cancelled.
    """
    if not session_id:
        return
    try:
        r = _get_client()
        r.delete(_pending_key(session_id))
        logger.info("pending_wf.cleared", session_id=session_id[:8])
    except Exception as exc:
        logger.warning("pending_wf.clear_failed", session_id=session_id[:8], error=str(exc))
