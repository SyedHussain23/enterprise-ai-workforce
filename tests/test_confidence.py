"""Tests for confidence calculator."""
import pytest
from app.utils.confidence import calculate_confidence


def test_high_confidence_rag_verified():
    score, reason = calculate_confidence(
        answer="Annual leave is 21 days per year.",
        keyword_match=True,
        rag_used=True,
        source="hr_policy",
    )
    assert score >= 70
    assert isinstance(reason, str)


def test_low_confidence_fallback():
    score, reason = calculate_confidence(
        answer="I don't know.",
        keyword_match=False,
        rag_used=False,
        source="fallback",
    )
    assert score < 40


def test_confidence_in_valid_range():
    score, _ = calculate_confidence(
        answer="Some answer",
        keyword_match=True,
        rag_used=False,
        source="it_policy",
    )
    assert 0 <= score <= 100


def test_returns_tuple():
    result = calculate_confidence(
        answer="test", keyword_match=False, rag_used=False, source="internal_kb"
    )
    assert isinstance(result, tuple)
    assert len(result) == 2
