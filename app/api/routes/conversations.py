"""
Conversation history endpoints.

GET  /conversations                      — list the authenticated user's sessions
GET  /conversations/{session_id}/messages — load messages for a session
DELETE /session/{session_id}/memory      — moved from actions.py (clear Redis memory)

These endpoints let the frontend load server-persisted history so chat
sessions survive browser clears and device switches.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.dependencies import get_current_user
from app.core.logger import get_logger
from app.db.repositories import ConversationRepository, UserRepository

router = APIRouter(tags=["conversations"])
logger = get_logger(__name__)


@router.get("/conversations")
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the authenticated user's conversation sessions, newest first.

    Each item includes session_id, title, department, message count, and the
    timestamp of the most recent activity so the frontend can display a
    sidebar history list.
    """
    company_id_str = user.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")

    user_repo  = UserRepository(db)
    db_user    = await user_repo.get_by_username(user.get("sub", ""))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    repo = ConversationRepository(db)
    convos = await repo.get_user_conversations(
        user_id=db_user.id,
        company_id=uuid.UUID(company_id_str),
        limit=min(limit, 100),
        offset=offset,
    )
    total = await repo.count_user_conversations(
        user_id=db_user.id,
        company_id=uuid.UUID(company_id_str),
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "conversations": [
            {
                "session_id":  c.session_id,
                "title":       c.title,
                "department":  c.department,
                "status":      c.status,
                "created_at":  c.created_at.isoformat(),
                "updated_at":  c.updated_at.isoformat(),
            }
            for c in convos
        ],
    }


@router.get("/conversations/{session_id}/messages")
async def get_conversation_messages(
    session_id: str,
    limit: int = 100,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return all messages for a session, oldest first.

    Only returns messages that belong to the authenticated user — attempting
    to fetch another user's session returns an empty list (not a 403, to
    avoid leaking session existence).
    """
    company_id_str = user.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")

    user_repo = UserRepository(db)
    db_user   = await user_repo.get_by_username(user.get("sub", ""))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    repo     = ConversationRepository(db)
    messages = await repo.get_messages(
        session_id=session_id,
        company_id=uuid.UUID(company_id_str),
        user_id=db_user.id,
        limit=min(limit, 500),
    )

    return {
        "session_id": session_id,
        "messages": [
            {
                "id":               str(m.id),
                "role":             m.role,
                "content":          m.content,
                "agent":            m.agent,
                "confidence":       m.confidence,
                "source":           m.source,
                "response_time":    m.response_time,
                "evaluation_score": m.evaluation_score,
                "created_at":       m.created_at.isoformat(),
            }
            for m in messages
        ],
    }
