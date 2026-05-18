# Enterprise AI Workforce

> **Multi-agent AI platform for enterprise HR, IT, and Finance.**
> Built for UAE/GCC organisations. Production-grade architecture: RAG, streaming, human approval workflows, semantic caching, circuit breaker, and full audit trail.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-black?logo=vercel)](https://frontend-1k4olnq4e-syedhussain23s-projects.vercel.app/)
[![Backend](https://img.shields.io/badge/API-Railway-purple?logo=railway)](https://enterprise-ai-workforce-production.up.railway.app/docs)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-blue?logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-6-blue?logo=typescript)](https://typescriptlang.org)

---

## What This Platform Does

Enterprise employees ask questions in natural language. The AI routes the question to the correct department agent (HR, IT, or Finance), retrieves relevant policy documents via RAG, synthesises an answer, and streams it token-by-token. Sensitive requests (salary advances, purchase orders) trigger a human approval workflow.

**Sample queries the platform handles:**

| Question | Agent | Source |
|----------|-------|--------|
| "What is the annual leave policy?" | HR | ChromaDB RAG |
| "How do I reset my MFA?" | IT | ChromaDB RAG |
| "How is gratuity calculated?" | HR | UAE Labour Law + RAG |
| "I want to apply for a salary advance" | Finance | Approval workflow |
| "What is the UAE VAT rate?" | Finance | Policy document |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React 19 Frontend                       │
│  ChatPage · AdminPage · ProfilePage · Error Boundary        │
│  SSE streaming · RTL/Arabic · Voice input · File upload+OCR │
└─────────────────────┬───────────────────────────────────────┘
                      │  HTTPS / SSE
┌─────────────────────▼───────────────────────────────────────┐
│                  FastAPI Backend (Railway)                   │
│                                                             │
│  ┌─────────────┐  ┌───────────────┐  ┌──────────────────┐  │
│  │  Guardrails  │  │ Rate Limiter  │  │ Semantic Cache   │  │
│  │  PII·inject  │  │  Redis SSet   │  │  exact+cosine    │  │
│  └──────┬───────┘  └───────────────┘  └──────────────────┘  │
│         │                                                    │
│  ┌──────▼──────────────────────────────────────────────┐    │
│  │           LangGraph Workflow Orchestrator            │    │
│  │   Planner → Router → CRAG → Report                  │    │
│  │   keyword-first routing, LLM fallback on ambiguity  │    │
│  └──────┬──────────────────┬───────────────────────────┘    │
│         │                  │                                 │
│  ┌──────▼──────┐   ┌───────▼────────┐                       │
│  │  Department │   │  Hybrid RAG    │                       │
│  │   Agents    │   │  BM25 + Dense  │                       │
│  │  HR·IT·Fin  │   │  CRAG grading  │                       │
│  └──────┬──────┘   └───────┬────────┘                       │
│         │                  │                                 │
│  ┌──────▼──────────────────▼──────────────────────────────┐  │
│  │   OpenAI GPT-4o  ·  Circuit Breaker  ·  Retry 3x       │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                             │
│  PostgreSQL  ·  Redis  ·  ChromaDB  ·  Immutable Audit Log │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Engineering Decisions

### 1. Hybrid Keyword + LLM Planner
Fast path: keyword scoring against 300+ department-specific terms (< 5ms). Slow path: GPT-4o-mini only when no clear keyword winner. **Result:** ~70% of requests resolved without an LLM routing call.

### 2. CRAG Batch Grading
All N retrieved chunks graded in a single LLM call via `response_format=json_object`. Naive implementations use N calls. **Result:** RAG quality check costs exactly 1 LLM call regardless of chunk count.

### 3. Two-Tier Semantic Cache
- Tier 1: SHA-256 exact match (O(1), Redis GET)
- Tier 2: Cosine similarity ≥ 0.85 over stored question embeddings

**Result:** 60–80% cache hit rate on common enterprise queries. Each hit saves 2–5 seconds and 500–2,000 tokens.

### 4. Circuit Breaker + Exponential Backoff
`CLOSED → OPEN` after 5 consecutive OpenAI failures. `HALF-OPEN` probe after 60s. Backoff: 1s → 2s over 3 attempts. **Result:** OpenAI outage causes fast-fail in < 5ms, not 30-second thread-pool hangs.

### 5. JWT Token Blocklist
Every JWT embeds a `jti` (UUID4) claim. On logout or password change, the JTI is written to Redis with TTL = token remaining lifetime. The auth dependency checks the blocklist on every request (O(1)). **Result:** Tokens are immediately invalid server-side after logout — no replay window.

### 6. Background Memory Summarisation
Conversation summarisation (triggered at 10 turns) runs as a FastAPI `BackgroundTasks` task — off the hot path. **Result:** Zero latency spike at turn 10; user sees their response immediately.

### 7. Real Document Extraction in Chat
Uploaded files are extracted server-side (`/ask/extract`, pypdf + python-docx) and injected as context into the AI query. Previously files were UI-only cosmetics. **Result:** AI can actually read and reason about uploaded HR letters, payslips, receipts.

### 8. Redis Sliding-Window Rate Limiter
O(log N) sorted-set: ZADD + ZREMRANGEBYSCORE + ZCARD per request. Fail-closed for `/ask` when Redis is unavailable. **Result:** Precise per-user-per-minute control without performance penalty.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript 6, Tailwind CSS 4, Vite 8 |
| Backend | FastAPI 0.115, SQLAlchemy 2 (async), Pydantic v2 |
| AI Orchestration | LangGraph, LangChain 0.3 |
| LLM | OpenAI GPT-4o (synthesis), GPT-4o-mini (grading/routing) |
| Vector Store | ChromaDB |
| Hybrid Search | ChromaDB dense + BM25 sparse (rank-bm25) |
| Embeddings | OpenAI text-embedding-3-small |
| Memory | Redis (conversation history, semantic cache, rate limiter, token blocklist) |
| Database | PostgreSQL (async via asyncpg + SQLAlchemy 2) |
| Auth | JWT (python-jose) + bcrypt + Redis JTI blocklist |
| Deployment | Vercel (frontend) + Railway (backend, Redis, PostgreSQL) |
| Observability | LangSmith, structured JSON logs, request ID propagation |
| Testing | pytest, pytest-asyncio, k6 load tests |

---

## Project Structure

```
enterprise-ai-workforce/
├── app/
│   ├── agents/           # HR, IT, Finance agents + hybrid keyword/LLM planner
│   ├── api/              # FastAPI server — routes, middleware, SSE streaming
│   ├── auth/             # JWT creation, JTI token blocklist, role dependencies
│   ├── core/             # Config, circuit breaker, semantic cache, rate limiter
│   ├── db/               # SQLAlchemy models, repositories, Alembic migrations
│   ├── memory/           # Redis conversation memory + background summarisation
│   ├── rag/              # ChromaDB, CRAG batch grading, hybrid BM25+dense retriever
│   ├── schemas/          # Pydantic request/response models
│   ├── utils/            # Guardrails (PII, injection, profanity), multi-intent
│   └── workflows/        # LangGraph state machine (planner→router→CRAG→report)
├── frontend/
│   ├── src/
│   │   ├── api/          # Typed API client (SSE, file extraction, auth, logout)
│   │   ├── components/   # Chat, admin, shared UI (ErrorBoundary, skeletons)
│   │   ├── context/      # Auth (with server-logout), RTL contexts
│   │   └── pages/        # ChatPage (retry+file+streaming), AdminPage, Login, Profile
│   └── vercel.json       # CSP, HSTS, security headers, rewrite rules
├── tests/
│   ├── test_auth.py · test_guardrails.py · test_confidence.py ...
│   └── load/             # k6 smoke, load, and stress test scripts
├── alembic/              # Database migration versions
├── data/                 # 75 HR/IT/Finance policy documents (txt)
├── Dockerfile
└── docker-compose.yml    # Local: FastAPI + PostgreSQL + Redis
```

---

## API Reference

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/login` | — | Authenticate → JWT |
| POST | `/logout` | Bearer | Invalidate token (JTI blocklist) |
| POST | `/ask` | Bearer | Blocking AI response |
| POST | `/ask/stream` | Bearer | SSE streaming response |
| POST | `/ask/extract` | Bearer | Extract text from uploaded file |
| GET | `/actions/pending` | Admin | Pending approval queue |
| POST | `/actions/{id}/approve` | Admin | Approve workflow action |
| POST | `/actions/{id}/reject` | Admin | Reject workflow action |
| POST | `/admin/documents` | Admin | Index PDF into ChromaDB |
| GET | `/admin/stats` | Admin | Usage analytics |
| GET | `/admin/cost` | Admin | Token cost tracking |
| GET | `/admin/users` | Admin | User management |
| GET | `/admin/audit` | Admin | Immutable audit log |
| GET | `/health/deep` | — | Full-stack health check |
| GET/PUT | `/me` | Bearer | Profile management |
| PUT | `/me/password` | Bearer | Password change + token revocation |

---

## Local Development

```bash
# Infrastructure
docker-compose up -d   # PostgreSQL + Redis

# Backend
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY
alembic upgrade head
python scripts/seed_db.py
python build_vector_db.py
uvicorn app.api.server:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

Open: **http://localhost:5173** | Default: `admin / admin123`

---

## Security Controls

| Control | Implementation |
|---------|---------------|
| Authentication | JWT HS256 + bcrypt |
| Session invalidation | Redis JTI blocklist — immediate on logout |
| Rate limiting | Sliding-window: 20/min per user (`/ask`), 5/min (`/login`) |
| Prompt injection | 30+ phrase blocklist + enterprise scope guardrails |
| PII detection | Emirates ID, IBAN, credit card, passport regex patterns |
| HTTP security | CSP, HSTS (1yr+preload), X-Frame-Options, X-Content-Type-Options |
| File validation | MIME + extension + 5MB size limit |
| Audit trail | Immutable `workflow_log` + `audit_log` per every request |

---

Built by [Syed Hussain](https://github.com/SyedHussain23) · MIT License
