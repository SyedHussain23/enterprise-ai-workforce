"""
Human-in-the-loop action approval endpoints.

GET  /actions/pending          — list pending actions (admin)
GET  /actions/mine             — list my submitted actions (authenticated user)
POST /actions/{id}/approve     — approve an action (admin)
POST /actions/{id}/reject      — reject an action (admin)
DELETE /session/{id}/memory    — clear chat memory for a session
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.core.logger import get_logger
from app.db.repositories import ActionRepository, AuditLogRepository, UserRepository
from app.memory.redis_memory import clear_session
from app.schemas.api import ActionApprovalRequest

router = APIRouter(tags=["actions"])
logger = get_logger(__name__)


# ── Pending actions (admin) ───────────────────────────────────────────────────

@router.get("/actions/pending")
async def get_pending_actions(
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    company_id_str = user.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")

    repo    = ActionRepository(db)
    actions = await repo.get_pending(uuid.UUID(company_id_str))

    # Resolve usernames in one batch
    user_repo  = UserRepository(db)
    user_cache: dict[str, str] = {}
    for a in actions:
        if a.user_id:
            key = str(a.user_id)
            if key not in user_cache:
                u = await user_repo.get_by_id(a.user_id)
                user_cache[key] = u.username if u else "Unknown"

    return [
        {
            "id":           str(a.id),
            "action_type":  a.action_type,
            "department":   a.department,
            "status":       a.status,
            "payload":      a.payload,
            "requested_by": user_cache.get(str(a.user_id), "Unknown") if a.user_id else "System",
            "notes":        a.notes,
            "created_at":   a.created_at.isoformat(),
        }
        for a in actions
    ]


# ── My actions (authenticated user) ──────────────────────────────────────────

@router.get("/actions/mine")
async def get_my_actions(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_repo = UserRepository(db)
    db_user   = await user_repo.get_by_username(user.get("sub", ""))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    repo    = ActionRepository(db)
    actions = await repo.get_by_user(db_user.id)
    return [
        {
            "id":          str(a.id),
            "action_type": a.action_type,
            "department":  a.department,
            "status":      a.status,
            "payload":     a.payload,
            "created_at":  a.created_at.isoformat(),
        }
        for a in actions
    ]


# ── Action execution helper ───────────────────────────────────────────────────

def _execute_approved_action(action_type: str, payload: dict) -> dict | None:
    """Execute the real-world side effect for an approved action."""
    from app.tools.automation_engine import (
        generate_leave_summary,
        generate_it_ticket_summary,
        generate_expense_report,
        generate_report,
    )
    try:
        if action_type == "apply_leave":
            return generate_leave_summary(
                employee_name=payload.get("username", "Employee"),
                leave_type=payload.get("leave_type", "Annual Leave"),
                start_date=payload.get("start_date", "TBD"),
                end_date=payload.get("end_date", "TBD"),
                days=int(payload.get("days", 1)),
            )
        if action_type == "create_ticket":
            return generate_it_ticket_summary(
                employee_name=payload.get("username", "Employee"),
                issue_type=payload.get("issue_type", "General IT Issue"),
                description=payload.get("raw_request", ""),
                priority=payload.get("priority", "Medium"),
            )
        if action_type == "submit_expense":
            items = payload.get("items", [{"description": "Expense", "amount": 0}])
            total = sum(float(i.get("amount", 0)) for i in items)
            return generate_expense_report(
                employee_name=payload.get("username", "Employee"),
                items=items,
                total_aed=total,
            )
        if action_type in ("generate_report", "query_payslip", "request_certificate"):
            return generate_report(
                title=f"{action_type.replace('_', ' ').title()}",
                content=payload.get("raw_request", ""),
            )
        return None
    except Exception as exc:
        logger.error("action_execute_failed", action_type=action_type, error=str(exc))
        return None


# ── Approve ───────────────────────────────────────────────────────────────────

@router.post("/actions/{action_id}/approve")
async def approve_action(
    action_id: str,
    body: ActionApprovalRequest,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    company_id_str = user.get("company_id")
    user_repo  = UserRepository(db)
    db_user    = await user_repo.get_by_username(user.get("sub", ""))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    repo   = ActionRepository(db)
    action = await repo.approve(uuid.UUID(action_id), db_user.id, body.notes)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    exec_result = _execute_approved_action(action.action_type, action.payload or {})
    if exec_result:
        await repo.complete(uuid.UUID(action_id), exec_result)

    audit = AuditLogRepository(db)
    await audit.log(
        "action_approved",
        company_id=uuid.UUID(company_id_str) if company_id_str else None,
        user_id=db_user.id,
        entity_type="action",
        entity_id=action.id,
        payload={
            "action_type": action.action_type,
            "notes": body.notes,
            "executed": exec_result is not None,
        },
    )
    await db.commit()
    return {
        "status":           "approved",
        "action_id":        action_id,
        "executed":         exec_result is not None,
        "execution_result": exec_result,
    }


# ── Reject ────────────────────────────────────────────────────────────────────

@router.post("/actions/{action_id}/reject")
async def reject_action(
    action_id: str,
    body: ActionApprovalRequest,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    company_id_str = user.get("company_id")
    user_repo = UserRepository(db)
    db_user   = await user_repo.get_by_username(user.get("sub", ""))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    repo   = ActionRepository(db)
    action = await repo.reject(uuid.UUID(action_id), db_user.id, body.notes)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    audit = AuditLogRepository(db)
    await audit.log(
        "action_rejected",
        company_id=uuid.UUID(company_id_str) if company_id_str else None,
        user_id=db_user.id,
        entity_type="action",
        entity_id=action.id,
        payload={"action_type": action.action_type, "notes": body.notes},
    )
    await db.commit()
    return {"status": "rejected", "action_id": action_id}


# ── Session memory ────────────────────────────────────────────────────────────

@router.delete("/session/{session_id}/memory")
async def clear_memory(session_id: str, user: dict = Depends(get_current_user)):
    clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}
