# app/utils/confidence.py
from __future__ import annotations

from app.core.constants import VERIFIED_SOURCES
from app.core.logger import get_logger

logger = get_logger(__name__)


def calculate_confidence(
    answer:           str,
    keyword_match:    bool = False,
    rag_used:         bool = False,
    source:           str  = "",
    action_triggered: bool = False,
) -> tuple[int, str]:
    """
    Signal-based confidence score.

    Signals:
        Action triggered         → +40 (system executed a real DB action)
        Keyword match            → +35
        RAG returned content     → +30
        Answer length > 80 chars → +15
        Verified policy source   → +10
        Hard cap                 → 92
    """
    score  = 0
    labels: list[str] = []

    # Signal 0 — System executed a real action (highest certainty)
    if action_triggered:
        score  += 40
        labels.append("action executed")

    # Signal 1 — Direct keyword match (most reliable)
    if keyword_match:
        score  += 35
        labels.append("keyword match")

    # Signal 2 — RAG retrieved real content
    if rag_used and answer and "no relevant" not in answer.lower():
        score  += 30
        labels.append("RAG match")

    # Signal 3 — Answer has real substance
    if answer and len(answer.strip()) > 80:
        score  += 15
        labels.append("detailed answer")

    # Signal 4 — Known verified source (uses full VERIFIED_SOURCES list from constants)
    src_lower = (source or "").lower()
    if any(v in src_lower for v in VERIFIED_SOURCES):
        score  += 10
        labels.append("verified source")

    # Cap — never claim perfect confidence
    score = min(score, 92)

    if not labels:
        reason = "Low confidence — no signal found"
    elif score >= 80:
        reason = f"High confidence — {' + '.join(labels)}"
    elif score >= 60:
        reason = f"High confidence — {' + '.join(labels)}"
    elif score >= 40:
        reason = f"Moderate confidence — {' + '.join(labels)}"
    else:
        reason = f"Low confidence — {' + '.join(labels)}"

    logger.debug("confidence.scored", score=score, reason=reason, source=source)
    return score, reason