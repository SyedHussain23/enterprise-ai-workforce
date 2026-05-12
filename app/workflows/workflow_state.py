import uuid
from typing import Optional, TypedDict


class WorkflowState(TypedDict, total=False):
    # ── Request identity ──────────────────────────────────────────────────────
    # These three are the minimum context needed for DB writes and multi-tenancy.
    # They are set by the API layer before invoking the graph — not inside nodes.
    request_id: str            # UUID string — correlation ID for log tracing
    session_id: str            # Frontend session ID (maps to Conversation row)
    company_id: Optional[str]  # Tenant UUID string — scopes every DB query
    user_id: Optional[str]     # Authenticated user UUID string

    # ── User input ────────────────────────────────────────────────────────────
    user_input: str

    # ── Planner output ────────────────────────────────────────────────────────
    agent: str
    plan: str
    requires_approval: bool

    # ── Router output ─────────────────────────────────────────────────────────
    answer: str
    confidence: int
    source: Optional[str]
    keyword_match: bool
    rag_used: bool
    action_triggered: bool
    action_type: Optional[str]
    action_payload: Optional[dict]

    # ── CRAG node output (Day 53) ────────────────────────────────────────────
    crag_action: Optional[str]     # "pass" | "filter" | "rewrite"
    crag_context: Optional[str]    # corrected context after rewrite/filter

    # ── Report output (final wire format) ────────────────────────────────────
    status: str
    steps: list[str]
    confidence_reason: Optional[str]
    evaluation_score: Optional[float]
    timestamp: str
