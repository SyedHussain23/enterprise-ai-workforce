"""
Day 53 — Corrective RAG (CRAG) node.

Flow:
  1. Retrieve chunks with hybrid search
  2. Grade each chunk: relevant / irrelevant / ambiguous  (LLM-as-grader)
  3. Decision:
     - ALL relevant → proceed with context (standard RAG path)
     - SOME relevant → filter to relevant only, proceed
     - NONE relevant → rewrite query + retry hybrid search once
  4. Return graded, filtered context

Why CRAG?
  Most RAG systems blindly pass retrieved chunks to the generator, even when
  chunks are off-topic (hallucination risk). CRAG adds a cheap grading step
  (one LLM call per retrieval) that dramatically reduces hallucination rate —
  the most common failure mode in enterprise RAG systems.

Reference: "Corrective Retrieval Augmented Generation" (Yan et al., 2024)
"""
from __future__ import annotations

from langsmith import traceable
from openai import OpenAI

from app.core.config import settings
from app.core.logger import get_logger
from app.rag.hybrid_retriever import hybrid_search

logger = get_logger(__name__)

_openai = OpenAI(api_key=settings.OPENAI_API_KEY)

GRADE_PROMPT = """You are a retrieval grader. Given a user question and a document chunk, output exactly one word:
- "relevant"   — chunk directly helps answer the question
- "ambiguous"  — chunk is partially related
- "irrelevant" — chunk is off-topic

Question: {question}
Chunk: {chunk}

Your answer (one word only):"""

REWRITE_PROMPT = """Rewrite this question to improve document retrieval. Make it more specific and keyword-rich.
Original: {question}
Rewritten (one sentence):"""


def _grade_chunk(question: str, chunk: str) -> str:
    try:
        resp = _openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": GRADE_PROMPT.format(question=question, chunk=chunk[:800])}],
            max_tokens=5,
            temperature=0,
        )
        verdict = resp.choices[0].message.content.strip().lower()
        if verdict not in {"relevant", "ambiguous", "irrelevant"}:
            verdict = "ambiguous"
        return verdict
    except Exception as exc:
        logger.warning("crag.grade_failed", error=str(exc))
        return "ambiguous"


def _rewrite_query(question: str) -> str:
    try:
        resp = _openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": REWRITE_PROMPT.format(question=question)}],
            max_tokens=80,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("crag.rewrite_failed", error=str(exc))
        return question


@traceable
def corrective_rag(query: str, grade: bool = True) -> dict:
    """
    Run hybrid search and apply CRAG grading.

    Args:
        query: The user question.
        grade: If False, skip LLM grading (useful for tests or when cost-conscious).

    Returns:
        {context, source, confidence, crag_action: "pass"|"filter"|"rewrite", hybrid: True}
    """
    result = hybrid_search(query)
    context: str = result.get("context", "")
    chunks = [c.strip() for c in context.split("\n\n") if c.strip()]

    if not chunks or not grade:
        return {**result, "crag_action": "pass"}

    # ── Grade each chunk ──────────────────────────────────────────────────────
    grades: list[str] = []
    for chunk in chunks:
        grade_label = _grade_chunk(query, chunk)
        grades.append(grade_label)
        logger.debug("crag.graded", verdict=grade_label, chunk_preview=chunk[:60])

    relevant   = [c for c, g in zip(chunks, grades) if g in {"relevant", "ambiguous"}]
    irrelevant = [c for c, g in zip(chunks, grades) if g == "irrelevant"]

    logger.info(
        "crag.grades",
        relevant=len(relevant),
        irrelevant=len(irrelevant),
        total=len(chunks),
    )

    # ── Decision ──────────────────────────────────────────────────────────────
    if not relevant:
        # ALL chunks are irrelevant → rewrite query and retry once
        rewritten = _rewrite_query(query)
        logger.info("crag.rewrite", original=query, rewritten=rewritten)
        retry = hybrid_search(rewritten)
        return {**retry, "crag_action": "rewrite", "rewritten_query": rewritten}

    if len(irrelevant) > 0:
        # SOME irrelevant → filter them out
        filtered_context = "\n\n".join(relevant)
        # Recalculate confidence (fewer chunks = slightly lower)
        conf = min(result.get("confidence", 50) + 5, 95) if len(relevant) == len(chunks) else max(result.get("confidence", 50) - 10, 20)
        return {
            **result,
            "context": filtered_context,
            "confidence": conf,
            "crag_action": "filter",
        }

    # ALL relevant → pass through unchanged
    return {**result, "crag_action": "pass"}
