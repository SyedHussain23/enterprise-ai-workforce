# app/utils/guardrails.py

from app.core.constants import ALLOWED_KEYWORDS, DEPT_CONTACTS, OUT_OF_SCOPE_KEYWORDS


def is_gibberish(query: str) -> bool:
    query_lower = query.lower().strip()

    if len(query_lower) < 3:
        return True

    if query_lower.isdigit():
        return True

    letters = [c for c in query_lower if c.isalpha()]
    if len(letters) > 4:
        vowels      = set("aeiou")
        vowel_ratio = sum(1 for c in letters if c in vowels) / len(letters)
        if vowel_ratio < 0.1:
            return True

    common = [
        "what", "how", "when", "where", "who", "why", "can", "is",
        "the", "my", "do", "i", "need", "want", "help", "tell",
        "show", "get", "find", "about", "please", "for", "me",
        "are", "does", "a",
    ]
    has_known  = any(kw in query_lower for kw in ALLOWED_KEYWORDS)
    has_common = any(w in query_lower.split() for w in common)

    return not has_known and not has_common


def get_guardrail_response(query: str) -> dict | None:
    """
    Returns block dict if query must be stopped.
    Returns None if query is allowed to proceed.
    """
    # ✅ FIX 3 — Input validation first
    if not query or not query.strip():
        return _block(
            answer = "⚠️ Please enter a valid question.",
            reason = "Empty input rejected",
            step   = "⚠️ Guardrail → empty input blocked",
        )

    query_lower = query.lower().strip()

    # Too short after strip
    if len(query_lower) < 2:
        return _block(
            answer = "⚠️ Please enter a valid question.",
            reason = "Input too short",
            step   = "⚠️ Guardrail → input too short",
        )

    # Gibberish
    if is_gibberish(query):
        return _block(
            answer = (
                "Sorry, I couldn't understand your request. "
                "Please ask a valid company-related question.\n\n"
                "Try asking:\n"
                "- What is the leave policy?\n"
                "- How do I reset my password?\n"
                "- How do I submit an expense claim?"
            ),
            reason = "Gibberish or unrecognisable input",
            step   = "⚠️ Guardrail → gibberish input blocked",
        )

    # Out of scope
    if any(kw in query_lower for kw in OUT_OF_SCOPE_KEYWORDS):
        return _block(
            answer = (
                "⚠️ This system only handles company-related queries.\n\n"
                "I can help with:\n"
                "- 👩‍💼 HR: Leave, onboarding, employee matters\n"
                "- 💻 IT: Password reset, VPN, system access\n"
                "- 💰 Finance: Salary, expenses, reimbursements"
            ),
            reason = "Out of scope query blocked",
            step   = "⚠️ Guardrail → out of scope blocked",
        )

    return None  # ✅ Proceed


def get_fallback_response(agent: str = "Unknown") -> dict:
    """
    ✅ FIX 2 — Default fallback when agent returns nothing.
    Called from workflow_graph report_node or router_node.
    """
    contact = DEPT_CONTACTS.get(agent, DEPT_CONTACTS["default"])

    return {
        "answer": (
            f"I couldn't find exact information for your query.\n\n"
            f"Please contact the {agent} team directly:\n"
            f"📧 {contact}\n\n"
            "Or try rephrasing your question with more specific terms."
        ),
        "agent":             agent,
        "confidence":        40,
        "source":            "fallback",
        "keyword_match":     False,
        "rag_used":          False,
        "confidence_reason": "Low confidence — no relevant data found",
    }


def _block(answer: str, reason: str, step: str) -> dict:
    return {
        "status":            "error",
        "answer":            answer,
        "agent":             "guardrail",
        "confidence":        0,
        "source":            "guardrail",
        "steps":             [step],
        "confidence_reason": reason,
        "evaluation_score":  0,
        "response_time":     0,
    }