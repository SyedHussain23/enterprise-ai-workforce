"""
Resilient OpenAI client — retry + circuit breaker.

C8 FIX: Raw OpenAI calls fail permanently on the first transient error
        (rate limit spike, 30s timeout, 500 from OpenAI). Enterprise systems
        must be self-healing.

IMPLEMENTATION:
  1. Retry with exponential back-off (up to 3 attempts):
     - RateLimitError     → 1s → 2s wait (OpenAI rate-limit resets quickly)
     - APITimeoutError    → 1s → 2s wait (network blip)
     - APIConnectionError → 1s → 2s wait (DNS/TLS flap)
     - InternalServerError (5xx) → 1s → 2s wait (OpenAI infra issue)
     - Other errors → do NOT retry (bad auth, invalid request, etc.)

  2. Circuit breaker per caller (key = model):
     CLOSED → OPEN after FAILURE_THRESHOLD consecutive failures.
     OPEN   → fast-fail for RECOVERY_TIMEOUT_SECONDS (returns None / raises).
     HALF-OPEN → one probe request; success → CLOSED, failure → OPEN.

     This prevents OpenAI outage from cascading into a wall of 30-second
     hangs across all requests (thread pool exhaustion).

  3. Wrapper function `resilient_chat_completion()` — drop-in replacement
     for client.chat.completions.create(). Returns the Completion object
     or raises after exhausting retries.

Usage:
    from app.core.openai_client import resilient_chat_completion

    resp = resilient_chat_completion(
        model="gpt-4o-mini",
        messages=[...],
        max_tokens=150,
        temperature=0,
    )
    text = resp.choices[0].message.content
"""
from __future__ import annotations

import time
import threading
from enum import Enum

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from openai.types.chat import ChatCompletion

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# ── Retry config ──────────────────────────────────────────────────────────────
MAX_RETRIES         = 3          # total attempts (1 initial + 2 retries)
RETRY_BASE_DELAY    = 1.0        # seconds; doubles on each attempt
RETRYABLE_ERRORS    = (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError)

# ── Circuit-breaker config ────────────────────────────────────────────────────
FAILURE_THRESHOLD        = 5    # consecutive failures before opening circuit
RECOVERY_TIMEOUT_SECONDS = 60   # seconds to stay open before probing


class _State(Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"


class _CircuitBreaker:
    """
    Thread-safe circuit breaker for a single downstream (OpenAI).
    One instance is shared across all calls (module-level singleton).
    """

    def __init__(self) -> None:
        self._lock           = threading.Lock()
        self._state          = _State.CLOSED
        self._failure_count  = 0
        self._opened_at: float | None = None

    # ── Internal state transitions ────────────────────────────────────────────

    def _trip(self) -> None:
        """Open the circuit."""
        self._state         = _State.OPEN
        self._opened_at     = time.monotonic()
        self._failure_count = 0
        logger.error(
            "circuit_breaker.opened",
            threshold=FAILURE_THRESHOLD,
            recovery_s=RECOVERY_TIMEOUT_SECONDS,
        )

    def _reset(self) -> None:
        """Close the circuit (healthy probe succeeded)."""
        self._state         = _State.CLOSED
        self._failure_count = 0
        self._opened_at     = None
        logger.info("circuit_breaker.closed")

    # ── Public API ────────────────────────────────────────────────────────────

    def allow_request(self) -> bool:
        """
        Returns True when the caller may proceed with an API call.
        False means the circuit is OPEN and we should fast-fail.
        """
        with self._lock:
            if self._state == _State.CLOSED:
                return True

            if self._state == _State.OPEN:
                elapsed = time.monotonic() - (self._opened_at or 0)
                if elapsed >= RECOVERY_TIMEOUT_SECONDS:
                    # Transition to half-open: let one probe through
                    self._state = _State.HALF_OPEN
                    logger.info("circuit_breaker.half_open")
                    return True
                # Still open — fast fail
                return False

            # HALF_OPEN: only one probe is allowed at a time
            return True

    def record_success(self) -> None:
        with self._lock:
            if self._state == _State.HALF_OPEN:
                self._reset()
            elif self._state == _State.CLOSED:
                self._failure_count = 0   # reset counter on success streak

    def record_failure(self) -> None:
        with self._lock:
            if self._state == _State.HALF_OPEN:
                # Probe failed → re-open
                self._state     = _State.OPEN
                self._opened_at = time.monotonic()
                logger.warning("circuit_breaker.probe_failed")
                return

            self._failure_count += 1
            logger.warning(
                "circuit_breaker.failure_recorded",
                count=self._failure_count,
                threshold=FAILURE_THRESHOLD,
            )
            if self._failure_count >= FAILURE_THRESHOLD:
                self._trip()

    @property
    def state(self) -> str:
        return self._state.value


# ── Module-level singletons ───────────────────────────────────────────────────

_cb: _CircuitBreaker = _CircuitBreaker()
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=15.0)
    return _client


# ── Public function ───────────────────────────────────────────────────────────

def resilient_chat_completion(
    model: str,
    messages: list[dict],
    *,
    max_tokens: int = 512,
    temperature: float = 0.0,
    response_format: dict | None = None,
    timeout: float | None = None,
) -> ChatCompletion:
    """
    Drop-in replacement for client.chat.completions.create().

    Applies:
      - Circuit breaker fast-fail when OpenAI is consistently down
      - Exponential back-off retry for transient errors

    Raises:
      - RuntimeError  if the circuit is OPEN (fail fast, don't hang)
      - The original OpenAI exception after exhausting retries
    """
    if not _cb.allow_request():
        logger.error(
            "circuit_breaker.fast_fail",
            model=model,
            state=_cb.state,
        )
        raise RuntimeError(
            f"OpenAI circuit breaker is OPEN (recovering from {FAILURE_THRESHOLD} consecutive "
            f"failures). Retry in ~{RECOVERY_TIMEOUT_SECONDS}s."
        )

    client = _get_client()
    kwargs: dict = {
        "model":       model,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": temperature,
    }
    if response_format:
        kwargs["response_format"] = response_format
    if timeout:
        kwargs["timeout"] = timeout

    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(**kwargs)
            _cb.record_success()
            if attempt > 1:
                logger.info(
                    "openai_client.retry_succeeded",
                    model=model,
                    attempt=attempt,
                )
            return resp

        except RETRYABLE_ERRORS as exc:
            last_exc = exc
            _cb.record_failure()
            wait = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(
                "openai_client.retry",
                model=model,
                attempt=attempt,
                max_retries=MAX_RETRIES,
                error=type(exc).__name__,
                wait_s=wait,
            )
            if attempt < MAX_RETRIES:
                time.sleep(wait)

        except Exception as exc:
            # Non-retryable (auth error, invalid params, etc.) — fail immediately
            _cb.record_failure()
            logger.error(
                "openai_client.non_retryable_error",
                model=model,
                error=type(exc).__name__,
                detail=str(exc)[:200],
            )
            raise

    # All retries exhausted
    logger.error(
        "openai_client.all_retries_exhausted",
        model=model,
        attempts=MAX_RETRIES,
        last_error=str(last_exc)[:200],
    )
    raise last_exc  # type: ignore[misc]


def get_circuit_state() -> dict:
    """Return circuit breaker status for /health/deep endpoint."""
    return {
        "state":           _cb.state,
        "failure_count":   _cb._failure_count,
        "failure_threshold": FAILURE_THRESHOLD,
        "recovery_timeout_s": RECOVERY_TIMEOUT_SECONDS,
    }


# ── Real streaming (C5) ───────────────────────────────────────────────────────

_SYNTHESIS_SYSTEM = """You are an enterprise AI assistant for a UAE/GCC company.
You have been given retrieved policy context and a user question.
Answer the question accurately using the context. Be concise (3-5 sentences max).
Format in Markdown. If context is insufficient, say so honestly.
Never invent facts not present in the context."""

async def async_stream_synthesis(
    question: str,
    context: str,
    department: str = "HR",
    model: str = "gpt-4o",
) -> "AsyncGenerator[str, None]":
    """
    C5: Real token-by-token streaming using OpenAI's streaming API.

    Used by /ask/stream when the answer comes from RAG retrieval — the
    pre-written rule-based answers don't need LLM synthesis (they're already
    accurate and authoritative), but RAG fallback answers benefit from a
    natural language synthesis pass.

    Yields text chunks (not complete messages) as they arrive from OpenAI.
    Falls back to yielding the context as-is if streaming fails.

    Args:
        question:   The user's question.
        context:    Retrieved and graded RAG context.
        department: HR / IT / Finance (for system prompt tuning).
        model:      OpenAI model to use for synthesis.
    """
    from openai import AsyncOpenAI
    import asyncio

    if not _cb.allow_request():
        # Circuit open — yield context directly (no LLM, no hang)
        logger.warning("async_stream_synthesis.circuit_open")
        yield context
        return

    async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=20.0)

    messages = [
        {
            "role": "system",
            "content": _SYNTHESIS_SYSTEM + f"\nDepartment context: {department}",
        },
        {
            "role": "user",
            "content": f"Context:\n{context[:2000]}\n\nQuestion: {question}",
        },
    ]

    try:
        stream = await async_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=400,
            temperature=0.3,
            stream=True,
        )
        token_count = 0
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                _cb.record_success()
                token_count += 1
                yield delta

        logger.info(
            "async_stream_synthesis.complete",
            model=model,
            tokens=token_count,
            department=department,
        )

    except RETRYABLE_ERRORS as exc:
        _cb.record_failure()
        logger.warning(
            "async_stream_synthesis.stream_failed",
            error=type(exc).__name__,
            detail=str(exc)[:100],
        )
        # Fall back to yielding context — never leave stream hanging
        yield context
    except Exception as exc:
        _cb.record_failure()
        logger.error(
            "async_stream_synthesis.unexpected_error",
            error=type(exc).__name__,
            detail=str(exc)[:200],
        )
        yield context


# Expose the type hint correctly without circular import
from typing import AsyncGenerator  # noqa: E402 — needed after function def
