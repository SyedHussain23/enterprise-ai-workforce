"""
Regression tests for the orchestration bugs observed in production.

Each test is a 1:1 mapping to a failure that appeared in the user's chat
log on 2026-05-19. Every test name documents the exact symptom; the body
exercises the code path that produced it.

Bugs covered:
  1. "What is the UAE gratuity formula?" → "You're welcome 😊"
     Root cause: semantic cache stored a gratitude response (confidence 100)
     and the embedding of "gratitude" matched "gratuity" above the 0.85
     cosine threshold.
  2. "How do I submit an expense claim?" → silently filed an expense action
     Root cause: _SUBMIT_EXPENSE_PHRASES contained "how do i claim".
  3. "I need maternity leave" → policy dump OR gratitude hijack
     Should now return a clarification prompt asking for dates/docs.
  4. "How do I apply for a salary advance?" → multi-intent fired HR+Finance
     Root cause: multi-intent splitter didn't respect informational queries.
  5. "when should i submit leave for parental leave" → silently created a
     leave action. Should be informational.
  6. "increase my salary" → returned generic salary policy instead of
     creating a formal request action.
"""
import pytest

from app.utils.intent_classifier import is_informational_query, has_personal_action_intent


# ── intent_classifier unit tests ──────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "What is the UAE gratuity formula?",
    "How do I submit an expense claim?",
    "How do I apply for a salary advance?",
    "When should I submit leave for parental leave?",
    "what is the annual leave policy?",
    "How is gratuity calculated?",
    "How does WFH work?",
    "Tell me about maternity leave",
    "Explain the expense process",
])
def test_information_queries_are_classified_as_info(query):
    assert is_informational_query(query), f"{query!r} should be informational"


@pytest.mark.parametrize("query", [
    "I need leave for 2 days emergency",
    "apply for leave next week",
    "I want to take leave tomorrow",
    "submit my expense",
    "I am sick today",
    "increase my salary by 500",
    "raise my salary please",
    "apply for me",
])
def test_action_queries_are_NOT_info(query):
    assert not is_informational_query(query), f"{query!r} should be an action"


def test_action_override_beats_question_word():
    """When the user phrases an action with a clear first-person intent,
    the personal-action override must win even if a question word appears.

    We test the unambiguous cases — 'can you increase my salary?' contains
    'increase my salary' which is in the override list, so it stays an
    action. Borderline cases like 'could you please apply for leave for me?'
    are intentionally treated as informational (the classifier is
    conservative — degrading an action to a policy answer is recoverable;
    the user can re-state with 'I need leave next week').
    """
    assert not is_informational_query("can you increase my salary?")
    assert not is_informational_query("please raise my salary")
    assert has_personal_action_intent("I am sick today, please notify HR")


# ── Bug 1: gratuity-formula must never trigger gratitude ──────────────────────

def test_gratuity_formula_never_hits_gratitude_guardrail():
    """Even without the cache, the gratitude branch must not fire on the
    word 'gratuity'."""
    from app.utils.guardrails import get_guardrail_response
    r = get_guardrail_response("What is the UAE gratuity formula?")
    # Either passes through (None) or returns a non-gratitude block —
    # but the answer must NEVER be the gratitude response.
    if r is not None:
        assert "you're welcome" not in r["answer"].lower(), (
            f"Gratuity formula hit gratitude branch: {r['answer'][:80]}"
        )


def test_semantic_cache_refuses_to_store_guardrail_responses():
    """The poisoning vector — guardrail responses must never enter the cache.
    We mock the redis client to capture writes."""
    from unittest.mock import patch, MagicMock
    from app.core import semantic_cache as sc

    fake_redis = MagicMock()
    with patch.object(sc, "_get_client", return_value=fake_redis):
        # Gratitude response from the guardrail layer
        sc.set_cached(
            "thanks",
            "company-1",
            {
                "answer":      "You're welcome! 😊",
                "agent":       "guardrail",
                "source":      "guardrail",
                "confidence":  100,
            },
        )
        # The cache must NOT have been written
        assert not fake_redis.setex.called, (
            "Guardrail response was cached — this is the root cause of the "
            "gratuity-formula → 'You're welcome' bug."
        )
        assert not fake_redis.lpush.called, "Guardrail entry pushed to semantic index"


# ── Bug 2: informational expense query must NOT auto-submit ───────────────────

def test_how_do_i_submit_expense_does_not_create_action():
    from app.agents.finance_agent import finance_agent
    r = finance_agent("How do I submit an expense claim?")
    assert not r.action_triggered, (
        "Informational query auto-submitted an expense action. "
        f"action_type={r.action_type}"
    )
    assert r.action_type is None


# ── Bug 3: maternity must trigger clarification, not policy dump ─────────────

def test_i_need_maternity_leave_returns_clarification():
    from app.agents.hr_agent import hr_agent
    r = hr_agent("I need maternity leave")
    a = r.answer.lower()
    # Should ask for the slots, NOT just dump policy
    assert "start date" in a or "expected" in a, (
        "Maternity clarification did not ask for a start date"
    )
    assert "medical" in a or "documentation" in a, (
        "Maternity clarification did not mention medical documentation"
    )
    # And must NOT silently create an action
    assert not r.action_triggered


def test_what_is_maternity_policy_returns_policy():
    """Pure informational maternity query still returns the policy."""
    from app.agents.hr_agent import hr_agent
    r = hr_agent("What is the maternity leave policy?")
    assert not r.action_triggered
    assert "maternity" in r.answer.lower()


# ── Bug 4: how-do-I-apply-for-advance must not split intents ─────────────────

def test_how_do_i_apply_for_salary_advance_is_not_multi_intent():
    from app.utils.multi_intent import detect_intents
    intents = detect_intents("How do I apply for a salary advance?")
    assert len(intents) <= 1, (
        f"Multi-intent splitter fan-out on an informational query: {intents}"
    )


def test_how_do_i_apply_for_salary_advance_does_not_create_action():
    from app.agents.finance_agent import finance_agent
    r = finance_agent("How do I apply for a salary advance?")
    assert not r.action_triggered, (
        f"Informational advance query created action_type={r.action_type}"
    )


# ── Bug 5: 'when should I submit leave' must not auto-file ───────────────────

def test_when_should_i_submit_leave_does_not_create_action():
    from app.agents.hr_agent import hr_agent
    r = hr_agent("when should i submit leave for parental leave")
    assert not r.action_triggered, (
        f"Informational leave-timing query auto-filed action: {r.action_type}"
    )


# ── Bug 6: salary-increase imperative must create action ─────────────────────

def test_increase_my_salary_creates_formal_request_action():
    from app.agents.finance_agent import finance_agent
    r = finance_agent("increase my salary by 500 AED")
    assert r.action_triggered, "Salary increase request should create an action"
    assert r.action_type == "salary_increase_request", (
        f"Wrong action_type: {r.action_type}"
    )


def test_can_you_increase_my_salary_still_creates_action():
    """The action-override list ensures even a question-phrased salary
    increase still files a request."""
    from app.agents.finance_agent import finance_agent
    r = finance_agent("can you increase my salary?")
    assert r.action_triggered
    assert r.action_type == "salary_increase_request"


# ── Bug 7: first-person sick reporting still works ───────────────────────────

def test_i_am_sick_still_creates_sick_leave_action():
    """Regression — ensure the info guard didn't accidentally break the
    explicit sick-reporting path."""
    from app.agents.hr_agent import hr_agent
    r = hr_agent("I am sick today, please notify HR")
    assert r.action_triggered
    assert r.action_type == "sick_leave_report"
