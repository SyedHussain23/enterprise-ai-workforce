import json

from langsmith import traceable
from openai import OpenAI

from app.core.config import settings
from app.core.constants import APPROVAL_KEYWORDS, DEPARTMENT_KEYWORDS
from app.core.logger import get_logger
from app.cost.cost_tracker import track_cost
from app.utils.fuzzy_match import normalize_query
from app.workflows.task_manager import determine_workflow

logger = get_logger(__name__)

# Lazy-initialized sync client — only instantiated on first LLM fallback call.
# Sync client is acceptable here because planner_agent is called from within
# the LangGraph graph which runs in a thread executor (not blocking the async
# event loop). Day 35 async migration will upgrade this.
_openai_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


_FALLBACK_RESULT = {
    "department": "IT",
    "plan": "Could not classify — routing to default",
    "priority": "normal",
    "requires_approval": False,
    "workflow": "default",
}


@traceable
def planner_agent(user_input: str, history: list, company_id: str = "global") -> dict:
    normalized = normalize_query(user_input)
    q = normalized.lower().strip()

    logger.info("planner.start", user_input=user_input, normalized=normalized)

    if not q or len(q) < 3:
        return _FALLBACK_RESULT

    # ── Keyword routing (fast path, no LLM call) ──────────────────────────────
    department: str | None = None
    plan = ""

    for dept, keywords in DEPARTMENT_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            department = dept
            plan = f"Keyword match → routed to {dept}"
            break

    # ── LLM classification (slow path, only when keywords miss) ───────────────
    if not department:
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an enterprise AI planner. "
                        "Classify the request into EXACTLY ONE: HR, IT, or Finance.\n"
                        "If unrelated to company operations, default to IT.\n"
                        'Respond ONLY with valid JSON: {"department": "HR or IT or Finance", "plan": "brief reason"}'
                    ),
                }
            ]
            for h in history:
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
            messages.append({"role": "user", "content": normalized})

            response = _get_client().chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
            track_cost(response.usage.prompt_tokens, response.usage.completion_tokens, company_id=company_id)

            parsed = json.loads(response.choices[0].message.content)
            raw = str(parsed.get("department", "IT")).strip().lower()
            department = "HR" if "hr" in raw else ("Finance" if "finance" in raw else "IT")
            plan = parsed.get("plan", "LLM classification")
            logger.info("planner.llm_classified", department=department, plan=plan)

        except Exception as exc:
            logger.error("planner.llm_failed", error=str(exc))
            department = "IT"
            plan = "LLM failed — default routing"

    requires_approval = any(kw in q for kw in APPROVAL_KEYWORDS)

    result = {
        "department": department,
        "plan": plan,
        "priority": "high" if requires_approval else "normal",
        "requires_approval": requires_approval,
        "workflow": determine_workflow(user_input),
    }
    logger.info("planner.result", **result)
    return result
