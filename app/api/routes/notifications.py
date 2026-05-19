"""
In-app notification endpoints.

  GET   /notifications              — paginated list (newest first)
  GET   /notifications/unread/count — number badge for the bell
  POST  /notifications/{id}/read    — mark single as read
  POST  /notifications/read-all     — mark all as read

All endpoints are scoped to the calling user — there is no cross-user access.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.dependencies import get_current_user
from app.db.repositories import NotificationRepository, UserRepository

router = APIRouter(tags=["notifications"])


async def _resolve_user(db: AsyncSession, jwt_sub: str):
    repo = UserRepository(db)
    db_user = await repo.get_by_username(jwt_sub)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.get("/notifications")
async def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    unread_only: bool = Query(False),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company_id_str = user.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")

    db_user = await _resolve_user(db, user.get("sub", ""))
    repo = NotificationRepository(db)
    items = await repo.list_for_user(
        recipient_id=db_user.id,
        company_id=uuid.UUID(company_id_str),
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )
    unread = await repo.unread_count(
        recipient_id=db_user.id,
        company_id=uuid.UUID(company_id_str),
    )
    return {
        "unread_count": unread,
        "limit":  limit,
        "offset": offset,
        "notifications": [
            {
                "id":          str(n.id),
                "kind":        n.kind,
                "title":       n.title,
                "message":     n.message,
                "entity_type": n.entity_type,
                "entity_id":   str(n.entity_id) if n.entity_id else None,
                "payload":     n.payload,
                "is_read":     n.is_read,
                "read_at":     n.read_at.isoformat() if n.read_at else None,
                "created_at":  n.created_at.isoformat(),
            }
            for n in items
        ],
    }


@router.get("/notifications/unread/count")
async def unread_count(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company_id_str = user.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")

    db_user = await _resolve_user(db, user.get("sub", ""))
    repo = NotificationRepository(db)
    count = await repo.unread_count(
        recipient_id=db_user.id,
        company_id=uuid.UUID(company_id_str),
    )
    return {"unread_count": count}


@router.post("/notifications/{notif_id}/read")
async def mark_read(
    notif_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        nid = uuid.UUID(notif_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification id")

    db_user = await _resolve_user(db, user.get("sub", ""))
    repo = NotificationRepository(db)
    updated = await repo.mark_read(notification_id=nid, recipient_id=db_user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.commit()
    return {"status": "read", "id": notif_id}


@router.post("/notifications/read-all")
async def mark_all_read(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company_id_str = user.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")

    db_user = await _resolve_user(db, user.get("sub", ""))
    repo = NotificationRepository(db)
    n = await repo.mark_all_read(
        recipient_id=db_user.id,
        company_id=uuid.UUID(company_id_str),
    )
    await db.commit()
    return {"status": "ok", "marked_read": n}
