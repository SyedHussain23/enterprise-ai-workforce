"""
Intent classifier — distinguishes informational queries from action requests.

WHY THIS EXISTS
  An agent receiving "How do I submit an expense claim?" should EXPLAIN the
  process, not silently file a claim. Without this guard, any query that
  contains an action keyword ("submit expense", "salary advance", "apply
  leave") triggers a downstream workflow even when the user is just asking
  how it works — which is exactly the bug reported in production.

USAGE
    if is_informational_query(query):
        # short-circuit to policy answer — never set action_triggered=True
        ...
    else:
        # this is a real action request — proceed with the workflow

The check is intentionally conservative: it only flags clear-cut info queries
(starts with What/How/When/Where/Why or "tell me / explain") AND lacks a
strong personal-action signal ("apply for me", "submit it now", "do it").
False negatives go to the agent's action branch (existing behaviour);
false positives merely degrade an action request into a policy answer —
which the user can easily re-state.
"""
from __future__ import annotations

import re

# Question-leading patterns. Anchored at the start so "is the leave policy?"
# qualifies but "I want to apply for leave" does not.
_INFO_PREFIXES = (
    "what ", "what's ", "whats ", "what is ", "what are ", "what does ",
    "how ", "how's ", "hows ", "how do ", "how to ", "how can ", "how does ",
    "how long ", "how much ", "how many ",
    "when ", "when do ", "when should ", "when can ", "when is ", "when does ",
    "where ", "where do ", "where can ", "where is ",
    "why ", "why is ", "why do ", "why are ", "why does ",
    "who ", "who do ", "who is ", "who can ", "who should ",
    "which ", "which is ", "which one ",
    "is the ", "is there ", "are there ", "does the ", "do i need ",
    "tell me ", "explain ", "describe ", "show me how ", "guide me ",
    "any policy ", "any rule ",
)

# Signals that override the info classification — these are clear personal
# action intents that should NOT be treated as informational even if they
# happen to start with a question word ("when can I take leave next week?"
# is borderline, but "I need leave next week" is unambiguous).
_ACTION_OVERRIDE_PHRASES = (
    "i need leave", "i need a leave", "i want leave", "i want to take leave",
    "i'd like to take", "i want to apply", "i need to apply",
    "apply for me", "apply on my behalf", "submit on my behalf",
    "submit it", "do it now", "go ahead and submit",
    "raise the ticket", "raise a ticket", "create a ticket for me",
    # First-person sick reporting must still fire the sick-leave action
    "i am sick", "i'm sick", "im sick", "i have a fever", "feeling sick",
    "send email to hr", "call in sick",
    # Salary increase as a personal request
    "increase my salary", "raise my salary", "i want a raise", "i need a raise",
)


def is_informational_query(query: str) -> bool:
    """Return True when the query is asking *how/what/when* about a process
    rather than asking the system to *do* it.

    Conservative — only matches obvious question phrasings.
    """
    if not query:
        return False
    q = query.strip().lower()

    # Action-override wins — if the user explicitly says "I need leave"
    # / "increase my salary", it stays as an action even if a How/What word
    # appears later in the sentence.
    if any(p in q for p in _ACTION_OVERRIDE_PHRASES):
        return False

    # Strip leading punctuation/quotes so " what is..." still matches.
    q_stripped = q.lstrip(" \"'`(*-")

    if q_stripped.startswith(_INFO_PREFIXES):
        return True

    # Also: ends with ? AND contains no first-person action verb
    if q_stripped.endswith("?"):
        # Single-word questions like "leave?" are not unambiguously info —
        # leave to the agent. Only treat multi-word ? sentences as info.
        if len(re.findall(r"\w+", q_stripped)) >= 3:
            return True

    return False


def has_personal_action_intent(query: str) -> bool:
    """Inverse helper — convenient for agents that want to check
    'is this a clear personal action request?'."""
    return any(p in (query or "").lower() for p in _ACTION_OVERRIDE_PHRASES)
