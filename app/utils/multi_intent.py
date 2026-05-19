# app/utils/multi_intent.py
from __future__ import annotations

import re

from app.agents.registry import AGENT_REGISTRY
from app.core.constants import DEPARTMENT_KEYWORDS, DEPT_ICONS
from app.core.logger import get_logger

logger = get_logger(__name__)

INTENT_KEYWORDS = DEPARTMENT_KEYWORDS

# Short keywords (≤3 chars) that are only safe as whole words.
# Substring matching for these causes false positives (e.g. "po" inside "policy").
_SHORT_KW_THRESHOLD = 3


def _keyword_matches(kw: str, text: str) -> bool:
    """
    Match keyword against text.
    - Multi-word phrases (contain a space): substring match is fine.
    - Short single tokens (≤3 chars): require whole-word boundary match.
    - Longer single tokens (>3 chars): substring match is fine.
    """
    if " " in kw:
        # Phrase: match as-is (e.g. "annual leave", "purchase order")
        return kw in text
    if len(kw) <= _SHORT_KW_THRESHOLD:
        # Short token: whole-word only (e.g. "po", "ar", "ap", "wfh")
        return bool(re.search(rf"\b{re.escape(kw)}\b", text))
    # Longer token: substring is fine (e.g. "payroll", "gratuity")
    return kw in text


def detect_intents(query: str) -> list[str]:
    """
    Return list of departments whose keywords are genuinely present in query.
    Uses word-boundary matching for short keywords to avoid false positives
    (e.g. 'po' inside 'policy' triggering Finance for an HR question).

    INFORMATIONAL QUERY SHORT-CIRCUIT:
      A question like "How do I apply for a salary advance?" was triggering
      multi-intent (HR via "career"/"promotion" keyword + Finance via "salary
      advance"), producing a confused response with two unrelated agents.
      Single-question informational queries are coalesced to *at most one*
      department so we never spuriously split a how-to.
    """
    from app.utils.intent_classifier import is_informational_query

    query_lower = query.lower()
    matched = []
    for dept, keywords in INTENT_KEYWORDS.items():
        if any(_keyword_matches(kw, query_lower) for kw in keywords):
            matched.append(dept)

    # If the user is asking a single informational question, never fan out
    # to multiple agents — pick the strongest match (the one with the most
    # keyword hits, falling back to the first deterministic order).
    if len(matched) > 1 and is_informational_query(query):
        best = None
        best_score = -1
        for dept in matched:
            score = sum(
                1 for kw in INTENT_KEYWORDS[dept]
                if _keyword_matches(kw, query_lower)
            )
            if score > best_score:
                best_score = score
                best = dept
        return [best] if best else matched[:1]

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