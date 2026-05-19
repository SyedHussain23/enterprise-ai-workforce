from langsmith import traceable

from app.core.constants import DEPT_CONTACTS
from app.core.logger import get_logger
from app.rag.hybrid_retriever import hybrid_search as search_knowledge_base_raw
from app.rag.utils import clean_rag_output
from app.schemas.agent import AgentResponse
from app.tools.automation_engine import generate_report

logger = get_logger(__name__)

# ── UAE Labour Law constants ───────────────────────────────────────────────────
ANNUAL_LEAVE_BASE     = 21        # days (UAE law, <5 yrs service)
ANNUAL_LEAVE_SENIOR   = 30        # days (UAE law, ≥5 yrs service)
SICK_LEAVE_FULL_PAY   = 15        # days full pay
SICK_LEAVE_HALF_PAY   = 30        # days half pay
SICK_LEAVE_UNPAID     = 45        # days unpaid (total 90 possible)
PATERNITY_DAYS        = 10        # working days
MATERNITY_DAYS        = 60        # calendar days (UAE law)
MATERNITY_COMPANY     = 90        # company enhanced (full pay)
NOTICE_PERIOD_STD     = "30 days"
NOTICE_PERIOD_SENIOR  = "60 days"
PROBATION_MONTHS      = 6
GRATUITY_RATE_1       = 21        # days per year (1–5 yrs)
GRATUITY_RATE_2       = 30        # days per year (>5 yrs)

# ── Intent phrase lists ────────────────────────────────────────────────────────
_APPLY_LEAVE_PHRASES = [
    "apply for leave", "apply leave", "request leave", "book leave",
    "i want to take leave", "i'd like to take leave", "request time off",
    "take leave", "i need leave", "submit leave", "apply for annual leave",
    "apply for sick leave", "i want leave", "need time off", "book time off",
    "submit a leave", "leave request", "plan to take leave",
]
# Leave approval-status / follow-up phrases — user has already applied and
# is asking about the approval status or how to get it approved.
_LEAVE_APPROVAL_PHRASES = [
    "approve my leave", "approve leave", "need it approved", "need my leave approved",
    "already applied", "already submitted leave", "submitted my leave",
    "waiting for approval", "leave pending", "pending leave",
    "my leave not approved", "leave status", "check my leave",
    "when will leave be approved", "follow up on leave", "leave follow up",
]
# Maternity / pregnancy-related phrases
_MATERNITY_PHRASES = [
    "maternity", "maternity leave", "pregnant", "pregnancy", "eighth month",
    "ninth month", "due date", "labor", "labour", "childbirth", "baby",
    "newborn", "nursing", "breastfeeding", "paternity",
]
_UPDATE_PROFILE_PHRASES = [
    "update my profile", "change my details", "update my information",
    "change my contact", "update my address", "change my name", "update contact",
    "change my phone", "update emergency contact", "edit my profile",
]
_GRATUITY_PHRASES = [
    "gratuity", "end of service", "eosb", "end of service benefit",
    "gratuity calculation", "how much gratuity", "gratuity entitlement",
    "dews", "workplace savings",
]
_PROBATION_PHRASES = [
    "probation", "probationary", "trial period", "probation period",
    "probation review", "pass probation", "fail probation", "extend probation",
    "during probation",
]
_PERFORMANCE_PHRASES = [
    "performance review", "appraisal", "kpi", "performance rating",
    "annual review", "performance management", "performance improvement",
    "pip", "mid-year review", "goal setting", "objectives",
]
_BENEFITS_PHRASES = [
    "benefits", "health insurance", "medical insurance", "flight ticket",
    "annual ticket", "housing allowance", "transport allowance", "employee benefits",
    "insurance card", "gym allowance", "education allowance",
]
_GRIEVANCE_PHRASES = [
    "grievance", "complaint", "harassment", "discrimination", "bully",
    "report concern", "workplace issue", "unfair treatment", "hostile",
    "report harassment", "file a complaint",
]
_TRAINING_PHRASES = [
    "training", "learning", "course", "certification", "upskill",
    "development", "learning budget", "study leave", "lms", "workshop",
]
_WFH_PHRASES = [
    "work from home", "wfh", "remote work", "work remotely", "home office",
    "work from home policy", "flexible work", "remote working",
]
_DISCIPLINE_PHRASES = [
    "disciplinary", "warning", "misconduct", "violation", "fired",
    "terminate for cause", "written warning", "verbal warning", "final warning",
]


@traceable
def hr_agent(query: str) -> AgentResponse:
    q = query.lower().strip()

    # ── Maternity / Pregnancy Guidance ────────────────────────────────────────
    # Must be checked BEFORE generic leave policy (it contains "leave").
    if any(phrase in q for phrase in _MATERNITY_PHRASES):
        return AgentResponse(
            answer=(
                "**Maternity & Parental Leave Policy**\n\n"
                f"**Maternity Leave:** {MATERNITY_COMPANY} days at full pay (company enhanced)\n"
                "- Begins up to 30 days before the expected due date\n"
                "- Must notify your manager and HR **at least 4 weeks** before leave starts\n"
                "- Submit a medical certificate confirming expected delivery date\n\n"
                "**Paternity Leave:** 10 working days at full pay\n"
                "- To be taken within 3 months of the child's birth\n\n"
                "**How to notify your manager:**\n"
                "1. Inform your manager verbally as early as possible (8th month is great timing)\n"
                "2. Submit the formal notice via **HR Portal → My Leaves → Maternity Leave**\n"
                "3. Attach your medical certificate (doctor's letter with expected due date)\n"
                "4. HR acknowledges within 2 business days and coordinates with your manager\n\n"
                "**Your job is protected** during maternity leave under UAE Labour Law.\n"
                "Dismissal during maternity leave is prohibited.\n\n"
                f"Questions: {DEPT_CONTACTS['HR']}"
            ),
            confidence=93,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Leave Approval Status / Follow-up ────────────────────────────────────
    # User has ALREADY submitted a leave request and wants it approved or
    # is checking the status.  Do NOT trigger a new leave action — inform
    # about the approval process.
    if any(phrase in q for phrase in _LEAVE_APPROVAL_PHRASES):
        return AgentResponse(
            answer=(
                "**Leave Approval Status**\n\n"
                "Your leave request has been submitted and is **awaiting manager approval**.\n\n"
                "**How leave approval works:**\n"
                "1. Your manager receives an automatic email notification\n"
                "2. They approve or reject via **HR Portal → Team Leave Requests**\n"
                "3. Approval typically takes **1–2 business days**\n"
                "4. You'll receive an email notification once a decision is made\n\n"
                "**Check your request status:**\n"
                "→ HR Portal → My Leaves → My Leave Requests\n\n"
                "**If still pending after 2 business days:**\n"
                "- Follow up directly with your manager\n"
                "- Escalate to HR if needed: hr@company.com | Ext. HR 1000\n\n"
                "⚠️ Note: Only your manager or HR admin can approve leave — "
                "this assistant cannot approve requests on their behalf."
            ),
            confidence=90,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Action: Apply Leave ───────────────────────────────────────────────────
    if any(phrase in q for phrase in _APPLY_LEAVE_PHRASES):
        return AgentResponse(
            answer=(
                "✅ **Leave Request Submitted**\n\n"
                "Your leave application has been initiated successfully.\n\n"
                "**What happens next:**\n"
                "1. Your manager will be notified within minutes\n"
                "2. Approval typically takes 1–2 business days\n"
                "3. You'll receive an email once approved or rejected\n"
                "4. Leave balance updated automatically on approval\n\n"
                "**Leave Entitlements (UAE Labour Law):**\n"
                f"- Annual leave: **{ANNUAL_LEAVE_BASE} days/year** (30 days after 5 years)\n"
                f"- Sick leave: **{SICK_LEAVE_FULL_PAY} days full pay**, {SICK_LEAVE_HALF_PAY} days half pay\n"
                "- Leave accrues from Day 1 of employment\n\n"
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
                "**What you can update yourself (HR Portal → My Profile):**\n"
                "- Contact number and personal email\n"
                "- Emergency contact details\n"
                "- Bank account (IBAN) details\n"
                "- Home address\n"
                "- Marital status and dependents\n\n"
                "**What HR needs to update (requires documentation):**\n"
                "- Name change (legal document required)\n"
                "- Nationality / Emirates ID update\n"
                "- Salary or grade changes\n\n"
                f"HR will process your request within 2 business days.\n"
                f"Contact: {DEPT_CONTACTS['HR']}"
            ),
            confidence=90,
            source="hr_action",
            keyword_match=True,
            action_triggered=True,
            action_type="update_profile",
            action_payload={"raw_request": query, "department": "HR"},
        )

    # ── Gratuity / End of Service ─────────────────────────────────────────────
    if any(phrase in q for phrase in _GRATUITY_PHRASES):
        return AgentResponse(
            answer=(
                "**UAE End of Service Gratuity (EOSB)**\n\n"
                "Gratuity is a mandatory UAE Labour Law benefit for all private sector employees.\n\n"
                "**Calculation Formula:**\n"
                f"- Years 1–5: **{GRATUITY_RATE_1} calendar days** of basic salary per year\n"
                f"- After 5 years: **{GRATUITY_RATE_2} calendar days** of basic salary per year\n"
                "- Maximum cap: 2 years total basic salary\n"
                "- Based on BASIC SALARY only (not housing/transport allowances)\n\n"
                "**Example:** 3 years service, AED 10,000 basic salary:\n"
                "- Daily rate = AED 10,000 / 30 = AED 333\n"
                "- Gratuity = 21 days × AED 333 × 3 years = **AED 20,979**\n\n"
                "**Resignation Entitlement:**\n"
                "- Less than 1 year: No gratuity\n"
                "- 1–3 years: One-third of entitlement\n"
                "- 3–5 years: Two-thirds of entitlement\n"
                "- 5+ years: Full entitlement\n\n"
                "**Calculate yours:** HR Portal → Payroll → Gratuity Calculator\n"
                f"Queries: {DEPT_CONTACTS['HR']}"
            ),
            confidence=92,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Probation Policy ──────────────────────────────────────────────────────
    if any(phrase in q for phrase in _PROBATION_PHRASES):
        return AgentResponse(
            answer=(
                "**Probation Policy**\n\n"
                f"- Standard probation period: **{PROBATION_MONTHS} months** (UAE Labour Law maximum)\n"
                "- May be extended by up to 3 additional months with written notice\n\n"
                "**Notice during probation:**\n"
                "- Employee resigning: 14 days notice (UAE law minimum)\n"
                "- Company terminating: 14 days notice (company policy: 30 days)\n\n"
                "**During probation:**\n"
                "- Sick leave: Permitted after completing 3 months\n"
                "- Annual leave: Accrues but generally not taken until probation complete\n"
                "- Medical insurance: Active from Day 1\n"
                "- Objectives set within first 2 weeks of joining\n\n"
                "**Probation Reviews:**\n"
                "- 30-day check-in: Informal verbal feedback\n"
                "- 90-day: Formal midpoint review with manager\n"
                "- Final review (Day 150–180): Pass / Extend / Unsuccessful decision\n\n"
                "**Successful completion:**\n"
                "- Confirmation letter issued\n"
                "- Full annual leave now accessible\n"
                "- Bonus eligibility activates\n\n"
                f"Questions: {DEPT_CONTACTS['HR']}"
            ),
            confidence=90,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Performance Review ────────────────────────────────────────────────────
    if any(phrase in q for phrase in _PERFORMANCE_PHRASES):
        return AgentResponse(
            answer=(
                "**Annual Performance Review Process**\n\n"
                "**Timeline:**\n"
                "- January–February: Goal setting (SMART objectives)\n"
                "- June–July: Mid-year progress review\n"
                "- November–December: Year-end review\n"
                "- January: Salary letters and promotion decisions\n\n"
                "**Rating Scale (1–5):**\n"
                "- ⭐⭐⭐⭐⭐ 5: Outstanding — 15–20% salary increase\n"
                "- ⭐⭐⭐⭐ 4: Exceeds Expectations — 10–15% increase\n"
                "- ⭐⭐⭐ 3: Meets Expectations — 5–8% increase\n"
                "- ⭐⭐ 2: Below Expectations — 0–3%, improvement plan\n"
                "- ⭐ 1: Unsatisfactory — No increase, PIP initiated\n\n"
                "**How it works:**\n"
                "1. You complete self-assessment on HR Portal\n"
                "2. Manager rates independently\n"
                "3. 1:1 review meeting (minimum 60 minutes)\n"
                "4. Calibration with peer managers ensures fairness\n"
                "5. Final rating communicated in writing\n\n"
                "**Appealing your rating:**\n"
                "Submit appeal to HR within 14 days of notification\n\n"
                "Access: HR Portal → Performance → My Review"
            ),
            confidence=90,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Employee Benefits ─────────────────────────────────────────────────────
    if any(phrase in q for phrase in _BENEFITS_PHRASES):
        return AgentResponse(
            answer=(
                "**Employee Benefits Package**\n\n"
                "**Medical Insurance:**\n"
                "- Group health insurance from Day 1\n"
                "- Coverage: Employee + spouse + up to 3 children\n"
                "- Inpatient: AED 500,000/year | Outpatient: AED 500/visit\n"
                "- Dental, optical, maternity included\n\n"
                "**Financial Benefits:**\n"
                "- Housing allowance: AED 3,000–12,000/month (grade-based)\n"
                "- Transport allowance: AED 1,000–3,500/month\n"
                "- Annual flight ticket to home country (economy)\n"
                "- Education allowance for children (Grade 5+)\n\n"
                "**Other Perks:**\n"
                "- Gym subsidy: AED 300/month reimbursement\n"
                "- LinkedIn Learning, Coursera access\n"
                "- Training budget: AED 5,000–15,000/year\n"
                "- Life insurance: 3× annual basic salary\n\n"
                "**UAE-Specific:**\n"
                "- No income tax on salary\n"
                "- End of Service Gratuity per UAE Labour Law\n"
                "- Prayer room and Ramadan facilities\n\n"
                "Full details: HR Portal → My Benefits"
            ),
            confidence=90,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Grievance / Harassment ────────────────────────────────────────────────
    if any(phrase in q for phrase in _GRIEVANCE_PHRASES):
        return AgentResponse(
            answer=(
                "**Grievance and Complaint Procedure**\n\n"
                "The company has a zero-tolerance policy for harassment and discrimination.\n\n"
                "**How to report:**\n"
                "1. **Informal:** Speak directly with the person (if safe) or your manager\n"
                "2. **Formal:** HR Portal → Employee Relations → Raise Grievance\n"
                "3. **Confidential:** Email hr@company.com directly\n"
                "4. **Anonymous:** ethics@company.com (Ethics Hotline)\n\n"
                "**Timeline:**\n"
                "- HR acknowledges within 2 business days\n"
                "- Investigation completed within 15 business days\n"
                "- Outcome communicated in writing\n"
                "- Appeal available within 10 days of outcome\n\n"
                "**Your protection:**\n"
                "- Full confidentiality maintained\n"
                "- No retaliation permitted (retaliation is a serious offence)\n"
                "- Free counseling via Employee Assistance Program (EAP)\n"
                "- UAE law protects against workplace harassment\n\n"
                "You are not alone. Please reach out — your concerns matter.\n"
                f"Contact: {DEPT_CONTACTS['HR']}"
            ),
            confidence=92,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Training and Development ──────────────────────────────────────────────
    if any(phrase in q for phrase in _TRAINING_PHRASES):
        return AgentResponse(
            answer=(
                "**Training and Development Policy**\n\n"
                "**Annual Training Budget:**\n"
                "- Grade 1–3: AED 5,000/year\n"
                "- Grade 4–5: AED 8,000/year\n"
                "- Grade 6+: AED 15,000/year\n\n"
                "**Mandatory Training (All Employees):**\n"
                "- Information Security Awareness — Annual\n"
                "- Anti-Harassment / Code of Conduct — Annual\n"
                "- Data Privacy Compliance — Annual\n"
                "- Must complete within 30 days of joining\n\n"
                "**Available Resources:**\n"
                "- LinkedIn Learning, Coursera, Udemy for Business (unlimited)\n"
                "- Internal LMS: learning.company.internal\n"
                "- Quarterly internal workshops and lunch & learns\n"
                "- Professional certifications (CIPD, PMP, CFA) — company sponsored\n\n"
                "**How to Request Training:**\n"
                "1. HR Portal → Learning → Request Training\n"
                "2. Add business justification and cost\n"
                "3. Manager approval → HR approves budget\n"
                "4. Finance pays provider directly or reimburses on receipt\n\n"
                "Note: Courses >AED 10,000 have a training bond (12–24 months).\n"
                f"Contact: {DEPT_CONTACTS['HR']}"
            ),
            confidence=90,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Work From Home ────────────────────────────────────────────────────────
    if any(phrase in q for phrase in _WFH_PHRASES):
        return AgentResponse(
            answer=(
                "**Work From Home (WFH) Policy**\n\n"
                "**Eligibility:**\n"
                "- Available after completing probation (6 months)\n"
                "- Role must be suitable for remote work\n\n"
                "**WFH Allowance:**\n"
                "- Up to **2 days/week** (8 days/month max)\n"
                "- Days agreed with manager each Friday for following week\n"
                "- Mondays and Fridays WFH require explicit approval\n\n"
                "**How to Request WFH:**\n"
                "1. Discuss with manager\n"
                "2. HR Portal → Attendance → WFH Request\n"
                "3. Manager approves in system\n\n"
                "**Requirements while WFH:**\n"
                "- VPN connected at all times (mandatory)\n"
                "- Available on Teams 9 AM–6 PM\n"
                "- Camera ON for team meetings\n"
                "- Respond to messages within 30 min during core hours\n\n"
                "**Internet allowance:** AED 150/month for Grade 4+ on regular WFH\n\n"
                "WFH is a privilege — can be revoked if productivity drops.\n"
                f"Contact: {DEPT_CONTACTS['HR']}"
            ),
            confidence=90,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Disciplinary Process ──────────────────────────────────────────────────
    if any(phrase in q for phrase in _DISCIPLINE_PHRASES):
        return AgentResponse(
            answer=(
                "**Disciplinary Procedure**\n\n"
                "The company follows a fair, progressive disciplinary process.\n\n"
                "**Stages:**\n"
                "1. **Verbal Warning:** Minor first offence — on record 6 months\n"
                "2. **Written Warning:** Second offence or moderate breach — 12 months\n"
                "3. **Final Written Warning:** Repeated misconduct — 18 months\n"
                "4. **Termination:** After warnings exhausted or gross misconduct\n\n"
                "**Immediate Termination (UAE Law Article 44 — no notice/gratuity):**\n"
                "- Fraud or impersonation\n"
                "- Physical assault of employer or colleague\n"
                "- Absent without leave for 7+ consecutive days\n"
                "- Disclosure of trade secrets\n"
                "- Drunk or under drug influence at work\n\n"
                "**Your Rights:**\n"
                "- Right to be heard before any decision\n"
                "- Right to bring a colleague to disciplinary meetings\n"
                "- Right to see all evidence against you\n"
                "- Right to appeal within 7 days of decision\n\n"
                f"Contact HR to understand your situation: {DEPT_CONTACTS['HR']}"
            ),
            confidence=88,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Leave Policy Info ─────────────────────────────────────────────────────
    if any(kw in q for kw in ["leave", "vacation", "annual", "sick day", "time off", "holiday entitlement"]):
        return AgentResponse(
            answer=(
                "**Leave Policy (UAE Labour Law)**\n\n"
                "**Annual Leave:**\n"
                f"- First 5 years: **{ANNUAL_LEAVE_BASE} calendar days/year**\n"
                f"- After 5 years: **{ANNUAL_LEAVE_SENIOR} calendar days/year** (UAE law)\n"
                "- Accrues from Day 1 at 1.75 days/month\n"
                "- Can carry forward max 10 days\n\n"
                "**Sick Leave (per year):**\n"
                f"- First {SICK_LEAVE_FULL_PAY} days: Full pay (100%)\n"
                f"- Next {SICK_LEAVE_HALF_PAY} days: Half pay (50%)\n"
                f"- Remaining days: Unpaid (total 90 days/year max)\n"
                "- 4+ consecutive days: Medical certificate required\n\n"
                "**Parental Leave:**\n"
                f"- Maternity (company enhanced): **{MATERNITY_COMPANY} days full pay**\n"
                f"- Paternity: **{PATERNITY_DAYS} working days**\n\n"
                "**Special Leave (not from annual balance):**\n"
                "- Marriage: 3 days | Bereavement: 3–5 days\n"
                "- Hajj: 30 days (once) | UAE public holidays\n\n"
                "Apply: HR Portal → My Leaves → New Request"
            ),
            confidence=90,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Resignation / Notice ──────────────────────────────────────────────────
    if any(kw in q for kw in ["resign", "notice", "quit", "exit", "leaving company", "notice period"]):
        return AgentResponse(
            answer=(
                "**Resignation and Notice Period Policy**\n\n"
                "**Notice Period:**\n"
                f"- Less than 5 years service: **{NOTICE_PERIOD_STD}** notice\n"
                f"- 5+ years service: **{NOTICE_PERIOD_SENIOR}** notice\n"
                "- Senior management (Grade 6+): 90 days notice\n\n"
                "**Resignation Steps:**\n"
                "1. Submit formal resignation letter to manager\n"
                "2. HR acknowledges within 2 business days\n"
                "3. Exit checklist provided (device return, handover, etc.)\n"
                "4. Exit interview scheduled with HR\n"
                "5. Final settlement within 14 days of last day\n\n"
                "**Final Settlement includes:**\n"
                "- Final salary (prorated)\n"
                "- Annual leave encashment (unused balance)\n"
                "- End of Service Gratuity (per UAE law)\n"
                "- Any outstanding reimbursements\n\n"
                "**Visa cancellation:** Company processes within 7 days of last day\n"
                "You have 30 days after visa cancellation to leave UAE or change status.\n\n"
                f"Contact: {DEPT_CONTACTS['HR']}"
            ),
            confidence=90,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Onboarding ────────────────────────────────────────────────────────────
    if any(kw in q for kw in ["onboard", "joining", "new employee", "first day", "start", "day 1", "orientation"]):
        return AgentResponse(
            answer=(
                "**Employee Onboarding Process**\n\n"
                "**Pre-Joining (1 week before):**\n"
                "- Welcome email with joining instructions\n"
                "- IT provisions laptop, email, system access\n"
                "- Manager prepares onboarding schedule\n\n"
                "**Day 1:**\n"
                "- Report to HR reception (Building A, Ground Floor) at 8:00 AM\n"
                "- Bring: Passport, Emirates ID, certificates, 4 photos\n"
                "- Sign employment contract and complete documentation\n"
                "- Receive laptop, access card, and credentials\n"
                "- Office tour (cafeteria, prayer room, emergency exits)\n\n"
                "**Week 1:**\n"
                "- Company overview and values session\n"
                "- Meet team and department heads\n"
                "- HR portal training and benefits enrollment\n"
                "- IT and security policy orientation\n"
                "- Buddy assigned for first 30 days\n\n"
                "**Probation Reviews:** 30-day, 90-day, and final (Day 150–180)\n\n"
                f"Onboarding questions: {DEPT_CONTACTS['HR']}"
            ),
            confidence=90,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Payroll / Salary Info ─────────────────────────────────────────────────
    if any(kw in q for kw in ["payslip", "salary certificate", "payroll", "salary date", "when is salary"]):
        return AgentResponse(
            answer=(
                "**Payroll and Salary Information**\n\n"
                "**Salary Payment:**\n"
                "- Payment date: **Last working day of each month** (UAE WPS)\n"
                "- Currency: AED via bank transfer\n"
                "- UAE has NO personal income tax — full gross received\n\n"
                "**Accessing Payslips:**\n"
                "- HR Portal → Payroll → My Payslips\n"
                "- Available from 25th of each month\n"
                "- Salary certificate (for bank/visa): HR Portal → My Documents\n\n"
                "**Salary Queries:**\n"
                "- Submit by 20th of month for same-month correction\n"
                "- After 20th: Corrected in following month\n"
                "- Email: payroll@company.com\n\n"
                "**Salary Structure:**\n"
                "- Basic Salary + Housing Allowance + Transport Allowance\n"
                "- Basic salary is used for: Gratuity, overtime, leave encashment calculations\n\n"
                f"Contact: {DEPT_CONTACTS['HR']}"
            ),
            confidence=90,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Ramadan Working Hours ─────────────────────────────────────────────────
    if any(kw in q for kw in ["ramadan", "fasting", "iftar", "suhoor"]):
        return AgentResponse(
            answer=(
                "**Ramadan Working Hours**\n\n"
                "As per UAE Labour Law, working hours are reduced during the holy month of Ramadan:\n\n"
                "- **Muslim employees:** 6 hours per day (instead of 9)\n"
                "- **Non-Muslim employees:** 7 hours per day\n\n"
                "**Modified Schedule:**\n"
                "- Typically: 9:00 AM – 3:00 PM or 10:00 AM – 4:00 PM\n"
                "- Exact schedule announced by HR at start of Ramadan\n\n"
                "**Ramadan in the Office:**\n"
                "- Eating, drinking, and smoking in public areas during fasting hours is prohibited\n"
                "- Prayer rooms fully available with proper facilities\n"
                "- Company may organize Iftar events\n"
                "- Dress modestly throughout Ramadan month\n\n"
                "**Prayer Times:**\n"
                "- Company accommodates the 5 daily prayers\n"
                "- Short prayer breaks integrated into working day\n\n"
                f"Contact: {DEPT_CONTACTS['HR']}"
            ),
            confidence=88,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Leave policy summary (informational — NOT an action that needs approval) ──
    if "leave report" in q or "leave policy" in q or "leave summary" in q:
        return AgentResponse(
            answer=(
                "**Leave Policy Summary**\n\n"
                f"- **Annual Leave:** {ANNUAL_LEAVE_BASE} days/year (30 days after 5 years)\n"
                f"- **Sick Leave:** {SICK_LEAVE_FULL_PAY} days full pay → {SICK_LEAVE_HALF_PAY} days half pay → {SICK_LEAVE_UNPAID} days unpaid\n"
                f"- **Maternity Leave:** {MATERNITY_COMPANY} days (company enhanced, full pay)\n"
                f"- **Paternity Leave:** {PATERNITY_DAYS} working days paid\n"
                "- **Public Holidays:** As per UAE government calendar\n\n"
                "To apply for leave: HR Portal → My Leaves → New Request\n"
                f"Questions: {DEPT_CONTACTS['HR']}"
            ),
            confidence=88,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Parental leave info ───────────────────────────────────────────────────
    if any(kw in q for kw in ["paternity", "maternity", "parental", "baby", "pregnancy", "new born", "newborn"]):
        return AgentResponse(
            answer=(
                "**Parental Leave Policy**\n\n"
                f"**Maternity Leave:**\n"
                f"- Company Enhanced: **{MATERNITY_COMPANY} days full pay**\n"
                f"- UAE Law minimum: {MATERNITY_DAYS} days (45 full + 15 half)\n"
                "- Notify HR by end of 4th month of pregnancy\n"
                "- Role protected during and after maternity leave\n"
                "- Breastfeeding breaks: 2×30 min/day for 18 months (paid)\n\n"
                f"**Paternity Leave:** **{PATERNITY_DAYS} working days** paid\n"
                "- Must be taken within 6 months of child's birth\n"
                "- Apply: HR Portal → My Leaves → Paternity Leave\n"
                "- Submit birth certificate within 30 days\n\n"
                "**Return to Work:**\n"
                "- Phased return available (4 weeks at 80% capacity)\n"
                "- Nursing room available at office\n"
                "- Flexible hours first 3 months post-maternity\n\n"
                f"Contact: {DEPT_CONTACTS['HR']}"
            ),
            confidence=90,
            source="hr_policy",
            keyword_match=True,
        )

    # ── Promotion / Career ────────────────────────────────────────────────────
    if any(kw in q for kw in ["promotion", "career", "career growth", "next level", "advance", "career path"]):
        return AgentResponse(
            answer=(
                "**Promotion and Career Development**\n\n"
                "**Promotion Eligibility:**\n"
                "- Minimum 12 months in current role\n"
                "- Performance rating of 4 or 5 in last two reviews\n"
                "- Open position at next level or business case for creation\n\n"
                "**Salary on Promotion:** Minimum 15% increase\n\n"
                "**Career Grade Structure:**\n"
                "- Grade 1–2: Junior/Entry | Grade 3: Senior Contributor\n"
                "- Grade 4: Lead/Team Lead | Grade 5: Manager\n"
                "- Grade 6: Senior Manager | Grade 7: Director | Grade 8: VP\n\n"
                "**Development Resources:**\n"
                "- Individual Development Plan (IDP): Reviewed annually\n"
                "- Training budget: AED 5,000–15,000/year\n"
                "- Mentorship program: Available after 6 months service\n"
                "- Fast-Track Leadership Program for high-potential staff\n\n"
                "**Internal Transfers:**\n"
                "- Eligible after 12 months in current role\n"
                "- HR Portal → Careers → Internal Job Board\n\n"
                f"Career discussions: {DEPT_CONTACTS['HR']}"
            ),
            confidence=88,
            source="hr_policy",
            keyword_match=True,
        )

    # ── RAG fallback ──────────────────────────────────────────────────────────
    rag = search_knowledge_base_raw(query)
    source = rag.get("source") or "hr_kb"

    if source and not any(s in source.lower() for s in ["hr_", "hr1", "hr_policy", "hr_kb"]):
        logger.warning("hr_agent.source_filtered", source=source)
        source = "hr_kb"
        rag["context"] = ""

    formatted = clean_rag_output(rag.get("context", ""), department="HR")

    if not formatted:
        return AgentResponse(
            answer=(
                f"I couldn't find specific information for your HR query. "
                f"Please contact our HR team directly:\n\n"
                f"📧 {DEPT_CONTACTS['HR']}\n"
                f"🌐 HR Portal: hr.company.internal\n\n"
                f"Or try asking more specifically about: leave, gratuity, onboarding, "
                f"performance review, benefits, WFH policy, or resignation."
            ),
            confidence=30,
            source="hr_kb",
        )

    return AgentResponse(
        answer=formatted,
        confidence=rag.get("confidence", 50),
        source=source,
        rag_used=True,
    )
