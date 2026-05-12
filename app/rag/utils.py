"""
Shared RAG utilities.

Previously `_clean_rag_output` was copy-pasted into hr_agent.py,
it_agent.py, and finance_agent.py — three identical copies that had
already started drifting apart. One canonical version lives here.
"""

# Metadata prefixes that are document-level noise, not answer content
_SKIP_PREFIXES = (
    "document id:",
    "doc id:",
    "topic:",
    "source:",
    "id:",
    "hr policy document",
    "it policy document",
    "finance policy document",
)


def clean_rag_output(raw: str, department: str | None = None) -> str:
    """
    Strip document metadata headers and cross-department noise from raw
    ChromaDB context before it reaches the LLM or the user.

    Args:
        raw:        Raw page_content from ChromaDB results.
        department: If provided, filter out noise from other departments.
                    One of "HR", "IT", "Finance".

    Returns:
        Clean multi-line string, or empty string if nothing useful found.
    """
    if not raw:
        return ""

    dept_noise: dict[str, list[str]] = {
        "HR":      ["it policy", "finance policy", "laptop", "password", "vpn"],
        "IT":      ["hr policy", "finance policy", "annual leave"],
        "Finance": ["hr policy", "it policy", "annual leave", "password", "vpn"],
    }
    noise_terms = dept_noise.get(department or "", [])

    useful: list[str] = []
    for line in raw.split("\n"):
        stripped = line.strip()
        lower = stripped.lower()

        if not stripped:
            continue

        if any(lower.startswith(p) for p in _SKIP_PREFIXES):
            # "Details:" prefix — keep the content after it
            if lower.startswith("details:"):
                content = stripped[8:].strip()
                if content:
                    useful.append(content)
            continue

        if any(term in lower for term in noise_terms):
            continue

        useful.append(stripped)

    return "\n".join(useful).strip()
