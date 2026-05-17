import json

from langsmith import traceable
from openai import OpenAI

from app.core.config import settings
from app.core.constants import APPROVAL_KEYWORDS, DEPARTMENT_KEYWORDS
from app.core.logger import get_logger
from app.cost.cost_tracker import track_cost
from app.utils.fuzzy_match import normalize_query
from app.workflows.task_manager import determine_workflow

logger = get_logger(__name__)

_openai_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


_FALLBACK_RESULT = {
    "department": "IT",
    "plan": "Could not classify — routing to default",
    "priority": "normal",
    "requires_approval": False,
    "workflow": "default",
}

# ── UAE/GCC-specific routing examples for the LLM classifier ─────────────────
_SYSTEM_PROMPT = """You are an enterprise AI router for a UAE/GCC company.
Classify each employee request into EXACTLY ONE department: HR, IT, or Finance.

ROUTING RULES:
- HR: Leave, attendance, onboarding, resignation, gratuity (end of service), EOSB, DEWS,
  probation, performance review, appraisal, KPIs, benefits, medical insurance, salary certificate,
  maternity/paternity leave, grievance, harassment, disciplinary, warnings, training, WFH policy,
  Ramadan working hours, promotion, internal transfer, dress code, code of conduct, Emiratization,
  employee wellbeing, EAP, payslip queries (when asking HR not Finance), Emirates ID for HR.
  Arabic: إجازة، راتب (موارد بشرية)، مكافأة نهاية الخدمة، استقالة، توظيف

- Finance: Salary payments (WPS, when salary is credited), expense claims, reimbursements,
  invoices, purchase orders, vendor payments, VAT (5%), corporate tax (9%), UAE tax,
  budget, CAPEX, OPEX, cost centers, financial reports, gratuity calculation (formula & amount),
  salary advance (loan), allowance payments, corporate cards, petty cash, AML, KYC,
  travel expenses, per diem, audit, financial compliance.
  Arabic: راتب (متى يصل)، مصاريف، ميزانية، ضريبة القيمة المضافة

- IT: Password reset, MFA, two-factor authentication, VPN (Cisco AnyConnect), laptop issues,
  software installation, system access, phishing/suspicious emails, malware, cybersecurity,
  device provisioning, BYOD, cloud storage (OneDrive, SharePoint), file backup/recovery,
  email setup, Microsoft Teams, printer issues, IT helpdesk tickets, data breach,
  CrowdStrike, BitLocker, Intune, MDM.
  Arabic: كلمة المرور، الشبكة، الحاسوب

EXAMPLES (query → department):
- "How many annual leave days do I have?" → HR
- "How do I apply for maternity leave?" → HR
- "What is the UAE gratuity formula?" → HR (gratuity eligibility/policy)
- "Calculate my end of service pay" → Finance (gratuity amount calculation)
- "When is my salary credited this month?" → Finance
- "How do I submit an expense claim?" → Finance
- "What is the VAT rate in UAE?" → Finance
- "How do I raise a purchase order?" → Finance
- "My laptop is not starting" → IT
- "I forgot my password" → IT
- "How do I connect to VPN from home?" → IT
- "I received a suspicious email" → IT
- "How do I set up MFA?" → IT
- "I need access to a new system" → IT
- "What is the WFH policy?" → HR
- "كيف أقدم طلب إجازة؟" → HR
- "متى يصل راتبي؟" → Finance
- "كيف أعيد تعيين كلمة المرور؟" → IT

If genuinely ambiguous, prefer IT as the safe default (IT can redirect).
Respond ONLY with valid JSON: {"department": "HR or IT or Finance", "plan": "brief reason (1 sentence)"}"""


@traceable
def planner_agent(user_input: str, history: list, company_id: str = "global") -> dict:
    normalized = normalize_query(user_input)
    q = normalized.lower().strip()

    logger.info("planner.start", user_input=user_input, normalized=normalized)

    if not q or len(q) < 3:
        return _FALLBACK_RESULT

    # ── Fast-path keyword routing (no LLM call) ───────────────────────────────
    department: str | None = None
    plan = ""

    # Score each department by number of keyword matches (most matches wins)
    scores: dict[str, int] = {}
    for dept, keywords in DEPARTMENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in q)
        if score > 0:
            scores[dept] = score

    if scores:
        department = max(scores, key=lambda d: scores[d])
        plan = f"Keyword match ({scores[department]} hits) → routed to {department}"
        logger.info("planner.keyword_routed", department=department, scores=scores)

    # ── Slow-path LLM classification (only when keywords miss or score is tied) ──
    top_scores = sorted(scores.values(), reverse=True)
    tied = len(top_scores) >= 2 and top_scores[0] == top_scores[1]

    if not department or tied:
        try:
            messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
            # Include last 3 conversation turns for context (not more, to stay fast)
            for h in history[-6:]:
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
            messages.append({"role": "user", "content": normalized})

            response = _get_client().chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0,
                max_tokens=80,
                response_format={"type": "json_object"},
            )
            track_cost(response.usage.prompt_tokens, response.usage.completion_tokens, company_id=company_id)

            parsed = json.loads(response.choices[0].message.content)
            raw    = str(parsed.get("department", "IT")).strip().lower()
            department = (
                "HR"      if "hr"      in raw else
                "Finance" if "finance" in raw else
                "IT"
            )
            plan = parsed.get("plan", "LLM classification")
            logger.info("planner.llm_classified", department=department, plan=plan)

        except Exception as exc:
            logger.error("planner.llm_failed", error=str(exc))
            if not department:
                department = "IT"
                plan = "LLM failed — default routing to IT"

    requires_approval = any(kw in q for kw in APPROVAL_KEYWORDS)

    result = {
        "department":       department,
        "plan":             plan,
        "priority":         "high" if requires_approval else "normal",
        "requires_approval": requires_approval,
        "workflow":         determine_workflow(user_input),
    }
    logger.info("planner.result", **result)
    return result
