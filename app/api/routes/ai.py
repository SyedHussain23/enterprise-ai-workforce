"""
AI chat endpoints — the core of the product.

POST /ask/extract   — extract text from uploaded doc for chat context (ephemeral)
POST /ask           — full blocking response
POST /ask/stream    — SSE streaming response
POST /feedback      — submit thumbs-up/down feedback on a response
"""
import asyncio
import io
import json
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_db
from app.auth.dependencies import get_current_user
from app.core.logger import get_logger
from app.core.rate_limiter import ask_rate_limiter
from app.core.semantic_cache import get_cached, set_cached
from app.db.models.workflow_log import WorkflowLog
from app.db.repositories import (
    ActionRepository,
    AuditLogRepository,
    ConversationRepository,
    UserRepository,
    WorkflowLogRepository,
)
from app.feedback.feedback_manager import FeedbackRepository
from app.schemas.api import FeedbackRequest, QueryRequest, WorkflowResponse
from app.utils.guardrails import get_guardrail_response
from app.utils.multi_intent import detect_intents, handle_multi_intent

router = APIRouter(tags=["ai"])
logger = get_logger(__name__)

# Allowed extensions for document extraction
_EXTRACT_ALLOWED_EXTS = {".pdf", ".txt", ".csv", ".docx", ".doc"}
_EXTRACT_MAX_SIZE     = 5 * 1024 * 1024   # 5 MB
_EXTRACT_MAX_CHARS    = 8_000


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )


def _build_response(
    *, status, answer, agent, confidence, source, steps,
    confidence_reason, evaluation_score, response_time,
    action_id=None, action_type=None, action_status=None,
    workflow_log_id=None,
) -> WorkflowResponse:
    return WorkflowResponse(
        status=status, answer=answer, agent=agent, confidence=confidence,
        source=source, steps=steps, confidence_reason=confidence_reason,
        evaluation_score=evaluation_score, response_time=response_time,
        timestamp=datetime.now(timezone.utc).isoformat(),
        action_id=action_id, action_type=action_type, action_status=action_status,
        workflow_log_id=workflow_log_id,
    )


# ── Document extraction (ephemeral — not indexed) ─────────────────────────────

@router.post("/ask/extract")
async def extract_document_for_chat(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """
    Extract plain text from an uploaded document so the chat can inject it
    as context. Ephemeral — not persisted to the RAG knowledge base.
    """
    filename = (file.filename or "").lower()
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in _EXTRACT_ALLOWED_EXTS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(_EXTRACT_ALLOWED_EXTS))}",
        )

    contents = await file.read()
    if len(contents) > _EXTRACT_MAX_SIZE:
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
            "filename":  file.filename,
            "chars":     len(text),
            "text":      text[:_EXTRACT_MAX_CHARS],
            "truncated": len(text) > _EXTRACT_MAX_CHARS,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("extract.failed", filename=file.filename, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to process the uploaded file.")


# ── Blocking ask ──────────────────────────────────────────────────────────────

@router.post("/ask", response_model=WorkflowResponse, dependencies=[Depends(ask_rate_limiter)])
async def ask_ai(
    request: Request,
    body: QueryRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _run_workflow(request, body, user, db)


# ── Streaming ask ─────────────────────────────────────────────────────────────

@router.post("/ask/stream", dependencies=[Depends(ask_rate_limiter)])
async def ask_stream(
    request: Request,
    body: QueryRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    def _status(msg: str) -> dict:
        return {"data": json.dumps({"type": "status", "content": msg})}

    async def generate():
        yield _status("Analyzing your request…")

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

        # Real LLM synthesis for RAG-retrieved answers (lower confidence = needs synthesis)
        # Pre-written keyword-matched answers are streamed word-by-word (cheap, fast)
        use_real_stream = (
            result.source not in (None, "guardrail", "cache", "approval_gate", "error")
            and result.agent not in ("guardrail", "cache", "error", "multi_intent")
            and not (result.action_id or result.action_type)
            and result.confidence is not None
            and result.confidence < 90
        )

        if use_real_stream:
            from app.core.openai_client import async_stream_synthesis
            department = result.agent or "HR"
            async for token in async_stream_synthesis(
                question=body.question,
                context=answer,
                department=department,
            ):
                yield {"data": json.dumps({"type": "token", "content": token})}
        else:
            words = answer.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield {"data": json.dumps({"type": "token", "content": chunk})}
                await asyncio.sleep(0.025)

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
            "workflow_log_id": result.workflow_log_id,
        })}

    return EventSourceResponse(generate())


# ── Core workflow (shared between /ask and /ask/stream) ───────────────────────

async def _run_workflow(
    request: Request,
    body: QueryRequest,
    user: dict,
    db: AsyncSession,
) -> WorkflowResponse:
    start    = time.perf_counter()
    question = body.question
    rid      = getattr(request.state, "request_id", str(uuid.uuid4()))
    ip       = _client_ip(request)

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
        return WorkflowResponse(**guard)

    # ── Semantic cache ────────────────────────────────────────────────────────
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
        # Access workflow from FastAPI app state via the request object.
        # This avoids a circular import between ai.py → server.py → ai.py.
        workflow = request.app.state.workflow
        result = workflow.invoke({
            "session_id":  body.session_id,
            "user_input":  question,
            "request_id":  rid,
            "company_id":  company_id_str,
            "user_id":     user_sub,
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
    workflow_log_id_str: str | None = None

    if company_id_str:
        try:
            company_uuid = uuid.UUID(company_id_str)
            user_repo    = UserRepository(db)
            db_user      = await user_repo.get_by_username(user_sub)
            user_uuid    = db_user.id if db_user else None

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

            wf_repo = WorkflowLogRepository(db)
            wf_log  = await wf_repo.create(
                company_id=company_uuid, conversation_id=convo.id, user_id=user_uuid,
                session_id=body.session_id, department=result.get("agent", "Unknown"),
                agent=result.get("agent", "Unknown"), user_input=question,
                final_answer=answer, confidence=result.get("confidence") or 0,
                evaluation_score=result.get("evaluation_score"),
                steps=result.get("steps") or [],
                execution_metadata={
                    "request_id":    rid,
                    "response_time": rt,
                    "source":        result.get("source"),
                    "rag_used":      result.get("rag_used", False),
                    "keyword_match": result.get("keyword_match", False),
                },
            )
            workflow_log_id_str = str(wf_log.id)

            # Action record — only create when agent explicitly signals action intent
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
        workflow_log_id=workflow_log_id_str,
    )

    # Cache non-action responses (async, non-blocking)
    if not result.get("action_triggered"):
        asyncio.get_event_loop().run_in_executor(
            None,
            set_cached,
            question,
            cache_company,
            {
                "answer":           answer,
                "agent":            result.get("agent"),
                "confidence":       result.get("confidence"),
                "source":           result.get("source"),
                "action_triggered": False,
            },
        )

    return final_response


# ── Feedback ──────────────────────────────────────────────────────────────────

@router.post("/feedback", status_code=201)
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
    repo      = FeedbackRepository(db)
    fb        = await repo.create(
        company_id=company_uuid, workflow_log_id=workflow_log_uuid,
        user_id=db_user.id if db_user else None,
        rating=body.rating, comment=body.comment,
    )
    await db.commit()
    return {"id": str(fb.id), "rating": body.rating, "status": "saved"}
