# app/utils/confidence.py


def calculate_confidence(
    answer:        str,
    keyword_match: bool = False,
    rag_used:      bool = False,
    source:        str  = "",
) -> tuple[int, str]:
    """
    Real signal-based confidence score.
    Signals must logically match evaluation score — no mismatch.

    Signals:
        Keyword match            → +35
        RAG returned content     → +30
        Answer length > 80 chars → +15
        Verified policy source   → +10
        Hard cap                 → 92
    """
    score  = 0
    labels = []

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

    # Signal 4 — Known verified source
    verified = [
        "hr_policy", "it_policy", "finance_policy",
        "hr_1", "it_1", "finance_1",
    ]
    if any(v in (source or "").lower() for v in verified):
        score  += 10
        labels.append("verified source")

    # Cap — never claim perfect confidence
    score = min(score, 92)

    # Reason must match score logically — no mismatch with eval
    if not labels:
        reason = "Low confidence — no signal found"
    elif score >= 75:
        reason = f"High confidence — {' + '.join(labels)}"
    elif score >= 45:
        reason = f"Moderate confidence — {' + '.join(labels)}"
    else:
        reason = f"Low confidence — {' + '.join(labels)}"

    print(f"[CONFIDENCE] score={score} | reason={reason}")
    return score, reason