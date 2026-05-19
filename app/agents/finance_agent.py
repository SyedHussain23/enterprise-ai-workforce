from langsmith import traceable

from app.core.constants import DEPT_CONTACTS
from app.core.logger import get_logger
from app.rag.hybrid_retriever import hybrid_search as search_knowledge_base_raw
from app.rag.utils import clean_rag_output
from app.schemas.agent import AgentResponse
from app.tools.automation_engine import generate_report

logger = get_logger(__name__)

EXPENSE_DEADLINE_DAYS = 30
MEAL_LIMIT_CLIENT     = 300
MEAL_LIMIT_INTERNAL   = 150
HOTEL_LIMIT_GRADE5    = 1000
HOTEL_LIMIT_STANDARD  = 600
TRAVEL_APPROVAL_LIMIT = 500
INVOICE_PAYMENT_DAYS  = 30
INVOICE_APPROVAL_AMT  = 10000
BONUS_MIN_RATING      = 3
VAT_RATE              = 5
GRATUITY_RATE_1       = 21
GRATUITY_RATE_2       = 30
SALARY_ADVANCE_MAX_PCT = 50

_SUBMIT_EXPENSE_PHRASES = [
    "submit expense", "claim expense", "expense claim", "submit my expense",
    "file expense", "i want to claim", "submit a claim", "raise expense",
    "expense submission", "reimburse me", "claim reimbursement", "expense report",
    "expense request", "want to be reimbursed", "how do i claim",
]
_REQUEST_ADVANCE_PHRASES = [
    "salary advance", "advance salary", "request advance", "advance payment",
    "pay advance", "need advance", "advance on salary", "advance request",
    "financial assistance", "emergency advance",
]
_GRATUITY_PHRASES = [
    "gratuity", "end of service", "eosb", "end of service benefit",
    "gratuity calculation", "how much gratuity", "final settlement",
    "dews", "workplace savings scheme",
]
_VAT_PHRASES = [
    "vat", "value added tax", "tax invoice", "5% tax", "vat claim",
    "vat registered", "trn", "tax registration", "vat refund",
]
_PAYROLL_PHRASES = [
    "payslip", "salary date", "salary payment", "when is salary", "wps",
    "salary structure", "pay date", "salary credited", "when do i get paid",
    "payroll query", "salary discrepancy", "wrong salary",
]
_BONUS_PHRASES = [
    "bonus", "incentive", "performance bonus", "annual bonus",
    "bonus eligibility", "when is bonus paid", "bonus calculation",
    "commission", "reward", "spot bonus",
]
_TRAVEL_PHRASES = [
    "travel", "business travel", "hotel", "flight", "per diem",
    "travel expense", "accommodation", "subsistence", "travel approval",
    "book travel", "business trip",
]
_PROCUREMENT_PHRASES = [
    "purchase order", "po", "procurement", "vendor", "supplier",
    "buying policy", "supplier registration", "new vendor", "rfq",
]
_BUDGET_PHRASES = [
    "budget", "budget request", "department budget", "capex", "opex",
    "unbudgeted spend", "budget approval", "cost center", "budget allocation",
]
_AUDIT_PHRASES = [
    "audit", "financial audit", "internal audit", "external audit",
    "financial compliance", "financial controls", "anti-fraud",
]
_CORPORATE_TAX_PHRASES = [
    "corporate tax", "income tax", "uae tax", "tax filing",
    "tax compliance", "tax return", "no income tax",
]
_PETTY_CASH_PHRASES = [
    "petty cash", "cash advance", "corporate card", "company card",
    "credit card", "card reconciliation", "card misuse",
]
# Salary increase / raise request — user is asking for a pay rise.
# These are formal compensation requests, not salary policy queries.
_SALARY_INCREASE_PHRASES = [
    "increase my salary", "raise my salary", "rise my salary",
    "salary increase", "salary raise", "pay raise", "pay rise",
    "increment my salary", "want a raise", "need a raise",
    "i deserve a raise", "salary hike", "hike my salary",
    "can you increase my salary", "can you raise my salary",
    "salary increment", "increase pay", "raise pay",
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
                "1. Upload receipts: Finance Portal → Expense Claims → My Claims\n"
                "2. Manager reviews and approves within 48 hours\n"
                "3. Finance processes within 5 business days of approval\n"
                "4. Reimbursement: Next payroll cycle (or mid-month for >AED 1,000)\n\n"
                "**Expense Limits (Without Pre-approval):**\n"
                f"- Client meals: AED {MEAL_LIMIT_CLIENT}/person\n"
                f"- Internal team meals: AED {MEAL_LIMIT_INTERNAL}/person\n"
                "- Taxi/Uber (local): AED 100/trip\n"
                "- Stationery: AED 200/purchase\n\n"
                "**Required Documentation:**\n"
                "- Original VAT invoice (not just payment receipt)\n"
                f"- Submit within {EXPENSE_DEADLINE_DAYS} days of expense date\n\n"
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
                "**Eligibility:**\n"
                "- Minimum 6 months of service\n"
                "- No active advance outstanding\n"
                "- Maximum 1 advance per 6-month period\n\n"
                f"**Amount Limits:** Up to {SALARY_ADVANCE_MAX_PCT}% of monthly basic salary\n"
                "(Up to 100% for genuine medical emergencies with documentation)\n\n"
                "**What happens next:**\n"
                "1. Manager and HR review your request\n"
                "2. Finance approves within 3–5 business days\n"
                "3. Advance transferred to salary account\n"
                "4. Repaid equally over next 3 months from salary\n\n"
                "**No interest charged** — this is an advance of your own salary.\n\n"
                "Submit: Finance Portal → Salary Advance\n"
                f"Questions: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=92,
            source="finance_action",
            keyword_match=True,
            action_triggered=True,
            action_type="request_advance",
            action_payload={"raw_request": query, "department": "Finance"},
        )

    # ── Gratuity Calculation ──────────────────────────────────────────────────
    if any(phrase in q for phrase in _GRATUITY_PHRASES):
        return AgentResponse(
            answer=(
                "**UAE End of Service Gratuity (EOSB)**\n\n"
                "Gratuity is mandatory under UAE Labour Law for all private sector employees.\n\n"
                "**Calculation:**\n"
                f"- Years 1–5: **{GRATUITY_RATE_1} calendar days** of basic salary per year\n"
                f"- After 5 years: **{GRATUITY_RATE_2} calendar days** of basic salary per year\n"
                "- Maximum: 2 years total basic salary\n"
                "- Based on **BASIC SALARY ONLY** (not housing/transport)\n\n"
                "**Example (3 years, AED 10,000 basic):**\n"
                "- Daily rate: AED 10,000 ÷ 30 = AED 333\n"
                f"- Gratuity: {GRATUITY_RATE_1} days × AED 333 × 3 years = **AED 20,979**\n\n"
                "**Resignation Entitlement:**\n"
                "- < 1 year: No gratuity\n"
                "- 1–3 years: One-third of entitlement\n"
                "- 3–5 years: Two-thirds of entitlement\n"
                "- 5+ years: Full entitlement\n\n"
                "**Paid within 14 days of last working day** (UAE law requirement)\n\n"
                "**Calculator:** Finance Portal → Tools → Gratuity Calculator\n"
                f"Queries: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=92,
            source="finance_policy",
            keyword_match=True,
        )

    # ── UAE VAT ───────────────────────────────────────────────────────────────
    if any(phrase in q for phrase in _VAT_PHRASES):
        return AgentResponse(
            answer=(
                "**UAE VAT Information**\n\n"
                f"UAE VAT rate: **{VAT_RATE}%** (introduced January 2018)\n"
                "UAE does **NOT** have personal income tax — VAT is a consumption tax.\n\n"
                "**Impact on Employees:**\n"
                "- Your salary: NOT subject to VAT\n"
                "- Expense claims: Always get a proper VAT invoice (not just receipt)\n"
                "- Without VAT invoice: Company cannot reclaim the 5% — costs more!\n\n"
                "**Valid VAT Invoice Must Include:**\n"
                "- Supplier name and TRN (Tax Registration Number)\n"
                "- Invoice date and number\n"
                "- Description of goods/services\n"
                "- Net amount, VAT amount (5%), total\n\n"
                "**VAT-Exempt Items:** Basic food, healthcare, education, residential rent\n"
                "**Zero-Rated:** Exports, international transport\n\n"
                "**UAE Corporate Tax (from June 2023):**\n"
                "- 9% on business profits above AED 375,000\n"
                "- This is company-level tax, NOT deducted from employee salaries\n\n"
                "Q: Do I need to file a tax return? A: **No** — UAE has no personal income tax\n\n"
                f"Finance queries: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=90,
            source="finance_policy",
            keyword_match=True,
        )

    # ── Payroll Info ──────────────────────────────────────────────────────────
    if any(phrase in q for phrase in _PAYROLL_PHRASES):
        return AgentResponse(
            answer=(
                "**Payroll and Salary Information**\n\n"
                "**Payment Schedule:**\n"
                "- Salary payment: **Last working day of each month**\n"
                "- Via UAE Wage Protection System (WPS) — bank transfer\n"
                "- Payslips available: HR Portal by 25th of each month\n\n"
                "**UAE — No Personal Income Tax:**\n"
                "- You receive 100% of your gross salary\n"
                "- No PAYE or tax deductions in UAE\n\n"
                "**Salary Queries:**\n"
                "- Submit by 20th for same-month correction\n"
                "- After 20th: Corrected in next month\n"
                "- Email: payroll@company.com\n\n"
                "**Possible Deductions:**\n"
                "- Unpaid leave, late arrival (per policy)\n"
                "- Salary advance repayments\n"
                "- GPSSA contributions (UAE Nationals only: 5%)\n\n"
                "**Accessing Payslips:**\n"
                "HR Portal → Payroll → My Payslips → Download PDF\n\n"
                "**Salary Certificate** (for bank/visa/school):\n"
                "HR Portal → My Documents → Salary Certificate (3 business days)\n\n"
                f"Payroll team: payroll@company.com"
            ),
            confidence=90,
            source="finance_policy",
            keyword_match=True,
        )

    # ── Bonus ─────────────────────────────────────────────────────────────────
    if any(phrase in q for phrase in _BONUS_PHRASES):
        return AgentResponse(
            answer=(
                "**Bonus and Incentive Policy**\n\n"
                "**Annual Performance Bonus:**\n"
                "- Paid in February (for previous year's performance)\n"
                f"- Minimum performance rating required: {BONUS_MIN_RATING}/5\n"
                "- Must be employed on 31st December to be eligible\n\n"
                "**Bonus Percentages (of annual basic salary):**\n"
                "- Grade 1–2: 5% | Grade 3–4: 10% | Grade 5: 15%\n"
                "- Grade 6: 20% | Grade 7+: 25–40%\n\n"
                "**Performance Multipliers:**\n"
                "- Rating 5 (Outstanding): 1.5× target bonus\n"
                "- Rating 4 (Exceeds): 1.2× target bonus\n"
                "- Rating 3 (Meets): 1.0× target bonus\n"
                "- Rating 2 (Below): 0.5× target\n"
                "- Rating 1: No bonus\n\n"
                "**Proration:** Mid-year joiners receive pro-rated bonus\n\n"
                "**Spot Bonuses:** AED 500–5,000 for exceptional contributions\n"
                "(Manager nomination + Dept Head approval required)\n\n"
                "**Sales Commission:** Defined in your employment contract\n"
                "Paid monthly, following month after deal closes\n\n"
                f"Queries: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=90,
            source="finance_policy",
            keyword_match=True,
        )

    # ── Travel Policy ─────────────────────────────────────────────────────────
    if any(phrase in q for phrase in _TRAVEL_PHRASES):
        return AgentResponse(
            answer=(
                "**Business Travel Policy**\n\n"
                "**Pre-Travel Approval Required:**\n"
                "Finance Portal → Travel → Travel Request (before booking)\n\n"
                "**Flight Class:**\n"
                "- Flights < 4 hours: Economy\n"
                "- Flights > 6 hours (Grade 5+): Business class\n"
                "- Book 7+ days in advance where possible\n\n"
                "**Hotel Limits:**\n"
                f"- Grade 1–4: Up to AED {HOTEL_LIMIT_STANDARD}/night (4-star)\n"
                f"- Grade 5+: Up to AED {HOTEL_LIMIT_GRADE5}/night (5-star)\n\n"
                "**Daily Subsistence (Per Diem):**\n"
                "- GCC: Meals AED 200/day + Incidentals AED 50/day\n"
                "- International: Meals AED 350/day + Incidentals AED 100/day\n\n"
                "**Client Entertainment:**\n"
                f"- Meals: Up to AED {MEAL_LIMIT_CLIENT}/person (client must be present)\n"
                "- Events > AED 500: Department head pre-approval required\n\n"
                "**Reconciliation:** Submit all receipts within 5 days of return\n"
                "Finance Portal → Travel → Trip Reconciliation\n\n"
                f"Questions: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=90,
            source="finance_policy",
            keyword_match=True,
        )

    # ── Procurement / PO ─────────────────────────────────────────────────────
    if any(phrase in q for phrase in _PROCUREMENT_PHRASES):
        return AgentResponse(
            answer=(
                "**Procurement and Purchase Order Policy**\n\n"
                "**Purchase Thresholds:**\n"
                "- < AED 500: Direct purchase (claim via expense)\n"
                "- AED 500–5,000: Dept head approval, PO required\n"
                "- AED 5,001–25,000: Finance Manager approval, 2+ quotes\n"
                "- AED 25,001–100,000: Finance Director, 3+ quotes (RFQ)\n"
                "- > AED 100,000: CFO + CEO, formal RFP process\n\n"
                "**Raising a Purchase Order:**\n"
                "1. Finance Portal → Procurement → New Purchase Order\n"
                "2. Select approved vendor (or register new vendor first)\n"
                "3. Enter item details, cost center, delivery date\n"
                "4. Attach supplier quote\n"
                "5. Submit for approval — PO number issued on approval\n\n"
                "**New Vendor Registration:**\n"
                "Finance Portal → Vendors → Register New Vendor\n"
                "Required: Trade license, TRN, bank details\n"
                "Processing: 5–7 business days\n\n"
                "⚠️ Never receive goods or services without an approved PO.\n"
                "Retroactive POs require Finance Director approval.\n\n"
                f"Procurement: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=90,
            source="finance_policy",
            keyword_match=True,
        )

    # ── Budget ────────────────────────────────────────────────────────────────
    if any(phrase in q for phrase in _BUDGET_PHRASES):
        return AgentResponse(
            answer=(
                "**Budget Management**\n\n"
                "**Annual Budget Cycle:**\n"
                "- Oct–Nov: Department budget preparation\n"
                "- December: CFO review and consolidation\n"
                "- January: Board approval\n"
                "- 15th January: Budgets communicated to departments\n\n"
                "**Monthly Monitoring:**\n"
                "- Finance sends budget vs actuals by 5th of each month\n"
                "- Variances > 10%: Written explanation required to Finance\n"
                "- Access live budget: Finance Portal → Reports → My Department Budget\n\n"
                "**Requesting Unbudgeted Spend:**\n"
                "Finance Portal → Budget → Unbudgeted Request\n"
                "Include: Amount, description, business justification\n"
                "Approval: Dept Head → Finance Director → CFO (if > AED 50,000)\n\n"
                "**CAPEX vs OPEX:**\n"
                "- CAPEX: Asset > AED 5,000 with useful life > 1 year\n"
                "- OPEX: Recurring costs, subscriptions, maintenance\n"
                "- CAPEX > AED 25,000 requires CFO approval\n\n"
                f"Budget queries: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=88,
            source="finance_policy",
            keyword_match=True,
        )

    # ── Corporate Tax / UAE Tax ───────────────────────────────────────────────
    if any(phrase in q for phrase in _CORPORATE_TAX_PHRASES):
        return AgentResponse(
            answer=(
                "**UAE Tax Information**\n\n"
                "**Personal Income Tax:**\n"
                "✅ UAE has **NO personal income tax** — you keep 100% of your salary\n"
                "No tax returns needed for UAE income\n\n"
                "**For employees with foreign tax obligations (US, UK, etc.):**\n"
                "- You are personally responsible for home country tax filings\n"
                "- Company provides: Salary certificates, employment letters for your tax advisor\n"
                "- Tax residency certificate: HR Portal → My Documents\n\n"
                "**VAT: 5%** (on goods and services — not on salary)\n\n"
                "**UAE Corporate Tax (from June 2023):**\n"
                "- 9% on company profits above AED 375,000\n"
                "- This is company-level — NOT deducted from your salary\n\n"
                "**UAE Banking — No Restrictions:**\n"
                "- Freely transfer money abroad (no capital controls)\n"
                "- Keep financial records for personal tax purposes if needed\n\n"
                "Q: Do I file a tax return in UAE? A: **No** — no personal tax in UAE\n"
                "Q: Is my bonus taxed? A: **Not in UAE** — you receive full gross\n\n"
                f"Finance: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=90,
            source="finance_policy",
            keyword_match=True,
        )

    # ── Petty Cash / Corporate Cards ──────────────────────────────────────────
    if any(phrase in q for phrase in _PETTY_CASH_PHRASES):
        return AgentResponse(
            answer=(
                "**Petty Cash and Corporate Card Policy**\n\n"
                "**Petty Cash:**\n"
                "- For small urgent expenses under AED 100\n"
                "- Contact your department's petty cash custodian\n"
                "- Fill petty cash voucher + attach receipt\n"
                "- Monthly reconciliation mandatory\n\n"
                "**Corporate Credit Card:**\n"
                "- Available to Grade 5+ and approved frequent travelers\n"
                "- Request: Finance Portal → Corporate Card → Card Request\n"
                "- Limit: AED 5,000–25,000 (based on role)\n\n"
                "**Corporate Card Rules:**\n"
                "- Business use ONLY — personal expenses prohibited\n"
                "- Monthly reconciliation by 15th (Finance Portal → Cards → Reconcile)\n"
                "- Upload receipt for EVERY transaction\n"
                "- Lost card: Call bank immediately + notify Finance\n\n"
                "**Personal Expense on Company Card:**\n"
                "- Must be repaid within 5 days of notification\n"
                "- Repeated misuse: Card cancelled + disciplinary action\n\n"
                "**Cash Advance for Travel:**\n"
                "- Finance Portal → Travel → Cash Advance Request\n"
                "- Reconcile within 5 days of return\n\n"
                f"Finance: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=88,
            source="finance_policy",
            keyword_match=True,
        )

    # ── Action: Salary Increase Request ─────────────────────────────────────
    # User is requesting a pay rise. This is a formal request that must go
    # through a manager → HR → Finance approval chain, NOT just info.
    # Must be checked BEFORE the generic salary info fallback.
    if any(phrase in q for phrase in _SALARY_INCREASE_PHRASES):
        return AgentResponse(
            answer=(
                "📋 **Salary Increase Request Logged**\n\n"
                "Your compensation review request has been submitted for manager consideration.\n\n"
                "**Approval Chain:**\n"
                "1. **Manager Review** — your direct manager evaluates the request\n"
                "2. **HR Validation** — HR benchmarks against grade structure and market rates\n"
                "3. **Finance Approval** — Finance Director signs off on budget impact\n"
                "4. **Executive Sign-off** — Required for increases >15% (out-of-cycle)\n\n"
                "**Expected Timeline:** 10–15 business days for a decision\n\n"
                "**What strengthens your case:**\n"
                "- Strong performance rating (4 or 5 in last review)\n"
                "- 12+ months in current role without a review\n"
                "- Market rate evidence (salary benchmark data)\n"
                "- Expanded responsibilities since last review\n\n"
                "⚠️ **Note:** Salary changes take effect from the **1st of the following month** once approved.\n\n"
                "Out-of-cycle increases require Finance Director + CHRO approval.\n"
                f"Payroll queries: payroll@company.com | HR: {DEPT_CONTACTS['HR']}"
            ),
            confidence=90,
            source="finance_action",
            keyword_match=True,
            action_triggered=True,
            action_type="salary_increase_request",
            action_payload={"raw_request": query, "department": "Finance"},
        )

    # ── Salary / Compensation Info ────────────────────────────────────────────
    if any(kw in q for kw in ["salary", "raise", "increment", "payroll", "compensation", "wage", "income"]):
        return AgentResponse(
            answer=(
                "**Salary and Compensation**\n\n"
                "**Salary Structure:**\n"
                "- Basic Salary (40–60% of package) + Housing + Transport + Other Allowances\n"
                "- Basic salary used for: Gratuity, overtime, leave encashment\n\n"
                "**Annual Salary Review:**\n"
                "- Cycle: January–March | Effective: 1st April\n"
                "- Rating 5: 10–20% increase\n"
                "- Rating 4: 7–12% increase\n"
                "- Rating 3: 3–6% increase\n\n"
                "**UAE — No Income Tax:**\n"
                "- You receive 100% of gross package\n"
                "- Salary paid last working day via WPS (bank transfer)\n\n"
                "**Salary Certificate / Payslip:**\n"
                "- HR Portal → Payroll → My Payslips\n"
                "- Salary certificate: HR Portal → My Documents (3 business days)\n\n"
                "**Salary Increase Request:**\n"
                "- Discuss with manager during annual review\n"
                "- Out-of-cycle increases require Finance Director + CHRO approval\n\n"
                f"Payroll: payroll@company.com | HR: {DEPT_CONTACTS['HR']}"
            ),
            confidence=90,
            source="finance_policy",
            keyword_match=True,
        )

    # ── Expense general ───────────────────────────────────────────────────────
    if any(kw in q for kw in ["expense", "reimbursement", "claim", "receipt"]):
        return AgentResponse(
            answer=(
                "**Expense Reimbursement Policy**\n\n"
                "**Eligible Expenses:**\n"
                "- Business meals with clients (VAT invoice required)\n"
                "- Local taxi/Uber for business travel\n"
                "- Approved conference/training fees\n"
                "- Office supplies (urgent, under AED 200)\n\n"
                "**Not Reimbursable:**\n"
                "- Personal meals, commuting, personal items, fines\n"
                "- Expenses without valid VAT invoice\n"
                f"- Expenses older than {EXPENSE_DEADLINE_DAYS} days\n\n"
                "**Limits (No pre-approval needed):**\n"
                f"- Client meal: AED {MEAL_LIMIT_CLIENT}/person\n"
                f"- Internal team meal: AED {MEAL_LIMIT_INTERNAL}/person\n"
                "- Taxi: AED 100/trip | Stationery: AED 200\n\n"
                "**Submission:**\n"
                "Finance Portal → Expense Claims → New Claim\n"
                "Upload VAT invoice → Manager approves → Finance reimburses\n\n"
                "**Reimbursement Timeline:**\n"
                "5–7 business days from Finance approval (next payroll cycle)\n\n"
                f"Finance: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=90,
            source="finance_policy",
            keyword_match=True,
        )

    # ── Bonus and Finance Report ──────────────────────────────────────────────
    if any(kw in q for kw in ["invoice", "payment", "vendor", "supplier", "bill"]):
        return AgentResponse(
            answer=(
                "**Invoice and Vendor Payment Process**\n\n"
                "**For Submitting Supplier Invoices:**\n"
                "Email: accounts.payable@company.com\n"
                "Required: Company name, PO number, TRN, itemized amounts\n\n"
                "**Standard Payment Terms:** Net 30 days from invoice date\n\n"
                "**Payment Approval Thresholds:**\n"
                f"- Up to AED {INVOICE_APPROVAL_AMT:,}: Finance Manager\n"
                "- AED 10,001–50,000: Finance Director\n"
                "- Above AED 50,000: CFO\n\n"
                "**New Vendor Setup:**\n"
                "Finance Portal → Vendors → Register New Vendor\n"
                "Required: Trade license, TRN, bank IBAN\n\n"
                "**PO Requirement:**\n"
                "All purchases above AED 500 require a Purchase Order number on invoice.\n\n"
                "**Query Status of Payment:**\n"
                "Finance Portal → Procurement → My POs → Payment Status\n"
                "Or email: ap@company.com\n\n"
                f"Finance: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=88,
            source="finance_policy",
            keyword_match=True,
        )

    # ── Budget / Forecast ─────────────────────────────────────────────────────
    if any(kw in q for kw in ["budget", "forecast", "allocation", "planning", "capex", "cost center"]):
        return AgentResponse(
            answer=(
                "**Budget and Allocation Process**\n\n"
                "**Annual Budget Cycle:**\n"
                "- Q4 (Oct–Nov): Departments prepare next year's budget\n"
                "- December: Finance consolidates and CFO reviews\n"
                "- January: Board approves; departments notified\n\n"
                "**Budget Management:**\n"
                "- Monthly budget vs actuals sent by Finance (5th of month)\n"
                "- Variances > 10%: Explanation required\n"
                "- Live tracking: Finance Portal → Reports → My Department\n\n"
                "**Requesting Unbudgeted Spend:**\n"
                "Finance Portal → Budget → Unbudgeted Request\n"
                "Approval: Dept Head → Finance Director → CFO\n\n"
                "**CAPEX (Capital Expenditure):**\n"
                "- Items > AED 5,000 with life > 1 year\n"
                "- Finance Portal → CAPEX → New Request\n"
                "- < AED 25,000: Finance Director | > AED 100,000: Board\n\n"
                "**Unspent Budget:** Does not carry forward to next year\n\n"
                f"Finance: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=86,
            source="finance_policy",
            keyword_match=True,
        )

    # ── Expense policy summary (informational — not an approval action) ──────────
    if "expense report" in q or "finance report" in q or "expense summary" in q:
        return AgentResponse(
            answer=(
                "**Expense Policy Summary**\n\n"
                f"- **Submission Deadline:** Within {EXPENSE_DEADLINE_DAYS} days of incurring the expense\n"
                f"- **Client Entertainment:** AED {MEAL_LIMIT_CLIENT}/person (manager approval required)\n"
                f"- **Internal Meals:** AED {MEAL_LIMIT_INTERNAL}/person\n"
                f"- **Hotel (Grade 5+):** AED {HOTEL_LIMIT_GRADE5}/night | Standard: AED {HOTEL_LIMIT_STANDARD}/night\n"
                f"- **Travel Approval:** Required for trips > AED {TRAVEL_APPROVAL_LIMIT}\n"
                f"- **UAE VAT:** {VAT_RATE}% — include VAT invoices for reimbursement\n\n"
                "To submit an expense: Finance Portal → Expense Claims → New Claim\n"
                f"Questions: {DEPT_CONTACTS['Finance']}"
            ),
            confidence=88,
            source="finance_policy",
            keyword_match=True,
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
            answer=(
                f"I couldn't find specific information for your Finance query. "
                f"Please contact the Finance team directly:\n\n"
                f"📧 {DEPT_CONTACTS['Finance']}\n"
                f"🌐 Finance Portal: finance.company.internal\n\n"
                f"Or try asking about: salary, expense claims, gratuity, VAT, "
                f"salary advance, bonus, travel expenses, or procurement."
            ),
            confidence=30,
            source="finance_kb",
        )

    return AgentResponse(
        answer=formatted,
        confidence=rag.get("confidence", 50),
        source=source,
        rag_used=True,
    )
