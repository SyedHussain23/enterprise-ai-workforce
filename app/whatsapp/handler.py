"""
WhatsApp message handler.

Processes inbound messages and runs them through the AI workflow.
Runs synchronously (called from the webhook route in a thread pool).
"""
import uuid

from app.core.logger import get_logger
from app.utils.guardrails import get_guardrail_response
from app.whatsapp.client import mark_read, send_text

logger = get_logger(__name__)

# Simple in-memory session map for WhatsApp: phone → session_id
# In production this would be in Redis keyed per phone number.
_sessions: dict[str, str] = {}

MAX_RESPONSE_LENGTH = 1500   # WhatsApp renders long messages poorly


def _truncate(text: str, max_len: int = MAX_RESPONSE_LENGTH) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "…"


def _strip_markdown(text: str) -> str:
    """Remove markdown that doesn't render in WhatsApp (headers, bold syntax)."""
    import re
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)   # **bold** → *bold* (WhatsApp bold)
    text = re.sub(r"#{1,6}\s+", "", text)             # remove headers
    return text.strip()


def handle_whatsapp_message(from_number: str, message_id: str, text: str) -> None:
    """
    Process one inbound WhatsApp message end-to-end.

    Called from the webhook route. Runs the workflow synchronously.
    """
    logger.info("whatsapp.message_received", from_number=from_number, text=text[:80])
    mark_read(message_id)

    # Session per phone number
    if from_number not in _sessions:
        _sessions[from_number] = str(uuid.uuid4())
    session_id = _sessions[from_number]

    # Guardrail check
    guard = get_guardrail_response(text)
    if guard:
        reply = guard.get("answer", "Sorry, I can't help with that.")
        send_text(from_number, _truncate(_strip_markdown(reply)))
        return

    # Run workflow
    try:
        from app.workflows.workflow_graph import build_workflow

        # Reuse compiled workflow (cached at module level to avoid rebuild per message)
        workflow = _get_workflow()
        result = workflow.invoke({
            "session_id": session_id,
            "user_input": text,
            "request_id": str(uuid.uuid4()),
            "company_id": None,   # WhatsApp channel uses global company for now
            "user_id": from_number,
        })
        answer = (result.get("answer") or "Sorry, I couldn't find an answer.").strip()
    except Exception as exc:
        logger.error("whatsapp.workflow_failed", error=str(exc))
        answer = "⚠️ Something went wrong. Please try again later."

    send_text(from_number, _truncate(_strip_markdown(answer)))


_compiled_workflow = None


def _get_workflow():
    global _compiled_workflow
    if _compiled_workflow is None:
        from app.workflows.workflow_graph import build_workflow
        _compiled_workflow = build_workflow()
    return _compiled_workflow
