# Changelog

All notable changes to this project are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] — 2026-05-18

### Added
- **Circuit breaker + retry** (`app/core/openai_client.py`): thread-safe, 3-state circuit breaker (CLOSED → OPEN → HALF_OPEN) wrapping all OpenAI calls. Exponential back-off (1s → 2s) for RateLimitError, APITimeoutError, APIConnectionError, InternalServerError. Fast-fail when circuit is open to prevent thread-pool exhaustion during outages.
- **13 new unit tests** covering all circuit breaker state transitions and retry paths (31 unit tests total).
- **`/health/deep` circuit breaker visibility**: circuit state and failure count exposed in deep health endpoint for ops dashboards.

### Changed
- `planner_agent.py`, `crag.py`, `redis_memory.py` now call `resilient_chat_completion()` — single wrapper for all OpenAI chat calls.

---

## [1.1.0] — 2026-05-18

### Added
- **Semantic response cache** (`app/core/semantic_cache.py`): two-tier Redis cache — exact SHA256 match (1h TTL) + cosine-similarity embedding match (4h TTL, threshold 0.92). Skips full LangGraph + RAG + LLM pipeline on cache hit (~60–80% hit rate in steady state; saves 500–2000 tokens and 2–5s per request).
- **Conversation summarization** (`app/memory/redis_memory.py`): sessions exceeding 12 turns compress older history into a 2–3 sentence LLM summary stored separately. Prevents context-window overflow; active window stays at 8 turns verbatim.
- **`/health/deep` endpoint**: comprehensive health check for PostgreSQL, Redis, ChromaDB, OpenAI, and circuit breaker state. Returns `degraded` (not 500) on partial failure so Railway doesn't restart unnecessarily.
- **Database migration** (`alembic/versions/20260518_0001_add_indexes_and_constraints.py`): `UNIQUE(username, company_id)` constraint + 22 query-pattern indexes applied to production PostgreSQL.
- **`invalidate_company()`** called after document upload to flush semantic cache on knowledge base changes.

### Changed
- **Rate limiter** (`app/core/rate_limiter.py`): proxy-aware IP extraction honours `X-Forwarded-For` and `X-Real-IP` (Railway, Nginx, Cloudflare). `/ask` and `/login` endpoints now fail-closed on Redis unavailability — rate limiting is a security control, not a convenience feature.
- **CRAG batch grading** (`app/rag/crag.py`): N per-chunk LLM calls → 1 batch call using `gpt-4o-mini` with `response_format=json_object`. Ambiguous chunks now filtered as irrelevant (was kept; caused hedging). Grading latency reduced ~80%.
- `server.py`: semantic cache lookup before guardrails pipeline; non-blocking async store after reply; `ask_rate_limiter` on `/ask/stream`.

---

## [1.0.2] — 2026-05-17

### Fixed
- **JWT session expiry UX**: SSE `onError()` and `ChatPage.tsx` now detect auth errors and redirect to `/login` instead of displaying "Invalid token" as a chat bubble error message.
- **Token lifetime**: `ACCESS_TOKEN_EXPIRE_MINUTES` raised from 60 → 480 (8 hours) — matches a standard enterprise working day.

---

## [1.0.1] — 2026-05-17

### Fixed
- **Confidence scoring** (`app/workflows/workflow_graph.py`): `confidence = max(signal_confidence, result.confidence or 0)` — previously, the signal-derived score could silently discard an agent's own hardcoded confidence=90, resulting in authoritative policy answers showing "Low 60%".
- **Confidence labels** (`app/utils/confidence.py`): ≥60 now shows "High confidence" (was only ≥75). Aligned thresholds to actual answer quality.
- **Multi-intent false positive** (`app/utils/multi_intent.py`): word-boundary regex (`\b`) for short keywords (≤3 chars). "po" (purchase order) was substring-matching inside "policy" → "annual leave policy" was incorrectly routed to HR + Finance. Now correctly routes to HR only.

---

## [1.0.0] — 2026-05-15

### Added
- **LangGraph multi-agent orchestration**: Planner → Router → HR / IT / Finance specialist agents → Evaluator pipeline. Full stateful workflow with audit trail.
- **Corrective RAG (CRAG)**: hybrid BM25 + dense vector retrieval with relevance grading and automatic query rewrite on full irrelevance.
- **Multi-intent detection**: single query routed to multiple specialist agents with combined structured response.
- **UAE/GCC domain expertise**: HR (gratuity/EOSB/DEWS, Emiratization, Ramadan hours), Finance (WPS, VAT 5%, corporate tax 9%), IT (CrowdStrike, Intune, Cisco AnyConnect VPN) routing rules.
- **Semantic caching** (initial version), **Redis sliding-window rate limiting**, **JWT auth**, **async PostgreSQL** (SQLAlchemy 2.0).
- **LangSmith tracing** for full observability.
- **Guardrails**: off-topic and harmful request interception before any LLM processing.
- **Cost tracking** per company and per department.
- **Action engine**: leave applications, expense submissions, IT ticket creation integrated into chat flow.
- **Admin dashboard**: company management, document upload, usage analytics, audit logs.
- **StreamingResponse SSE**: real-time token-by-token delivery via `/ask/stream`.
- **Production deployment**: Railway (backend + Postgres + Redis) + Vercel (React frontend).

---

[1.2.0]: https://github.com/SyedHussain23/enterprise-ai-workforce/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/SyedHussain23/enterprise-ai-workforce/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/SyedHussain23/enterprise-ai-workforce/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/SyedHussain23/enterprise-ai-workforce/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/SyedHussain23/enterprise-ai-workforce/releases/tag/v1.0.0
