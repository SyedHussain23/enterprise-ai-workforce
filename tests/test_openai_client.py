"""
Unit tests for the resilient OpenAI client — circuit breaker and retry logic.

These tests mock the OpenAI SDK so no real API calls are made.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from openai import RateLimitError, APITimeoutError

from app.core.openai_client import (
    _CircuitBreaker,
    _State,
    FAILURE_THRESHOLD,
    RECOVERY_TIMEOUT_SECONDS,
    resilient_chat_completion,
)


# ── Circuit breaker unit tests ────────────────────────────────────────────────

class TestCircuitBreaker:
    def setup_method(self):
        self.cb = _CircuitBreaker()

    def test_initial_state_is_closed(self):
        assert self.cb._state == _State.CLOSED
        assert self.cb.allow_request() is True

    def test_trips_after_threshold_failures(self):
        for _ in range(FAILURE_THRESHOLD):
            self.cb.record_failure()
        assert self.cb._state == _State.OPEN

    def test_open_circuit_blocks_requests(self):
        for _ in range(FAILURE_THRESHOLD):
            self.cb.record_failure()
        assert self.cb.allow_request() is False

    def test_success_resets_failure_count(self):
        for _ in range(FAILURE_THRESHOLD - 1):
            self.cb.record_failure()
        self.cb.record_success()
        assert self.cb._failure_count == 0
        assert self.cb._state == _State.CLOSED

    def test_transitions_to_half_open_after_recovery_timeout(self):
        for _ in range(FAILURE_THRESHOLD):
            self.cb.record_failure()
        assert self.cb._state == _State.OPEN

        # Force opened_at into the past to simulate timeout
        self.cb._opened_at -= RECOVERY_TIMEOUT_SECONDS + 1
        assert self.cb.allow_request() is True
        assert self.cb._state == _State.HALF_OPEN

    def test_successful_probe_closes_circuit(self):
        for _ in range(FAILURE_THRESHOLD):
            self.cb.record_failure()
        self.cb._opened_at -= RECOVERY_TIMEOUT_SECONDS + 1
        self.cb.allow_request()   # transition to HALF_OPEN
        self.cb.record_success()
        assert self.cb._state == _State.CLOSED
        assert self.cb._failure_count == 0

    def test_failed_probe_reopens_circuit(self):
        for _ in range(FAILURE_THRESHOLD):
            self.cb.record_failure()
        self.cb._opened_at -= RECOVERY_TIMEOUT_SECONDS + 1
        self.cb.allow_request()   # transition to HALF_OPEN
        self.cb.record_failure()
        assert self.cb._state == _State.OPEN

    def test_state_property_returns_string(self):
        assert self.cb.state == "closed"
        for _ in range(FAILURE_THRESHOLD):
            self.cb.record_failure()
        assert self.cb.state == "open"


# ── resilient_chat_completion integration tests ───────────────────────────────

def _make_completion(content: str = "ok") -> MagicMock:
    """Build a fake ChatCompletion response object."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture(autouse=True)
def reset_module_state():
    """
    Reset the module-level circuit breaker before each test so tests are isolated.
    """
    import app.core.openai_client as mod
    mod._cb = _CircuitBreaker()
    mod._client = None
    yield
    # Teardown: reset again to avoid leaking state
    mod._cb = _CircuitBreaker()
    mod._client = None


class TestResilientChatCompletion:
    def test_success_on_first_attempt(self):
        with patch("app.core.openai_client._get_client") as mock_get:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = _make_completion("hello")
            mock_get.return_value = mock_client

            resp = resilient_chat_completion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "hi"}],
            )
            assert resp.choices[0].message.content == "hello"
            assert mock_client.chat.completions.create.call_count == 1

    def test_retries_on_rate_limit_then_succeeds(self):
        fake_error = RateLimitError(
            message="rate limit",
            response=MagicMock(headers={}, status_code=429),
            body={},
        )
        success_resp = _make_completion("retried ok")

        with patch("app.core.openai_client._get_client") as mock_get, \
             patch("app.core.openai_client.time") as mock_time:
            mock_time.sleep = MagicMock()
            mock_time.monotonic = MagicMock(return_value=0)

            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = [
                fake_error,
                success_resp,
            ]
            mock_get.return_value = mock_client

            resp = resilient_chat_completion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "hi"}],
            )
            assert resp.choices[0].message.content == "retried ok"
            assert mock_client.chat.completions.create.call_count == 2
            mock_time.sleep.assert_called_once_with(1.0)  # first retry delay

    def test_raises_after_all_retries_exhausted(self):
        fake_error = APITimeoutError(request=MagicMock())

        with patch("app.core.openai_client._get_client") as mock_get, \
             patch("app.core.openai_client.time") as mock_time:
            mock_time.sleep = MagicMock()
            mock_time.monotonic = MagicMock(return_value=0)

            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = fake_error
            mock_get.return_value = mock_client

            with pytest.raises(APITimeoutError):
                resilient_chat_completion(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "hi"}],
                )
            # MAX_RETRIES=3 attempts total
            assert mock_client.chat.completions.create.call_count == 3

    def test_fast_fails_when_circuit_is_open(self):
        import app.core.openai_client as mod
        # Manually trip the circuit
        for _ in range(FAILURE_THRESHOLD):
            mod._cb.record_failure()

        with patch("app.core.openai_client._get_client") as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            with pytest.raises(RuntimeError, match="circuit breaker is OPEN"):
                resilient_chat_completion(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "hi"}],
                )
            # Must not make any API calls when circuit is open
            mock_client.chat.completions.create.assert_not_called()

    def test_non_retryable_error_fails_immediately(self):
        """ValueError (bad params) should not be retried."""
        with patch("app.core.openai_client._get_client") as mock_get:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = ValueError("bad model")
            mock_get.return_value = mock_client

            with pytest.raises(ValueError, match="bad model"):
                resilient_chat_completion(
                    model="bad-model",
                    messages=[{"role": "user", "content": "hi"}],
                )
            # Only 1 attempt — non-retryable
            assert mock_client.chat.completions.create.call_count == 1
