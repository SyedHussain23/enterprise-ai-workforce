"""
Admin-only endpoints.

GET  /admin/stats       — query volume, confidence, agent distribution
GET  /admin/logs        — recent workflow logs
GET  /admin/cost        — daily and lifetime LLM cost
GET  /admin/feedback    — user feedback submissions
POST /admin/documents   — upload PDF to RAG knowledge base (201)
GET  /admin/users       — list users in company
PATCH /admin/users/{id} — update user role / status / department
GET  /admin/audit       — paginated audit log
"""
import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.dependencies import require_admin
from app.core.logger import get_logger
from app.cost.cost_tracker import get_daily_cost, get_lifetime_cost
from app.db.models.workflow_log import WorkflowLog
from app.db.repositories import (
    AuditLogRepository,
    UserRepository,
    WorkflowLogRepository,
)
from app.feedback.feedback_manager import FeedbackRepository
from app.schemas.api import UpdateUserRequest

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger(__name__)

# PDF magic bytes — first 5 bytes of any valid PDF
_PDF_MAGIC = b"%PDF-"
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def admin_stats(
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import cast, Date as SADate

    company_id_str = user.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")
    company_uuid = uuid.UUID(company_id_str)

    total = (
        await db.execute(
            select(func.count()).where(WorkflowLog.company_id == company_uuid)
        )
    ).scalar() or 0

    avg_c = round(
        float(
            (
                await db.execute(
                    select(func.avg(WorkflowLog.confidence)).where(
                        WorkflowLog.company_id == company_uuid
                    )
                )
            ).scalar()
            or 0
        ),
        1,
    )

    rt_rows = (
        await db.execute(
            select(WorkflowLog.execution_metadata)
            .where(WorkflowLog.company_id == company_uuid)
            .limit(500)
        )
    ).scalars().all()
    rt_values = [
        float(r["response_time"])
        for r in rt_rows
        if isinstance(r, dict) and "response_time" in r
    ]
    avg_rt = round(sum(rt_values) / len(rt_values), 3) if rt_values else 0.0

    dept_r = await db.execute(
        select(WorkflowLog.department, func.count().label("count"))
        .where(WorkflowLog.company_id == company_uuid)
        .group_by(WorkflowLog.department)
        .order_by(func.count().desc())
    )
    agent_distribution = {row.department: row.count for row in dept_r}

    daily_r = await db.execute(
        select(
            cast(WorkflowLog.created_at, SADate).label("date"),
            func.count().label("count"),
        )
        .where(WorkflowLog.company_id == company_uuid)
        .group_by(cast(WorkflowLog.created_at, SADate))
        .order_by(cast(WorkflowLog.created_at, SADate).desc())
        .limit(14)
    )
    daily_volume = [
        {"date": str(row.date), "count": row.count}
        for row in reversed(daily_r.fetchall())
    ]

    return {
        "total_queries":     total,
        "avg_confidence":    avg_c,
        "avg_response_time": avg_rt,
        "agent_distribution": agent_distribution,
        "daily_volume":      daily_volume,
    }


# ── Recent logs ───────────────────────────────────────────────────────────────

@router.get("/logs")
async def admin_logs(
    limit: int = 20,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    company_id_str = user.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")
    repo = WorkflowLogRepository(db)
    logs = await repo.get_recent(
        company_id=uuid.UUID(company_id_str), limit=min(limit, 100)
    )
    return [
        {
            "id":               str(l.id),
            "agent":            l.agent,
            "department":       l.department,
            "user_input":       l.user_input,
            "final_answer":     l.final_answer[:200],
            "confidence":       l.confidence,
            "evaluation_score": l.evaluation_score,
            "session_id":       l.session_id,
            "created_at":       l.created_at.isoformat(),
        }
        for l in logs
    ]


# ── Feedback ──────────────────────────────────────────────────────────────────

@router.get("/feedback")
async def admin_feedback(
    limit: int = 50,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    company_id_str = user.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")
    repo  = FeedbackRepository(db)
    items = await repo.get_recent(uuid.UUID(company_id_str), limit=min(limit, 100))
    return [
        {
            "id":               str(f.id),
            "workflow_log_id":  str(f.workflow_log_id),
            "rating":           f.rating,
            "comment":          f.comment,
            "created_at":       f.created_at.isoformat(),
        }
        for f in items
    ]


# ── Cost ──────────────────────────────────────────────────────────────────────

@router.get("/cost")
async def admin_costs(user: dict = Depends(require_admin)):
    company_id    = user.get("company_id", "global")
    daily_data    = get_daily_cost(company_id)
    lifetime_data = get_lifetime_cost(company_id)
    return {
        "daily":    daily_data.get("estimated_cost_usd", 0.0) if daily_data else 0.0,
        "lifetime": lifetime_data.get("estimated_cost_usd", 0.0) if lifetime_data else 0.0,
    }


# ── Document upload ───────────────────────────────────────────────────────────

@router.post("/documents", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    user: dict = Depends(require_admin),
):
    company_id_str = user.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")

    # Extension check (fast first gate)
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are supported")

    try:
        from pypdf import PdfReader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from app.rag.client import get_chroma_client
        from app.rag.hybrid_retriever import invalidate_bm25_cache
        from app.core.semantic_cache import invalidate_company

        contents = await file.read()

        # Size check
        if len(contents) > _MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large ({len(contents) // (1024 * 1024)}MB). Maximum is 20MB.",
            )

        # Magic bytes — defence against extension spoofing
        if not contents.startswith(_PDF_MAGIC):
            raise HTTPException(
                status_code=422,
                detail="File does not appear to be a valid PDF (magic bytes mismatch).",
            )

        reader   = PdfReader(io.BytesIO(contents))
        raw_text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()

        if not raw_text:
            raise HTTPException(status_code=422, detail="Could not extract text from PDF")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=120,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks  = splitter.split_text(raw_text)
        chroma  = get_chroma_client()
        doc_id  = str(uuid.uuid4())
        ids     = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {"source": file.filename, "company_id": company_id_str, "doc_id": doc_id}
            for _ in chunks
        ]
        chroma.add_texts(texts=chunks, metadatas=metadatas, ids=ids)

        # Invalidate BM25 (all workers) and semantic cache
        invalidate_bm25_cache()
        invalidate_company(company_id_str or "global")

        logger.info(
            "document.uploaded",
            doc_filename=file.filename,
            chunks=len(chunks),
            company_id=company_id_str,
        )
        return {
            "doc_id":          doc_id,
            "filename":        file.filename,
            "chunks":          len(chunks),
            "chunks_indexed":  len(chunks),
            "message":         f"✅ '{file.filename}' indexed — {len(chunks)} chunks added to knowledge base.",
            "status":          "indexed",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("document.upload_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(exc)}")


# ── User management ───────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    limit: int = 50,
    offset: int = 0,
    department: str | None = None,
    role: str | None = None,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models.user import User as UserModel

    company_id_str = user.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")
    company_uuid = uuid.UUID(company_id_str)

    stmt = (
        select(UserModel)
        .where(UserModel.company_id == company_uuid, UserModel.deleted_at == None)
        .order_by(UserModel.created_at.desc())
        .limit(min(limit, 200))
        .offset(offset)
    )
    if department:
        stmt = stmt.where(UserModel.department == department)
    if role:
        stmt = stmt.where(UserModel.role == role)

    result = await db.execute(stmt)
    users  = result.scalars().all()

    total_stmt = select(func.count()).where(
        UserModel.company_id == company_uuid, UserModel.deleted_at == None
    )
    if department:
        total_stmt = total_stmt.where(UserModel.department == department)
    if role:
        total_stmt = total_stmt.where(UserModel.role == role)
    total = (await db.execute(total_stmt)).scalar() or 0

    return {
        "total":  total,
        "limit":  limit,
        "offset": offset,
        "users": [
            {
                "id":         str(u.id),
                "username":   u.username,
                "email":      u.email,
                "role":       u.role,
                "department": u.department,
                "is_active":  u.is_active,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    company_id_str = admin.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")

    repo    = UserRepository(db)
    db_user = await repo.get_by_id(uuid.UUID(user_id))
    if not db_user or str(db_user.company_id) != company_id_str:
        raise HTTPException(status_code=404, detail="User not found")

    changes: dict = {}
    if body.role is not None:
        db_user.role = body.role
        changes["role"] = body.role
    if body.is_active is not None:
        db_user.is_active = body.is_active
        changes["is_active"] = body.is_active
    if body.department is not None:
        db_user.department = body.department
        changes["department"] = body.department

    if not changes:
        raise HTTPException(status_code=422, detail="No changes provided")

    admin_user = await UserRepository(db).get_by_username(admin.get("sub", ""))
    audit = AuditLogRepository(db)
    await audit.log(
        "user_updated",
        company_id=uuid.UUID(company_id_str),
        user_id=admin_user.id if admin_user else None,
        entity_type="user",
        entity_id=db_user.id,
        payload={"target_user": db_user.username, "changes": changes},
    )
    await db.commit()
    logger.info("admin.user_updated", target=db_user.username, changes=changes)
    return {"status": "updated", "user_id": user_id, "changes": changes}


# ── Audit log ─────────────────────────────────────────────────────────────────

@router.get("/audit")
async def admin_audit_trail(
    limit: int = 50,
    offset: int = 0,
    action: str | None = None,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models.audit_log import AuditLog

    company_id_str = user.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")
    company_uuid = uuid.UUID(company_id_str)

    stmt = (
        select(AuditLog)
        .where(AuditLog.company_id == company_uuid)
        .order_by(AuditLog.created_at.desc())
        .limit(min(limit, 500))
        .offset(offset)
    )
    if action:
        stmt = stmt.where(AuditLog.event_type == action)

    result = await db.execute(stmt)
    logs   = result.scalars().all()

    total_stmt = select(func.count()).where(AuditLog.company_id == company_uuid)
    if action:
        total_stmt = total_stmt.where(AuditLog.event_type == action)
    total = (await db.execute(total_stmt)).scalar() or 0

    return {
        "total":  total,
        "limit":  limit,
        "offset": offset,
        "logs": [
            {
                "id":          str(log.id),
                "event_type":  log.event_type,
                "user_id":     str(log.user_id) if log.user_id else None,
                "entity_type": log.entity_type,
                "entity_id":   str(log.entity_id) if log.entity_id else None,
                "ip_address":  log.ip_address,
                "payload":     log.payload,
                "created_at":  log.created_at.isoformat(),
            }
            for log in logs
        ],
    }
