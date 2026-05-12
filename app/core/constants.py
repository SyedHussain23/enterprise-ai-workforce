"""
Single source of truth for department routing, keyword classification,
and source filtering across the entire platform.

Any file that needs "what keywords belong to which department" imports
from here — never re-defines it locally.
"""
from typing import Final


# ── Department routing keywords ──────────────────────────────────────────────
# Used by: planner_agent (routing), multi_intent (intent detection),
#          guardrails (scope validation), rag_tool (source filtering)
DEPARTMENT_KEYWORDS: Final[dict[str, list[str]]] = {
    "HR": [
        "leave", "vacation", "sick", "holiday", "onboarding",
        "resignation", "hire", "employee", "hr", "annual",
        "paternity", "maternity", "parental", "notice", "quit",
        "attendance", "medical",
    ],
    "IT": [
        "password", "login", "vpn", "laptop", "software",
        "system", "network", "access", "reset", "computer",
        "device", "email", "ticket", "provision", "account",
    ],
    "Finance": [
        "salary", "payment", "bonus", "expense", "invoice",
        "budget", "reimbursement", "finance", "payroll",
        "raise", "increment", "claim", "receipt", "vendor",
    ],
}

# ── All allowed keywords for scope guardrail ──────────────────────────────────
# Built from DEPARTMENT_KEYWORDS + generic enterprise terms
ALLOWED_KEYWORDS: Final[list[str]] = [
    kw
    for keywords in DEPARTMENT_KEYWORDS.values()
    for kw in keywords
] + [
    "company", "office", "work", "manager", "team", "department",
    "report", "request", "approval", "portal", "process", "policy",
    "benefits", "it",
]

# ── Out-of-scope topics to reject ────────────────────────────────────────────
OUT_OF_SCOPE_KEYWORDS: Final[list[str]] = [
    "ipl", "cricket", "football", "soccer", "sports", "movie", "film",
    "recipe", "cook", "weather", "stock", "crypto", "bitcoin", "nft",
    "game", "play", "music", "song", "news", "politics", "celebrity",
    "actor", "actress", "instagram", "tiktok", "youtube", "netflix",
]

# ── Approval-required keywords ────────────────────────────────────────────────
APPROVAL_KEYWORDS: Final[list[str]] = [
    "salary", "bonus", "payment", "raise", "increment", "budget",
]

# ── RAG source prefix → department mapping ───────────────────────────────────
# Used by rag_tool to filter cross-department documents
DEPT_SOURCE_PREFIXES: Final[dict[str, str]] = {
    "hr": "HR",
    "it": "IT",
    "finance": "Finance",
}

# ── RAG keyword → expected source prefix mapping ─────────────────────────────
QUERY_SOURCE_MAP: Final[dict[str, str]] = {
    "leave": "hr",     "vacation": "hr",   "sick": "hr",
    "onboard": "hr",   "employee": "hr",   "resignation": "hr",
    "salary": "finance", "expense": "finance", "bonus": "finance",
    "payroll": "finance", "invoice": "finance", "budget": "finance",
    "password": "it",  "vpn": "it",        "laptop": "it",
    "reset": "it",     "login": "it",      "software": "it",
}

# ── RAG relevance scoring keywords ───────────────────────────────────────────
RAG_PRIORITY_KEYWORDS: Final[dict[str, list[str]]] = {
    "leave":    ["leave", "annual", "sick", "policy", "holiday", "vacation"],
    "salary":   ["salary", "bonus", "payment", "payroll", "increment"],
    "password": ["password", "reset", "login", "credentials", "access"],
    "expense":  ["expense", "reimbursement", "claim", "receipt", "budget"],
    "vpn":      ["vpn", "remote", "network", "cisco", "access"],
    "laptop":   ["laptop", "device", "computer", "equipment"],
}

# ── Verified source names (boost confidence score) ───────────────────────────
VERIFIED_SOURCES: Final[list[str]] = [
    "hr_policy", "it_policy", "finance_policy",
    "hr_1", "it_1", "finance_1",
]

# ── Department contact emails ─────────────────────────────────────────────────
DEPT_CONTACTS: Final[dict[str, str]] = {
    "HR": "hr@company.com",
    "IT": "it-support@company.com",
    "Finance": "finance@company.com",
    "default": "support@company.com",
}

# ── Department display icons ──────────────────────────────────────────────────
DEPT_ICONS: Final[dict[str, str]] = {
    "HR": "👩‍💼",
    "IT": "💻",
    "Finance": "💰",
}
