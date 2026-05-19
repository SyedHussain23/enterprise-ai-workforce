"""
Enterprise AI Workforce — LangGraph Orchestration.

Node flow:
    ┌─────────┐
    │ planner │   ← ConversationEngine: classify intent, extract slots,
    └────┬────┘     handle SYSTEM / ACTION / FOLLOWUP short-circuits
         │
    ┌────▼──────────────────────────┐
    │ short_circuit?                │
    │  True  → report (skip agents) │
    │  False → router               │
    └───────────────────────────────┘
         │
    ┌────▼────┐   ← domain agent (HR / Finance / IT) for INFO queries
    │ router  │
    └────┬────┘
         │
    ┌────▼────┐   ← corrective RAG quality gate
    │  crag   │
    └────┬────┘
         │
    ┌────▼────┐   ← final confidence, evaluation, memory save
    │ report  │
    └─────────┘

Key design changes vs. old architecture:
  - planner now uses GPT-4o (via ConversationEngine) for true intent understanding
  - SYSTEM queries ("what do you do?") return platform capabilities immediately
  - ACTION queries with missing slots → clarification question saved to Redis,
    short_circuit=True so we don't hit the domain agent
  - ACTION queries with all slots → workflow created, short_circuit=True
  - FOLLOWUP queries → new slots merged into pending workflow, same decision tree
  - INFO queries → domain agents still handle them (policy knowledge stays useful)
    but LLM synthesis gives a natural answer instead of raw templates
"""
from datetime import datetime, timezone

from langgraph.graph import StateGraph

from app.agents.planner_agent import planner_agent
from app.agents.registry import AGENT_REGISTRY
from app.core.constants import DEPT_CONTACTS
from app.core.logger import get_logger, set_request_id
from app.evaluation.evaluator import evaluate_response
from app.memory.redis_memory import (
    clear_pending_workflow,
    get_history,
    get_pending_workflow,
    save_pending_workflow,
    save_turn,
)
from app.rag.crag import corrective_rag
from app.schemas.agent import AgentResponse
from app.utils.confidence import calculate_confidence
from app.utils.guardrails import get_fallback_response
from app.workflows.workflow_state import WorkflowState

logger = get_logger(__name__)


def build_workflow():
    graph = StateGraph(WorkflowState)

    # ── Planner node — ConversationEngine-powered ─────────────────────────────
    def planner_node(state: WorkflowState) -> dict:
        rid = state.get("request_id", "")
        if rid:
            set_request_id(rid)

        user_input = state.get("user_input", "")
        session_id = state.get("session_id", "")
        company_id = state.get("company_id") or "global"
        steps: list[str] = ["Planner → analyzing request"]

        history = get_history(session_id) if session_id else []
        if history:
            steps.append(f"Planner → loaded {len(history)} history messages")

        # ── Load pending workflow (multi-turn slot collection) ────────────────
        pending_wf = get_pending_workflow(session_id) if session_id else None
        if pending_wf:
            steps.append(
                f"Planner → pending workflow: {pending_wf.get('workflow_type')}, "
                f"missing: {pending_wf.get('missing_slots', [])}"
            )

        # ── ConversationEngine: deterministic-first intent + slot extraction ────
        # classify_and_extract() tries pure-Python detection first (no API call),
        # escalates to GPT-4o only for genuinely ambiguous queries, and always
        # produces a result — never silently falls back to FAQ behavior.
        try:
            from app.core.conversation_engine import get_engine, PLATFORM_CAPABILITIES
            from app.utils.workflow_slots import get_missing_slots, get_workflow_def, get_action_type

            engine = get_engine()
            classification = engine.classify_and_extract(user_input, history, pending_wf)
        except Exception as exc:
            logger.error("planner.engine_import_failed", error=str(exc))
            classification = {
                "intent_type": "INFO",
                "department": "HR",
                "workflow_type": None,
                "slots_extracted": {},
                "reasoning": f"Import error: {exc}",
            }

        intent_type   = classification.get("intent_type", "INFO")
        department    = classification.get("department", "IT")
        workflow_type = classification.get("workflow_type")
        new_slots     = classification.get("slots_extracted", {}) or {}

        # For FOLLOWUP intent: inherit workflow_type from pending state when LLM
        # doesn't re-specify it (the LLM knows the context but may omit the field)
        if intent_type == "FOLLOWUP" and not workflow_type and pending_wf:
            workflow_type = pending_wf.get("workflow_type")
            department = pending_wf.get("department", department)

        steps.append(
            f"Planner → intent={intent_type}, dept={department}, "
            f"workflow={workflow_type}"
        )
        logger.info(
            "planner.classified",
            intent=intent_type,
            department=department,
            workflow=workflow_type,
            reasoning=classification.get("reasoning", "")[:80],
        )

        # ══════════════════════════════════════════════════════════════════════
        # SYSTEM intent: "What do you do?" / "What are your capabilities?"
        # ══════════════════════════════════════════════════════════════════════
        if intent_type == "SYSTEM":
            steps.append("Planner → SYSTEM intent → returning platform capabilities")
            return {
                "answer": PLATFORM_CAPABILITIES,
                "agent": "system",
                "confidence": 99,
                "source": "system",
                "keyword_match": True,
                "rag_used": False,
                "action_triggered": False,
                "short_circuit": True,
                "steps": steps,
            }

        # ══════════════════════════════════════════════════════════════════════
        # ACTION / FOLLOWUP intent: slot collection flow
        # ══════════════════════════════════════════════════════════════════════
        if intent_type in ("ACTION", "FOLLOWUP") and workflow_type:
            try:
                from app.core.conversation_engine import get_engine
                from app.utils.workflow_slots import get_missing_slots, get_workflow_def, get_action_type
                engine = get_engine()
                wf_def = get_workflow_def(workflow_type)

                # Merge old (pending) slots with new slots extracted from this message
                if pending_wf and pending_wf.get("workflow_type") == workflow_type:
                    collected = {**pending_wf.get("collected_slots", {}), **new_slots}
                else:
                    # New workflow (different type, or no pending state)
                    collected = {k: v for k, v in new_slots.items() if v is not None}

                # Remove null/empty values from collected
                collected = {k: v for k, v in collected.items() if v is not None and str(v).strip()}

                # Which required slots are still missing?
                missing = get_missing_slots(workflow_type, collected)
                steps.append(
                    f"Planner → slots collected={list(collected.keys())}, "
                    f"missing={missing}"
                )

                if missing:
                    # ── Need more info: generate clarification question ────────
                    clarification = engine.generate_clarification(
                        workflow_type, collected, missing, user_input
                    )
                    # Save partial state for next turn
                    if session_id:
                        save_pending_workflow(session_id, {
                            "workflow_type": workflow_type,
                            "collected_slots": collected,
                            "missing_slots": missing,
                        })
                    steps.append(
                        f"Planner → asking for: {missing} → clarification generated"
                    )
                    logger.info(
                        "planner.clarifying",
                        workflow=workflow_type,
                        missing=missing,
                    )
                    return {
                        "answer": clarification,
                        "agent": department,
                        "confidence": 88,
                        "source": "workflow_intake",
                        "keyword_match": False,
                        "rag_used": False,
                        "action_triggered": False,
                        "short_circuit": True,
                        "steps": steps,
                    }

                else:
                    # ── All slots collected → create the workflow ─────────────
                    confirmation = engine.generate_workflow_confirmation(
                        workflow_type, collected
                    )
                    # Clear pending state — workflow is now complete
                    if session_id:
                        clear_pending_workflow(session_id)

                    action_type = get_action_type(workflow_type)
                    steps.append(
                        f"Planner → all slots collected → {action_type} workflow created"
                    )
                    logger.info(
                        "planner.workflow_created",
                        workflow=workflow_type,
                        action_type=action_type,
                        slots=list(collected.keys()),
                    )
                    return {
                        "answer": confirmation,
                        "agent": department,
                        "confidence": 96,
                        "source": "workflow_created",
                        "keyword_match": True,
                        "rag_used": False,
                        "action_triggered": True,
                        "action_type": action_type,
                        "action_payload": {
                            "slots": collected,
                            "raw_request": user_input,
                            "department": department,
                        },
                        "short_circuit": True,
                        "steps": steps,
                    }

            except Exception as exc:
                logger.error("planner.action_flow_failed", error=str(exc))
                # Fall through to legacy department routing
                steps.append(f"Planner → action flow error, falling back: {exc}")

        # ══════════════════════════════════════════════════════════════════════
        # INFO / APPROVAL / fallback: use legacy department routing
        # ══════════════════════════════════════════════════════════════════════
        try:
            result = planner_agent(user_input, history, company_id=company_id)
            routed_dept = result.get("department") or department or "IT"
        except Exception as exc:
            logger.error("planner.legacy_failed", error=str(exc))
            routed_dept = department or "IT"
            result = {"plan": "Fallback routing", "requires_approval": False}

        steps.append(f"Planner → INFO query → routing to {routed_dept} agent")
        logger.info("planner.info_routed", department=routed_dept)

        return {
            "agent": routed_dept,
            "plan": result.get("plan", ""),
            "requires_approval": result.get("requires_approval", False),
            "short_circuit": False,
            "steps": steps,
        }

    # ── Short-circuit gate: skip domain agents when planner handled it ────────
    def should_skip_router(state: WorkflowState) -> str:
        return "report" if state.get("short_circuit") else "router"

    # ── Router node — domain agents for INFO queries ──────────────────────────
    def router_node(state: WorkflowState) -> dict:
        agent_name = state.get("agent") or "IT"
        user_input = state.get("user_input", "")
        steps: list[str] = list(state.get("steps") or [])

        logger.info("node.router.start", agent=agent_name)
        steps.append(f"Router → selecting {agent_name} agent")

        if state.get("requires_approval"):
            steps.append("Approval gate → request blocked pending manager sign-off")
            contact = DEPT_CONTACTS.get(agent_name, DEPT_CONTACTS["default"])
            return {
                "answer": (
                    "This request requires manager approval.\n"
                    f"Please submit a formal request via the {agent_name} portal "
                    f"or contact {contact}."
                ),
                "confidence": 85,
                "source": "approval_gate",
                "agent": agent_name,
                "keyword_match": False,
                "rag_used": False,
                "steps": steps,
            }

        agent_fn = AGENT_REGISTRY.get(agent_name)
        if not agent_fn:
            logger.error("node.router.no_agent", agent=agent_name)
            steps.append(f"Router → no agent for {agent_name}, using fallback")
            fallback = get_fallback_response(agent_name)
            return {**fallback, "agent": agent_name, "steps": steps}

        steps.append(f"{agent_name} Agent → processing request")

        try:
            raw = agent_fn(user_input)
            result: AgentResponse = raw if isinstance(raw, AgentResponse) else AgentResponse(**raw)
        except Exception as exc:
            logger.error("node.router.agent_failed", agent=agent_name, error=str(exc))
            steps.append(f"{agent_name} Agent → failed, using fallback")
            fallback = get_fallback_response(agent_name)
            return {**fallback, "agent": agent_name, "steps": steps}

        answer = result.answer.strip()
        if not answer:
            logger.warning("node.router.empty_answer", agent=agent_name)
            fallback = get_fallback_response(agent_name)
            return {**fallback, "agent": agent_name, "steps": steps}

        # ── LLM synthesis for INFO responses ──────────────────────────────────
        # If the agent returned a policy template (not a triggered action),
        # use the ConversationEngine to synthesize a natural, targeted answer
        # instead of dumping the full template at the user.
        if not result.action_triggered and not result.rag_used:
            try:
                from app.core.conversation_engine import get_engine
                engine = get_engine()
                session_id = state.get("session_id", "")
                history = get_history(session_id) if session_id else []
                synthesized = engine.generate_info_response(
                    query=user_input,
                    department=agent_name,
                    policy_context=answer,
                    history=history,
                )
                if synthesized and len(synthesized) > 30:
                    answer = synthesized
                    steps.append(f"{agent_name} Agent → LLM synthesis applied")
            except Exception as exc:
                logger.warning("router.synthesis_failed", error=str(exc))
                # Keep the original agent answer — graceful degradation

        signal_confidence, _ = calculate_confidence(
            answer=answer,
            keyword_match=result.keyword_match,
            rag_used=result.rag_used,
            source=result.source,
        )
        confidence = max(signal_confidence, result.confidence or 0)

        logger.info("node.router.done", agent=agent_name, confidence=confidence)

        return {
            "answer": answer,
            "confidence": confidence,
            "source": result.source,
            "agent": agent_name,
            "keyword_match": result.keyword_match,
            "rag_used": result.rag_used,
            "action_triggered": result.action_triggered,
            "action_type": result.action_type,
            "action_payload": result.action_payload,
            "steps": steps,
        }

    # ── CRAG node ─────────────────────────────────────────────────────────────
    def crag_node(state: WorkflowState) -> dict:
        rag_used = state.get("rag_used", False)
        steps: list[str] = list(state.get("steps") or [])

        if not rag_used:
            return {"steps": steps}

        user_input = state.get("user_input", "")
        source = state.get("source") or "internal_kb"
        steps.append("CRAG → grading retrieval quality")

        try:
            crag_result = corrective_rag(user_input, grade=True)
            action = crag_result.get("crag_action", "pass")

            if action == "rewrite":
                rewritten = crag_result.get("rewritten_query", user_input)
                steps.append(f"CRAG → retrieval poor, rewrote: '{rewritten[:60]}'")
                steps.append("CRAG → re-retrieved with corrected query")
            elif action == "filter":
                steps.append("CRAG → filtered irrelevant chunks")
            else:
                steps.append("CRAG → retrieval quality: ✓ pass")

            new_context = crag_result.get("context", "")
            if new_context and action in {"rewrite", "filter"}:
                return {
                    "crag_context": new_context,
                    "crag_action": action,
                    "confidence": crag_result.get("confidence", state.get("confidence", 50)),
                    "source": crag_result.get("source") or source,
                    "steps": steps,
                }

            return {"crag_action": action, "steps": steps}

        except Exception as exc:
            logger.warning("node.crag.failed", error=str(exc))
            steps.append("CRAG → grading skipped (error)")
            return {"steps": steps}

    # ── Report node ───────────────────────────────────────────────────────────
    def report_node(state: WorkflowState) -> dict:
        query             = state.get("user_input", "")
        answer            = (state.get("answer") or "").strip()
        source            = state.get("source") or "internal_kb"
        agent             = state.get("agent") or "Unknown"
        keyword_match     = state.get("keyword_match", False)
        rag_used          = state.get("rag_used", False)
        action_triggered  = state.get("action_triggered", False)
        action_type       = state.get("action_type")
        action_payload    = state.get("action_payload")
        crag_action       = state.get("crag_action", "pass")
        steps: list[str]  = list(state.get("steps") or [])

        steps.append("Report → generating final response")

        if not answer:
            fallback = get_fallback_response(agent)
            answer = fallback["answer"]
            source = fallback["source"]

        signal_confidence, confidence_reason = calculate_confidence(
            answer=answer,
            keyword_match=keyword_match,
            rag_used=rag_used,
            source=source,
            action_triggered=action_triggered,
        )

        router_confidence = state.get("confidence", 0) or 0
        confidence = max(signal_confidence, router_confidence)

        if crag_action in {"filter", "rewrite"} and state.get("confidence"):
            confidence = min(confidence, state["confidence"])
            confidence_reason = f"CRAG-adjusted ({crag_action}): {confidence_reason}"

        try:
            evaluation_score = float(evaluate_response(query, answer, source))
        except Exception as exc:
            logger.warning("node.report.eval_failed", error=str(exc))
            evaluation_score = 0.0

        logger.info(
            "node.report.done",
            agent=agent,
            confidence=confidence,
            evaluation_score=evaluation_score,
            short_circuit=state.get("short_circuit", False),
        )

        session_id = state.get("session_id", "")
        if session_id:
            save_turn(session_id, query, answer)

        return {
            "status": "success",
            "answer": answer,
            "agent": agent,
            "confidence": confidence,
            "source": source,
            "steps": steps,
            "confidence_reason": confidence_reason,
            "evaluation_score": evaluation_score,
            "action_triggered": action_triggered,
            "action_type": action_type,
            "action_payload": action_payload,
            "crag_action": crag_action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Graph wiring ──────────────────────────────────────────────────────────
    graph.add_node("planner", planner_node)
    graph.add_node("router",  router_node)
    graph.add_node("crag",    crag_node)
    graph.add_node("report",  report_node)

    graph.set_entry_point("planner")

    # Conditional: planner may short-circuit directly to report
    # (SYSTEM response, slot-collection clarification, or completed workflow)
    graph.add_conditional_edges(
        "planner",
        should_skip_router,
        {"report": "report", "router": "router"},
    )

    graph.add_edge("router", "crag")
    graph.add_edge("crag",   "report")
    graph.set_finish_point("report")

    return graph.compile()
