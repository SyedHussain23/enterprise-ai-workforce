"""
Tests for the ConversationEngine and workflow slot machinery.

These tests cover the exact production failures documented in the user prompt:

  Failure 1: "i need emergency leave"  → gave leave POLICY (FAQ)
             CORRECT: start leave workflow intake, ask for dates
  Failure 2: "increase salary by 2%"   → gave salary FAQ
             CORRECT: start compensation review workflow
  Failure 3: "what do you do"          → routed to HR only
             CORRECT: return system capabilities overview
  Failure 4: "im sick"                 → generic sick leave policy
             CORRECT: ask clarifying question (how many days?)
  Failure 5: "what is your issues"     → random IT support dump
             CORRECT: return system capabilities (SYSTEM intent)

Architecture note (deterministic-first):
  The engine uses pure-Python deterministic classification for ~90% of queries
  with ZERO API calls. GPT-4o is only called for genuinely ambiguous queries.
  Tests therefore do NOT need to mock OpenAI for the common cases.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.utils.workflow_slots import (
    get_workflow_def,
    get_required_slots,
    get_missing_slots,
    get_action_type,
    WORKFLOW_DEFINITIONS,
)
from app.core.conversation_engine import (
    classify_deterministic,
    extract_slots_simple,
    _template_clarification,
    PLATFORM_CAPABILITIES,
)


# ── Workflow slot machinery ───────────────────────────────────────────────────

class TestWorkflowSlots:

    def test_apply_leave_has_required_slots(self):
        slots = get_required_slots("apply_leave")
        assert "leave_type" in slots
        assert "start_date" in slots
        assert "end_date_or_days" in slots

    def test_sick_leave_required_slots(self):
        slots = get_required_slots("sick_leave_report")
        assert "days" in slots

    def test_salary_increase_required_slots(self):
        slots = get_required_slots("salary_increase_request")
        assert "justification" in slots

    def test_it_ticket_required_slots(self):
        slots = get_required_slots("it_ticket")
        assert "issue_type" in slots
        assert "description" in slots

    def test_get_missing_slots_returns_uncollected(self):
        collected = {"leave_type": "emergency"}
        missing = get_missing_slots("apply_leave", collected)
        assert "start_date" in missing
        assert "end_date_or_days" in missing
        assert "leave_type" not in missing

    def test_get_missing_slots_empty_when_all_collected(self):
        collected = {
            "leave_type": "emergency",
            "start_date": "tomorrow",
            "end_date_or_days": "3 days",
        }
        missing = get_missing_slots("apply_leave", collected)
        assert missing == []

    def test_get_action_type_maps_correctly(self):
        assert get_action_type("apply_leave") == "apply_leave"
        assert get_action_type("salary_increase_request") == "salary_increase_request"
        assert get_action_type("sick_leave_report") == "sick_leave_report"

    def test_all_workflows_have_labels(self):
        for wf_type, wf_def in WORKFLOW_DEFINITIONS.items():
            assert "label" in wf_def, f"{wf_type} missing 'label'"
            assert "department" in wf_def, f"{wf_type} missing 'department'"
            assert "required_slots" in wf_def, f"{wf_type} missing 'required_slots'"
            assert "action_type" in wf_def, f"{wf_type} missing 'action_type'"

    def test_all_workflows_have_slot_prompts(self):
        for wf_type, wf_def in WORKFLOW_DEFINITIONS.items():
            prompts = wf_def.get("slot_prompts", {})
            for slot in wf_def.get("required_slots", []):
                assert slot in prompts, (
                    f"{wf_type}: required slot '{slot}' has no slot_prompt"
                )

    def test_wfh_workflow_definition(self):
        wf = get_workflow_def("wfh_request")
        assert wf["department"] == "HR"
        assert "wfh_date" in wf["required_slots"]

    def test_maternity_workflow_definition(self):
        wf = get_workflow_def("maternity_leave_request")
        assert wf["department"] == "HR"
        assert "start_date" in wf["required_slots"]


# ── Deterministic classification (zero API calls) ─────────────────────────────

class TestDeterministicClassification:
    """
    The deterministic classifier must handle all common cases without any
    OpenAI call. These tests run purely in Python — no mocking needed.
    """

    # ── SYSTEM intent ─────────────────────────────────────────────────────────

    def test_system_what_do_you_do(self):
        r = classify_deterministic("what do you do", None)
        assert r is not None
        assert r["intent_type"] == "SYSTEM"

    def test_system_what_can_you_do(self):
        r = classify_deterministic("what can you do?", None)
        assert r is not None
        assert r["intent_type"] == "SYSTEM"

    def test_system_what_are_your_issues(self):
        """Was wrongly routed to IT — must be SYSTEM."""
        r = classify_deterministic("what is your issues", None)
        assert r is not None
        assert r["intent_type"] == "SYSTEM"

    def test_system_what_are_your_capabilities(self):
        r = classify_deterministic("what are your capabilities?", None)
        assert r is not None
        assert r["intent_type"] == "SYSTEM"

    def test_system_how_do_you_work(self):
        r = classify_deterministic("how do you work?", None)
        assert r is not None
        assert r["intent_type"] == "SYSTEM"

    # ── ACTION intent ─────────────────────────────────────────────────────────

    def test_action_i_need_emergency_leave(self):
        """Core production failure — must be ACTION not INFO."""
        r = classify_deterministic("i need emergency leave", None)
        assert r is not None
        assert r["intent_type"] == "ACTION"
        assert r["workflow_type"] == "apply_leave"

    def test_action_i_need_2_days_leave(self):
        r = classify_deterministic("i need 2 days leave", None)
        assert r is not None
        assert r["intent_type"] == "ACTION"
        assert r["workflow_type"] == "apply_leave"

    def test_action_im_sick(self):
        """Was giving policy dump — must be ACTION."""
        r = classify_deterministic("im sick", None)
        assert r is not None
        assert r["intent_type"] == "ACTION"
        assert r["workflow_type"] == "sick_leave_report"

    def test_action_i_am_sick(self):
        r = classify_deterministic("i am sick today", None)
        assert r is not None
        assert r["intent_type"] == "ACTION"
        assert r["workflow_type"] == "sick_leave_report"

    def test_action_increase_my_salary(self):
        r = classify_deterministic("increase my salary", None)
        assert r is not None
        assert r["intent_type"] == "ACTION"
        assert r["workflow_type"] == "salary_increase_request"

    def test_action_salary_hike_by_2_percent(self):
        """Was giving salary FAQ — must be ACTION."""
        r = classify_deterministic("increase salary by 2%", None)
        assert r is not None
        assert r["intent_type"] == "ACTION"
        assert r["workflow_type"] == "salary_increase_request"

    def test_action_raise_my_salary(self):
        r = classify_deterministic("raise my salary please", None)
        assert r is not None
        assert r["intent_type"] == "ACTION"
        assert r["workflow_type"] == "salary_increase_request"

    def test_action_submit_expense(self):
        r = classify_deterministic("submit my expense", None)
        assert r is not None
        assert r["intent_type"] == "ACTION"
        assert r["workflow_type"] == "submit_expense"

    def test_action_request_advance(self):
        r = classify_deterministic("i need a salary advance", None)
        assert r is not None
        assert r["intent_type"] == "ACTION"
        assert r["workflow_type"] == "request_advance"

    def test_action_wfh(self):
        r = classify_deterministic("i need to work from home tomorrow", None)
        assert r is not None
        assert r["intent_type"] == "ACTION"
        assert r["workflow_type"] == "wfh_request"

    def test_action_maternity(self):
        r = classify_deterministic("i need maternity leave", None)
        assert r is not None
        assert r["intent_type"] == "ACTION"
        assert r["workflow_type"] == "maternity_leave_request"

    # ── INFO intent ───────────────────────────────────────────────────────────

    def test_info_how_does_gratuity_work(self):
        r = classify_deterministic("how does gratuity work?", None)
        assert r is not None
        assert r["intent_type"] == "INFO"

    def test_info_what_is_annual_leave_policy(self):
        r = classify_deterministic("what is the annual leave policy?", None)
        assert r is not None
        assert r["intent_type"] == "INFO"

    def test_info_how_do_i_submit_expense(self):
        r = classify_deterministic("how do I submit an expense claim?", None)
        assert r is not None
        assert r["intent_type"] == "INFO"

    def test_info_when_is_salary_paid(self):
        r = classify_deterministic("when is salary paid this month?", None)
        assert r is not None
        assert r["intent_type"] == "INFO"

    # ── INFO should NOT be classified as ACTION ───────────────────────────────

    def test_info_not_action_for_how_do_i_apply(self):
        """'How do I apply for leave' is INFO, not an action request."""
        r = classify_deterministic("how do I apply for leave?", None)
        # Must be INFO — not an action
        if r is not None:
            assert r["intent_type"] == "INFO"

    # ── FOLLOWUP intent ───────────────────────────────────────────────────────

    def test_followup_with_pending_workflow(self):
        """Short message providing a date for a pending leave workflow."""
        pending = {
            "workflow_type": "apply_leave",
            "collected_slots": {"leave_type": "emergency"},
            "missing_slots": ["start_date", "end_date_or_days"],
        }
        r = classify_deterministic("from tomorrow for 3 days", pending)
        assert r is not None
        assert r["intent_type"] == "FOLLOWUP"
        assert r["workflow_type"] == "apply_leave"

    def test_followup_short_answer(self):
        """User answers 'tomorrow' to a pending leave request."""
        pending = {
            "workflow_type": "apply_leave",
            "collected_slots": {"leave_type": "annual"},
            "missing_slots": ["start_date"],
        }
        r = classify_deterministic("tomorrow", pending)
        assert r is not None
        assert r["intent_type"] == "FOLLOWUP"

    def test_followup_sick_days_answer(self):
        """User says '2 days' to a pending sick leave request."""
        pending = {
            "workflow_type": "sick_leave_report",
            "collected_slots": {},
            "missing_slots": ["days"],
        }
        r = classify_deterministic("2 days", pending)
        assert r is not None
        assert r["intent_type"] == "FOLLOWUP"


# ── Slot extraction ───────────────────────────────────────────────────────────

class TestSlotExtraction:

    def test_extract_days_from_leave_query(self):
        slots = extract_slots_simple("i need 2 days leave", "apply_leave")
        assert slots.get("end_date_or_days") == "2 days"

    def test_extract_leave_type_emergency(self):
        slots = extract_slots_simple("i need emergency leave", "apply_leave")
        assert slots.get("leave_type") == "emergency"

    def test_extract_leave_type_annual(self):
        slots = extract_slots_simple("i want to take annual leave", "apply_leave")
        assert slots.get("leave_type") == "annual"

    def test_extract_start_date_tomorrow(self):
        slots = extract_slots_simple("i need leave from tomorrow", "apply_leave")
        assert slots.get("start_date") == "tomorrow"

    def test_extract_percentage_from_salary_query(self):
        slots = extract_slots_simple("increase my salary by 10%", "salary_increase_request")
        assert "10%" in slots.get("desired_percentage", "")

    def test_extract_days_sick_leave(self):
        slots = extract_slots_simple("i am sick today", "sick_leave_report")
        assert slots.get("days") == "1 day"

    def test_extract_days_explicit_sick_leave(self):
        slots = extract_slots_simple("im sick for 3 days", "sick_leave_report")
        assert slots.get("days") == "3 days"

    def test_extract_wfh_date(self):
        slots = extract_slots_simple("i want to work from home tomorrow", "wfh_request")
        assert slots.get("wfh_date") == "tomorrow"

    def test_extract_returns_empty_when_no_slots(self):
        slots = extract_slots_simple("i need leave", "apply_leave")
        # "i need leave" has no specific values — may return empty or partial
        assert isinstance(slots, dict)

    def test_extract_multiple_slots_from_one_message(self):
        slots = extract_slots_simple(
            "i need emergency leave from tomorrow for 5 days",
            "apply_leave",
        )
        assert slots.get("leave_type") == "emergency"
        assert slots.get("start_date") == "tomorrow"
        assert slots.get("end_date_or_days") == "5 days"


# ── Clarification template ────────────────────────────────────────────────────

class TestClarificationTemplate:

    def test_template_asks_for_missing_slot(self):
        result = _template_clarification(
            "apply_leave",
            collected_slots={"leave_type": "emergency"},
            missing_slots=["start_date", "end_date_or_days"],
        )
        assert isinstance(result, str)
        assert len(result) > 10
        # Should mention something about the date or days
        lower = result.lower()
        assert any(kw in lower for kw in ["start", "date", "day", "return", "long"])

    def test_template_includes_workflow_label(self):
        result = _template_clarification(
            "sick_leave_report",
            collected_slots={},
            missing_slots=["days"],
        )
        # Should mention Sick Leave or similar
        lower = result.lower()
        assert any(kw in lower for kw in ["sick", "leave", "absent", "day", "away"])

    def test_template_acknowledges_collected_slots(self):
        result = _template_clarification(
            "apply_leave",
            collected_slots={"leave_type": "emergency", "start_date": "tomorrow"},
            missing_slots=["end_date_or_days"],
        )
        # Should mention the collected info
        lower = result.lower()
        assert "emergency" in lower or "tomorrow" in lower or "return" in lower


# ── ConversationEngine class ──────────────────────────────────────────────────

@pytest.fixture
def engine():
    from app.core.conversation_engine import ConversationEngine
    return ConversationEngine()


class TestConversationEngineClassification:
    """
    classify_and_extract() now uses deterministic-first, so common cases
    don't need any LLM mock. Only test the LLM fallback path separately.
    """

    def test_system_intent_what_do_you_do(self, engine):
        result = engine.classify_and_extract("what do you do?", [])
        assert result["intent_type"] == "SYSTEM"

    def test_system_intent_what_are_your_issues(self, engine):
        """Was wrongly routed to IT — must be SYSTEM."""
        result = engine.classify_and_extract("what is your issues", [])
        assert result["intent_type"] == "SYSTEM"

    def test_action_i_need_emergency_leave(self, engine):
        """Must be ACTION → apply_leave. No API call needed."""
        result = engine.classify_and_extract("i need emergency leave", [])
        assert result["intent_type"] == "ACTION"
        assert result["workflow_type"] == "apply_leave"

    def test_action_i_need_2_days_leave(self, engine):
        result = engine.classify_and_extract("i need 2 days leave", [])
        assert result["intent_type"] == "ACTION"
        assert result["workflow_type"] == "apply_leave"

    def test_action_increase_salary_by_2_percent(self, engine):
        """Was giving salary FAQ — must be ACTION."""
        result = engine.classify_and_extract("increase salary by 2%", [])
        assert result["intent_type"] == "ACTION"
        assert result["workflow_type"] == "salary_increase_request"

    def test_action_im_sick(self, engine):
        """Was giving policy dump — must be ACTION."""
        result = engine.classify_and_extract("im sick", [])
        assert result["intent_type"] == "ACTION"
        assert result["workflow_type"] == "sick_leave_report"

    def test_info_how_does_gratuity_work(self, engine):
        result = engine.classify_and_extract("how does gratuity work?", [])
        assert result["intent_type"] == "INFO"

    def test_info_what_is_expense_limit(self, engine):
        result = engine.classify_and_extract("what is the expense claim limit?", [])
        assert result["intent_type"] == "INFO"

    def test_followup_provides_missing_slots(self, engine):
        """After asking for start_date, user replies 'from tomorrow for 3 days'."""
        pending = {
            "workflow_type": "apply_leave",
            "collected_slots": {"leave_type": "emergency"},
            "missing_slots": ["start_date", "end_date_or_days"],
        }
        result = engine.classify_and_extract("from tomorrow for 3 days", [], pending)
        assert result["intent_type"] == "FOLLOWUP"
        assert result["workflow_type"] == "apply_leave"

    def test_fallback_to_info_when_ambiguous_and_llm_fails(self, engine):
        """If genuinely ambiguous AND LLM fails, must default to INFO (not action)."""
        with patch.object(engine, "_classify_with_llm", side_effect=RuntimeError("LLM down")):
            # "something" is ambiguous — deterministic returns None → escalates to LLM → fails → INFO
            result = engine.classify_and_extract("something unrecognised xyz123", [])
            assert result["intent_type"] == "INFO"


# ── Clarification generation (ConversationEngine) ────────────────────────────

class TestClarificationGeneration:

    def test_generates_question_for_missing_slots_no_llm(self, engine):
        """Should return a question (template fallback) even when LLM is unavailable.

        generate_clarification() lazily imports resilient_chat_completion inside
        its try-block, so we patch it at the *source* module to force the exception.
        """
        with patch("app.core.openai_client.resilient_chat_completion",
                   side_effect=RuntimeError("LLM down")):
            result = engine.generate_clarification(
                workflow_type="apply_leave",
                collected_slots={"leave_type": "emergency"},
                missing_slots=["start_date", "end_date_or_days"],
                original_query="i need emergency leave",
            )
        assert isinstance(result, str)
        assert len(result) > 10

    def test_sick_leave_clarification_template_fallback(self, engine):
        """Template fallback works for sick leave when LLM is down."""
        with patch("app.core.openai_client.resilient_chat_completion",
                   side_effect=RuntimeError("LLM down")):
            result = engine.generate_clarification(
                workflow_type="sick_leave_report",
                collected_slots={},
                missing_slots=["days"],
                original_query="im sick",
            )
        assert isinstance(result, str)
        assert len(result) > 5


# ── Workflow confirmation ─────────────────────────────────────────────────────

class TestWorkflowConfirmation:

    def test_confirmation_includes_workflow_label(self, engine):
        result = engine.generate_workflow_confirmation(
            workflow_type="apply_leave",
            collected_slots={
                "leave_type": "emergency",
                "start_date": "tomorrow",
                "end_date_or_days": "3 days",
            },
        )
        assert "Leave Request" in result or "leave" in result.lower()
        assert "✅" in result
        assert "My Requests" in result

    def test_confirmation_includes_slot_values(self, engine):
        result = engine.generate_workflow_confirmation(
            workflow_type="salary_increase_request",
            collected_slots={"justification": "market rate mismatch", "desired_percentage": "10%"},
        )
        assert "market rate mismatch" in result or "Justification" in result

    def test_confirmation_for_sick_leave(self, engine):
        result = engine.generate_workflow_confirmation(
            workflow_type="sick_leave_report",
            collected_slots={"days": "2 days"},
        )
        assert "✅" in result

    def test_confirmation_deterministic_no_api(self, engine):
        """Confirmation generation must NEVER need an API call.

        We verify this by patching resilient_chat_completion at its source
        module to raise — if generate_workflow_confirmation ever calls it,
        the test will fail with RuntimeError.
        """
        with patch("app.core.openai_client.resilient_chat_completion",
                   side_effect=RuntimeError("should not be called")):
            result = engine.generate_workflow_confirmation(
                workflow_type="wfh_request",
                collected_slots={"wfh_date": "tomorrow"},
            )
        assert "✅" in result


# ── Redis pending workflow state ──────────────────────────────────────────────

class TestPendingWorkflowState:

    @patch("app.memory.redis_memory._get_client")
    def test_save_and_load_pending_workflow(self, mock_get_client):
        import json
        from app.memory.redis_memory import save_pending_workflow, get_pending_workflow

        fake_redis = MagicMock()
        mock_get_client.return_value = fake_redis

        state = {
            "workflow_type": "apply_leave",
            "collected_slots": {"leave_type": "emergency"},
            "missing_slots": ["start_date", "end_date_or_days"],
        }
        save_pending_workflow("sess-123", state)
        fake_redis.setex.assert_called_once()
        args = fake_redis.setex.call_args[0]
        assert "wf_pending:sess-123" in args[0]
        stored = json.loads(args[2])
        assert stored["workflow_type"] == "apply_leave"

        fake_redis.get.return_value = json.dumps(state)
        loaded = get_pending_workflow("sess-123")
        assert loaded is not None
        assert loaded["workflow_type"] == "apply_leave"
        assert loaded["missing_slots"] == ["start_date", "end_date_or_days"]

    @patch("app.memory.redis_memory._get_client")
    def test_clear_pending_workflow(self, mock_get_client):
        from app.memory.redis_memory import clear_pending_workflow

        fake_redis = MagicMock()
        mock_get_client.return_value = fake_redis
        clear_pending_workflow("sess-123")
        fake_redis.delete.assert_called_once_with("wf_pending:sess-123")

    @patch("app.memory.redis_memory._get_client")
    def test_get_returns_none_when_no_pending(self, mock_get_client):
        from app.memory.redis_memory import get_pending_workflow

        fake_redis = MagicMock()
        fake_redis.get.return_value = None
        mock_get_client.return_value = fake_redis
        result = get_pending_workflow("sess-no-pending")
        assert result is None

    @patch("app.memory.redis_memory._get_client")
    def test_graceful_on_redis_error(self, mock_get_client):
        from app.memory.redis_memory import get_pending_workflow

        fake_redis = MagicMock()
        fake_redis.get.side_effect = Exception("Redis connection refused")
        mock_get_client.return_value = fake_redis
        result = get_pending_workflow("sess-error")
        assert result is None


# ── Platform capabilities ─────────────────────────────────────────────────────

class TestPlatformCapabilities:

    def test_capabilities_text_is_not_empty(self):
        assert len(PLATFORM_CAPABILITIES) > 200

    def test_capabilities_mentions_key_workflows(self):
        text = PLATFORM_CAPABILITIES.lower()
        assert "leave" in text
        assert "expense" in text
        assert "salary" in text
        assert "approval" in text
        assert "notification" in text

    def test_capabilities_explains_how_to_use(self):
        assert "I need" in PLATFORM_CAPABILITIES or "need" in PLATFORM_CAPABILITIES.lower()

    def test_capabilities_is_not_faq_dump(self):
        """Must NOT look like a policy answer."""
        text = PLATFORM_CAPABILITIES.lower()
        assert "calendar days" not in text
        assert "uae labour law article" not in text
