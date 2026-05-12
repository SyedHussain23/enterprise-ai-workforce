"""Tests for input guardrail — blocked queries, allowed queries."""
import pytest
from app.utils.guardrails import get_guardrail_response


def test_out_of_scope_blocked():
    result = get_guardrail_response("who won the IPL match?")
    assert result is not None
    assert result["agent"] == "guardrail"
    assert result["confidence"] == 0


def test_hr_query_passes():
    result = get_guardrail_response("how many leave days do I have?")
    assert result is None


def test_it_query_passes():
    result = get_guardrail_response("how do I reset my VPN password?")
    assert result is None


def test_finance_query_passes():
    result = get_guardrail_response("when will my salary be credited?")
    assert result is None


def test_empty_query_blocked():
    result = get_guardrail_response("")
    assert result is not None
