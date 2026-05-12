from app.core.logger import get_logger

logger = get_logger(__name__)


def evaluate_response(query: str, answer: str, source: str) -> float:
    """
    ✅ FIX 3 — Real evaluation score. Never hardcoded 100.

    Signals:
        Source found             → +30
        Answer > 20 words        → +25
        Answer > 50 words        → +20 bonus
        Query word in answer     → +15
        Verified policy source   → +10
        Max                      → 100
    """
    if not answer or not query:
        return 0.0

    score      = 0
    ans_lower  = answer.lower()
    word_count = len(answer.split())

    # Signal 1 — Real source exists
    if source and source not in ("fallback", "guardrail", "error", "N/A", ""):
        score += 30

    # Signal 2 — Substance check
    if word_count > 20:
        score += 25

    # Signal 3 — Detail check
    if word_count > 50:
        score += 20

    # Signal 4 — Query relevance
    meaningful = [w for w in query.lower().split() if len(w) > 3]
    if any(w in ans_lower for w in meaningful):
        score += 15

    # Signal 5 — Policy source bonus
    verified = ["hr_policy", "it_policy", "finance_policy",
                "hr_1", "it_1", "finance_1"]
    if any(v in (source or "").lower() for v in verified):
        score += 10

    final = min(round(float(score), 1), 100.0)
    logger.debug("evaluator.scored", words=word_count, source=source, score=final)
    return final