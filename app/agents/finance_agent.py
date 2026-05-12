from langsmith import traceable

from app.core.constants import DEPT_CONTACTS
from app.core.logger import get_logger
from app.rag.hybrid_retriever import hybrid_search as search_knowledge_base_raw
from app.rag.utils import clean_rag_output
from app.schemas.agent import AgentResponse
from app.tools.automation_engine import generate_report

logger = get_logger(__name__)

EXPENSE_DEADLINE_DAYS = 30
MEAL_LIMIT = 50
HOTEL_LIMIT = 200
TRAVEL_APPROVAL_LIMIT = 500
INVOICE_PAYMENT_DAYS = 30
INVOICE_APPROVAL_AMT = 1000
BONUS_MIN_RATING = 3


_SUBMIT_EXPENSE_PHRASES = [
    "submit expense", "claim expense", "expense claim", "submit my expense",
    "file expense", "i want to claim", "submit a claim", "raise expense",
    "expense submission", "reimburse me", "claim reimbursement",
]
_REQUEST_ADVANCE_PHRASES = [
    "salary advance", "advance salary", "request advance", "advance payment",
    "pay advance", "need advance",
]


@traceable
def finance_agent(query: str) -> AgentResponse:
    q = query.lower().strip()

    # ── Action: Submit Expense ────────────────────────────────────────────────
    if any(phrase in q for phrase in _SUBMIT_EXPENSE_PHRASES):
        return AgentResponse(
            answer=(
                "✅ **Expense Claim Submitted**\n\n"
                "Your expense claim has been initiated successfully.\n\n"
                "**What happens next:**\n"
                "1. Attach your receipts in: **Finance Portal → Expense Claims**\n"
                "2. Your manager will review and approve within 2 business days\n"
                "3. Approved claims are processed in the next payroll cycle\n\n"
                f"**Reminder:** Submit within {EXPENSE_DEADLINE_DAYS} days of expense date.\n"
                f"Questions: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=95,
            source="finance_action",
            keyword_match=True,
            action_triggered=True,
            action_type="submit_expense",
            action_payload={"raw_request": query, "department": "Finance"},
        )

    # ── Action: Request Advance ───────────────────────────────────────────────
    if any(phrase in q for phrase in _REQUEST_ADVANCE_PHRASES):
        return AgentResponse(
            answer=(
                "✅ **Salary Advance Request Submitted**\n\n"
                "Your advance request has been logged for Finance review.\n\n"
                "**What happens next:**\n"
                "1. Finance team will review eligibility within 2 business days\n"
                "2. HR manager approval required for advances over 50% of monthly salary\n"
                "3. Approved advances reflected in next payslip\n\n"
                f"Questions: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=90,
            source="finance_action",
            keyword_match=True,
            action_triggered=True,
            action_type="request_advance",
            action_payload={"raw_request": query, "department": "Finance"},
        )

    if any(kw in q for kw in ["salary", "raise", "increment", "payroll", "compensation"]):
        return AgentResponse(
            answer=(
                "**Salary Increase Process:**\n\n"
                "1. Annual performance review must be completed\n"
                "2. Direct manager submits recommendation\n"
                "3. HR validates against compensation bands\n"
                "4. Finance approves and processes adjustment\n\n"
                "**Timeline:** 2–4 weeks after submission\n\n"
                "**Rules:**\n"
                f"- Performance rating of {BONUS_MIN_RATING}+ required\n"
                "- Only one review per year\n\n"
                "Submit via: HR Portal → 'Compensation Requests'"
            ),
            confidence=90,
            source="finance_policy",
            keyword_match=True,
        )

    if any(kw in q for kw in ["expense", "reimbursement", "claim", "receipt"]):
        return AgentResponse(
            answer=(
                "**Expense Reimbursement Policy:**\n\n"
                f"- Submit receipts within **{EXPENSE_DEADLINE_DAYS} days** of expense\n"
                f"- Travel over **${TRAVEL_APPROVAL_LIMIT}** requires pre-approval\n"
                f"- Meal allowance: up to **${MEAL_LIMIT}/day**\n"
                f"- Hotel: up to **${HOTEL_LIMIT}/night**\n"
                "- Manager approval required for all claims\n\n"
                "**Rules:**\n"
                "- Original receipts must be attached\n"
                "- Personal expenses are not reimbursable\n\n"
                "Submit via: Finance Portal → 'Expense Claims'\n"
                f"Queries: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=90,
            source="finance_policy",
            keyword_match=True,
        )

    if any(kw in q for kw in ["bonus", "incentive", "reward", "payout"]):
        return AgentResponse(
            answer=(
                "**Bonus and Incentive Policy:**\n\n"
                "- Bonuses processed **annually** in Q1\n"
                "- Based on individual + company performance\n"
                "- Manager nomination required\n"
                f"- Minimum performance rating: **{BONUS_MIN_RATING}/5**\n"
                "- Finance and HR must both approve\n\n"
                "**Rules:**\n"
                "- Must have completed full year of service\n"
                "- Prorated for mid-year joiners\n\n"
                f"Queries: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=88,
            source="finance_policy",
            keyword_match=True,
        )

    if any(kw in q for kw in ["invoice", "payment", "vendor", "supplier", "bill"]):
        return AgentResponse(
            answer=(
                "**Invoice and Payment Process:**\n\n"
                f"- Submit invoices to: {DEPT_CONTACTS['Finance']}\n"
                f"- Payment terms: **Net {INVOICE_PAYMENT_DAYS} days** from invoice date\n"
                f"- Amounts over **${INVOICE_APPROVAL_AMT}** require manager approval\n"
                "- Finance reviews within **5 business days**\n\n"
                "**Rules:**\n"
                "- Invoice must include PO number\n"
                "- GST/VAT details mandatory\n\n"
                "Submit via: Finance Portal → 'Invoice Submission'"
            ),
            confidence=87,
            source="finance_policy",
            keyword_match=True,
        )

    if any(kw in q for kw in ["budget", "forecast", "allocation", "planning"]):
        return AgentResponse(
            answer=(
                "**Budget and Allocation Process:**\n\n"
                "- Annual budgets set in **Q4** for following year\n"
                "- Department heads submit budget proposals\n"
                "- Finance reviews and approves allocations\n"
                "- Mid-year adjustments require **CFO approval**\n\n"
                "**Rules:**\n"
                "- All budget requests must include business justification\n"
                "- Unspent budget does not carry forward\n\n"
                f"Contact: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=86,
            source="finance_policy",
            keyword_match=True,
        )

    if "expense report" in q:
        content = (
            f"Expense Report Summary\n"
            f"Travel: $250 | Meals: $80 | Hotel: $400\n"
            f"Total: $730 | Status: Pending Approval\n"
            f"Deadline: Submit within {EXPENSE_DEADLINE_DAYS} days of expense date\n"
        )
        result = generate_report("expense_report", content)
        return AgentResponse(
            answer=result.get("message", "Expense report generated."),
            confidence=88,
            source="finance_reports",
            keyword_match=True,
            action_triggered=True,
            action_type="generate_report",
        )

    # ── RAG fallback ──────────────────────────────────────────────────────────
    rag = search_knowledge_base_raw(query)
    source = rag.get("source") or "finance_kb"

    if source and not any(s in source.lower() for s in ["finance_", "fin_", "finance_policy", "finance_kb"]):
        logger.warning("finance_agent.source_filtered", source=source)
        source = "finance_kb"
        rag["context"] = ""

    formatted = clean_rag_output(rag.get("context", ""), department="Finance")

    if not formatted:
        return AgentResponse(
            answer=f"Sorry, I couldn't find relevant finance information. Contact {DEPT_CONTACTS['Finance']}",
            confidence=30,
            source="finance_kb",
        )

    return AgentResponse(
        answer=formatted,
        confidence=rag.get("confidence", 50),
        source=source,
        rag_used=True,
    )
