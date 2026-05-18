"""
Semantic response cache — eliminates duplicate LLM calls for similar queries.

PROBLEM:
  An employee asking "What is the annual leave policy?" every day triggers a full
  LangGraph workflow + RAG + LLM generation each time. In a company of 500 people,
  common HR/IT/Finance questions are asked dozens of times per day.

SOLUTION:
  Two-tier cache:
    1. Exact match (Redis hash, TTL 1 hour): byte-perfect identical queries
    2. Semantic match (vector similarity, TTL 4 hours): paraphrased equivalents

  Only cache deterministic, policy-lookup responses (confidence ≥ 70).
  Never cache action-triggered responses (leave applications, expense submissions).

ARCHITECTURE:
  - Exact: Redis hash key = sha256(normalized_query + company_id)
  - Semantic: Redis stores question embeddings as JSON; cosine similarity at query time
  - Cache invalidation: prefix-keyed by company_id — flush on document upload
  - Async-safe: uses synchronous Redis (same client as rate limiter)

SAVINGS:
  Cache hit rate for common enterprise queries: ~60–80% in steady state.
  Each cache hit saves: ~500–2000 tokens + 2–4 seconds latency.
"""
from __future__ import annotations

import hashlib
import json
import math
import time

import redis

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
EXACT_TTL_SECONDS    = 3_600       # 1 hour  — exact matches
SEMANTIC_TTL_SECONDS = 14_400      # 4 hours — semantic matches
SIMILARITY_THRESHOLD = 0.85        # cosine similarity to consider a hit
MIN_CONFIDENCE       = 70          # only cache high-confidence answers
MAX_SEMANTIC_ENTRIES = 200         # max semantic cache entries per company

_client: redis.Redis | None = None


def _get_client() -> redis.Redis | None:
    global _client
    if _client is None:
        try:
            _client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            _client.ping()
        except Exception as exc:
            logger.warning("semantic_cache.redis_unavailable", error=str(exc))
            _client = None
    return _client


# ── Embedding ─────────────────────────────────────────────────────────────────

_embed_client = None

def _get_embed_client():
    global _embed_client
    if _embed_client is None:
        from openai import OpenAI
        _embed_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _embed_client


def _embed(text: str) -> list[float] | None:
    """Get text embedding using text-embedding-3-small (cheapest, fastest)."""
    try:
        resp = _get_embed_client().embeddings.create(
            model="text-embedding-3-small",
            input=text[:512],   # truncate to avoid token limits
        )
        return resp.data[0].embedding
    except Exception as exc:
        logger.warning("semantic_cache.embed_failed", error=str(exc))
        return None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ── Key helpers ───────────────────────────────────────────────────────────────

def _exact_key(query: str, company_id: str) -> str:
    normalized = query.strip().lower()
    h = hashlib.sha256(f"{company_id}:{normalized}".encode()).hexdigest()[:16]
    return f"cache:exact:{company_id}:{h}"


def _semantic_list_key(company_id: str) -> str:
    return f"cache:semantic:{company_id}:index"


# ── Public API ────────────────────────────────────────────────────────────────

def get_cached(query: str, company_id: str) -> dict | None:
    """
    Look up query in cache. Returns cached response dict or None.

    Tries exact match first (O(1)), then semantic match (O(N) over embeddings).
    """
    r = _get_client()
    if r is None:
        return None

    # 1. Exact match
    try:
        exact_key = _exact_key(query, company_id)
        raw = r.get(exact_key)
        if raw:
            cached = json.loads(raw)
            logger.info("semantic_cache.exact_hit", query=query[:60], company_id=company_id)
            return {**cached, "_cache": "exact"}
    except Exception as exc:
        logger.warning("semantic_cache.exact_lookup_failed", error=str(exc))

    # 2. Semantic match
    try:
        list_key = _semantic_list_key(company_id)
        entries_raw = r.lrange(list_key, 0, MAX_SEMANTIC_ENTRIES - 1)
        if not entries_raw:
            return None

        query_vec = _embed(query)
        if query_vec is None:
            return None

        best_score = 0.0
        best_entry = None
        for raw in entries_raw:
            try:
                entry = json.loads(raw)
                cached_vec = entry.get("embedding")
                if not cached_vec:
                    continue
                score = _cosine_similarity(query_vec, cached_vec)
                if score > best_score:
                    best_score = score
                    best_entry = entry
            except Exception:
                continue

        if best_score >= SIMILARITY_THRESHOLD and best_entry:
            logger.info(
                "semantic_cache.semantic_hit",
                query=query[:60],
                similarity=round(best_score, 4),
                matched=best_entry.get("query", "")[:60],
            )
            response = best_entry.get("response", {})
            return {**response, "_cache": "semantic", "_similarity": round(best_score, 4)}

    except Exception as exc:
        logger.warning("semantic_cache.semantic_lookup_failed", error=str(exc))

    return None


def set_cached(query: str, company_id: str, response: dict) -> None:
    """
    Store a response in the cache (exact + semantic tiers).

    Only caches:
    - confidence >= MIN_CONFIDENCE
    - non-action responses (actions are user-specific, must not be shared)
    """
    if response.get("action_triggered"):
        return  # Never cache action responses
    if (response.get("confidence") or 0) < MIN_CONFIDENCE:
        return  # Don't cache low-confidence answers

    r = _get_client()
    if r is None:
        return

    try:
        # Exact cache
        exact_key = _exact_key(query, company_id)
        cache_payload = {
            k: v for k, v in response.items()
            if k not in ("steps", "timestamp", "evaluation_score")  # strip volatile fields
        }
        r.setex(exact_key, EXACT_TTL_SECONDS, json.dumps(cache_payload))

        # Semantic index (background, fire-and-forget)
        embedding = _embed(query)
        if embedding:
            list_key = _semantic_list_key(company_id)
            entry = json.dumps({
                "query":     query,
                "embedding": embedding,
                "response":  cache_payload,
                "cached_at": time.time(),
            })
            r.lpush(list_key, entry)
            r.ltrim(list_key, 0, MAX_SEMANTIC_ENTRIES - 1)
            r.expire(list_key, SEMANTIC_TTL_SECONDS)

        logger.info("semantic_cache.stored", query=query[:60], company_id=company_id)

    except Exception as exc:
        logger.warning("semantic_cache.store_failed", error=str(exc))


def invalidate_company(company_id: str) -> None:
    """
    Flush all cache entries for a company.
    Called after document upload or knowledge base update.
    """
    r = _get_client()
    if r is None:
        return
    try:
        pattern = f"cache:*:{company_id}:*"
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = r.scan(cursor, match=pattern, count=100)
            if keys:
                r.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        logger.info("semantic_cache.invalidated", company_id=company_id, keys_deleted=deleted)
    except Exception as exc:
        logger.warning("semantic_cache.invalidate_failed", error=str(exc))
