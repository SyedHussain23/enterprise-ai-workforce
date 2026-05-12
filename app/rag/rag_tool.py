import os

from langsmith import traceable

from app.core.constants import QUERY_SOURCE_MAP, RAG_PRIORITY_KEYWORDS
from app.core.logger import get_logger
from app.rag.client import MAX_FINAL_CHUNKS, MAX_RETRIEVAL_CHUNKS, get_chroma_client

logger = get_logger(__name__)


def _expected_source(query_lower: str) -> str | None:
    for keyword, prefix in QUERY_SOURCE_MAP.items():
        if keyword in query_lower:
            return prefix
    return None


def _priority_keywords(query_lower: str) -> list[str]:
    for topic, keywords in RAG_PRIORITY_KEYWORDS.items():
        if topic in query_lower:
            return keywords
    return []


def _source_basename(source: str) -> str:
    return os.path.basename(source).lower()


@traceable
def search_knowledge_base_raw(query: str) -> dict:
    """
    Search ChromaDB and return clean, deduplicated, department-filtered context.

    Uses the module-level singleton client (one connection per process).
    Previously this created a new Chroma() + OpenAIEmbeddings() on every call.

    Returns:
        {"context": str, "source": str | None, "confidence": int}
    """
    try:
        query = query.strip()
        q = query.lower()

        client = get_chroma_client()
        raw_results = client.similarity_search(query, k=MAX_RETRIEVAL_CHUNKS)
        logger.debug("rag.raw_results", count=len(raw_results), query=query)

        if not raw_results:
            return _empty()

        expected_src = _expected_source(q)
        priority_kws = _priority_keywords(q)
        filtered: list = []

        for doc in raw_results:
            content = doc.page_content.lower()
            src = _source_basename(doc.metadata.get("source", "unknown"))

            if expected_src and not src.startswith(expected_src):
                logger.debug("rag.cross_dept_filtered", source=src, expected=expected_src)
                continue

            if priority_kws and not any(kw in content for kw in priority_kws):
                logger.debug("rag.no_keyword_match", source=src)
                continue

            filtered.append(doc)

        if not filtered:
            logger.warning("rag.filter_removed_all", query=query)
            filtered = raw_results  # fallback: use raw results rather than empty

        # Deduplicate by exact content
        seen: set[str] = set()
        unique: list = []
        for doc in filtered:
            content = doc.page_content.strip()
            if content not in seen and len(content) >= 20:
                seen.add(content)
                unique.append(doc)

        final_docs = unique[:MAX_FINAL_CHUNKS]
        if not final_docs:
            return _empty()

        # Collect sources, enforcing department filter one more time
        sources: list[str] = []
        for doc in final_docs:
            src = _source_basename(doc.metadata.get("source", "unknown"))
            if expected_src and not src.startswith(expected_src):
                continue
            if src not in sources:
                sources.append(src)
        sources = sorted(sources)[:2]

        context = "\n\n".join(doc.page_content.strip() for doc in final_docs)

        # Signal-based confidence — never hardcoded
        score = 0
        if expected_src and sources:
            score += 35
        score += min(30, len(final_docs) * 15)
        if sources:
            score += 20
        if priority_kws and context:
            kw_hits = sum(1 for kw in priority_kws if kw in context.lower())
            if kw_hits >= 2:
                score += 15
        confidence = min(score, 92)

        logger.info(
            "rag.complete",
            chunks=len(final_docs),
            sources=sources,
            confidence=confidence,
        )
        return {
            "context": context,
            "source": ", ".join(sources) if sources else None,
            "confidence": confidence,
        }

    except Exception as exc:
        logger.error("rag.search_failed", error=str(exc))
        return _empty()


def _empty() -> dict:
    return {"context": "", "source": None, "confidence": 0}
