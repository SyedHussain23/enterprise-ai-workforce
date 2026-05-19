"""
Request lifecycle endpoints — the workflow-engine surface of the platform.

A "request" is the user-facing concept that maps 1:1 to an Action row.
We expose it under /requests/* (instead of only /actions/*) because the
language users see in dashboards is "requests" and "approvals", not
"actions" (which is internal vocabulary).

Endpoints:
  GET    /requests/mine              — paginated list of my own requests
  GET    /requests/{id}              — full detail + comments + timeline
  GET    /requests/{id}/timeline     — audit history of the request
  GET    /requests/{id}/comments     — comment thread
  POST   /requests/{id}/comments     — add a comment (requester or approver)
  POST   /requests/{id}/cancel       — requester cancels their own request

Approver actions still live in /actions/{id}/approve and /reject.
"""
import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.dependencies import get_current_user
from app.core.logger import get_logger
from app.db.models.action import Action
from app.db.models.audit_log import AuditLog
from app.db.repositories import (
    ActionCommentRepository,
    ActionRepository,
    AuditLogRepository,
    NotificationRepository,
    UserRepository,
)

router = APIRouter(tags=["requests"])
logger = get_logger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _serialize_action(a: Action, *, requester_name: str | None = None) -> dict[str, Any]:
    return {
        "id":               str(a.id),
        "action_type":      a.action_type,
        "department":       a.department,
        "status":           a.status,
        "requires_approval": a.requires_approval,
        "payload":          a.payload or {},
        "notes":            a.notes,
        "requested_by":     requester_name,
        "created_at":       a.created_at.isoformat(),
        "approved_at":      a.approved_at.isoformat() if a.approved_at else None,
    }


async def _resolve_user_or_404(db: AsyncSession, jwt_sub: str):
    repo = UserRepository(db)
    db_user = await repo.get_by_username(jwt_sub)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


# ── My requests ──────────────────────────────────────────────────────────────

@router.get("/requests/mine")
async def list_my_requests(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None, description="Filter by status"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    db_user = await _resolve_user_or_404(db, user.get("sub", ""))
    repo = ActionRepository(db)
    rows, total = await repo.list_for_user_paginated(
        user_id=db_user.id, limit=limit, offset=offset, status=status,
    )
    return {
        "total":    total,
        "limit":    limit,
        "offset":   offset,
        "requests": [_serialize_action(a, requester_name=db_user.username) for a in rows],
    }


# ── Request detail ───────────────────────────────────────────────────────────

@router.get("/requests/{request_id}")
async def get_request(
    request_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full detail of a single request — owner, manager, or admin only."""
    try:
        rid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request id")

    repo = ActionRepository(db)
    action = await repo.get_by_id(rid)
    if not action:
        raise HTTPException(status_code=404, detail="Request not found")

    db_user = await _resolve_user_or_404(db, user.get("sub", ""))

    # Authorisation: requester themselves, OR manager/admin of same company.
    role = (user.get("role") or "").lower()
    is_owner = action.user_id == db_user.id
    is_approver_in_tenant = (
        role in ("manager", "admin")
        and str(action.company_id) == user.get("company_id")
    )
    if not (is_owner or is_approver_in_tenant):
        raise HTTPException(status_code=403, detail="You don't have access to this request")

    # Requester display name
    requester_name = None
    if action.user_id:
        u_repo = UserRepository(db)
        requester = await u_repo.get_by_id(action.user_id)
        requester_name = requester.username if requester else None

    # Comments
    c_repo = ActionCommentRepository(db)
    comments = await c_repo.list_for_action(action_id=rid)

    # Timeline = audit entries scoped to this entity
    stmt = (
        select(AuditLog)
        .where(AuditLog.entity_type == "action", AuditLog.entity_id == rid)
        .order_by(AuditLog.created_at.asc())
    )
    timeline_rows = (await db.execute(stmt)).scalars().all()

    return {
        "request": _serialize_action(action, requester_name=requester_name),
        "comments": [
            {
                "id":         str(c.id),
                "body":       c.body,
                "author":     c.author.username if c.author else None,
                "created_at": c.created_at.isoformat(),
            }
            for c in comments
        ],
        "timeline": [
            {
                "id":         str(t.id),
                "event_type": t.event_type,
                "payload":    t.payload,
                "created_at": t.created_at.isoformat(),
            }
            for t in timeline_rows
        ],
    }


# ── Comments ─────────────────────────────────────────────────────────────────

@router.post("/requests/{request_id}/comments")
async def add_comment(
    request_id: str,
    body: dict = Body(..., examples=[{"body": "Looks good."}]),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    text = (body.get("body") or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="Comment body cannot be empty")
    if len(text) > 2000:
        raise HTTPException(status_code=422, detail="Comment is too long (2000 chars max)")

    try:
        rid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request id")

    repo = ActionRepository(db)
    action = await repo.get_by_id(rid)
    if not action:
        raise HTTPException(status_code=404, detail="Request not found")

    db_user = await _resolve_user_or_404(db, user.get("sub", ""))

    role = (user.get("role") or "").lower()
    is_owner = action.user_id == db_user.id
    is_approver_in_tenant = (
        role in ("manager", "admin")
        and str(action.company_id) == user.get("company_id")
    )
    if not (is_owner or is_approver_in_tenant):
        raise HTTPException(status_code=403, detail="You don't have access to this request")

    c_repo = ActionCommentRepository(db)
    comment = await c_repo.add(action_id=rid, author_id=db_user.id, body=text)

    # Audit
    audit = AuditLogRepository(db)
    await audit.log(
        "action_commented",
        company_id=action.company_id,
        user_id=db_user.id,
        entity_type="action",
        entity_id=action.id,
        payload={"comment_id": str(comment.id), "body_preview": text[:200]},
    )

    # Notify the *other* party (requester or any prior commenter)
    notif = NotificationRepository(db)
    if action.user_id and action.user_id != db_user.id:
        await notif.emit(
            company_id=action.company_id,
            recipient_id=action.user_id,
            actor_id=db_user.id,
            kind="request_commented",
            title="New comment on your request",
            message=f"{db_user.username} commented on your {action.action_type.replace('_', ' ')} request.",
            entity_type="action",
            entity_id=action.id,
            payload={"action_type": action.action_type},
        )

    await db.commit()
    return {
        "id":         str(comment.id),
        "body":       comment.body,
        "author":     db_user.username,
        "created_at": comment.created_at.isoformat(),
    }


# ── Cancel ───────────────────────────────────────────────────────────────────

@router.post("/requests/{request_id}/cancel")
async def cancel_request(
    request_id: str,
    body: dict = Body(default_factory=dict),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Requester cancels their own pending request."""
    try:
        rid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request id")

    db_user = await _resolve_user_or_404(db, user.get("sub", ""))
    repo = ActionRepository(db)
    action = await repo.get_by_id(rid)
    if not action:
        raise HTTPException(status_code=404, detail="Request not found")
    if action.user_id != db_user.id:
        raise HTTPException(status_code=403, detail="You can only cancel your own requests")

    reason = (body.get("reason") or "Cancelled by requester").strip()[:500]
    cancelled = await repo.cancel(action_id=rid, canceller_id=db_user.id, reason=reason)
    if not cancelled:
        raise HTTPException(
            status_code=409,
            detail="Request cannot be cancelled — it is already in a final state.",
        )

    audit = AuditLogRepository(db)
    await audit.log(
        "action_cancelled",
        company_id=action.company_id,
        user_id=db_user.id,
        entity_type="action",
        entity_id=action.id,
        payload={"action_type": action.action_type, "reason": reason},
    )
    await db.commit()
    return {"status": "cancelled", "request_id": request_id}
