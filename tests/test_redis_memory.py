"""Tests for Redis multi-turn memory."""
import pytest
from app.memory.redis_memory import clear_session, get_history, save_turn

SESSION = "test-session-memory-pytest"


@pytest.fixture(autouse=True)
def cleanup():
    clear_session(SESSION)
    yield
    clear_session(SESSION)


def test_empty_history_on_new_session():
    history = get_history(SESSION)
    assert history == []


def test_save_and_retrieve_turn():
    save_turn(SESSION, "how many leave days?", "You have 21 days annual leave.")
    history = get_history(SESSION)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "how many leave days?"
    assert history[1]["role"] == "assistant"


def test_multiple_turns_ordered_oldest_first():
    save_turn(SESSION, "question 1", "answer 1")
    save_turn(SESSION, "question 2", "answer 2")
    history = get_history(SESSION)
    # oldest turn comes first
    assert history[0]["content"] == "question 1"
    assert history[2]["content"] == "question 2"


def test_clear_session():
    save_turn(SESSION, "some question", "some answer")
    clear_session(SESSION)
    assert get_history(SESSION) == []


def test_history_capped_at_max():
    for i in range(12):
        save_turn(SESSION, f"q{i}", f"a{i}")
    history = get_history(SESSION)
    assert len(history) <= 20  # MAX_HISTORY * 2
