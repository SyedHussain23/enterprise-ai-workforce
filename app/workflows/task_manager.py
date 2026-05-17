# app/workflows/task_manager.py
from __future__ import annotations

from app.core.logger import get_logger

logger = get_logger(__name__)

# Workflow definitions: trigger keywords → departments to involve
_WORKFLOWS: list[tuple[list[str], list[str]]] = [
    # ── Multi-department workflows ────────────────────────────────────────────
    (
        ["onboarding", "new hire", "new employee", "joining"],
        ["HR", "IT", "Finance"],
    ),
    (
        ["employee setup", "set up employee", "setup new staff"],
        ["HR", "IT"],
    ),
    (
        ["offboarding", "resignation", "leaving", "exit"],
        ["HR", "IT", "Finance"],
    ),
    (
        ["promotion", "grade change", "salary increase", "band change"],
        ["HR", "Finance"],
    ),
    (
        ["transfer", "internal transfer", "department change", "relocation"],
        ["HR", "IT"],
    ),
    (
        ["audit", "compliance audit", "regulatory review"],
        ["Finance", "HR"],
    ),
    # ── HR-only workflows ─────────────────────────────────────────────────────
    (
        ["annual leave", "leave request", "time off", "vacation request", "pto"],
        ["HR"],
    ),
    (
        ["maternity", "paternity", "parental leave", "special leave"],
        ["HR"],
    ),
    (
        ["sick leave", "medical leave", "sick day"],
        ["HR"],
    ),
    (
        ["performance review", "appraisal", "kpi", "okr", "goal setting"],
        ["HR"],
    ),
    (
        ["grievance", "complaint", "harassment", "misconduct", "disciplinary"],
        ["HR"],
    ),
    (
        ["training request", "learning", "course", "certification", "upskill"],
        ["HR"],
    ),
    (
        ["visa", "work permit", "emirates id", "immigration"],
        ["HR"],
    ),
    (
        ["emiratization", "nafis", "uae national", "quota"],
        ["HR"],
    ),
    (
        ["probation", "probation review", "probation completion"],
        ["HR"],
    ),
    # ── IT-only workflows ─────────────────────────────────────────────────────
    (
        ["password reset", "forgot password", "locked out", "account locked"],
        ["IT"],
    ),
    (
        ["vpn", "remote access", "cisco anyconnect"],
        ["IT"],
    ),
    (
        ["laptop", "device", "equipment request", "hardware"],
        ["IT"],
    ),
    (
        ["software request", "software install", "application access"],
        ["IT"],
    ),
    (
        ["mfa", "2fa", "authenticator", "multi-factor"],
        ["IT"],
    ),
    (
        ["it helpdesk", "helpdesk", "it support", "tech support", "ticket"],
        ["IT"],
    ),
    (
        ["phishing", "cybersecurity", "security incident", "data breach"],
        ["IT"],
    ),
    (
        ["email setup", "microsoft 365", "teams setup", "outlook"],
        ["IT"],
    ),
    (
        ["byod", "bring your own device", "mobile device"],
        ["IT"],
    ),
    # ── Finance-only workflows ────────────────────────────────────────────────
    (
        ["expense reimbursement", "expense claim", "reimbursement"],
        ["Finance"],
    ),
    (
        ["salary advance", "advance request", "loan"],
        ["Finance"],
    ),
    (
        ["payroll", "pay slip", "salary query", "salary issue"],
        ["Finance"],
    ),
    (
        ["invoice", "purchase order", "po", "supplier payment"],
        ["Finance"],
    ),
    (
        ["budget", "budget approval", "budget request"],
        ["Finance"],
    ),
    (
        ["gratuity", "eosb", "end of service"],
        ["Finance"],
    ),
    (
        ["vat", "tax", "corporate tax", "uae tax"],
        ["Finance"],
    ),
    (
        ["travel expense", "business travel", "flight", "hotel booking"],
        ["Finance"],
    ),
    (
        ["petty cash", "cash request", "corporate card"],
        ["Finance"],
    ),
    (
        ["bonus", "incentive", "commission"],
        ["Finance"],
    ),
]


def determine_workflow(user_input: str) -> list[str]:
    """
    Return the list of departments to involve for a given user request.

    Matches the first workflow whose trigger keywords appear in the input.
    Returns [] if no workflow matches (caller falls back to single-agent routing).
    """
    text = user_input.lower()

    for triggers, departments in _WORKFLOWS:
        if any(kw in text for kw in triggers):
            logger.info(
                "task_manager.workflow_matched",
                departments=departments,
                trigger=[kw for kw in triggers if kw in text][0],
            )
            return departments

    logger.debug("task_manager.no_workflow", query=user_input[:80])
    return []
