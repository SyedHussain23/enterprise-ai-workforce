<div align="center">

# Enterprise AI Workforce

**Production-grade multi-agent AI platform for enterprise HR, IT & Finance automation**

[![CI](https://github.com/SyedHussain23/enterprise-ai-workforce/actions/workflows/ci.yml/badge.svg)](https://github.com/SyedHussain23/enterprise-ai-workforce/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-FF6B35?logo=chainlink&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](docker-compose.yml)

<br/>

> **Designed for the transition from AI assistants to AI agents that execute enterprise workflows.**  
> Self-hosted · Arabic/RTL · WhatsApp-native · CRAG + RRF retrieval · Approval-gated actions

<br/>

[**Live Demo**](#deployment) · [**Architecture**](#architecture) · [**Quick Start**](#quick-start) · [**API Docs**](http://localhost:8000/docs)

</div>

---

## What This Is

Enterprise AI Workforce is an **agentic AI platform** — not a chatbot wrapper. It routes natural language queries to specialist AI agents (HR, IT, Finance), retrieves grounded answers from a 100-document knowledge base using hybrid CRAG+RRF retrieval, gates executable actions through a human approval workflow, and streams responses token-by-token to a React frontend with full Arabic/RTL support.

The system answers the question: *what does enterprise AI look like when it's actually production-ready?*

```
User Query → Planner → Guardrail → Router → CRAG Retrieval → Specialist Agent → Approval Gate → Response
```

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                           │
│        React 19 · TypeScript · Tailwind · RTL/Arabic           │
└──────────────────────────┬──────────────────────────────────────┘
                           │  REST + SSE streaming
┌──────────────────────────▼──────────────────────────────────────┐
│                      API LAYER                                  │
│     FastAPI · JWT (HS256) · Pydantic · Redis rate limiter       │
│   /ask · /ask/stream · /admin · /actions · /kb · /profile       │
└────┬──────────────────────┬────────────────────┬────────────────┘
     │                      │                    │
┌────▼────────┐  ┌──────────▼──────────┐  ┌─────▼──────────────┐
│ PostgreSQL  │  │  Redis              │  │  Workflow Engine    │
│ 8 tables    │  │  Session memory     │  │  PENDING→APPROVED   │
│ Alembic     │  │  Rate limiting      │  │  →EXECUTING→DONE    │
│ Audit trail │  │  BM25 cache         │  │  Human gate         │
└─────────────┘  └─────────────────────┘  └────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                  LANGGRAPH ORCHESTRATION                        │
│          Planner → Guardrail → Router → CRAG → Report           │
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────────────────────┐  │
│   │ HR Agent │    │ IT Agent │    │    Finance Agent         │  │
│   └──────────┘    └──────────┘    └──────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    RETRIEVAL LAYER                              │
│  ChromaDB (dense) + BM25 (sparse) → RRF Fusion → CRAG Grader   │
│            ↑ query rewrite on all-irrelevant                    │
└─────────────────────────────────────────────────────────────────┘
```

### Agentic Pipeline — Step by Step

| Step | Component | What Happens |
|------|-----------|--------------|
| 1 | **FastAPI** | Authenticates JWT, validates request, calls LangGraph |
| 2 | **Planner** | Keyword trie → LLM fallback; outputs intent label |
| 3 | **Guardrail** | Blocks: out-of-scope, multi-intent, prompt injection |
| 4 | **Router** | Selects specialist agent via conditional LangGraph edge |
| 5 | **CRAG** | Dense + sparse retrieval → RRF fusion → LLM chunk grading |
| 6 | **Agent** | Generates grounded answer from graded context |
| 7 | **Report** | Attaches confidence (0-100), eval score, source, steps |
| 8 | **SSE** | Streams tokens to React frontend in real time |
| 9 | **DB** | Logs full response to `conversation_logs` for audit |

### Database Schema

```
users          → id, username, email, hashed_password, role, company_id
sessions       → id, user_id, title, created_at
conversation_logs → session_id, agent, question, answer, confidence,
                   evaluation_score, response_time, source
actions        → id, session_id, action_type, payload, status,
                 created_at, approved_at, executed_at
companies      → id, name, domain
kb_documents   → id, category, filename, company_id
profiles       → user_id, department, updated_at
alembic_version → version_num
```

---

## Key Engineering Decisions

### Why CRAG + RRF instead of naive RAG?

Standard RAG retrieves top-K chunks and passes them all to the LLM regardless of relevance. This causes hallucination when retrieved context doesn't actually answer the question.

CRAG (Corrective RAG) adds an LLM-based grading step that labels each chunk `relevant / ambiguous / irrelevant`. Only passing chunks reach the agent. If all chunks fail, the query is automatically rewritten and retrieval retried once.

RRF (Reciprocal Rank Fusion) merges dense vector results (ChromaDB) and sparse keyword results (BM25) without requiring score calibration — giving the best of both retrieval methods.

### Why LangGraph instead of a chain?

LangChain chains are linear. LangGraph gives explicit graph structure with conditional edges — the routing logic (`is this HR? IT? Finance? None?`) is a first-class graph decision, not an if/else buried in a function. Every node failure is catchable. The execution trace is inspectable. The pipeline is testable node-by-node.

### Why an approval-gated action system?

Enterprise AI that can *do things* (approve leave, create tickets, submit expenses) needs a human in the loop before execution. The action lifecycle (`PENDING → APPROVED → EXECUTING → COMPLETED`) ensures no AI-initiated action touches any downstream system without explicit human authorisation. Every state transition is timestamped and auditable.

### Why self-hosted?

UAE and GCC enterprises face data residency requirements. Internal HR/Finance documents cannot be sent to external SaaS systems. This platform runs entirely within the customer's infrastructure — knowledge base files, vector embeddings, conversation history, and user data never leave the deployment environment.

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| LLM | OpenAI GPT-4o-mini | latest |
| Orchestration | LangGraph StateGraph | 0.2 |
| Dense Retrieval | ChromaDB | 0.5 |
| Sparse Retrieval | BM25 (rank-bm25) | 0.2 |
| Fusion | RRF (custom) | — |
| Backend | FastAPI + SQLAlchemy async | 0.115 |
| Migrations | Alembic | 1.13 |
| Database | PostgreSQL | 16 |
| Cache / Memory | Redis | 7 |
| Auth | JWT HS256 + bcrypt | — |
| Frontend | React 19 + Vite + TypeScript | 19 / 6.0 |
| Styling | Tailwind CSS | 4 |
| Streaming | SSE (Server-Sent Events) | — |
| Charts | Recharts | 3 |
| Tracing | LangSmith | latest |
| Load Testing | k6 | latest |
| CI/CD | GitHub Actions | — |
| Containers | Docker + Compose | — |
| Deployment | Railway + Vercel | — |

---

## Features

<table>
<tr>
<td width="50%">

**🤖 Multi-Agent Routing**
- Planner: keyword trie + LLM fallback
- HR Agent: UAE Labour Law, leave, onboarding
- IT Agent: password reset, VPN, access
- Finance Agent: salary, expenses, VAT/tax
- Guardrail: injection/scope/intent gate

</td>
<td width="50%">

**📚 Hybrid RAG**
- 100-document knowledge base
- ChromaDB dense + BM25 sparse
- RRF fusion without calibration
- CRAG grading per chunk
- Automatic query rewrite on failure

</td>
</tr>
<tr>
<td width="50%">

**⚡ Workflow Engine**
- PENDING → APPROVED → EXECUTING → COMPLETED
- Human approval gate on all agent actions
- Full audit trail per state transition
- Admin dashboard with action queue
- Rejection with reason + logging

</td>
<td width="50%">

**🔐 Security**
- JWT HS256 + bcrypt cost 12
- Path traversal protection (_safe_path)
- SECRET_KEY enforced at container start
- Redis sliding-window rate limiter
- Role-based access (user/admin)

</td>
</tr>
<tr>
<td width="50%">

**🌍 Internationalisation**
- English + Arabic out of the box
- Full RTL layout toggle
- All UI labels translated
- Language preference persists

</td>
<td width="50%">

**📊 Observability**
- LangSmith end-to-end tracing
- Confidence score + eval score per response
- Execution steps in every API response
- Structured logging to mounted volume

</td>
</tr>
</table>

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node 22+
- Docker + Docker Compose
- OpenAI API key

### Local Development (5 minutes)

```bash
# 1. Clone
git clone https://github.com/SyedHussain23/enterprise-ai-workforce.git
cd enterprise-ai-workforce

# 2. Environment
cp .env.example .env
# Open .env — set OPENAI_API_KEY and SECRET_KEY
# Generate a strong key: openssl rand -hex 32

# 3. Start infrastructure
docker compose up postgres redis -d

# 4. Backend setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_db.py       # creates employee1/emp123 and admin/admin123
python build_vector_db.py       # ingests 100 KB documents into ChromaDB + BM25

# 5. Start API
uvicorn app.api.server:app --reload --port 8000

# 6. Start frontend (new terminal)
cd frontend
npm install
npm run dev

# Open http://localhost:5173
```

### Docker (Full Stack)

```bash
cp .env.example .env
# Set OPENAI_API_KEY and SECRET_KEY in .env

docker compose up --build
docker compose --profile migrate up migrate   # run DB migrations

# API:      http://localhost:8000
# Frontend: http://localhost:5173
# Docs:     http://localhost:8000/docs
```

### Default Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Employee | `employee1` | `emp123` |

> **Change these immediately in any non-local deployment.**

---

## API Reference

### Authentication

```bash
# Login
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "employee1", "password": "emp123"}'

# Response
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "role": "user"
}
```

### Ask a Question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"session_id": "uuid-here", "question": "What is the annual leave policy?"}'

# Response
{
  "answer": "Employees receive 21 days of annual leave per year for the first 5 years...",
  "agent": "hr",
  "confidence": 92,
  "confidence_reason": "Answer found directly in HR policy document",
  "source": "hr_1.txt",
  "evaluation_score": 89,
  "response_time": 1.24,
  "steps": [
    "Planner → classified as HR intent",
    "Guardrail → passed",
    "Router → dispatched to HR Agent",
    "CRAG → 3/4 chunks graded relevant",
    "HR Agent → generated grounded response",
    "Report → confidence 92%, eval 89"
  ],
  "status": "success"
}
```

### Streaming Response

```bash
curl -X POST http://localhost:8000/ask/stream \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"session_id": "uuid-here", "question": "How do I reset my VPN?"}'

# Server-Sent Events stream: token-by-token
data: {"token": "To"}
data: {"token": " reset"}
data: {"token": " your"}
...
data: {"done": true, "metadata": {...}}
```

### Action Management (Admin)

```bash
# List pending actions
curl http://localhost:8000/actions?status=PENDING \
  -H "Authorization: Bearer <admin-token>"

# Approve an action
curl -X POST http://localhost:8000/actions/{id}/approve \
  -H "Authorization: Bearer <admin-token>" \
  -d '{"notes": "Approved — valid request"}'
```

Full interactive API documentation: **http://localhost:8000/docs**

---

## Project Structure

```
enterprise-ai-workforce/
├── app/
│   ├── agents/             # Specialist AI agents (HR, IT, Finance, Planner)
│   ├── api/                # FastAPI routes (server.py, kb_manager.py)
│   ├── auth/               # JWT creation, verification, bcrypt
│   ├── config/             # Settings (Pydantic), logger
│   ├── core/               # Constants, middleware, shared utilities
│   ├── db/                 # SQLAlchemy models, async session, repositories
│   ├── evaluation/         # Response quality scorer (0-100)
│   ├── knowledge/          # Static policy docs (hr_policy.txt etc.)
│   ├── llm/                # OpenAI client wrapper with retry/backoff
│   ├── rag/                # ChromaDB, BM25, RRF fusion, CRAG grader
│   ├── schemas/            # Pydantic request/response schemas
│   ├── tools/              # PDF generator, automation engine
│   ├── utils/              # Confidence scorer, guardrails, fuzzy match
│   └── workflows/          # LangGraph StateGraph pipeline
├── alembic/                # DB migration versions
├── data/                   # Knowledge base documents (100 .txt files)
│   ├── HR/                 # 25 HR policy documents
│   ├── IT/                 # 25 IT policy documents
│   ├── Finance/            # 25 Finance policy documents
│   ├── General/            # 12 general workplace documents
│   └── Company/            # 25 company information documents
├── frontend/
│   └── src/
│       ├── api/            # Axios client, TypeScript types
│       ├── components/     # UI components (chat, admin, shared)
│       ├── context/        # Auth, RTL React contexts
│       └── pages/          # Login, Chat, Admin, Profile
├── scripts/                # seed_db.py, generate_kb.py
├── tests/                  # pytest unit tests + k6 load tests
├── .github/
│   ├── workflows/          # ci.yml, deploy.yml
│   └── ISSUE_TEMPLATE/     # Bug report, feature request templates
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ | OpenAI API key |
| `SECRET_KEY` | ✅ | JWT signing secret (min 32 chars) — `openssl rand -hex 32` |
| `DATABASE_URL` | ✅ | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `DATABASE_URL_SYNC` | ✅ | Sync PostgreSQL URL for Alembic (`postgresql+psycopg2://...`) |
| `REDIS_URL` | ✅ | Redis URL (`redis://host:6379`) |
| `LANGCHAIN_TRACING_V2` | Optional | `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | Optional | LangSmith API key |
| `LANGCHAIN_PROJECT` | Optional | LangSmith project name |
| `WHATSAPP_TOKEN` | Optional | WhatsApp Business API token |
| `WHATSAPP_PHONE_NUMBER_ID` | Optional | WhatsApp sender phone number ID |
| `WHATSAPP_VERIFY_TOKEN` | Optional | Webhook verify token |
| `PORT` | Optional | API port (default: 8000) |
| `DEBUG` | Optional | `false` in production |

> `SECRET_KEY` uses Docker Compose `:?` — the container **refuses to start** if this variable is unset. There is no insecure default.

---

## Deployment

### Railway (API) + Vercel (Frontend)

**Backend — Railway:**

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

Set these environment variables in the Railway dashboard:
- `OPENAI_API_KEY`, `SECRET_KEY`, `DATABASE_URL`, `DATABASE_URL_SYNC`, `REDIS_URL`

**Frontend — Vercel:**

```bash
cd frontend
npx vercel --prod
```

Set `VITE_API_URL` to your Railway API URL in Vercel dashboard.

**Enable CI/CD auto-deploy:**

Add these to GitHub → Settings → Secrets and Variables → Actions:
- Secrets: `RAILWAY_TOKEN`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`
- Variables: `RAILWAY_ENABLED=true`, `VERCEL_ENABLED=true`

### Self-Hosted (Docker)

```bash
# Production deployment
docker compose up --build -d
docker compose --profile migrate up migrate

# With custom domain via nginx reverse proxy
# Point nginx to port 8000 (API) and 5173 (frontend)
```

---

## CI/CD

```
Push to main
     │
     ├── CI / Backend (Python 3.12)
     │     ├── pytest unit tests
     │     ├── server import smoke test
     │     └── LangGraph workflow smoke test
     │
     ├── CI / Frontend (Node 22)
     │     ├── npm ci
     │     ├── tsc --noEmit (strict type check)
     │     └── npm run build (production build)
     │
     ├── CI / Docker build
     │     └── docker build + import check
     │
     └── Deploy (if RAILWAY_ENABLED / VERCEL_ENABLED = true)
           ├── railway up → API
           └── vercel --prod → Frontend
```

---

## Resilience Design

| Failure | Behaviour |
|---------|-----------|
| **LLM unavailable** | Exponential backoff ×3 (1s/2s/4s) → graceful user message |
| **Redis down** | Conversation continues without memory context |
| **ChromaDB down** | BM25 sparse retrieval continues independently |
| **PostgreSQL down** | 503 returned; no partial writes; filesystem fallback log |
| **All chunks irrelevant** | Automatic query rewrite + one retry before fallback |
| **Unauthorised action** | Blocked at PENDING state; never reaches EXECUTING without admin gate |

---

## Security

- **JWT HS256** — stateless auth; expiry enforced on every protected route
- **bcrypt cost 12** — timing-safe password hashing and comparison
- **Path traversal protection** — `_safe_path()` uses `.resolve()` + `startswith()` on all KB file operations
- **Secret enforcement** — `SECRET_KEY` uses Docker `:?` syntax; container startup fails if unset
- **Rate limiting** — Redis sliding-window per-user on all `/ask` endpoints
- **No secrets in git** — `.env` excluded; `.env.example` contains only placeholders
- **Input validation** — Pydantic schemas validate all request bodies before business logic

To report a vulnerability: see [SECURITY.md](SECURITY.md)

---

## Scalability

Current architecture supports single-server deployment with ~50 concurrent users (validated via k6 load tests — p95 < 3s, p99 < 6s).

**Horizontal scaling path:**
1. Multiple FastAPI replicas behind NGINX (stateless API — JWT + Redis session)
2. Celery/ARQ async workers for action execution (decouple from API)
3. ChromaDB collection sharding by `company_id` (column already exists on all tables)
4. Read replicas for PostgreSQL analytics queries
5. Kubernetes Helm chart for enterprise on-premise deployment

---

## Future Roadmap

**Near-term:**
- [ ] WhatsApp channel integration (webhook scaffolded, needs pipeline wiring)
- [ ] Voice input via Whisper API
- [ ] Jira/ServiceNow ticket creation from actions
- [ ] Admin analytics dashboard (query trends, confidence over time)

**Medium-term:**
- [ ] Multi-company SaaS (`company_id` column already in schema)
- [ ] Fine-tuned intent classifier to replace GPT-4o-mini Planner
- [ ] Per-session document Q&A (user uploads PDF, temporary collection)
- [ ] SAML/SSO — Okta + Azure AD integration

**Long-term:**
- [ ] Agent builder UI (create new agents via form, no redeploy)
- [ ] Multi-step approval chains (HR → Finance → Payroll)
- [ ] GCC policy packs (Saudi, DIFC, Kuwait Labour Law)
- [ ] Kubernetes Helm chart for on-premise enterprise deployment

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, branch strategy, commit conventions, and PR checklist.

---

## License

[MIT](LICENSE) — free to use, modify, and deploy.

---

<div align="center">

**Built for enterprise operations. Architected for production deployment.**

*LangGraph · GPT-4o-mini · ChromaDB · BM25 · RRF · CRAG · FastAPI · React · PostgreSQL · Redis*

</div>
