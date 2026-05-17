# app/utils/multi_intent.py
from __future__ import annotations

from app.agents.registry import AGENT_REGISTRY
from app.core.constants import DEPARTMENT_KEYWORDS, DEPT_ICONS
from app.core.logger import get_logger

logger = get_logger(__name__)

INTENT_KEYWORDS = DEPARTMENT_KEYWORDS


def detect_intents(query: str) -> list[str]:
    """Return list of departments detected in query"""
    query_lower = query.lower()
    matched = []
    for dept, keywords in INTENT_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            matched.append(dept)
    return matched


def handle_multi_intent(query: str, departments: list[str]) -> dict:
    """
    Split query across multiple agents and combine results.
    Returns single unified response dict.
    """
    results     = []
    combined    = []
    total_conf  = 0
    sources     = []

    for dept in departments:
        agent_fn = AGENT_REGISTRY.get(dept)
        if not agent_fn:
            continue

        try:
            raw    = agent_fn(query)
            # Agents return AgentResponse (Pydantic model) — normalise to dict
            result = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw)
            answer = (result.get("answer") or "No information found.").strip()
            confidence = result.get("confidence", 60)
            source     = result.get("source", f"{dept.lower()}_kb")

            results.append({
                "dept":       dept,
                "answer":     answer,
                "confidence": confidence,
                "source":     source,
            })

            combined.append(f"**{_dept_icon(dept)} {dept}:**\n{answer}")
            total_conf += confidence
            sources.append(source)

        except Exception as e:
            combined.append(f"**{dept}:** ⚠️ Could not retrieve information.")
            logger.error("multi_intent.agent_failed", dept=dept, error=str(e))

    # Build unified answer
    if not combined:
        return {
            "answer":            "Sorry, I couldn't process your requests.",
            "agent":             "multi_intent",
            "confidence":        0,
            "source":            "fallback",
            "confidence_reason": "No agents returned data",
        }

    header        = f"I handled both your requests:\n\n"
    full_answer   = header + "\n\n---\n\n".join(combined)
    avg_conf      = round(total_conf / len(results)) if results else 0
    combined_src  = " + ".join(sources)

    return {
        "answer":            full_answer,
        "agent":             "multi_intent",
        "confidence":        avg_conf,
        "source":            combined_src,
        "confidence_reason": f"Multi-intent: handled {', '.join(departments)}",
    }


def _dept_icon(dept: str) -> str:
    return DEPT_ICONS.get(dept, "🤖")