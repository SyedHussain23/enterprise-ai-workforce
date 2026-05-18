from datetime import datetime, timezone

from langgraph.graph import StateGraph

from app.agents.planner_agent import planner_agent
from app.agents.registry import AGENT_REGISTRY
from app.core.constants import DEPT_CONTACTS
from app.core.logger import get_logger, set_request_id
from app.evaluation.evaluator import evaluate_response
from app.memory.redis_memory import get_history, save_turn
from app.rag.crag import corrective_rag
from app.schemas.agent import AgentResponse
from app.utils.confidence import calculate_confidence
from app.utils.guardrails import get_fallback_response
from app.workflows.workflow_state import WorkflowState

logger = get_logger(__name__)


def build_workflow():
    graph = StateGraph(WorkflowState)

    # ── Planner node ──────────────────────────────────────────────────────────
    def planner_node(state: WorkflowState) -> dict:
        rid = state.get("request_id", "")
        if rid:
            set_request_id(rid)

        user_input = state.get("user_input", "")
        session_id = state.get("session_id", "")
        company_id = state.get("company_id") or "global"
        logger.info("node.planner.start", user_input=user_input)

        steps: list[str] = ["Planner → analyzing request"]

        history = get_history(session_id) if session_id else []
        if history:
            steps.append(f"Planner → loaded {len(history)} previous messages from memory")

        try:
            result = planner_agent(user_input, history, company_id=company_id)
            department = result.get("department") or "IT"
        except Exception as exc:
            logger.error("node.planner.failed", error=str(exc))
            department = "IT"
            result = {"plan": "Planner failed — default routing", "requires_approval": False}

        steps.append(f"Planner → classified as {department}")
        logger.info("node.planner.done", department=department)

        return {
            "agent": department,
            "plan": result.get("plan", ""),
            "requires_approval": result.get("requires_approval", False),
            "steps": steps,
        }

    # ── Router node ───────────────────────────────────────────────────────────
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
            steps.append(f"Router → no agent registered for {agent_name}, using fallback")
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

        signal_confidence, _ = calculate_confidence(
            answer=answer,
            keyword_match=result.keyword_match,
            rag_used=result.rag_used,
            source=result.source,
        )
        # Trust the agent's own certainty when it's higher than signal-based score.
        # Hardcoded authoritative responses (keyword_match=True, rag_used=False)
        # correctly return high confidence that signal scoring undervalues.
        confidence = max(signal_confidence, result.confidence or 0)

        logger.info("node.router.done", agent=agent_name, confidence=confidence, source=result.source)

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

    # ── CRAG node (Day 53) ────────────────────────────────────────────────────
    def crag_node(state: WorkflowState) -> dict:
        """
        Corrective RAG gate. Only activates when the router used RAG retrieval.
        For keyword/policy answers (rag_used=False), pass straight through.
        """
        rag_used = state.get("rag_used", False)
        steps: list[str] = list(state.get("steps") or [])

        if not rag_used:
            # Keyword or policy answer — CRAG not needed, skip silently
            return {"steps": steps}

        user_input = state.get("user_input", "")
        answer = state.get("answer", "")
        source = state.get("source") or "internal_kb"
        steps.append("CRAG → grading retrieval quality")

        try:
            crag_result = corrective_rag(user_input, grade=True)
            action = crag_result.get("crag_action", "pass")

            if action == "rewrite":
                rewritten = crag_result.get("rewritten_query", user_input)
                steps.append(f"CRAG → retrieval poor, rewrote query: '{rewritten[:60]}'")
                steps.append("CRAG → re-retrieved with corrected query")
            elif action == "filter":
                steps.append("CRAG → filtered irrelevant chunks")
            else:
                steps.append("CRAG → retrieval quality: ✓ pass")

            # If CRAG found a better context, update answer source/confidence
            # but keep the agent's structured answer if it was keyword-matched
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
        query = state.get("user_input", "")
        answer = (state.get("answer") or "").strip()
        source = state.get("source") or "internal_kb"
        agent = state.get("agent") or "Unknown"
        keyword_match = state.get("keyword_match", False)
        rag_used = state.get("rag_used", False)
        action_triggered = state.get("action_triggered", False)
        action_type = state.get("action_type")
        action_payload = state.get("action_payload")
        crag_action = state.get("crag_action", "pass")
        steps: list[str] = list(state.get("steps") or [])

        steps.append("Report → generating final response")
        logger.info("node.report.start", agent=agent, answer_len=len(answer), crag_action=crag_action)

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

        # Preserve the agent's own confidence from router_node.
        # router_node already stored max(signal, agent_confidence) in state.
        # report_node must not discard it by recalculating from signals alone.
        # Example: keyword-match HR answer has agent.confidence=90 but
        # signal-only scoring gives 60 → report must honour the 90.
        router_confidence = state.get("confidence", 0) or 0
        confidence = max(signal_confidence, router_confidence)

        # CRAG-corrected confidence takes precedence over router's score
        # (CRAG penalises confidence when irrelevant chunks were filtered)
        if crag_action in {"filter", "rewrite"} and state.get("confidence"):
            crag_confidence = state["confidence"]
            confidence = min(confidence, crag_confidence)  # CRAG can only lower, not raise
            confidence_reason = f"CRAG-adjusted ({crag_action}): {confidence_reason}"
        elif confidence >= 80:
            confidence_reason = confidence_reason.replace("High confidence", "High confidence")

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
            crag_action=crag_action,
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
    graph.add_node("router", router_node)
    graph.add_node("crag", crag_node)
    graph.add_node("report", report_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "router")
    graph.add_edge("router", "crag")    # Day 53: CRAG gate after router
    graph.add_edge("crag", "report")
    graph.set_finish_point("report")

    return graph.compile()
