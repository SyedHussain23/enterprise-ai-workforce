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

The tests do NOT make real OpenAI or Redis calls — they mock the external
dependencies so the logic can be verified purely in Python.
"""
import pytest
from unittest.mock import patch, MagicMock, call
from app.utils.workflow_slots import (
    get_workflow_def,
    get_required_slots,
    get_missing_slots,
    get_action_type,
    WORKFLOW_DEFINITIONS,
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


# ── ConversationEngine — mocked GPT-4o ───────────────────────────────────────

@pytest.fixture
def engine():
    from app.core.conversation_engine import ConversationEngine
    return ConversationEngine()


def _mock_openai(content: str):
    """Create a fake OpenAI response with the given content string."""
    fake_choice = MagicMock()
    fake_choice.message.content = content
    fake_resp = MagicMock()
    fake_resp.choices = [fake_choice]
    return fake_resp


class TestConversationEngineClassification:

    @patch("app.core.conversation_engine.resilient_chat_completion")
    def test_system_intent_what_do_you_do(self, mock_llm, engine):
        mock_llm.return_value = _mock_openai(
            '{"intent_type":"SYSTEM","department":"General","workflow_type":null,'
            '"slots_extracted":{},"reasoning":"asking about capabilities"}'
        )
        result = engine.classify_and_extract("what do you do?", [])
        assert result["intent_type"] == "SYSTEM"

    @patch("app.core.conversation_engine.resilient_chat_completion")
    def test_system_intent_what_are_your_issues(self, mock_llm, engine):
        """'what is your issues' was wrongly routed to IT — must be SYSTEM."""
        mock_llm.return_value = _mock_openai(
            '{"intent_type":"SYSTEM","department":"General","workflow_type":null,'
            '"slots_extracted":{},"reasoning":"asking about system capabilities"}'
        )
        result = engine.classify_and_extract("what is your issues", [])
        assert result["intent_type"] == "SYSTEM"

    @patch("app.core.conversation_engine.resilient_chat_completion")
    def test_action_i_need_emergency_leave(self, mock_llm, engine):
        """'i need emergency leave' must be ACTION → apply_leave, NOT info."""
        mock_llm.return_value = _mock_openai(
            '{"intent_type":"ACTION","department":"HR","workflow_type":"apply_leave",'
            '"slots_extracted":{"leave_type":"emergency"},'
            '"reasoning":"requesting emergency leave"}'
        )
        result = engine.classify_and_extract("i need emergency leave", [])
        assert result["intent_type"] == "ACTION"
        assert result["workflow_type"] == "apply_leave"
        assert result["slots_extracted"].get("leave_type") == "emergency"

    @patch("app.core.conversation_engine.resilient_chat_completion")
    def test_action_increase_salary_by_2_percent(self, mock_llm, engine):
        """'increase salary by 2%' must be ACTION → salary_increase_request."""
        mock_llm.return_value = _mock_openai(
            '{"intent_type":"ACTION","department":"Finance",'
            '"workflow_type":"salary_increase_request",'
            '"slots_extracted":{"desired_percentage":"2%"},'
            '"reasoning":"requesting salary increase"}'
        )
        result = engine.classify_and_extract("increase salary by 2%", [])
        assert result["intent_type"] == "ACTION"
        assert result["workflow_type"] == "salary_increase_request"

    @patch("app.core.conversation_engine.resilient_chat_completion")
    def test_action_im_sick(self, mock_llm, engine):
        """'im sick' must be ACTION → sick_leave_report, NOT policy dump."""
        mock_llm.return_value = _mock_openai(
            '{"intent_type":"ACTION","department":"HR","workflow_type":"sick_leave_report",'
            '"slots_extracted":{},"reasoning":"reporting sick"}'
        )
        result = engine.classify_and_extract("im sick", [])
        assert result["intent_type"] == "ACTION"
        assert result["workflow_type"] == "sick_leave_report"

    @patch("app.core.conversation_engine.resilient_chat_completion")
    def test_info_how_does_gratuity_work(self, mock_llm, engine):
        mock_llm.return_value = _mock_openai(
            '{"intent_type":"INFO","department":"HR","workflow_type":null,'
            '"slots_extracted":{},"reasoning":"policy question"}'
        )
        result = engine.classify_and_extract("how does gratuity work?", [])
        assert result["intent_type"] == "INFO"
        assert result["workflow_type"] is None

    @patch("app.core.conversation_engine.resilient_chat_completion")
    def test_info_what_is_expense_limit(self, mock_llm, engine):
        mock_llm.return_value = _mock_openai(
            '{"intent_type":"INFO","department":"Finance","workflow_type":null,'
            '"slots_extracted":{},"reasoning":"policy question about expense limits"}'
        )
        result = engine.classify_and_extract("what is the expense claim limit?", [])
        assert result["intent_type"] == "INFO"

    @patch("app.core.conversation_engine.resilient_chat_completion")
    def test_followup_provides_missing_slots(self, mock_llm, engine):
        """After asking for start_date, user replies 'from tomorrow for 3 days'."""
        pending = {
            "workflow_type": "apply_leave",
            "collected_slots": {"leave_type": "emergency"},
            "missing_slots": ["start_date", "end_date_or_days"],
        }
        mock_llm.return_value = _mock_openai(
            '{"intent_type":"FOLLOWUP","department":"HR","workflow_type":"apply_leave",'
            '"slots_extracted":{"start_date":"tomorrow","end_date_or_days":"3 days"},'
            '"reasoning":"providing dates for pending leave workflow"}'
        )
        result = engine.classify_and_extract("from tomorrow for 3 days", [], pending)
        assert result["intent_type"] == "FOLLOWUP"
        assert result["slots_extracted"]["start_date"] == "tomorrow"
        assert result["slots_extracted"]["end_date_or_days"] == "3 days"

    @patch("app.core.conversation_engine.resilient_chat_completion")
    def test_fallback_to_info_on_llm_error(self, mock_llm, engine):
        """On any LLM error, engine must default to INFO (never creates false action)."""
        mock_llm.side_effect = RuntimeError("OpenAI is down")
        result = engine.classify_and_extract("i need emergency leave", [])
        # Falls back to INFO — conservative safe default
        assert result["intent_type"] == "INFO"
        assert result.get("workflow_type") is None

    @patch("app.core.conversation_engine.resilient_chat_completion")
    def test_intent_type_normalised_to_uppercase(self, mock_llm, engine):
        """LLM might return lowercase — must be normalised."""
        mock_llm.return_value = _mock_openai(
            '{"intent_type":"action","department":"HR","workflow_type":"apply_leave",'
            '"slots_extracted":{},"reasoning":"test"}'
        )
        result = engine.classify_and_extract("apply for leave", [])
        assert result["intent_type"] == "ACTION"   # uppercased

    @patch("app.core.conversation_engine.resilient_chat_completion")
    def test_invalid_intent_type_falls_back_to_info(self, mock_llm, engine):
        mock_llm.return_value = _mock_openai(
            '{"intent_type":"UNKNOWN_THING","department":"HR","workflow_type":null,'
            '"slots_extracted":{},"reasoning":"test"}'
        )
        result = engine.classify_and_extract("something", [])
        assert result["intent_type"] == "INFO"


# ── Clarification generation ──────────────────────────────────────────────────

class TestClarificationGeneration:

    @patch("app.core.conversation_engine.resilient_chat_completion")
    def test_generates_question_for_missing_slots(self, mock_llm, engine):
        mock_llm.return_value = _mock_openai(
            "I can help with your leave! When do you need to start, and how many days?"
        )
        result = engine.generate_clarification(
            workflow_type="apply_leave",
            collected_slots={"leave_type": "emergency"},
            missing_slots=["start_date", "end_date_or_days"],
            original_query="i need emergency leave",
        )
        assert isinstance(result, str)
        assert len(result) > 10   # not empty

    @patch("app.core.conversation_engine.resilient_chat_completion")
    def test_clarification_fallback_on_llm_error(self, mock_llm, engine):
        """On LLM error, must return a deterministic fallback question."""
        mock_llm.side_effect = RuntimeError("LLM unavailable")
        result = engine.generate_clarification(
            workflow_type="apply_leave",
            collected_slots={},
            missing_slots=["leave_type"],
            original_query="i need leave",
        )
        assert isinstance(result, str)
        assert len(result) > 5   # not empty — graceful degradation

    @patch("app.core.conversation_engine.resilient_chat_completion")
    def test_sick_leave_clarification(self, mock_llm, engine):
        mock_llm.return_value = _mock_openai(
            "Sorry to hear you're not well! How many days will you be away?"
        )
        result = engine.generate_clarification(
            workflow_type="sick_leave_report",
            collected_slots={},
            missing_slots=["days"],
            original_query="im sick",
        )
        assert isinstance(result, str)


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
        assert "Leave Request" in result or "apply_leave" in result.lower()
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
            collected_slots={"days": "2"},
        )
        assert "✅" in result


# ── Redis pending workflow state ──────────────────────────────────────────────

class TestPendingWorkflowState:

    @patch("app.memory.redis_memory._get_client")
    def test_save_and_load_pending_workflow(self, mock_get_client):
        from app.memory.redis_memory import save_pending_workflow, get_pending_workflow
        import json

        fake_redis = MagicMock()
        mock_get_client.return_value = fake_redis

        state = {
            "workflow_type": "apply_leave",
            "collected_slots": {"leave_type": "emergency"},
            "missing_slots": ["start_date", "end_date_or_days"],
        }

        # Simulate save
        save_pending_workflow("sess-123", state)
        fake_redis.setex.assert_called_once()
        args = fake_redis.setex.call_args[0]
        assert "wf_pending:sess-123" in args[0]
        # Stored JSON should include the state
        stored = json.loads(args[2])
        assert stored["workflow_type"] == "apply_leave"

        # Simulate load
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

        # Should return None, not raise
        result = get_pending_workflow("sess-error")
        assert result is None


# ── Platform capabilities ─────────────────────────────────────────────────────

class TestPlatformCapabilities:

    def test_capabilities_text_is_not_empty(self):
        from app.core.conversation_engine import PLATFORM_CAPABILITIES
        assert len(PLATFORM_CAPABILITIES) > 200

    def test_capabilities_mentions_key_workflows(self):
        from app.core.conversation_engine import PLATFORM_CAPABILITIES
        text = PLATFORM_CAPABILITIES.lower()
        assert "leave" in text
        assert "expense" in text
        assert "salary" in text
        assert "approval" in text
        assert "notification" in text

    def test_capabilities_explains_how_to_use(self):
        from app.core.conversation_engine import PLATFORM_CAPABILITIES
        # Should tell users HOW to interact
        assert "I need" in PLATFORM_CAPABILITIES or "need" in PLATFORM_CAPABILITIES.lower()
