"""
Conversation Engine — Enterprise AI Workforce Operating System Brain.

DESIGN PRINCIPLE: deterministic-first, LLM-enhanced second.

The core intent classification and slot extraction NEVER depend on an OpenAI
call succeeding. A GPT-4o failure should degrade gracefully to a slightly less
natural response — NOT fall back to the old "FAQ dump" behavior.

Layers:
  1. classify_deterministic()   — pure Python, zero API calls, always works
  2. extract_slots_simple()     — regex-based, zero API calls, always works
  3. generate_clarification()   — tries GPT-4o for natural phrasing; falls back
                                  to a template if unavailable
  4. generate_info_response()   — tries GPT-4o for synthesis; falls back to the
                                  domain agent's raw answer

This means:
  "i need 2 days leave"         → ALWAYS starts leave workflow intake
  "what do you do"              → ALWAYS returns platform capabilities
  "im sick"                     → ALWAYS asks for days
  ... regardless of OpenAI status, Redis status, or any other dependency.
"""
from __future__ import annotations

import json
import re
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


# ── Platform capabilities (SYSTEM intent response) ────────────────────────────

PLATFORM_CAPABILITIES = """\
# 🤖 Enterprise AI Workforce Operating System

I'm not a chatbot or FAQ bot. I'm your company's **AI workforce operator** — \
I execute real enterprise workflows, manage approvals, and coordinate humans on your behalf.

## What I can do for you:

### 📋 HR Operations
- **Apply for leave** — emergency, annual, personal, sick, parental leave
- **Report sick** — log absence and auto-notify your manager immediately
- **Request WFH** — submit and track work-from-home days
- **Maternity / Paternity leave** — guided application with HR coordination
- **File a grievance** — confidential complaint + escalation workflow
- **Request training** — budget approval through manager → HR → Finance
- **Update your profile** — contact info, bank details, emergency contacts

### 💰 Finance Operations
- **Submit expense claims** — receipt-based, manager-approved, auto-reimbursed
- **Request salary advance** — formal advance with Finance approval workflow
- **Request salary increase** — compensation review with full approval chain

### 💻 IT Operations
- **Raise IT support tickets** — hardware, software, network, security issues
- **Request system access** — provisioning with IT Security approval

### 📊 Every Request Gets:
- A **trackable workflow** in your personal dashboard
- **Automatic manager / approver notifications**
- **Full lifecycle** — pending → under review → approved / rejected
- **Audit trail** on every state change

## How to use me:
- *"I need 2 days emergency leave from tomorrow"* → I'll file it right away
- *"I'm sick today"* → I'll notify your manager and log the absence
- *"Increase my salary by 10%"* → I'll start the compensation review
- *"How does gratuity work?"* → I'll explain the policy

What would you like me to do today?
"""


# ── Deterministic SYSTEM intent detection ─────────────────────────────────────

_SYSTEM_PHRASES = (
    "what do you do", "what can you do", "what are you",
    "what is your purpose", "what are your capabilities", "your capabilities",
    "what are your features", "what are your functions",
    "what are your options", "what are your services",
    "what issues can you", "what problems can you",
    "what is your issues", "what are your issues",
    "what can i ask", "what can this do", "how do you work",
    "how can you help", "help me understand what you",
    "what do you handle", "what workflows", "what requests",
    "tell me what you can", "explain what you do",
    "what do you support", "show me what you do",
)


# ── Deterministic ACTION intent — workflow type mapping ───────────────────────

_WORKFLOW_PHRASE_MAP: dict[str, list[str]] = {
    "apply_leave": [
        "i need leave", "i need a leave", "i need annual leave",
        "i need emergency leave", "i need sick leave", "i need personal leave",
        "i need study leave", "i need unpaid leave",
        "i want leave", "i want to take leave", "i'd like to take leave",
        "apply for leave", "apply leave", "request leave", "book leave",
        "take leave", "submit leave", "leave request",
        "need time off", "book time off", "request time off",
        "i need 1 day", "i need 2 days", "i need 3 days",
        "i need 4 days", "i need 5 days", "i need a day off",
        "i need days off", "taking leave",
    ],
    "sick_leave_report": [
        "im sick", "i am sick", "i'm sick", "i am unwell", "i'm unwell",
        "im unwell", "feeling sick", "not feeling well", "sick today",
        "sick tomorrow", "sick leave today", "call in sick",
        "i have a fever", "i have fever", "i am ill", "i'm ill", "im ill",
        "taking sick leave", "absent today", "absent tomorrow",
        "doctor appointment", "going to doctor", "medical appointment",
        "medical leave today", "report sick", "notify hr i am sick",
        "send email to hr", "email hr that i am sick",
    ],
    "salary_increase_request": [
        "increase my salary", "raise my salary", "rise my salary",
        "salary increase", "salary raise", "salary hike", "pay raise",
        "pay rise", "increment my salary", "want a raise", "need a raise",
        "i deserve a raise", "hike my salary", "salary increment",
        "increase pay", "raise pay", "increase my pay",
        "increase salary by", "raise salary by", "hike salary by",
        "increment salary", "compensation review", "compensation increase",
    ],
    "submit_expense": [
        "submit expense", "submit my expense", "claim expense",
        "file expense", "submit a claim", "raise expense",
        "reimburse me", "claim reimbursement", "want to be reimbursed",
        "please submit my expense", "submit my claim",
    ],
    "request_advance": [
        "salary advance", "advance salary", "advance on salary",
        "request advance", "advance payment", "advance request",
        "need advance", "financial advance", "emergency advance",
        "advance my salary",
    ],
    "wfh_request": [
        "work from home", "wfh", "work remotely", "remote work",
        "wfh request", "request wfh", "apply for wfh",
        "work from home tomorrow", "work from home today",
        "working from home",
    ],
    "grievance_report": [
        "file a complaint", "file a grievance", "report harassment",
        "report discrimination", "workplace complaint", "grievance",
        "i want to complain", "i need to complain",
        "hostile environment", "unfair treatment",
    ],
    "training_request": [
        "request training", "apply for training", "training request",
        "enroll in course", "training budget", "learning request",
        "course approval", "certification request",
    ],
    "maternity_leave_request": [
        "i need maternity", "i want maternity", "apply for maternity",
        "maternity leave request", "going on maternity",
        "i need paternity", "i want paternity", "apply for paternity",
        "i am pregnant", "im pregnant", "i'm pregnant",
    ],
    "it_ticket": [
        "my laptop", "my computer", "laptop issue", "computer issue",
        "raise a ticket", "create a ticket", "it ticket", "it issue",
        "system crash", "software issue", "network issue",
        "printer issue", "hardware issue", "it support",
    ],
    "request_access": [
        "need access to", "request access", "give me access",
        "access to system", "system access", "access provisioning",
    ],
    "update_profile": [
        "update my profile", "change my details", "update my information",
        "update my contact", "change my phone", "update emergency contact",
        "edit my profile", "update my bank", "change my iban",
    ],
}


# ── Simple regex slot extraction ──────────────────────────────────────────────

_DAYS_PATTERN  = re.compile(r'\b(\d+)\s*days?\b', re.IGNORECASE)
_WEEKS_PATTERN = re.compile(r'\b(\d+)\s*weeks?\b', re.IGNORECASE)
_PCT_PATTERN   = re.compile(r'\b(\d+(?:\.\d+)?)\s*%', re.IGNORECASE)
_AMT_PATTERN   = re.compile(r'\b(?:aed\s*)?(\d[\d,]*(?:\.\d+)?)\s*(?:aed|dirhams?)?\b', re.IGNORECASE)

_LEAVE_TYPES = {
    "emergency": "emergency", "urgent": "emergency",
    "annual": "annual", "yearly": "annual",
    "sick": "sick", "medical": "sick",
    "personal": "personal", "private": "personal",
    "study": "study", "education": "study",
    "unpaid": "unpaid",
    "parental": "parental", "paternity": "paternity", "maternity": "maternity",
}

_DATE_WORDS = (
    "today", "tomorrow", "yesterday",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "next week", "this week", "next monday", "next tuesday",
    "next wednesday", "next thursday", "next friday",
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)

_EXPENSE_CATEGORIES = (
    "client meal", "team meal", "lunch", "dinner", "breakfast",
    "taxi", "uber", "careem", "transport",
    "stationery", "office supply",
    "training", "conference", "course",
    "accommodation", "hotel",
    "flight", "airfare",
)


def _extract_date(text: str) -> str | None:
    q = text.lower()
    for dw in _DATE_WORDS:
        if dw in q:
            return dw
    # Look for DD/MM or DD-MM-YYYY
    m = re.search(r'\b(\d{1,2}[-/]\d{1,2}(?:[-/]\d{2,4})?)\b', q)
    if m:
        return m.group(1)
    # DD Month (e.g., "15 June")
    m = re.search(
        r'\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*)\b',
        q,
    )
    if m:
        return m.group(1)
    return None


def _extract_days_duration(text: str) -> str | None:
    m = _DAYS_PATTERN.search(text)
    if m:
        n = m.group(1)
        return f"{n} day{'s' if int(n) != 1 else ''}"
    m = _WEEKS_PATTERN.search(text)
    if m:
        n = m.group(1)
        return f"{n} week{'s' if int(n) != 1 else ''}"
    if "half day" in text.lower():
        return "half day"
    if "a day off" in text.lower() or "one day" in text.lower():
        return "1 day"
    return None


def extract_slots_simple(query: str, workflow_type: str) -> dict:
    """
    Zero-API regex-based slot extraction for common patterns.
    Returns a dict of {slot_name: value} for values found in the message.
    Missing slots will have no key (not null).
    """
    q = query.lower()
    slots: dict[str, str] = {}

    if workflow_type == "apply_leave":
        # leave_type
        for kw, ltype in _LEAVE_TYPES.items():
            if kw in q:
                slots["leave_type"] = ltype
                break
        # start_date
        dt = _extract_date(query)
        if dt:
            slots["start_date"] = dt
        # end_date_or_days
        dur = _extract_days_duration(query)
        if dur:
            slots["end_date_or_days"] = dur

    elif workflow_type == "sick_leave_report":
        dur = _extract_days_duration(query)
        if dur:
            slots["days"] = dur
        elif "today" in q or "absent today" in q:
            slots["days"] = "1 day"
        if "certificate" in q or "medical cert" in q or "doctor" in q:
            slots["medical_cert_available"] = "yes"

    elif workflow_type == "salary_increase_request":
        m = _PCT_PATTERN.search(query)
        if m:
            slots["desired_percentage"] = m.group(0)
        # justification is harder to extract, skip for now

    elif workflow_type == "submit_expense":
        m = _AMT_PATTERN.search(query)
        if m:
            slots["amount"] = m.group(0)
        for cat in _EXPENSE_CATEGORIES:
            if cat in q:
                slots["category"] = cat
                break
        dt = _extract_date(query)
        if dt:
            slots["expense_date"] = dt

    elif workflow_type == "request_advance":
        m = _AMT_PATTERN.search(query)
        if m:
            slots["amount"] = m.group(0)

    elif workflow_type == "wfh_request":
        dt = _extract_date(query)
        if dt:
            slots["wfh_date"] = dt
        dur = _extract_days_duration(query)
        if dur:
            slots["wfh_date"] = dur   # treat "3 days WFH" as the date spec

    elif workflow_type in ("it_ticket", "grievance_report", "training_request"):
        # These need free-text descriptions — regex won't help much here
        pass

    return slots


# ── Deterministic intent classifier ──────────────────────────────────────────

def classify_deterministic(
    query: str,
    pending_workflow: dict | None = None,
) -> dict | None:
    """
    Pure Python, zero-API intent classification.

    Returns a classification dict (same shape as classify_and_extract) when
    the intent is clear, or None when genuinely ambiguous (→ caller may try
    GPT-4o for those cases).

    Priority order:
      1. SYSTEM  — capability / meta questions
      2. FOLLOWUP — if there's a pending workflow and the message looks like
                    it's providing missing information
      3. ACTION  — clear first-person action request
      4. INFO    — question phrasing (is_informational_query)
      5. None    — genuinely ambiguous → escalate to LLM
    """
    from app.utils.intent_classifier import is_informational_query, has_personal_action_intent

    q = query.lower().strip()
    q_stripped = q.lstrip(" \"'`(*-")

    # ── 1. SYSTEM intent ──────────────────────────────────────────────────────
    for phrase in _SYSTEM_PHRASES:
        if phrase in q:
            return {
                "intent_type": "SYSTEM",
                "department": "General",
                "workflow_type": None,
                "slots_extracted": {},
                "reasoning": f"SYSTEM: matched '{phrase}'",
            }

    # ── 2. FOLLOWUP — pending workflow + doesn't look like a new ACTION ───────
    if pending_workflow:
        wf_type = pending_workflow.get("workflow_type")
        missing = pending_workflow.get("missing_slots", [])
        if wf_type and missing:
            # Check if ANY of the missing slot values appear to be in this message
            extracted = extract_slots_simple(query, wf_type)
            # Also: if the message is short and doesn't match a new ACTION pattern,
            # it's likely a followup answer
            new_action_detected = any(
                any(phrase in q for phrase in phrases)
                for wt, phrases in _WORKFLOW_PHRASE_MAP.items()
                if wt != wf_type
            )
            # Simple heuristic: if the message is ≤8 words and no new action, treat as FOLLOWUP
            word_count = len(query.split())
            if not new_action_detected and (extracted or word_count <= 8):
                return {
                    "intent_type": "FOLLOWUP",
                    "department": "HR",   # will be overridden by pending_wf dept
                    "workflow_type": wf_type,
                    "slots_extracted": extracted,
                    "reasoning": f"FOLLOWUP: continuing {wf_type}, new_slots={list(extracted.keys())}",
                }

    # ── 3. INFO guard — question phrasing takes priority over ACTION map ─────
    # "How do I apply for leave?" should be INFO, not ACTION.  Run this check
    # before the phrase map so informational questions are never mis-fired as
    # workflow actions even if they contain action-ish words.
    if is_informational_query(query):
        return {
            "intent_type": "INFO",
            "department": "HR",      # planner_agent will refine this
            "workflow_type": None,
            "slots_extracted": {},
            "reasoning": "INFO: question phrasing detected (before ACTION map)",
        }

    # ── 4. ACTION — first-person action phrasing ──────────────────────────────
    for workflow_type, phrases in _WORKFLOW_PHRASE_MAP.items():
        for phrase in phrases:
            if phrase in q:
                slots = extract_slots_simple(query, workflow_type)
                from app.utils.workflow_slots import WORKFLOW_DEFINITIONS
                dept = WORKFLOW_DEFINITIONS.get(workflow_type, {}).get("department", "HR")
                return {
                    "intent_type": "ACTION",
                    "department": dept,
                    "workflow_type": workflow_type,
                    "slots_extracted": slots,
                    "reasoning": f"ACTION: '{phrase}' matched → {workflow_type}",
                }

    # ── 5. Ambiguous — caller may escalate to GPT-4o ─────────────────────────
    return None


# ── Deterministic clarification templates ────────────────────────────────────

def _template_clarification(
    workflow_type: str,
    collected_slots: dict,
    missing_slots: list[str],
) -> str:
    """
    Simple template-based clarification — no API call required.
    Returns a natural-enough question string for common cases.
    """
    from app.utils.workflow_slots import get_workflow_def

    wf_def = get_workflow_def(workflow_type)
    wf_label = wf_def.get("label", workflow_type.replace("_", " ").title())
    slot_prompts = wf_def.get("slot_prompts", {})

    # Build a sentence describing what we already know
    known_parts = [f"{k.replace('_', ' ')}: **{v}**" for k, v in collected_slots.items() if v]
    known_str = ", ".join(known_parts)

    # Ask for the first 2 missing slots
    ask_about = missing_slots[:2]
    questions = [slot_prompts.get(s, s.replace("_", " ")) for s in ask_about]

    prefix = f"Got it" + (f" ({known_str})" if known_str else "") + f"! "
    if len(questions) == 1:
        return prefix + f"To complete your {wf_label}, could you share the {questions[0]}?"
    else:
        return (
            prefix
            + f"To complete your {wf_label}, I need a couple more details: "
            + f"{questions[0]}, and {questions[1]}?"
        )


# ── Main ConversationEngine class ─────────────────────────────────────────────

class ConversationEngine:
    """
    The orchestration brain of the Enterprise AI Workforce OS.

    classify_and_extract()        — deterministic first; GPT-4o for edge cases
    generate_clarification()      — template first; GPT-4o for natural phrasing
    generate_workflow_confirmation() — deterministic (no API needed)
    generate_info_response()      — GPT-4o synthesis; fallback to raw answer
    """

    def classify_and_extract(
        self,
        query: str,
        history: list[dict],
        pending_workflow: dict | None = None,
    ) -> dict:
        """
        Step 1: try deterministic classification (always works, zero API cost).
        Step 2: if ambiguous, try GPT-4o (enhanced, but optional).
        Step 3: if GPT-4o fails too, default to INFO (never false action).
        """
        # Step 1 — deterministic (covers ~90% of cases)
        det = classify_deterministic(query, pending_workflow)
        if det is not None:
            logger.info(
                "engine.deterministic",
                intent=det["intent_type"],
                workflow=det.get("workflow_type"),
                reasoning=det.get("reasoning", "")[:80],
            )
            return det

        # Step 2 — GPT-4o for ambiguous cases
        logger.info("engine.ambiguous_escalating_to_llm", query=query[:60])
        try:
            return self._classify_with_llm(query, history, pending_workflow)
        except Exception as exc:
            logger.warning("engine.llm_classify_failed", error=str(exc))

        # Step 3 — safe INFO fallback
        return {
            "intent_type": "INFO",
            "department": "HR",
            "workflow_type": None,
            "slots_extracted": {},
            "reasoning": "Ambiguous and LLM unavailable — defaulting to INFO",
        }

    def _classify_with_llm(
        self,
        query: str,
        history: list[dict],
        pending_workflow: dict | None,
    ) -> dict:
        """GPT-4o classification for genuinely ambiguous queries."""
        from app.core.config import settings
        from app.core.openai_client import resilient_chat_completion

        _SYSTEM = """\
You are an enterprise AI intent classifier. Classify the employee's message.
Intent types: ACTION, INFO, SYSTEM, APPROVAL, FOLLOWUP.
For ACTION: also identify workflow_type from: apply_leave, sick_leave_report,
salary_increase_request, submit_expense, request_advance, wfh_request,
grievance_report, training_request, maternity_leave_request, it_ticket, request_access.
Return ONLY JSON: {"intent_type":"...", "department":"...", "workflow_type":null or "...",
"slots_extracted":{}, "reasoning":"..."}"""

        messages = [{"role": "system", "content": _SYSTEM}]
        for h in history[-4:]:
            messages.append({"role": h.get("role", "user"), "content": str(h.get("content", ""))[:300]})
        if pending_workflow:
            messages.append({"role": "system", "content":
                f"[Pending workflow: {pending_workflow.get('workflow_type')}, "
                f"missing: {pending_workflow.get('missing_slots', [])}]"
            })
        messages.append({"role": "user", "content": query})

        resp = resilient_chat_completion(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=0,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        result = json.loads(resp.choices[0].message.content)

        # Normalise
        raw_intent = str(result.get("intent_type", "INFO")).upper()
        result["intent_type"] = raw_intent if raw_intent in (
            "ACTION", "INFO", "SYSTEM", "APPROVAL", "FOLLOWUP"
        ) else "INFO"
        if not isinstance(result.get("slots_extracted"), dict):
            result["slots_extracted"] = {}

        logger.info("engine.llm_classified", intent=result["intent_type"])
        return result

    def generate_clarification(
        self,
        workflow_type: str,
        collected_slots: dict,
        missing_slots: list[str],
        original_query: str,
    ) -> str:
        """
        Try GPT-4o for a natural clarification question.
        Falls back to the deterministic template — which is also good.
        """
        # Try LLM first for natural language
        try:
            from app.core.config import settings
            from app.core.openai_client import resilient_chat_completion
            from app.utils.workflow_slots import get_workflow_def

            wf_def = get_workflow_def(workflow_type)
            wf_label = wf_def.get("label", workflow_type.replace("_", " ").title())
            slot_prompts = wf_def.get("slot_prompts", {})
            ask_about = missing_slots[:2]
            slot_descriptions = [slot_prompts.get(s, s.replace("_", " ")) for s in ask_about]

            _SYS = (
                "You are a friendly enterprise HR/Finance/IT assistant collecting information "
                "from an employee to complete a workflow. Ask for missing information naturally "
                "and briefly — max 2 sentences. Acknowledge what you already know. "
                "Do NOT list every slot — ask conversationally."
            )
            user_prompt = (
                f"Workflow: {wf_label}\n"
                f"Already have: {json.dumps(collected_slots) if collected_slots else 'nothing yet'}\n"
                f"Need to ask for: {', '.join(slot_descriptions)}\n"
                f"Employee's message: \"{original_query}\"\n"
                "Generate 1-2 sentence clarification question:"
            )
            resp = resilient_chat_completion(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": _SYS},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.35,
                max_tokens=120,
            )
            return resp.choices[0].message.content.strip()

        except Exception as exc:
            logger.warning("engine.clarification_llm_failed", error=str(exc))

        # Deterministic fallback — still a good question
        return _template_clarification(workflow_type, collected_slots, missing_slots)

    def generate_workflow_confirmation(
        self,
        workflow_type: str,
        collected_slots: dict,
    ) -> str:
        """
        Build the confirmation message shown after all slots collected.
        Deterministic — no API call.
        """
        from app.utils.workflow_slots import get_workflow_def

        wf_def = get_workflow_def(workflow_type)
        wf_label = wf_def.get("label", workflow_type.replace("_", " ").title())
        approvers = wf_def.get("approvers", "your manager")
        sla = wf_def.get("sla", "1–2 business days")

        slot_lines = [
            f"  - **{k.replace('_', ' ').title()}**: {v}"
            for k, v in collected_slots.items()
            if v and str(v).strip()
        ]
        slot_summary = "\n".join(slot_lines) if slot_lines else "  - (details from your message)"

        return (
            f"✅ **{wf_label} Created**\n\n"
            f"Your request has been logged with the following details:\n{slot_summary}\n\n"
            f"**What happens next:**\n"
            f"1. {approvers.capitalize()} will be notified immediately\n"
            f"2. You'll receive a notification once reviewed\n"
            f"3. Track it in **My Requests** on your dashboard\n\n"
            f"⏱ Typical response time: {sla}"
        )

    def generate_info_response(
        self,
        query: str,
        department: str,
        policy_context: str,
        history: list[dict],
    ) -> str:
        """
        LLM synthesis for INFO queries.
        Falls back to the domain agent's raw answer if unavailable.
        """
        try:
            from app.core.config import settings
            from app.core.openai_client import resilient_chat_completion

            _SYS = (
                f"You are an enterprise AI assistant for a UAE/GCC company, "
                f"specializing in {department}. Answer the employee's question "
                "naturally and concisely — like a knowledgeable colleague, "
                "NOT a policy manual. Use Markdown. Answer the SPECIFIC question "
                "asked — do not dump the entire policy. 3-6 sentences or a short "
                "targeted list. At the end, optionally offer to take action for them."
            )
            messages = [{"role": "system", "content": _SYS}]
            for h in history[-4:]:
                messages.append({"role": h.get("role", "user"), "content": str(h.get("content", ""))[:300]})
            messages.append({
                "role": "user",
                "content": f"Question: {query}\n\nPolicy context:\n{policy_context[:2500]}",
            })
            resp = resilient_chat_completion(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0.25,
                max_tokens=450,
            )
            return resp.choices[0].message.content.strip()

        except Exception as exc:
            logger.warning("engine.info_synthesis_failed", error=str(exc))
            return policy_context   # raw domain agent answer — still correct facts


# ── Module-level singleton ────────────────────────────────────────────────────

_engine: ConversationEngine | None = None


def get_engine() -> ConversationEngine:
    global _engine
    if _engine is None:
        _engine = ConversationEngine()
    return _engine
