from langsmith import traceable

from app.core.constants import DEPT_CONTACTS
from app.core.logger import get_logger
from app.rag.hybrid_retriever import hybrid_search as search_knowledge_base_raw
from app.rag.utils import clean_rag_output
from app.schemas.agent import AgentResponse
from app.tools.automation_engine import generate_report

logger = get_logger(__name__)

# ── Policy constants ──────────────────────────────────────────────────────────
# These will move to tenant-level DB config in the admin panel (Stage 2).
# For now, a single named constant block is cleaner than magic numbers.
ANNUAL_LEAVE = 21
SICK_LEAVE = 12
PATERNITY_DAYS = 10
MATERNITY_DAYS = 90
NOTICE_PERIOD = "30 days"


_APPLY_LEAVE_PHRASES = [
    "apply for leave", "apply leave", "request leave", "book leave",
    "i want to take leave", "i'd like to take leave", "request time off",
    "take leave", "i need leave", "submit leave", "apply for annual leave",
    "apply for sick leave", "i want leave",
]
_UPDATE_PROFILE_PHRASES = [
    "update my profile", "change my details", "update my information",
    "change my contact", "update my address", "change my name",
]


@traceable
def hr_agent(query: str) -> AgentResponse:
    q = query.lower().strip()

    # ── Action: Apply Leave ───────────────────────────────────────────────────
    if any(phrase in q for phrase in _APPLY_LEAVE_PHRASES):
        return AgentResponse(
            answer=(
                "✅ **Leave Request Submitted**\n\n"
                "Your leave application has been initiated successfully.\n\n"
                "**What happens next:**\n"
                "1. Your manager will be notified within minutes\n"
                "2. Approval typically takes 1–2 business days\n"
                "3. You'll receive an email once approved or rejected\n\n"
                "Track your request: **HR Portal → My Leave Requests**"
            ),
            confidence=95,
            source="hr_action",
            keyword_match=True,
            action_triggered=True,
            action_type="apply_leave",
            action_payload={"raw_request": query, "department": "HR"},
        )

    # ── Action: Update Profile ────────────────────────────────────────────────
    if any(phrase in q for phrase in _UPDATE_PROFILE_PHRASES):
        return AgentResponse(
            answer=(
                "✅ **Profile Update Request Submitted**\n\n"
                "Your profile update request has been logged.\n\n"
                f"HR will review and process within 2 business days.\n"
                f"For urgent changes, contact: {DEPT_CONTACTS['HR']}"
            ),
            confidence=90,
            source="hr_action",
            keyword_match=True,
            action_triggered=True,
            action_type="update_profile",
            action_payload={"raw_request": query, "department": "HR"},
        )

    if "leave report" in q:
        content = (
            f"Employee Leave Report\n"
            f"Employee: Sarah Smith | Department: HR\n"
            f"Annual Leave: {ANNUAL_LEAVE} days | Sick Leave: {SICK_LEAVE} days\n"
        )
        result = generate_report("leave_report", content)
        return AgentResponse(
            answer=result.get("message", "Leave report generated."),
            confidence=88,
            source="hr_reports",
            keyword_match=True,
            action_triggered=True,
            action_type="generate_report",
        )

    if any(kw in q for kw in ["leave", "vacation", "annual", "sick day", "time off"]):
        return AgentResponse(
            answer=(
                "**Leave Policy:**\n\n"
                f"- Annual Leave: **{ANNUAL_LEAVE} days** per year\n"
                f"- Sick Leave: **{SICK_LEAVE} days** per year\n"
                f"- Paternity Leave: **{PATERNITY_DAYS} days**\n"
                f"- Maternity Leave: **{MATERNITY_DAYS} days**\n\n"
                "**Rules:**\n"
                "- Manager approval required for all leave\n"
                "- Submit requests at least 3 days in advance\n"
                "- Apply via: HR Portal → Leave Requests"
            ),
            confidence=90,
            source="hr_policy",
            keyword_match=True,
        )

    if any(kw in q for kw in ["paternity", "maternity", "parental", "baby"]):
        return AgentResponse(
            answer=(
                "**Parental Leave Policy:**\n\n"
                f"- Paternity Leave: **{PATERNITY_DAYS} days**\n"
                f"- Maternity Leave: **{MATERNITY_DAYS} days**\n\n"
                "Submit at least 4 weeks in advance.\n"
                f"Contact: {DEPT_CONTACTS['HR']}"
            ),
            confidence=88,
            source="hr_policy",
            keyword_match=True,
        )

    if any(kw in q for kw in ["onboard", "joining", "new employee", "first day", "start"]):
        return AgentResponse(
            answer=(
                "**Onboarding Process:**\n\n"
                "1. Complete HR documentation on Day 1\n"
                "2. IT provisions device and system access\n"
                "3. Attend company orientation session\n"
                "4. Meet your reporting manager and team\n"
                "5. 30-day onboarding plan assigned\n\n"
                f"Contact: {DEPT_CONTACTS['HR']}"
            ),
            confidence=88,
            source="hr_policy",
            keyword_match=True,
        )

    if any(kw in q for kw in ["resign", "notice", "quit", "exit", "leaving"]):
        return AgentResponse(
            answer=(
                "**Resignation Process:**\n\n"
                "1. Submit formal resignation letter to your manager\n"
                f"2. Notice period: **{NOTICE_PERIOD}**\n"
                "3. HR initiates exit checklist\n"
                "4. Return all company assets on last working day\n\n"
                "HR Portal → 'Exit Process' for full details."
            ),
            confidence=87,
            source="hr_policy",
            keyword_match=True,
        )

    # ── RAG fallback ──────────────────────────────────────────────────────────
    rag = search_knowledge_base_raw(query)
    source = rag.get("source") or "hr_kb"

    # Filter results from wrong departments
    if source and not any(s in source.lower() for s in ["hr_", "hr1", "hr_policy", "hr_kb"]):
        logger.warning("hr_agent.source_filtered", source=source)
        source = "hr_kb"
        rag["context"] = ""

    formatted = clean_rag_output(rag.get("context", ""), department="HR")

    if not formatted:
        return AgentResponse(
            answer=f"Sorry, I couldn't find relevant HR information. Please contact {DEPT_CONTACTS['HR']}",
            confidence=30,
            source="hr_kb",
        )

    return AgentResponse(
        answer=formatted,
        confidence=rag.get("confidence", 50),
        source=source,
        rag_used=True,
    )
