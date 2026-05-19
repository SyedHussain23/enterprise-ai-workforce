"""
Conversation Engine — Enterprise AI Workforce Operating System Brain.

This replaces the old pattern of:
    keyword match → hardcoded template string

With a proper intelligence layer:
    GPT-4o intent classification → slot extraction → clarification → workflow creation

Architecture:
    User Query
      → classify_and_extract()   ← single GPT-4o call (intent + slots in one shot)
      → If SYSTEM:     return platform capabilities
      → If ACTION:     check collected slots, ask for missing ones (Redis state)
      → If FOLLOWUP:   merge new slots into pending workflow
      → If INFO:       route to domain agent + LLM synthesis

Every single-turn slot collection and multi-turn conversation is handled here.
Domain agents (HR/Finance/IT) are still used for their POLICY KNOWLEDGE, but
they no longer create actions unilaterally — the engine owns that decision.
"""
from __future__ import annotations

import json
from typing import Any

from app.core.config import settings
from app.core.logger import get_logger
from app.core.openai_client import resilient_chat_completion

logger = get_logger(__name__)


# ── Platform capabilities (returned for SYSTEM queries) ───────────────────────

PLATFORM_CAPABILITIES = """\
# 🤖 Enterprise AI Workforce Operating System

I'm not a chatbot or FAQ assistant. I'm your company's **AI workforce operator** — \
I execute real enterprise workflows, manage approvals, and coordinate humans on your behalf.

## What I can do for you:

### 📋 HR Operations
- **Apply for leave** — emergency, annual, personal, study leave
- **Report sick** — auto-notify your manager, log absence
- **Request WFH** — submit and track work-from-home days
- **Maternity / Paternity leave** — guided application with HR coordination
- **File a grievance** — confidential complaint + escalation workflow
- **Request training** — budget approval through manager → HR → Finance
- **Update your profile** — contact info, bank details, emergency contacts

### 💰 Finance Operations
- **Submit expense claims** — receipt-based, manager-approved, auto-reimbursed
- **Request salary advance** — formal advance with Finance approval workflow
- **Request salary increase** — compensation review with full approval chain
- **Request training budget** — Finance sign-off + cost tracking

### 💻 IT Operations
- **Raise IT support tickets** — hardware, software, network, security
- **Request system access** — provisioning with IT Security approval
- **Report security incidents** — phishing, malware, data breach response

### 📊 Every Request Gets:
- A **trackable workflow** entry in your personal dashboard
- **Automatic manager notifications**
- **Full approval lifecycle** — pending → under review → approved/rejected
- **Real-time status updates** in My Requests
- **Audit trail** on every state change
- **Notification** when a decision is made

## How to use me:
Say what you need in plain English:
- *"I need 2 days emergency leave from tomorrow"* → I'll file it immediately
- *"I'm sick today"* → I'll notify your manager and log the absence
- *"Increase my salary by 10%"* → I'll start the compensation review workflow
- *"How does the gratuity formula work?"* → I'll explain the policy

What would you like me to do for you today?
"""


# ── GPT-4o classification prompt ──────────────────────────────────────────────

_CLASSIFICATION_SYSTEM = """\
You are the orchestration brain of an Enterprise AI Workforce Operating System \
for a UAE/GCC company. Your ONLY job is to classify employee messages and extract \
workflow slots from them. You do NOT generate answers — you produce structured JSON.

## Intent Types

ACTION — Employee wants to DO something: apply for leave, report sick, request salary \
increase, submit expense, request advance, request WFH, file grievance, request training, \
update profile, raise IT ticket, request system access.

INFO — Employee wants to KNOW something: policy questions, how something works, \
calculating entitlements, understanding a process. Examples: "what is the leave policy?", \
"how is gratuity calculated?", "what are the expense limits?", "how do I submit a claim?"

SYSTEM — Employee is asking about the system's capabilities or what it can do. \
Examples: "what can you do?", "what do you do?", "what are your features?", \
"what issues can you handle?", "how do you work?", "what are your capabilities?"

APPROVAL — Employee (as a manager or admin) wants to approve or reject a pending request. \
Examples: "approve the leave request", "reject this expense claim".

FOLLOWUP — Employee is continuing/providing information for a workflow already in progress. \
This is ONLY used when there is an explicit pending workflow context provided below.

## Workflow Types and Their Required Slots
- apply_leave: leave_type, start_date, end_date_or_days [optional: reason]
- sick_leave_report: days [optional: medical_cert_available]
- salary_increase_request: justification [optional: desired_percentage, effective_date]
- submit_expense: amount, category, expense_date [optional: description]
- request_advance: amount, reason [optional: repayment_months]
- wfh_request: wfh_date [optional: reason]
- grievance_report: issue_type, description [optional: preferred_resolution]
- training_request: course_name, justification [optional: estimated_cost, provider]
- maternity_leave_request: start_date [optional: expected_duration, medical_cert]
- update_profile: field_to_update, new_value
- it_ticket: issue_type, description [optional: urgency]
- request_access: system_name, access_type [optional: business_justification]

## Slot Extraction Rules
Extract ONLY values explicitly stated in the message. Do NOT infer or assume.
For dates: extract the literal text ("tomorrow", "Monday", "15 June", "next week").
For amounts: extract with currency if stated ("AED 500", "500 dirhams", "500").
A slot should be null if not mentioned in the message.

## Output Format
Return ONLY valid JSON with these exact keys:
{
  "intent_type": "ACTION" | "INFO" | "SYSTEM" | "APPROVAL" | "FOLLOWUP",
  "department": "HR" | "Finance" | "IT" | "General",
  "workflow_type": null or one of the workflow type identifiers above,
  "slots_extracted": {},
  "reasoning": "one sentence explaining the classification"
}
"""


# ── Clarification prompt ──────────────────────────────────────────────────────

_CLARIFICATION_SYSTEM = """\
You are a friendly enterprise AI assistant helping an employee complete a workflow \
request. You need to ask for missing information in a natural, conversational way.

Rules:
- Be warm and helpful, not robotic
- Acknowledge what you already know
- Ask for at most 2 pieces of information at once
- Keep it brief — 2-3 sentences max
- Do NOT use bullet points — keep it conversational
- DO NOT create the workflow yet — just ask the question
"""


# ── Info synthesis prompt ─────────────────────────────────────────────────────

_INFO_SYNTHESIS_SYSTEM = """\
You are an enterprise AI assistant for a UAE/GCC company. An employee asked a policy \
or process question. Answer it naturally and conversationally — like a knowledgeable \
colleague, NOT a policy manual.

Rules:
- Answer the SPECIFIC question asked — do not dump the entire policy
- Use Markdown for structure (bold key points, short lists where helpful)
- Be concise: 3-6 sentences or a short targeted list
- If the information in the context answers the question, use it
- If not, acknowledge you don't have that specific detail and suggest who to contact
- At the end, optionally offer to take action: "Would you like me to file this for you?"
- Do NOT sound scripted, do NOT start with "Certainly!" or "Of course!"
"""


class ConversationEngine:
    """
    The intelligence layer of the Enterprise AI Workforce OS.

    Used by workflow_graph.planner_node to:
    1. Classify intent (ACTION / INFO / SYSTEM / APPROVAL / FOLLOWUP)
    2. Extract slots from the user's message
    3. Generate clarification questions for missing slots
    4. Generate natural LLM-synthesized answers for INFO queries
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def classify_and_extract(
        self,
        query: str,
        history: list[dict],
        pending_workflow: dict | None = None,
    ) -> dict:
        """
        Single GPT-4o call that both classifies intent AND extracts any workflow
        slots present in the message.

        Returns a dict with keys:
            intent_type, department, workflow_type, slots_extracted, reasoning

        Falls back to INFO intent on any error — never creates a false action.
        """
        messages = [{"role": "system", "content": _CLASSIFICATION_SYSTEM}]

        # Context: recent conversation history (last 4 turns)
        for h in history[-8:]:
            messages.append({
                "role": h.get("role", "user"),
                "content": str(h.get("content", ""))[:400],
            })

        # Context: pending workflow (so FOLLOWUP can be detected)
        if pending_workflow:
            ctx = (
                f"\n[PENDING WORKFLOW CONTEXT: The user started a "
                f"'{pending_workflow.get('workflow_type')}' workflow. "
                f"Slots already collected: {json.dumps(pending_workflow.get('collected_slots', {}))}. "
                f"Slots still needed: {pending_workflow.get('missing_slots', [])}. "
                f"If the user's next message provides any of those missing slots, "
                f"classify as FOLLOWUP and extract the new slots.]"
            )
            messages.append({"role": "system", "content": ctx})

        messages.append({"role": "user", "content": query})

        try:
            resp = resilient_chat_completion(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0,
                max_tokens=250,
                response_format={"type": "json_object"},
            )
            result = json.loads(resp.choices[0].message.content)

            # Normalise intent type (defensive — LLM might return lowercase)
            raw_intent = str(result.get("intent_type", "INFO")).upper()
            result["intent_type"] = raw_intent if raw_intent in (
                "ACTION", "INFO", "SYSTEM", "APPROVAL", "FOLLOWUP"
            ) else "INFO"

            # Ensure slots_extracted is always a dict
            if not isinstance(result.get("slots_extracted"), dict):
                result["slots_extracted"] = {}

            logger.info(
                "engine.classified",
                intent=result["intent_type"],
                workflow=result.get("workflow_type"),
                reasoning=result.get("reasoning", "")[:80],
            )
            return result

        except Exception as exc:
            logger.error("engine.classify_failed", error=str(exc))
            # Safe fallback — never create a false action
            return {
                "intent_type": "INFO",
                "department": "HR",
                "workflow_type": None,
                "slots_extracted": {},
                "reasoning": f"Classification failed ({exc}) — defaulting to INFO",
            }

    def generate_clarification(
        self,
        workflow_type: str,
        collected_slots: dict,
        missing_slots: list[str],
        original_query: str,
    ) -> str:
        """
        Generate a natural conversational question asking for the next missing slot(s).
        Falls back to a simple template question if GPT-4o fails.
        """
        from app.utils.workflow_slots import get_workflow_def

        wf_def = get_workflow_def(workflow_type)
        wf_label = wf_def.get("label", workflow_type.replace("_", " ").title())
        slot_prompts = wf_def.get("slot_prompts", {})

        # Ask for at most 2 missing slots in one question
        ask_about = missing_slots[:2]
        slot_descriptions = [
            slot_prompts.get(s, s.replace("_", " "))
            for s in ask_about
        ]

        user_prompt = (
            f"Workflow being started: {wf_label}\n"
            f"Information already provided: {json.dumps(collected_slots) if collected_slots else 'nothing yet'}\n"
            f"I need to ask for: {', '.join(slot_descriptions)}\n"
            f"Employee's original message: \"{original_query}\"\n\n"
            "Generate a short, friendly clarification question:"
        )

        try:
            resp = resilient_chat_completion(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": _CLARIFICATION_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.35,
                max_tokens=120,
            )
            return resp.choices[0].message.content.strip()

        except Exception as exc:
            logger.warning("engine.clarification_failed", error=str(exc))
            # Deterministic fallback
            if ask_about:
                prompt = slot_prompts.get(ask_about[0], ask_about[0].replace("_", " "))
                return (
                    f"I can help you with your {wf_label}! "
                    f"To get started, could you share {prompt}?"
                )
            return f"I can help with your {wf_label}. Could you provide a few more details?"

    def generate_workflow_confirmation(
        self,
        workflow_type: str,
        collected_slots: dict,
    ) -> str:
        """
        Build the ✅ confirmation message shown after all slots are collected
        and the workflow entity has been created.
        """
        from app.utils.workflow_slots import get_workflow_def

        wf_def = get_workflow_def(workflow_type)
        wf_label = wf_def.get("label", workflow_type.replace("_", " ").title())
        approvers = wf_def.get("approvers", "your manager")
        sla = wf_def.get("sla", "1–2 business days")

        # Build slot summary (only non-empty values)
        slot_lines = [
            f"  - **{k.replace('_', ' ').title()}**: {v}"
            for k, v in collected_slots.items()
            if v and str(v).strip()
        ]
        slot_summary = "\n".join(slot_lines) if slot_lines else "  - (details from your message)"

        return (
            f"✅ **{wf_label} Created**\n\n"
            f"Your request has been logged:\n{slot_summary}\n\n"
            f"**What happens next:**\n"
            f"1. {approvers.capitalize()} will be notified immediately\n"
            f"2. You'll receive a notification once reviewed\n"
            f"3. Track it under **My Requests** in your dashboard\n\n"
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
        Use GPT-4o to synthesize a natural, targeted answer for INFO queries.
        The policy_context is the output from the domain agent (their policy text).

        Returns the synthesized answer, or falls back to policy_context if LLM fails.
        """
        dept_note = (
            f"You are answering {department} policy questions for a UAE/GCC company. "
            if department != "General"
            else ""
        )
        system = _INFO_SYNTHESIS_SYSTEM + f"\n{dept_note}"

        messages = [{"role": "system", "content": system}]
        for h in history[-4:]:
            messages.append({"role": h.get("role", "user"), "content": str(h.get("content", ""))[:300]})

        messages.append({
            "role": "user",
            "content": (
                f"Employee question: {query}\n\n"
                f"Available policy context:\n{policy_context[:2500]}"
            ),
        })

        try:
            resp = resilient_chat_completion(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0.25,
                max_tokens=450,
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            logger.warning("engine.info_synthesis_failed", error=str(exc))
            return policy_context  # fall back to the agent's original output


# ── Module-level singleton ────────────────────────────────────────────────────

_engine: ConversationEngine | None = None


def get_engine() -> ConversationEngine:
    global _engine
    if _engine is None:
        _engine = ConversationEngine()
    return _engine
