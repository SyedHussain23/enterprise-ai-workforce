# app/tools/automation_engine.py
from __future__ import annotations

import json
from datetime import datetime, timezone

from app.core.logger import get_logger
from app.tools.file_generator import generate_pdf

logger = get_logger(__name__)

_TIMESTAMP_FMT = "%Y-%m-%d %H:%M UTC"


def _now() -> str:
    return datetime.now(timezone.utc).strftime(_TIMESTAMP_FMT)


# ── Public API ────────────────────────────────────────────────────────────────

def generate_report(title: str, content: str) -> dict:
    """Generate a PDF report and return its path."""
    path = generate_pdf(title, content)
    logger.info("automation.report_generated", title=title, path=path)
    return {"message": f"Report generated: {path}", "file": path}


def generate_leave_summary(
    employee_name: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    days: int,
) -> dict:
    """Generate a leave request confirmation PDF."""
    title   = f"Leave_Request_{employee_name.replace(' ', '_')}"
    content = (
        f"LEAVE REQUEST SUMMARY\n"
        f"Generated: {_now()}\n"
        f"{'─' * 40}\n"
        f"Employee    : {employee_name}\n"
        f"Leave Type  : {leave_type}\n"
        f"From        : {start_date}\n"
        f"To          : {end_date}\n"
        f"Days        : {days}\n"
        f"Status      : Pending Approval\n"
        f"{'─' * 40}\n"
        f"Please submit this form to your line manager for approval.\n"
        f"Leave balance will be updated upon approval.\n"
    )
    path = generate_pdf(title, content)
    logger.info("automation.leave_summary_generated", employee=employee_name, days=days)
    return {"message": "Leave summary generated.", "file": path, "days": days}


def generate_expense_report(
    employee_name: str,
    items: list[dict],
    total_aed: float,
) -> dict:
    """Generate an expense reimbursement PDF."""
    title   = f"Expense_Report_{employee_name.replace(' ', '_')}"
    lines   = [
        "EXPENSE REIMBURSEMENT REPORT",
        f"Generated: {_now()}",
        "─" * 40,
        f"Employee    : {employee_name}",
        "",
        f"{'#':<4} {'Description':<30} {'Amount (AED)':>12}",
        "─" * 48,
    ]
    for idx, item in enumerate(items, 1):
        lines.append(f"{idx:<4} {item.get('description', ''):<30} {item.get('amount', 0):>12.2f}")

    lines += [
        "─" * 48,
        f"{'TOTAL':<34} {total_aed:>12.2f}",
        "",
        "Submit to finance@company.com with receipts attached.",
        "Reimbursement processed within 5 working days.",
    ]
    content = "\n".join(lines)
    path    = generate_pdf(title, content)
    logger.info("automation.expense_report_generated", employee=employee_name, total=total_aed)
    return {"message": "Expense report generated.", "file": path, "total_aed": total_aed}


def generate_onboarding_checklist(
    employee_name: str,
    department: str,
    start_date: str,
    grade: int,
) -> dict:
    """Generate an onboarding checklist PDF for a new hire."""
    title   = f"Onboarding_Checklist_{employee_name.replace(' ', '_')}"
    content = (
        f"EMPLOYEE ONBOARDING CHECKLIST\n"
        f"Generated: {_now()}\n"
        f"{'─' * 40}\n"
        f"Employee    : {employee_name}\n"
        f"Department  : {department}\n"
        f"Grade       : {grade}\n"
        f"Start Date  : {start_date}\n"
        f"{'─' * 40}\n\n"
        f"HR TASKS:\n"
        f"  [ ] Employment contract signed\n"
        f"  [ ] Emirates ID copy collected\n"
        f"  [ ] Visa / work permit arranged\n"
        f"  [ ] Bank account details for WPS\n"
        f"  [ ] Benefits enrollment completed\n"
        f"  [ ] HR Portal account created\n\n"
        f"IT TASKS:\n"
        f"  [ ] Laptop provisioned and imaged\n"
        f"  [ ] Corporate email created (@company.com)\n"
        f"  [ ] Microsoft 365 licence assigned\n"
        f"  [ ] VPN access configured\n"
        f"  [ ] MFA enrolled\n"
        f"  [ ] Role-based access (RBAC) granted\n\n"
        f"FINANCE TASKS:\n"
        f"  [ ] WPS bank details entered in payroll\n"
        f"  [ ] Expense account activated\n"
        f"  [ ] Corporate card request (if Grade 6+)\n\n"
        f"MANAGER TASKS:\n"
        f"  [ ] Buddy assigned\n"
        f"  [ ] 90-day onboarding plan shared\n"
        f"  [ ] First 1-on-1 scheduled (Week 1)\n"
        f"  [ ] Welcome to Our Mission presentation\n"
    )
    path = generate_pdf(title, content)
    logger.info(
        "automation.onboarding_checklist_generated",
        employee=employee_name,
        department=department,
    )
    return {"message": "Onboarding checklist generated.", "file": path}


def generate_it_ticket_summary(
    employee_name: str,
    issue_type: str,
    description: str,
    priority: str = "Medium",
) -> dict:
    """Generate an IT support ticket PDF."""
    title   = f"IT_Ticket_{employee_name.replace(' ', '_')}"
    content = (
        f"IT SUPPORT TICKET\n"
        f"Generated: {_now()}\n"
        f"{'─' * 40}\n"
        f"Raised By   : {employee_name}\n"
        f"Issue Type  : {issue_type}\n"
        f"Priority    : {priority}\n"
        f"Description :\n{description}\n"
        f"{'─' * 40}\n"
        f"Status      : Open\n"
        f"Contact IT Helpdesk: Ext. 1001 | it-support@company.com\n"
        f"SLA: P1=2h, P2=4h, P3=8h, P4=24h\n"
    )
    path = generate_pdf(title, content)
    logger.info("automation.it_ticket_generated", employee=employee_name, issue=issue_type)
    return {"message": "IT ticket summary generated.", "file": path, "priority": priority}
