"""
Day 52 — Hybrid RAG: BM25 + Dense vector fusion with RRF scoring.

Architecture:
  1. Dense retrieval  → ChromaDB (OpenAI embeddings)
  2. Sparse retrieval → BM25 (rank-bm25) over the same corpus
  3. Fusion          → Reciprocal Rank Fusion (RRF, k=60)
  4. Re-ranking      → Final top-N by RRF score

Why RRF over simple score averaging?
  - Dense scores are cosine similarities (bounded, embedding-model-dependent)
  - BM25 scores are TF-IDF-like (unbounded, query-length-dependent)
  - RRF normalises both into rank-position-based weights so they're comparable
    without any calibration: score = Σ 1 / (k + rank_i)
"""
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from langsmith import traceable
from rank_bm25 import BM25Okapi

from app.core.constants import QUERY_SOURCE_MAP, RAG_PRIORITY_KEYWORDS
from app.core.logger import get_logger
from app.rag.client import MAX_FINAL_CHUNKS, MAX_RETRIEVAL_CHUNKS, get_chroma_client

logger = get_logger(__name__)

RRF_K = 60          # RRF constant — 60 is the standard literature value
BM25_TOP_N = 10     # candidates from BM25 before RRF
DENSE_TOP_N = MAX_RETRIEVAL_CHUNKS   # candidates from dense before RRF


@dataclass
class RetrievedChunk:
    content: str
    source: str
    rrf_score: float = 0.0
    dense_rank: int | None = None
    bm25_rank: int | None = None
    metadata: dict = field(default_factory=dict)


# ── BM25 corpus cache ─────────────────────────────────────────────────────────
# We lazily build BM25 from the current vector store contents.
# The cache is invalidated by calling `invalidate_bm25_cache()` after uploads.

_bm25_cache: dict[str, Any] = {}   # {"bm25": BM25Okapi, "docs": list[dict]}


def _tokenise(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def _build_bm25() -> tuple[BM25Okapi, list[dict]]:
    """Fetch all docs from Chroma and build a BM25 index over them."""
    chroma = get_chroma_client()
    try:
        # LangChain Chroma wraps the underlying collection
        collection = chroma._collection
        result = collection.get(include=["documents", "metadatas"])
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
    except Exception as exc:
        logger.error("bm25.fetch_failed", error=str(exc))
        return BM25Okapi([[""]]), []

    if not documents:
        return BM25Okapi([[""]]), []

    corpus = [_tokenise(doc) for doc in documents]
    bm25 = BM25Okapi(corpus)
    docs = [{"content": d, "metadata": m} for d, m in zip(documents, metadatas)]
    logger.info("bm25.index_built", total_docs=len(docs))
    return bm25, docs


def get_bm25() -> tuple[BM25Okapi, list[dict]]:
    if "bm25" not in _bm25_cache:
        bm25, docs = _build_bm25()
        _bm25_cache["bm25"] = bm25
        _bm25_cache["docs"] = docs
    return _bm25_cache["bm25"], _bm25_cache["docs"]


def invalidate_bm25_cache() -> None:
    """Call this after uploading new documents so BM25 re-indexes."""
    _bm25_cache.clear()
    logger.info("bm25.cache_invalidated")


# ── RRF fusion ────────────────────────────────────────────────────────────────

def _rrf_score(rank: int | None, k: int = RRF_K) -> float:
    if rank is None:
        return 0.0
    return 1.0 / (k + rank + 1)   # +1 because ranks are 0-indexed


def _fuse(
    dense_docs: list[dict],   # [{content, source, metadata}]
    bm25_docs: list[dict],    # [{content, source, metadata}]
) -> list[RetrievedChunk]:
    """Reciprocal Rank Fusion over dense + BM25 candidate lists."""
    scores: dict[str, RetrievedChunk] = {}

    for rank, doc in enumerate(dense_docs):
        key = doc["content"].strip()
        if key not in scores:
            scores[key] = RetrievedChunk(
                content=key,
                source=doc.get("source", "unknown"),
                metadata=doc.get("metadata", {}),
            )
        scores[key].dense_rank = rank
        scores[key].rrf_score += _rrf_score(rank)

    for rank, doc in enumerate(bm25_docs):
        key = doc["content"].strip()
        if key not in scores:
            scores[key] = RetrievedChunk(
                content=key,
                source=doc.get("source", "unknown"),
                metadata=doc.get("metadata", {}),
            )
        scores[key].bm25_rank = rank
        scores[key].rrf_score += _rrf_score(rank)

    return sorted(scores.values(), key=lambda c: c.rrf_score, reverse=True)


# ── Source / keyword helpers (reused from rag_tool) ───────────────────────────

def _expected_source(q: str) -> str | None:
    for kw, prefix in QUERY_SOURCE_MAP.items():
        if kw in q:
            return prefix
    return None


def _priority_keywords(q: str) -> list[str]:
    for topic, kws in RAG_PRIORITY_KEYWORDS.items():
        if topic in q:
            return kws
    return []


# ── Main entry point ──────────────────────────────────────────────────────────

@traceable
def hybrid_search(query: str) -> dict:
    """
    Hybrid BM25 + dense retrieval with RRF fusion.

    Returns the same shape as `search_knowledge_base_raw` so agents are
    drop-in compatible:
        {"context": str, "source": str | None, "confidence": int, "hybrid": True}
    """
    try:
        q = query.strip()
        q_lower = q.lower()
        expected_src = _expected_source(q_lower)
        priority_kws = _priority_keywords(q_lower)

        # ── 1. Dense retrieval ────────────────────────────────────────────────
        chroma = get_chroma_client()
        dense_results = chroma.similarity_search(q, k=DENSE_TOP_N)
        dense_docs = [
            {
                "content": d.page_content,
                "source": d.metadata.get("source", "unknown"),
                "metadata": d.metadata,
            }
            for d in dense_results
        ]
        logger.debug("hybrid.dense", count=len(dense_docs))

        # ── 2. BM25 retrieval ─────────────────────────────────────────────────
        bm25, corpus_docs = get_bm25()
        tokens = _tokenise(q)
        if corpus_docs and tokens:
            scores = bm25.get_scores(tokens)
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:BM25_TOP_N]
            bm25_docs = [
                {
                    "content": corpus_docs[i]["content"],
                    "source": corpus_docs[i]["metadata"].get("source", "unknown"),
                    "metadata": corpus_docs[i]["metadata"],
                }
                for i in top_indices
                if scores[i] > 0
            ]
        else:
            bm25_docs = []
        logger.debug("hybrid.bm25", count=len(bm25_docs))

        # ── 3. RRF fusion ─────────────────────────────────────────────────────
        fused = _fuse(dense_docs, bm25_docs)
        logger.debug("hybrid.fused", total=len(fused))

        # ── 4. Department filter ──────────────────────────────────────────────
        import os
        def src_base(s: str) -> str:
            return os.path.basename(s).lower()

        if expected_src:
            filtered = [
                c for c in fused
                if src_base(c.source).startswith(expected_src)
            ]
            if not filtered:
                logger.warning("hybrid.filter_removed_all", fallback="using all")
                filtered = fused
        else:
            filtered = fused

        # Keyword filter
        if priority_kws:
            kw_filtered = [
                c for c in filtered
                if any(kw in c.content.lower() for kw in priority_kws)
            ]
            if kw_filtered:
                filtered = kw_filtered

        # ── 5. Dedup + truncate ───────────────────────────────────────────────
        seen: set[str] = set()
        final: list[RetrievedChunk] = []
        for chunk in filtered:
            key = chunk.content.strip()
            if key not in seen and len(key) >= 20:
                seen.add(key)
                final.append(chunk)
            if len(final) >= MAX_FINAL_CHUNKS:
                break

        if not final:
            return {"context": "", "source": None, "confidence": 0, "hybrid": True}

        # ── 6. Confidence scoring ─────────────────────────────────────────────
        both_hit = sum(1 for c in final if c.dense_rank is not None and c.bm25_rank is not None)
        score = 0
        if expected_src:
            score += 30
        score += min(30, len(final) * 15)
        if both_hit:
            score += both_hit * 12   # both retrievers agreed → higher confidence
        if priority_kws:
            kw_hits = sum(1 for c in final for kw in priority_kws if kw in c.content.lower())
            if kw_hits >= 2:
                score += 10
        confidence = min(score, 95)

        sources = list(dict.fromkeys(src_base(c.source) for c in final if c.source))[:2]
        context = "\n\n".join(c.content.strip() for c in final)

        logger.info(
            "hybrid.complete",
            chunks=len(final),
            both_hit=both_hit,
            confidence=confidence,
            sources=sources,
        )

        return {
            "context": context,
            "source": ", ".join(sources) if sources else None,
            "confidence": confidence,
            "hybrid": True,
        }

    except Exception as exc:
        logger.error("hybrid.failed", error=str(exc))
        # Graceful degradation to dense-only
        from app.rag.rag_tool import search_knowledge_base_raw
        return search_knowledge_base_raw(query)
