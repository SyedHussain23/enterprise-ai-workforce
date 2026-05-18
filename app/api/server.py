import asyncio
import io
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.auth.auth import create_access_token, hash_password, verify_password
from app.auth.dependencies import get_current_user, require_admin
from app.core.config import settings
from app.core.logger import clear_request_id, get_logger, set_request_id
from app.core.middleware import error_handling_middleware, security_headers_middleware
from app.core.rate_limiter import ask_rate_limiter, login_rate_limiter, rate_limiter
from app.core.semantic_cache import get_cached, invalidate_company, set_cached
from app.cost.cost_tracker import get_daily_cost, get_lifetime_cost
from app.db.engine import AsyncSessionLocal
from app.db.models.action import ActionStatus
from app.db.models.workflow_log import WorkflowLog
from app.db.repositories import (
    ActionRepository,
    AuditLogRepository,
    ConversationRepository,
    UserRepository,
    WorkflowLogRepository,
)
from app.feedback.feedback_manager import FeedbackRepository
from app.memory.redis_memory import clear_session
from app.monitoring.workflow_visualizer import generate_workflow_graph
from app.rag.client import get_chroma_client
from app.schemas.api import (
    ActionApprovalRequest,
    ChangePasswordRequest,
    FeedbackRequest,
    LoginRequest,
    LoginResponse,
    QueryRequest,
    UpdateProfileRequest,
    UpdateUserRequest,
    UserProfileResponse,
    WorkflowResponse,
)
from app.utils.guardrails import get_guardrail_response
from app.utils.multi_intent import detect_intents, handle_multi_intent
from app.workflows.workflow_graph import build_workflow

logger = get_logger(__name__)

# ── LangSmith tracing ─────────────────────────────────────────────────────────
if settings.LANGCHAIN_TRACING_V2 and settings.LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"]     = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"]     = settings.LANGCHAIN_PROJECT
    logger.info("langsmith.enabled", project=settings.LANGCHAIN_PROJECT)


# ── DB session dependency ─────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


# ── Startup / shutdown ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup.begin", app=settings.APP_NAME)
    try:
        get_chroma_client()
        logger.info("startup.chroma_ready")
    except Exception as exc:
        logger.error("startup.chroma_failed", error=str(exc))
    app.state.workflow = build_workflow()
    logger.info("startup.workflow_compiled")
    yield
    logger.info("shutdown.begin")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

# Build allowed origins list:
# - Debug mode: allow all (local development convenience)
# - Production: localhost defaults + any origins from ALLOWED_ORIGINS env var
#   Set ALLOWED_ORIGINS=https://your-app.vercel.app in Railway environment variables
_default_origins = ["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"]
_extra_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
_cors_origins = ["*"] if settings.DEBUG else _default_origins + _extra_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(error_handling_middleware)
app.middleware("http")(security_headers_middleware)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(rid)
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    clear_request_id()
    return response


# ── Helpers ───────────────────────────────────────────────────────────────────
def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")


def _build_response(*, status, answer, agent, confidence, source, steps,
                    confidence_reason, evaluation_score, response_time,
                    action_id=None, action_type=None, action_status=None) -> WorkflowResponse:
    return WorkflowResponse(
        status=status, answer=answer, agent=agent, confidence=confidence,
        source=source, steps=steps, confidence_reason=confidence_reason,
        evaluation_score=evaluation_score, response_time=response_time,
        timestamp=datetime.now(timezone.utc).isoformat(),
        action_id=action_id, action_type=action_type, action_status=action_status,
    )


# ── Auth ──────────────────────────────────────────────────────────────────────
@app.post("/login", response_model=LoginResponse, dependencies=[Depends(login_rate_limiter)])
async def login(data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    repo      = UserRepository(db)
    audit     = AuditLogRepository(db)
    ip        = _client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    user = await repo.get_by_username(data.username)
    if not user or not verify_password(data.password, user.hashed_password):
        await audit.log(
            "login_failed",
            ip_address=ip, user_agent=user_agent,
            payload={"username": data.username},
        )
        await db.commit()
        logger.warning("auth.login_failed", username=data.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await audit.log(
        "login",
        company_id=user.company_id, user_id=user.id,
        ip_address=ip, user_agent=user_agent,
    )
    await db.commit()

    token = create_access_token({"sub": data.username, "role": user.role, "company_id": str(user.company_id)})
    logger.info("auth.login_success", username=data.username, role=user.role)
    return LoginResponse(access_token=token, role=user.role)


# ── /logout — server-side token invalidation ──────────────────────────────────
@app.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """
    Explicitly invalidate the caller's JWT by adding its `jti` to the Redis
    blocklist. The blocklist entry TTL matches the token's remaining lifetime,
    so the entry self-expires — no cleanup job needed.

    Without this endpoint, JWTs remain valid until their `exp` claim passes
    even after the user clicks "Log out" — a stolen token could be replayed.
    """
    from app.core.token_blocklist import block_token

    jti = user.get("jti")
    exp = user.get("exp")   # Unix timestamp (int), set by create_access_token

    if jti and exp:
        remaining = int(exp - datetime.now(timezone.utc).timestamp())
        block_token(jti, max(remaining, 0))

    logger.info("auth.logout", user=user.get("sub", "unknown")[:20])
    return {"status": "logged_out"}


# ── /ask/extract — inline document text extraction for chat context ────────────
@app.post("/ask/extract")
async def extract_document_for_chat(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """
    Extract plain text from an uploaded document so the chat can inject it
    as context into the question sent to the AI workflow.

    This endpoint is distinct from /admin/documents (which indexes docs into
    the permanent RAG knowledge base). This is ephemeral — the extracted text
    is returned to the frontend and prepended to the user's query for a single
    conversation turn. No data is persisted.

    Supported: PDF, TXT, CSV, DOCX
    Limit: 5MB, 8 000 character output truncation
    """
    MAX_SIZE   = 5 * 1024 * 1024   # 5 MB
    MAX_CHARS  = 8_000             # keep context injection within GPT context limits

    filename = (file.filename or "").lower()
    allowed_exts = {".pdf", ".txt", ".csv", ".docx", ".doc"}
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(allowed_exts))}",
        )

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(contents) // 1024}KB). Maximum is 5MB.",
        )

    try:
        text = ""
        if ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(contents))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext in {".txt", ".csv"}:
            text = contents.decode("utf-8", errors="replace")
        elif ext in {".docx", ".doc"}:
            try:
                import docx
                doc = docx.Document(io.BytesIO(contents))
                text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            except ImportError:
                # python-docx not installed — fallback to raw text extraction
                text = contents.decode("utf-8", errors="replace")

        text = text.strip()
        if not text:
            raise HTTPException(status_code=422, detail="Could not extract text from the uploaded file.")

        logger.info(
            "extract.success",
            filename=file.filename,
            chars=len(text),
            user=user.get("sub", "")[:16],
        )
        return {
            "filename": file.filename,
            "chars":    len(text),
            "text":     text[:MAX_CHARS],
            "truncated": len(text) > MAX_CHARS,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("extract.failed", filename=file.filename, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to process the uploaded file.")


# ── /ask — full response ──────────────────────────────────────────────────────
@app.post("/ask", response_model=WorkflowResponse, dependencies=[Depends(ask_rate_limiter)])
async def ask_ai(
    request: Request,
    body: QueryRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _run_workflow(request, body, user, db)


# ── /ask/stream — SSE streaming ───────────────────────────────────────────────
@app.post("/ask/stream", dependencies=[Depends(ask_rate_limiter)])
async def ask_stream(
    request: Request,
    body: QueryRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    def _status(msg: str) -> dict:
        return {"data": json.dumps({"type": "status", "content": msg})}

    async def generate():
        # Emit immediately so the client shows activity right away
        yield _status("Analyzing your request…")

        # Fast guardrail check before spinning up the full workflow
        guard = get_guardrail_response(body.question)
        if guard:
            answer = guard.get("answer", "I can't help with that.")
            words  = answer.split(" ")
            for i, word in enumerate(words):
                yield {"data": json.dumps({"type": "token", "content": word + (" " if i < len(words) - 1 else "")})}
                await asyncio.sleep(0.03)
            yield {"data": json.dumps({
                "type": "done", "agent": "guardrail", "confidence": 100,
                "source": "guardrail", "steps": ["Guardrail → request blocked"],
                "confidence_reason": guard.get("confidence_reason"),
                "evaluation_score": 0.0, "response_time": 0.0,
                "action_id": None, "action_type": None, "action_status": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })}
            return

        # Detect intent and hint to user which agent is handling it
        from app.utils.multi_intent import detect_intents
        intents = detect_intents(body.question)
        if len(intents) > 1:
            yield _status(f"Routing to {' + '.join(intents)} agents…")
        elif len(intents) == 1:
            yield _status(f"Routing to {intents[0]} specialist…")
        else:
            yield _status("Routing to best-match agent…")

        result = await _run_workflow(request, body, user, db)
        answer = result.answer

        yield _status("Streaming response…")

        # C5: Real token streaming for RAG-retrieved answers.
        # Pre-written rule-based answers (keyword_match=True) are already
        # authoritative and accurate — word-split them (fast, no extra LLM cost).
        # RAG fallback answers benefit from LLM synthesis: it turns retrieved
        # policy text into a natural, conversational response in real time.
        use_real_stream = (
            result.source not in (None, "guardrail", "cache", "approval_gate", "error")
            and result.agent not in ("guardrail", "cache", "error", "multi_intent")
            and not (result.action_id or result.action_type)  # never stream action confirmations
            and result.confidence < 90  # hardcoded high-confidence = pre-written, skip synthesis
        )

        if use_real_stream:
            from app.core.openai_client import async_stream_synthesis
            department = result.agent or "HR"
            # Use the RAG-retrieved context stored in answer as synthesis input
            async for token in async_stream_synthesis(
                question=body.question,
                context=answer,
                department=department,
            ):
                yield {"data": json.dumps({"type": "token", "content": token})}
        else:
            # Word-split pre-written responses (fast, no LLM overhead)
            words = answer.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield {"data": json.dumps({"type": "token", "content": chunk})}
                await asyncio.sleep(0.025)

        # Final metadata event
        yield {"data": json.dumps({
            "type": "done",
            "agent": result.agent,
            "confidence": result.confidence,
            "source": result.source,
            "steps": result.steps,
            "confidence_reason": result.confidence_reason,
            "evaluation_score": result.evaluation_score,
            "response_time": result.response_time,
            "action_id": result.action_id,
            "action_type": result.action_type,
            "action_status": result.action_status,
            "timestamp": result.timestamp,
        })}

    return EventSourceResponse(generate())


# ── Core workflow logic (shared between /ask and /ask/stream) ─────────────────
async def _run_workflow(
    request: Request,
    body: QueryRequest,
    user: dict,
    db: AsyncSession,
) -> WorkflowResponse:
    start = time.perf_counter()
    question = body.question
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    ip  = _client_ip(request)

    company_id_str: str | None = user.get("company_id")
    user_sub: str = user.get("sub", "")

    logger.info("ask.received", question=question, session_id=body.session_id)

    # ── Guardrail ─────────────────────────────────────────────────────────────
    guard = get_guardrail_response(question)
    if guard:
        rt = round(time.perf_counter() - start, 3)
        if company_id_str:
            try:
                audit = AuditLogRepository(db)
                await audit.log(
                    "query_blocked",
                    company_id=uuid.UUID(company_id_str),
                    ip_address=ip,
                    payload={"question": question[:200], "reason": guard.get("confidence_reason")},
                )
                await db.commit()
            except Exception:
                pass
        guard["response_time"] = rt
        return WorkflowResponse(**guard, response_time=rt)

    # ── Semantic cache lookup ─────────────────────────────────────────────────
    # Check before any LLM/RAG work — cache hit saves 2–5 seconds + tokens.
    cache_company = company_id_str or "global"
    cached = await asyncio.get_event_loop().run_in_executor(
        None, get_cached, question, cache_company
    )
    if cached:
        rt = round(time.perf_counter() - start, 3)
        logger.info("ask.cache_hit", cache_type=cached.get("_cache"), rt=rt)
        return _build_response(
            status="success",
            answer=cached.get("answer", ""),
            agent=cached.get("agent", "cache"),
            confidence=cached.get("confidence", 80),
            source=cached.get("source", "cache"),
            steps=["Cache → semantic match found", "Response served from cache"],
            confidence_reason=f"Cached response ({cached.get('_cache', 'exact')} match)",
            evaluation_score=0,
            response_time=rt,
        )

    # ── Multi-intent ──────────────────────────────────────────────────────────
    intents = detect_intents(question)
    if len(intents) > 1:
        result = handle_multi_intent(question, intents)
        rt = round(time.perf_counter() - start, 3)
        return _build_response(
            status="success", answer=result["answer"], agent="multi_intent",
            confidence=result["confidence"], source=result["source"],
            steps=[
                "Planner → multi-intent detected",
                f"Planner → identified: {', '.join(intents)}",
                "Router → dispatched to multiple agents",
                *[f"{d} Agent → processed" for d in intents],
                "Report → combined response",
            ],
            confidence_reason=result.get("confidence_reason"),
            evaluation_score=0, response_time=rt,
        )

    # ── Single-intent workflow ────────────────────────────────────────────────
    try:
        result = app.state.workflow.invoke({
            "session_id": body.session_id,
            "user_input": question,
            "request_id": rid,
            "company_id": company_id_str,
            "user_id": user_sub,
        })
    except Exception as exc:
        rt = round(time.perf_counter() - start, 3)
        logger.error("ask.workflow_failed", error=str(exc))
        return _build_response(
            status="error", answer="System error. Please try again.",
            agent="error", confidence=0, source="error", steps=[],
            confidence_reason=str(exc), evaluation_score=0, response_time=rt,
        )

    rt = round(time.perf_counter() - start, 3)

    if not result or result.get("status") == "error":
        return _build_response(
            status="error",
            answer=result.get("answer", "Something went wrong.") if result else "Empty response.",
            agent=result.get("agent", "fallback") if result else "fallback",
            confidence=0, source=result.get("source", "fallback") if result else "fallback",
            steps=result.get("steps", []) if result else [],
            confidence_reason="Workflow error", evaluation_score=0, response_time=rt,
        )

    answer = (result.get("answer") or "").strip() or "I couldn't find relevant information. Please rephrase."

    # ── Persist to PostgreSQL ─────────────────────────────────────────────────
    action_id_str: str | None = None
    action_status_str: str | None = None

    if company_id_str:
        try:
            company_uuid = uuid.UUID(company_id_str)
            user_repo = UserRepository(db)
            db_user   = await user_repo.get_by_username(user_sub)
            user_uuid = db_user.id if db_user else None

            # Conversation + messages
            convo_repo = ConversationRepository(db)
            convo = await convo_repo.get_or_create_by_session(
                session_id=body.session_id, company_id=company_uuid,
                user_id=user_uuid, department=result.get("agent"),
            )
            await convo_repo.add_message(conversation_id=convo.id, role="user", content=question)
            await convo_repo.add_message(
                conversation_id=convo.id, role="assistant", content=answer,
                agent=result.get("agent"), confidence=result.get("confidence"),
                source=result.get("source"), response_time=rt,
                evaluation_score=result.get("evaluation_score"),
            )

            # Workflow log
            wf_repo = WorkflowLogRepository(db)
            wf_log  = await wf_repo.create(
                company_id=company_uuid, conversation_id=convo.id, user_id=user_uuid,
                session_id=body.session_id, department=result.get("agent", "Unknown"),
                agent=result.get("agent", "Unknown"), user_input=question,
                final_answer=answer, confidence=result.get("confidence") or 0,
                evaluation_score=result.get("evaluation_score"),
                steps=result.get("steps") or [],
                execution_metadata={
                    "request_id": rid, "response_time": rt,
                    "source": result.get("source"),
                    "rag_used": result.get("rag_used", False),
                    "keyword_match": result.get("keyword_match", False),
                },
            )

            # Action record (Day 43)
            if result.get("action_triggered") and result.get("action_type"):
                action_repo = ActionRepository(db)
                action = await action_repo.create(
                    company_id=company_uuid, user_id=user_uuid,
                    workflow_log_id=wf_log.id,
                    action_type=result["action_type"],
                    department=result.get("agent", "Unknown"),
                    payload=result.get("action_payload") or {},
                    requires_approval=True,
                )
                action_id_str    = str(action.id)
                action_status_str = action.status

            # Audit log — query submitted
            audit = AuditLogRepository(db)
            await audit.log(
                "query_submitted",
                company_id=company_uuid, user_id=user_uuid,
                entity_type="workflow_log", entity_id=wf_log.id,
                ip_address=ip,
                payload={"agent": result.get("agent"), "confidence": result.get("confidence")},
            )

            await db.commit()
            logger.info("ask.persisted", session_id=body.session_id, action_id=action_id_str)
        except Exception as exc:
            logger.error("ask.persist_failed", error=str(exc))

    logger.info("ask.complete", agent=result.get("agent"), confidence=result.get("confidence"), rt=rt)

    final_response = _build_response(
        status="success", answer=answer,
        agent=result.get("agent") or "Unknown",
        confidence=result.get("confidence") or 0,
        source=result.get("source") or "internal_kb",
        steps=result.get("steps") or [],
        confidence_reason=result.get("confidence_reason"),
        evaluation_score=result.get("evaluation_score"),
        response_time=rt,
        action_id=action_id_str,
        action_type=result.get("action_type"),
        action_status=action_status_str,
    )

    # ── Store in semantic cache (async, non-blocking) ─────────────────────────
    if not result.get("action_triggered"):
        asyncio.get_event_loop().run_in_executor(
            None,
            set_cached,
            question,
            cache_company,
            {
                "answer":     answer,
                "agent":      result.get("agent"),
                "confidence": result.get("confidence"),
                "source":     result.get("source"),
                "action_triggered": False,
            },
        )

    return final_response


# ── Actions (Day 43) ──────────────────────────────────────────────────────────
@app.get("/actions/pending")
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
    user_repo = UserRepository(db)
    user_cache: dict[str, str] = {}
    for a in actions:
        if a.user_id:
            key = str(a.user_id)
            if key not in user_cache:
                u = await user_repo.get_by_id(a.user_id)
                user_cache[key] = u.username if u else "Unknown"

    return [
        {
            "id": str(a.id),
            "action_type": a.action_type,
            "department": a.department,
            "status": a.status,
            "payload": a.payload,
            "requested_by": user_cache.get(str(a.user_id), "Unknown") if a.user_id else "System",
            "notes": a.notes,
            "created_at": a.created_at.isoformat(),
        }
        for a in actions
    ]


@app.get("/actions/mine")
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
            "id": str(a.id), "action_type": a.action_type, "department": a.department,
            "status": a.status, "payload": a.payload,
            "created_at": a.created_at.isoformat(),
        }
        for a in actions
    ]


def _execute_approved_action(action_type: str, payload: dict) -> dict | None:
    """
    Execute the real-world side effect for an approved action.
    Returns an execution result dict (stored back on the action payload).
    Runs synchronously — call in a thread pool for production at scale.
    """
    from app.tools.automation_engine import (
        generate_leave_summary,
        generate_it_ticket_summary,
        generate_expense_report,
        generate_onboarding_checklist,
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


@app.post("/actions/{action_id}/approve")
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

    # Execute the approved action and mark COMPLETED
    exec_result = _execute_approved_action(action.action_type, action.payload or {})
    if exec_result:
        await repo.complete(uuid.UUID(action_id), exec_result)

    audit = AuditLogRepository(db)
    await audit.log(
        "action_approved",
        company_id=uuid.UUID(company_id_str) if company_id_str else None,
        user_id=db_user.id,
        entity_type="action", entity_id=action.id,
        payload={"action_type": action.action_type, "notes": body.notes, "executed": exec_result is not None},
    )
    await db.commit()
    return {
        "status": "approved",
        "action_id": action_id,
        "executed": exec_result is not None,
        "execution_result": exec_result,
    }


@app.post("/actions/{action_id}/reject")
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
        entity_type="action", entity_id=action.id,
        payload={"action_type": action.action_type, "notes": body.notes},
    )
    await db.commit()
    return {"status": "rejected", "action_id": action_id}


# ── Document Upload (Day 44) ──────────────────────────────────────────────────
@app.post("/admin/documents", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    user: dict = Depends(require_admin),
):
    company_id_str = user.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are supported")

    try:
        from pypdf import PdfReader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from app.rag.client import get_chroma_client

        contents = await file.read()
        reader   = PdfReader(io.BytesIO(contents))
        raw_text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()

        if not raw_text:
            raise HTTPException(status_code=422, detail="Could not extract text from PDF")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, chunk_overlap=120,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks   = splitter.split_text(raw_text)

        chroma  = get_chroma_client()
        doc_id  = str(uuid.uuid4())
        ids     = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {"source": file.filename, "company_id": company_id_str, "doc_id": doc_id}
            for _ in chunks
        ]
        chroma.add_texts(texts=chunks, metadatas=metadatas, ids=ids)

        # Invalidate BM25 index so next query re-indexes the new doc
        from app.rag.hybrid_retriever import invalidate_bm25_cache
        invalidate_bm25_cache()
        # Invalidate semantic cache — new docs may change best answers
        invalidate_company(company_id_str or "global")

        logger.info("document.uploaded", doc_filename=file.filename, chunks=len(chunks), company_id=company_id_str)
        return {
            "doc_id": doc_id,
            "filename": file.filename,
            "chunks": len(chunks),
            "chunks_indexed": len(chunks),
            "message": f"✅ '{file.filename}' indexed — {len(chunks)} chunks added to knowledge base.",
            "status": "indexed",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("document.upload_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(exc)}")


# ── Admin analytics ───────────────────────────────────────────────────────────
@app.get("/admin/stats")
async def admin_stats(user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import cast, Date as SADate
    company_id_str = user.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")
    company_uuid = uuid.UUID(company_id_str)

    total  = (await db.execute(select(func.count()).where(WorkflowLog.company_id == company_uuid))).scalar() or 0
    avg_c  = round(float((await db.execute(select(func.avg(WorkflowLog.confidence)).where(WorkflowLog.company_id == company_uuid))).scalar() or 0), 1)

    # avg response time — pull raw rows and average in Python to avoid JSON cast issues
    rt_rows = (await db.execute(
        select(WorkflowLog.execution_metadata)
        .where(WorkflowLog.company_id == company_uuid)
        .limit(500)
    )).scalars().all()
    rt_values = [
        float(r["response_time"])
        for r in rt_rows
        if isinstance(r, dict) and "response_time" in r
    ]
    avg_rt = round(sum(rt_values) / len(rt_values), 3) if rt_values else 0.0

    dept_r = await db.execute(
        select(WorkflowLog.department, func.count().label("count"))
        .where(WorkflowLog.company_id == company_uuid)
        .group_by(WorkflowLog.department).order_by(func.count().desc())
    )
    agent_distribution = {row.department: row.count for row in dept_r}

    # Daily volume: last 14 days
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
        "total_queries": total,
        "avg_confidence": avg_c,
        "avg_response_time": avg_rt,
        "agent_distribution": agent_distribution,
        "daily_volume": daily_volume,
    }


@app.get("/admin/logs")
async def admin_logs(
    limit: int = 20,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    company_id_str = user.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")
    repo = WorkflowLogRepository(db)
    logs = await repo.get_recent(company_id=uuid.UUID(company_id_str), limit=min(limit, 100))
    return [
        {
            "id": str(l.id), "agent": l.agent, "department": l.department,
            "user_input": l.user_input, "final_answer": l.final_answer[:200],
            "confidence": l.confidence, "evaluation_score": l.evaluation_score,
            "session_id": l.session_id, "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


# ── Feedback ──────────────────────────────────────────────────────────────────
@app.post("/feedback", status_code=201)
async def submit_feedback(
    body: FeedbackRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company_id_str = user.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=400, detail="No company_id in token")
    try:
        company_uuid      = uuid.UUID(company_id_str)
        workflow_log_uuid = uuid.UUID(body.workflow_log_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID format")

    user_repo = UserRepository(db)
    db_user   = await user_repo.get_by_username(user.get("sub", ""))
    repo = FeedbackRepository(db)
    fb   = await repo.create(
        company_id=company_uuid, workflow_log_id=workflow_log_uuid,
        user_id=db_user.id if db_user else None,
        rating=body.rating, comment=body.comment,
    )
    await db.commit()
    return {"id": str(fb.id), "rating": body.rating, "status": "saved"}


@app.get("/admin/feedback")
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
        {"id": str(f.id), "workflow_log_id": str(f.workflow_log_id),
         "rating": f.rating, "comment": f.comment, "created_at": f.created_at.isoformat()}
        for f in items
    ]


# ── Cost ──────────────────────────────────────────────────────────────────────
@app.get("/admin/cost")
async def admin_costs(user: dict = Depends(require_admin)):
    company_id = user.get("company_id", "global")
    return {
        "daily":    get_daily_cost(company_id),
        "lifetime": get_lifetime_cost(company_id),
    }


# ── Memory ────────────────────────────────────────────────────────────────────
@app.delete("/session/{session_id}/memory")
async def clear_memory(session_id: str, user: dict = Depends(get_current_user)):
    clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


# ── Workflow graph visualization ──────────────────────────────────────────────
@app.get("/workflow-graph")
async def workflow_graph_view(user=Depends(get_current_user)):
    try:
        graph = generate_workflow_graph([])
        return Response(graph.pipe(format="png"), media_type="image/png")
    except Exception as exc:
        logger.error("workflow_graph.failed", error=str(exc))
        return JSONResponse(status_code=500, content={"error": "Graph rendering failed"})


# ── User profile ─────────────────────────────────────────────────────────────

@app.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's profile."""
    repo    = UserRepository(db)
    db_user = await repo.get_by_username(user.get("sub", ""))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfileResponse(
        id=str(db_user.id),
        username=db_user.username,
        email=db_user.email,
        role=db_user.role,
        department=db_user.department,
        is_active=db_user.is_active,
        company_id=str(db_user.company_id),
        created_at=db_user.created_at.isoformat(),
    )


@app.put("/me")
async def update_my_profile(
    body: UpdateProfileRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated user's email or department."""
    repo    = UserRepository(db)
    db_user = await repo.get_by_username(user.get("sub", ""))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.email is not None:
        db_user.email = body.email
    if body.department is not None:
        db_user.department = body.department

    audit = AuditLogRepository(db)
    await audit.log(
        "profile_updated",
        company_id=db_user.company_id,
        user_id=db_user.id,
        payload={"email_changed": body.email is not None, "dept_changed": body.department is not None},
    )
    await db.commit()
    logger.info("profile.updated", username=db_user.username)
    return {"status": "updated", "username": db_user.username}


@app.put("/me/password")
async def change_my_password(
    body: ChangePasswordRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the authenticated user's password after verifying the current one."""
    repo    = UserRepository(db)
    db_user = await repo.get_by_username(user.get("sub", ""))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(body.current_password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    db_user.hashed_password = hash_password(body.new_password)

    audit = AuditLogRepository(db)
    await audit.log(
        "password_changed",
        company_id=db_user.company_id,
        user_id=db_user.id,
        payload={},
    )
    await db.commit()
    logger.info("password.changed", username=db_user.username)
    return {"status": "password_changed"}


# ── Admin user management ─────────────────────────────────────────────────────

@app.get("/admin/users")
async def list_users(
    limit: int = 50,
    offset: int = 0,
    department: str | None = None,
    role: str | None = None,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users in the company (admin only). Supports filtering by department and role."""
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
        "total": total,
        "limit": limit,
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


@app.patch("/admin/users/{user_id}")
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's role, active status, or department (admin only)."""
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

    admin_repo = UserRepository(db)
    admin_user = await admin_repo.get_by_username(admin.get("sub", ""))

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


# ── Admin audit trail ─────────────────────────────────────────────────────────

@app.get("/admin/audit")
async def admin_audit_trail(
    limit: int = 50,
    offset: int = 0,
    action: str | None = None,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Return paginated audit log entries for the company.
    Optionally filter by action type (e.g. login, query_submitted, action_approved).
    """
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


# ── WhatsApp webhook (Day 54) ────────────────────────────────────────────────
@app.get("/webhook/whatsapp")
async def whatsapp_verify(
    hub_mode: str | None = None,
    hub_verify_token: str | None = None,
    hub_challenge: str | None = None,
):
    """
    Meta webhook verification handshake.
    Meta sends GET with hub.mode=subscribe and the verify token you configured
    in the Meta App dashboard. Return the challenge to confirm ownership.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("whatsapp.webhook_verified")
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@app.post("/webhook/whatsapp", status_code=200)
async def whatsapp_webhook(request: Request):
    """
    Receive inbound WhatsApp messages from Meta Cloud API.

    Meta expects HTTP 200 within 20 seconds — we acknowledge immediately
    and process in a background task so we never time out.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from app.whatsapp.handler import handle_whatsapp_message

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Parse Meta webhook payload
    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
    except (IndexError, KeyError, TypeError):
        return {"status": "ok"}   # not a message event — status updates, etc.

    for msg in messages:
        if msg.get("type") != "text":
            continue   # skip images, audio, etc. for now

        from_number = msg.get("from", "")
        message_id  = msg.get("id", "")
        text        = msg.get("text", {}).get("body", "").strip()

        if not (from_number and text):
            continue

        logger.info("whatsapp.inbound", from_number=from_number, text=text[:80])

        # Run handler in a thread so we don't block the event loop
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            None,
            handle_whatsapp_message,
            from_number,
            message_id,
            text,
        )

    return {"status": "ok"}


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """Shallow health check — used by Railway healthcheck probe."""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/health/deep")
async def health_deep(db: AsyncSession = Depends(get_db)):
    """
    Deep health check — verifies connectivity to all downstream dependencies.
    Used for monitoring dashboards, not Railway healthcheck (too slow for that).
    Returns degraded status (not 500) so Railway doesn't restart on partial failure.
    """
    import redis as _redis_lib

    checks: dict[str, str] = {}

    # PostgreSQL
    try:
        await db.execute(func.now().select())  # type: ignore[attr-defined]
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {str(exc)[:80]}"

    # Redis
    try:
        r = _redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {str(exc)[:80]}"

    # ChromaDB — LangChain wrapper doesn't expose heartbeat; verify via collection count
    try:
        chroma = get_chroma_client()
        # _collection is the underlying chromadb Collection; count() is always available
        count = chroma._collection.count()
        checks["chromadb"] = f"ok ({count} documents)"
    except Exception as exc:
        checks["chromadb"] = f"error: {str(exc)[:80]}"

    # OpenAI reachability (cheap — just validate key, no actual call)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=3.0)
        # List models — cheapest API call that confirms key validity
        client.models.list()
        checks["openai"] = "ok"
    except Exception as exc:
        checks["openai"] = f"error: {str(exc)[:80]}"

    # Circuit breaker state
    from app.core.openai_client import get_circuit_state
    cb = get_circuit_state()
    checks["circuit_breaker"] = cb["state"]

    overall = "ok" if all(
        v in ("ok", "closed") for v in checks.values()
    ) else "degraded"
    return {
        "status":          overall,
        "app":             settings.APP_NAME,
        "version":         settings.APP_VERSION,
        "checks":          checks,
        "circuit_breaker": cb,
    }
