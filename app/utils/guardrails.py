# app/utils/guardrails.py
"""
Production-grade input guardrails for the Enterprise AI Workforce platform.

Checks (in order):
  1. Empty / too-short input
  2. Prompt injection detection
  3. PII detection (Emirates ID, credit card, passport, IBAN)
  4. Profanity / offensive language filter
  5. Gibberish detection
  6. Out-of-scope topic detection
  7. Allow-list pass-through

Arabic queries are explicitly supported — Arabic HR/IT/Finance terms are
in ALLOWED_KEYWORDS and must never be blocked by the gibberish filter.
"""
from __future__ import annotations

import re
import unicodedata

from app.core.constants import (
    ALLOWED_KEYWORDS,
    DEPT_CONTACTS,
    OUT_OF_SCOPE_KEYWORDS,
    PII_PATTERNS,
    PROFANITY_WORDS,
    PROMPT_INJECTION_PHRASES,
)

# ── Compile PII patterns once at module load ──────────────────────────────────
_PII_COMPILED: dict[str, re.Pattern] = {
    name: re.compile(pattern, re.IGNORECASE)
    for name, pattern in PII_PATTERNS.items()
}

# ── Arabic Unicode block range ────────────────────────────────────────────────
# U+0600–U+06FF covers Arabic script; we detect Arabic queries to skip the
# vowel-ratio gibberish check (Arabic has far fewer Latin vowels).
_ARABIC_RE = re.compile(r"[؀-ۿ]")

# ── Common English stop-words to anchor gibberish check ──────────────────────
_COMMON_WORDS = frozenset([
    "what", "how", "when", "where", "who", "why", "can", "is", "the",
    "my", "do", "i", "need", "want", "help", "tell", "show", "get",
    "find", "about", "please", "for", "me", "are", "does", "a", "an",
    "will", "should", "would", "could", "have", "has", "had", "be",
    "to", "of", "in", "on", "at", "by", "with", "from", "into",
    "apply", "check", "submit", "request", "update", "approve",
])


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_guardrail_response(query: str) -> dict | None:
    """
    Returns a block dict if the query must be stopped.
    Returns None if the query is allowed to proceed to the workflow.

    Checks are ordered cheapest-first so we short-circuit early.
    """
    if not query or not query.strip():
        return _block(
            answer="⚠️ Please enter a valid question.",
            reason="Empty input rejected",
            step="⚠️ Guardrail → empty input blocked",
        )

    # Normalise: strip leading/trailing whitespace, collapse runs of spaces
    raw   = query.strip()
    clean = re.sub(r"\s+", " ", raw)
    lower = clean.lower()

    # 1. Minimum length
    if len(clean) < 3:
        return _block(
            answer="⚠️ Please enter a valid question.",
            reason="Input too short",
            step="⚠️ Guardrail → input too short",
        )

    # 1b. Greeting / small-talk — give a friendly reply, skip the full workflow
    _GREETINGS = frozenset([
        "hi", "hello", "hey", "hiya", "howdy", "greetings", "salam",
        "hi there", "hello there", "hey there", "good morning", "good afternoon",
        "good evening", "morning", "afternoon", "evening",
        "how are you", "how r u", "how are u", "how're you", "how do you do",
        "what's up", "whats up", "sup", "yo",
        "hi how r u", "hi how are you", "hello how are you", "hey how are you",
        "hi how are u", "hi how r you",
    ])
    _normalised = lower.strip().rstrip("!?. ")
    if _normalised in _GREETINGS or lower in {g + "!" for g in _GREETINGS}:
        return {
            "answer": (
                "Hello! 👋 I'm the **Enterprise AI Workforce Assistant**.\n\n"
                "I'm here to help you with company questions across:\n"
                "- 👩‍💼 **HR** — Leave, gratuity, onboarding, payslips\n"
                "- 💻 **IT** — Password reset, VPN, MFA, device support\n"
                "- 💰 **Finance** — Expenses, salary, VAT, procurement\n\n"
                "What can I help you with today?"
            ),
            "agent": "assistant",
            "confidence": 100,
            "source": "guardrail",
            "status": "success",
            "steps": ["Guardrail → greeting detected"],
            "confidence_reason": "Direct greeting — no workflow needed",
            "evaluation_score": 0.0,
            "response_time": 0.0,
            "action_id": None,
            "action_type": None,
            "action_status": None,
            "timestamp": "",
        }

    # 1c. Language / UI preference requests
    _LANG_REQUESTS = [
        "talk in arabic", "speak arabic", "reply in arabic", "answer in arabic",
        "use arabic", "in arabic please", "باللغة العربية", "بالعربي",
        "talk in english", "speak english", "reply in english", "use english",
        "switch to arabic", "switch to english", "change language",
    ]
    if any(phrase in lower for phrase in _LANG_REQUESTS):
        is_arabic_req = any(w in lower for w in ["arabic", "عربي", "عربية"])
        return {
            "answer": (
                "**Language / UI Preference**\n\n"
                + (
                    "To switch the interface to Arabic (RTL), click the **عربي** button "
                    "in the top-right corner of the screen. Once activated, the entire "
                    "interface — including menus and responses — will display in Arabic.\n\n"
                    "أنا أيضًا أفهم الأسئلة المكتوبة بالعربية مباشرةً."
                    if is_arabic_req else
                    "The interface language is currently set to English. "
                    "You can switch to Arabic by clicking the **عربي** button "
                    "in the top-right corner of the screen."
                )
            ),
            "agent": "assistant",
            "confidence": 100,
            "source": "guardrail",
            "status": "success",
            "steps": ["Guardrail → language preference request"],
            "confidence_reason": "UI language instruction — no workflow needed",
            "evaluation_score": 0.0,
            "response_time": 0.0,
            "action_id": None,
            "action_type": None,
            "action_status": None,
            "timestamp": "",
        }

    # 1d. Name / identity queries
    _NAME_QUERIES = [
        "what is your name", "what's your name", "whats your name",
        "who are you", "ur name", "your name", "tell me your name",
        "what are you", "who r u",
    ]
    if any(phrase in lower for phrase in _NAME_QUERIES):
        return {
            "answer": (
                "I'm the **Enterprise AI Workforce Assistant** — an AI built to help "
                "employees at your company with HR, IT, and Finance questions.\n\n"
                "I know UAE Labour Law, company policies, and can raise IT tickets or "
                "initiate leave/expense requests on your behalf.\n\n"
                "What can I help you with?"
            ),
            "agent": "assistant",
            "confidence": 100,
            "source": "guardrail",
            "status": "success",
            "steps": ["Guardrail → identity query"],
            "confidence_reason": "Identity query — no workflow needed",
            "evaluation_score": 0.0,
            "response_time": 0.0,
            "action_id": None,
            "action_type": None,
            "action_status": None,
            "timestamp": "",
        }

    # 2. Prompt injection
    injection_phrase = _detect_prompt_injection(lower)
    if injection_phrase:
        return _block(
            answer=(
                "⚠️ Your message contains content that cannot be processed.\n\n"
                "I'm here to help with company HR, IT, and Finance questions. "
                "Please ask a work-related question."
            ),
            reason=f"Prompt injection detected: '{injection_phrase}'",
            step="⚠️ Guardrail → prompt injection blocked",
        )

    # 3. PII detection — warn and sanitise rather than hard-block
    pii_hit = _detect_pii(clean)
    if pii_hit:
        return _block(
            answer=(
                f"⚠️ Your message appears to contain sensitive personal information "
                f"({pii_hit}).\n\n"
                "For security, please **do not share** Emirates IDs, passport numbers, "
                "credit card numbers, or bank account details in this chat.\n\n"
                "Rephrase your question without including personal identification numbers "
                "and I'll be happy to help."
            ),
            reason=f"PII detected: {pii_hit}",
            step=f"⚠️ Guardrail → PII ({pii_hit}) blocked",
        )

    # 4. Profanity / offensive language
    profanity_hit = _detect_profanity(lower)
    if profanity_hit:
        return _block(
            answer=(
                "⚠️ Your message contains language that is not appropriate for "
                "this workplace assistant.\n\n"
                "Please rephrase your question professionally and I'll be glad to help."
            ),
            reason=f"Profanity detected: '{profanity_hit}'",
            step="⚠️ Guardrail → profanity blocked",
        )

    # 5. Gibberish check (skipped for Arabic queries)
    is_arabic = bool(_ARABIC_RE.search(clean))
    if not is_arabic and _is_gibberish(lower):
        return _block(
            answer=(
                "Sorry, I couldn't understand your request. "
                "Please ask a clear company-related question.\n\n"
                "**Try asking:**\n"
                "- What is the annual leave policy?\n"
                "- How do I reset my password?\n"
                "- How do I submit an expense claim?\n"
                "- What is the UAE gratuity formula?\n"
                "- How do I connect to VPN?"
            ),
            reason="Gibberish or unrecognisable input",
            step="⚠️ Guardrail → gibberish input blocked",
        )

    # 6. Out-of-scope topic check
    if _is_out_of_scope(lower):
        return _block(
            answer=(
                "⚠️ This assistant only handles company-related queries.\n\n"
                "**I can help with:**\n"
                "- 👩‍💼 **HR:** Leave, gratuity, onboarding, payslip, grievances\n"
                "- 💻 **IT:** Password reset, VPN, MFA, device issues, phishing\n"
                "- 💰 **Finance:** Expenses, salary, VAT, procurement, budgets\n\n"
                "Please ask a work-related question."
            ),
            reason="Out of scope query blocked",
            step="⚠️ Guardrail → out of scope blocked",
        )

    return None  # ✅ Query is clean — proceed to workflow


def get_fallback_response(agent: str = "Unknown") -> dict:
    """
    Default fallback when the agent returns nothing useful.
    Called from workflow_graph report_node or router_node.
    """
    contact = DEPT_CONTACTS.get(agent, DEPT_CONTACTS["default"])
    return {
        "answer": (
            f"I couldn't find exact information for your query.\n\n"
            f"**Please contact the {agent} team directly:**\n"
            f"📧 {contact}\n\n"
            "Or try rephrasing your question with more specific terms.\n\n"
            "**Example questions:**\n"
            "- What is the annual leave policy?\n"
            "- How do I reset my password?\n"
            "- How do I submit an expense claim?"
        ),
        "agent":             agent,
        "confidence":        40,
        "source":            "fallback",
        "keyword_match":     False,
        "rag_used":          False,
        "confidence_reason": "Low confidence — no relevant data found",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Detection helpers
# ─────────────────────────────────────────────────────────────────────────────

def _detect_prompt_injection(lower: str) -> str | None:
    """Return the matched injection phrase, or None if clean."""
    for phrase in PROMPT_INJECTION_PHRASES:
        if phrase in lower:
            return phrase
    return None


def _detect_pii(text: str) -> str | None:
    """
    Return a human-readable PII type label if found, or None.

    Note: The bank_account pattern (10-16 consecutive digits) has a high
    false-positive rate for things like employee IDs or phone numbers, so
    we only flag it when no other pattern matched AND the number appears
    isolated (surrounded by whitespace or start/end of string).
    """
    # Check high-confidence patterns first
    high_confidence = ["emirates_id", "credit_card", "iban", "passport"]
    for name in high_confidence:
        if _PII_COMPILED[name].search(text):
            label = name.replace("_", " ").title()
            return label

    # Bank account — require word boundaries and length 10-16
    ba_pattern = re.compile(r"(?<!\d)\d{10,16}(?!\d)")
    match = ba_pattern.search(text)
    if match:
        return "Bank Account Number"

    return None


def _detect_profanity(lower: str) -> str | None:
    """Return the matched profanity word, or None if clean."""
    # Check exact word matches first
    words = re.findall(r"\b\w+\b", lower)
    for word in words:
        if word in PROFANITY_WORDS:
            return word

    # Check prefix matches (catches "fucking", "bullshit", etc.)
    for base in PROFANITY_WORDS:
        if " " in base:
            # Multi-word phrase — substring check
            if base in lower:
                return base
        else:
            # Check if any token starts with the base (e.g., "fucking" starts with "fuck")
            for word in words:
                if word.startswith(base) and len(word) <= len(base) + 4:
                    return base

    return None


def _is_gibberish(lower: str) -> bool:
    """
    Heuristic gibberish detection. Returns True if the text looks like
    random characters rather than a real question.

    Logic:
      - Single digit or pure number → gibberish
      - Fewer than 3 characters → too short (caught earlier, but double-check)
      - All characters are consonants with vowel ratio < 10% AND no known
        keywords → likely keyboard mashing
      - No vowels at all and no common words and no known keywords → gibberish
    """
    stripped = lower.strip()

    if len(stripped) < 3:
        return True

    if stripped.isdigit():
        return True

    # If the query contains any known keyword → definitely not gibberish
    if any(kw in lower for kw in ALLOWED_KEYWORDS):
        return False

    # If it contains any common stop-word → probably a real question
    tokens = set(re.findall(r"\b\w+\b", lower))
    if tokens & _COMMON_WORDS:
        return False

    # Vowel-ratio check on alphabetical characters only
    letters = [c for c in stripped if c.isalpha()]
    if len(letters) > 5:
        vowels      = set("aeiou")
        vowel_ratio = sum(1 for c in letters if c in vowels) / len(letters)
        if vowel_ratio < 0.08:
            return True

    return False


def _is_out_of_scope(lower: str) -> bool:
    """
    Returns True if the query matches an out-of-scope topic AND has no
    department-specific keyword that would redeem it.

    Examples:
      "football tournament at office" → redeemed by "office" (department kw)
      "news about company leave policy" → redeemed by "leave" (HR kw)
      "who won the cricket world cup" → NOT redeemed → blocked
    """
    from app.core.constants import DEPARTMENT_KEYWORDS
    matches_oos = any(kw in lower for kw in OUT_OF_SCOPE_KEYWORDS)
    if not matches_oos:
        return False

    # Redemption: only department-specific keywords count, not generic stop-words
    dept_keywords = [kw for kws in DEPARTMENT_KEYWORDS.values() for kw in kws]
    has_dept_kw = any(kw in lower for kw in dept_keywords)
    return not has_dept_kw


# ─────────────────────────────────────────────────────────────────────────────
# Internal block builder
# ─────────────────────────────────────────────────────────────────────────────

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
