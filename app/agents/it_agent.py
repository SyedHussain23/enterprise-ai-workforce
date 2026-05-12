from langsmith import traceable

from app.core.constants import DEPT_CONTACTS
from app.core.logger import get_logger
from app.rag.hybrid_retriever import hybrid_search as search_knowledge_base_raw
from app.rag.utils import clean_rag_output
from app.schemas.agent import AgentResponse
from app.tools.automation_engine import generate_report

logger = get_logger(__name__)

PASSWORD_EXPIRY_DAYS = 90
TICKET_RESPONSE_HRS = 4


_CREATE_TICKET_PHRASES = [
    "raise a ticket", "raise ticket", "create a ticket", "create ticket",
    "log a ticket", "log ticket", "log an issue", "report a problem",
    "submit a ticket", "open a ticket", "raise an issue", "i have an issue",
    "report issue", "need support", "request support",
]
_REQUEST_ACCESS_PHRASES = [
    "request access to", "need access to", "grant me access",
    "i need access", "can i get access", "provide access",
]


@traceable
def it_agent(query: str) -> AgentResponse:
    q = query.lower().strip()

    # ── Action: Create IT Ticket ──────────────────────────────────────────────
    if any(phrase in q for phrase in _CREATE_TICKET_PHRASES):
        return AgentResponse(
            answer=(
                "✅ **IT Support Ticket Created**\n\n"
                "Your support ticket has been raised successfully.\n\n"
                "**What happens next:**\n"
                f"1. IT team will respond within **{TICKET_RESPONSE_HRS} hours**\n"
                "2. You'll receive a ticket reference number via email\n"
                "3. Track progress: **IT Portal → My Tickets**\n\n"
                f"Urgent issues: Call IT Helpdesk ext. **1001**"
            ),
            confidence=95,
            source="it_action",
            keyword_match=True,
            action_triggered=True,
            action_type="create_ticket",
            action_payload={"raw_request": query, "department": "IT", "priority": "normal"},
        )

    # ── Action: Request Access ────────────────────────────────────────────────
    if any(phrase in q for phrase in _REQUEST_ACCESS_PHRASES):
        return AgentResponse(
            answer=(
                "✅ **Access Request Submitted**\n\n"
                "Your access request has been logged and sent for approval.\n\n"
                "**What happens next:**\n"
                "1. Your manager must approve the access request\n"
                "2. IT will provision access within 1 business day of approval\n"
                "3. You'll receive credentials via your company email\n\n"
                f"Questions: {DEPT_CONTACTS['IT']}"
            ),
            confidence=92,
            source="it_action",
            keyword_match=True,
            action_triggered=True,
            action_type="request_access",
            action_payload={"raw_request": query, "department": "IT"},
        )

    if any(kw in q for kw in ["password", "reset", "forgot", "credentials"]):
        return AgentResponse(
            answer=(
                "**Password Reset Instructions:**\n\n"
                "1. Go to the company login portal\n"
                "2. Click **'Forgot Password'**\n"
                "3. Enter your company email address\n"
                "4. Follow the reset link sent to your inbox\n\n"
                "**Security Policy:**\n"
                f"- Passwords must be updated every **{PASSWORD_EXPIRY_DAYS} days**\n"
                "- Minimum 12 characters required\n"
                "- Must include: uppercase, number, and symbol\n\n"
                f"Need help? Contact: {DEPT_CONTACTS['IT']}"
            ),
            confidence=92,
            source="it_policy",
            keyword_match=True,
        )

    if any(kw in q for kw in ["vpn", "remote", "work from home", "wfh"]):
        return AgentResponse(
            answer=(
                "**VPN and Remote Access Guide:**\n\n"
                "1. Download **Cisco AnyConnect** from the IT portal\n"
                "2. Use your employee credentials to connect\n"
                "3. VPN is **mandatory** for all remote work\n"
                "4. Disconnect when not in use to save bandwidth\n\n"
                "**Rules:**\n"
                "- Personal devices must be pre-approved by IT\n"
                "- Do not share VPN credentials\n\n"
                f"Connection issues? Contact: {DEPT_CONTACTS['IT']}"
            ),
            confidence=90,
            source="it_policy",
            keyword_match=True,
        )

    if any(kw in q for kw in ["laptop", "device", "computer", "equipment", "hardware"]):
        return AgentResponse(
            answer=(
                "**Device and Equipment Policy:**\n\n"
                "- Company laptop provided on your **joining date**\n"
                f"- Raise IT ticket for issues — response within **{TICKET_RESPONSE_HRS} hours**\n"
                "- IT Helpdesk ext. **1001**\n"
                "- Loaner devices available for critical roles\n\n"
                "**Rules:**\n"
                "- Do not attempt hardware repairs yourself\n"
                "- Report damage or loss to IT immediately\n\n"
                "Submit ticket: IT Portal → 'Device Support'"
            ),
            confidence=90,
            source="it_policy",
            keyword_match=True,
        )

    if any(kw in q for kw in ["email", "account", "access", "login", "provision"]):
        return AgentResponse(
            answer=(
                "**Email and Account Access:**\n\n"
                "- Company email provisioned within **24 hours** of joining\n"
                "- Login credentials sent to your personal email\n"
                "- Change your password on **first login**\n"
                "- MFA (Multi-Factor Authentication) is mandatory\n\n"
                f"Account issues: raise a ticket via IT portal\n"
                f"Contact: {DEPT_CONTACTS['IT']}"
            ),
            confidence=88,
            source="it_policy",
            keyword_match=True,
        )

    if any(kw in q for kw in ["software", "tool", "install", "application", "app"]):
        return AgentResponse(
            answer=(
                "**Software Installation Policy:**\n\n"
                "- Standard tools pre-installed on all company devices\n"
                "- Additional software requires **IT approval**\n"
                "- Personal software installation is **not permitted**\n"
                "- Approved software available via IT Software Portal\n\n"
                "Submit request: IT Portal → 'Software Request'\n"
                "Approval time: **2–3 business days**"
            ),
            confidence=87,
            source="it_policy",
            keyword_match=True,
        )

    if "system report" in q:
        content = (
            f"System Maintenance Report\n"
            f"Servers Updated: 12 | Security Patches: Applied\n"
            f"VPN Status: Active | Uptime: 99.9%\n"
            f"Response Time: {TICKET_RESPONSE_HRS}hr SLA\n"
        )
        result = generate_report("system_report", content)
        return AgentResponse(
            answer=result.get("message", "System report generated."),
            confidence=88,
            source="it_reports",
            keyword_match=True,
            action_triggered=True,
            action_type="generate_report",
        )

    # ── RAG fallback ──────────────────────────────────────────────────────────
    rag = search_knowledge_base_raw(query)
    source = rag.get("source") or "it_kb"

    if source and not any(s in source.lower() for s in ["it_", "it1", "it_policy", "it_kb"]):
        logger.warning("it_agent.source_filtered", source=source)
        source = "it_kb"
        rag["context"] = ""

    formatted = clean_rag_output(rag.get("context", ""), department="IT")

    if not formatted:
        return AgentResponse(
            answer=f"Sorry, I couldn't find relevant IT information. Contact {DEPT_CONTACTS['IT']}",
            confidence=30,
            source="it_kb",
        )

    return AgentResponse(
        answer=formatted,
        confidence=rag.get("confidence", 50),
        source=source,
        rag_used=True,
    )
