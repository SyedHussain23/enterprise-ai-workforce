"""Tests for the offline evaluator scoring logic."""
import pytest
from app.evaluation.evaluator import evaluate_response


def test_zero_on_empty_answer():
    assert evaluate_response("what is leave?", "", "hr_policy") == 0.0


def test_zero_on_empty_query():
    assert evaluate_response("", "some answer", "hr_policy") == 0.0


def test_full_score_detailed_policy_answer():
    answer = (
        "Annual leave is 21 days per year. Sick leave is 12 days. "
        "Maternity leave is 90 days. Paternity leave is 10 days. "
        "You must apply via HR Portal and get manager approval at least 3 days before."
    )
    score = evaluate_response("how many leave days", answer, "hr_policy")
    assert score >= 70.0


def test_low_score_fallback_source():
    score = evaluate_response("any question", "I don't know.", "fallback")
    assert score < 30.0


def test_score_capped_at_100():
    long_answer = "leave " * 100
    score = evaluate_response("leave", long_answer, "hr_policy")
    assert score <= 100.0


def test_score_is_float():
    score = evaluate_response("password reset", "Contact IT support.", "it_policy")
    assert isinstance(score, float)
