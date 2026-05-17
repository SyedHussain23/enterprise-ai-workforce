# Enterprise AI Workforce

[![CI](https://github.com/SyedHussain23/enterprise-ai-workforce/actions/workflows/ci.yml/badge.svg)](https://github.com/SyedHussain23/enterprise-ai-workforce/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Production-grade agentic AI platform for enterprise HR, IT, and Finance automation.**  
> Built for UAE/GCC enterprises. Arabic RTL support. WhatsApp-native.

---

## What It Does

Employees ask questions in natural language — the AI routes them to the right department agent, retrieves accurate policy information, and executes real actions (leave applications, IT tickets, expense claims) that flow into an approval workflow.

| What you ask | What happens |
|---|---|
| "What is the annual leave policy?" | HR Agent → Hybrid RAG → CRAG-graded answer |
| "I want to apply for leave" | HR Agent → Action created → Manager notified |
| "Reset my password" | IT Agent → Password policy + self-service steps |
| "Submit an expense claim" | Finance Agent → Expense action → Pending approval |
| WhatsApp: "How do I get a salary advance?" | Finance Agent → WhatsApp reply in <3s |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                           │
│        Login · Chat (SSE) · Admin Dashboard · Approvals        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ JWT · REST · SSE
┌──────────────────────────▼──────────────────────────────────────┐
│                      FastAPI Backend                            │
│   /ask  /ask/stream  /actions  /admin/*  /webhook/whatsapp      │
└──────┬──────────────────────────────────────┬───────────────────┘
       │                                      │
┌──────▼───────────────────────┐   ┌──────────▼──────────────────┐
│      LangGraph Workflow      │   │     PostgreSQL (multi-tenant)│
│                              │   │  companies · users · actions │
│  planner ──► router ──► crag │   │  workflow_logs · audit_log   │
│                │             │   └─────────────────────────────-┘
│              report          │
└──────┬───────────────────────┘   ┌─────────────────────────────┐
       │                           │   Redis                      │
  ┌────▼────┐  ┌────────────────┐  │   Multi-turn memory (10-turn)│
  │HR Agent │  │ Hybrid RAG     │  │   Cost tracking (per-company)│
  │IT Agent │  │ BM25 + Vector  │  │   Rate limiting              │
  │Finance  │  │ RRF Fusion     │  └─────────────────────────────-┘
  │Agent    │  │ CRAG Grading   │
  └─────────┘  └───────┬────────┘  ┌─────────────────────────────┐
                        │           │   ChromaDB                   │
                        └──────────►│   OpenAI Embeddings          │
                                    │   PDF document ingestion     │
                                    └─────────────────────────────-┘
```

**LangGraph flow:** `Planner → Router → CRAG → Report`
- **Planner**: classifies query to HR / IT / Finance using GPT-4o
- **Router**: runs the department agent (keyword match → policy answer → hybrid RAG)
- **CRAG**: grades retrieved chunks — filters irrelevant, rewrites query if needed
- **Report**: evaluates answer quality, saves to Redis memory, returns structured response

---

## Tech Stack

| Layer | Technology |
|---|---|
| **API** | FastAPI 0.115 · Uvicorn · SSE-Starlette |
| **AI Orchestration** | LangGraph · LangChain · LangSmith tracing |
| **LLM** | OpenAI GPT-4o (planner, CRAG grader, evaluation) |
| **Retrieval** | ChromaDB + BM25 hybrid · Reciprocal Rank Fusion · CRAG |
| **Database** | PostgreSQL 16 (async SQLAlchemy 2.0, Alembic migrations) |
| **Memory** | Redis (multi-turn conversation, cost counters, rate limiting) |
| **Frontend** | React 19 · TypeScript · Tailwind CSS 4 · Recharts · Vite |
| **Auth** | JWT (python-jose) · bcrypt · multi-tenant company_id scoping |
| **Messaging** | WhatsApp Business Cloud API (Meta Graph API v20.0) |
| **Observability** | LangSmith · structured JSON logging · audit log table |
| **Testing** | Pytest · pytest-asyncio · k6 load testing |
| **Deploy** | Railway (API) · Vercel (UI) · Docker Compose (local) |

---

## Key Features

### Agentic Action Execution
Unlike chatbots that just explain policies, this system **creates real DB records** when users trigger actions. Leave applications, IT tickets, expense claims — all flow into an approval queue visible in the admin dashboard.

### Hybrid RAG (BM25 + Vector + RRF)
Dense vector retrieval catches semantic matches; BM25 catches exact keyword hits. Reciprocal Rank Fusion merges both lists without calibration. Chunks appearing in both retrievers get a confidence boost.

### Corrective RAG (CRAG)
After retrieval, a GPT-4o-mini grader evaluates each chunk as `relevant / ambiguous / irrelevant`. If all chunks fail, the system rewrites the query and retries before generating an answer — dramatically reducing hallucination.

### SSE Streaming
Answers stream word-by-word from `/ask/stream` using Server-Sent Events. The React frontend renders tokens as they arrive with a blinking cursor, then displays the full agent trace (confidence, source, steps) when done.

### Multi-Tenant SaaS Ready
Every database table is scoped with `company_id`. JWT tokens carry the company UUID. All queries, actions, feedback, and cost tracking are isolated per tenant.

### Arabic RTL Support
One toggle switches the entire UI to Arabic right-to-left layout using `html[dir="rtl"]`. Quick-suggestions and placeholder text switch to Arabic. WhatsApp channel also handles Arabic queries natively.

---

## Quick Start

### Prerequisites
- Python 3.12+, Node 22+
- PostgreSQL 16, Redis 7
- OpenAI API key

### 1. Clone & configure
```bash
git clone https://github.com/SyedHussain23/enterprise-ai-workforce.git
cd enterprise-ai-workforce
cp .env.example .env
# Edit .env — add OPENAI_API_KEY and a strong SECRET_KEY
```

### 2. Backend
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run migrations
PYTHONPATH=. alembic upgrade head

# Seed demo users (admin + employee1)
python scripts/seed_db.py

# Build knowledge base from PDF files in data/
python build_vector_db.py

# Start API
uvicorn app.api.server:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### 4. Docker (alternative — full stack)
```bash
docker compose up --build
# API: http://localhost:8000
# Frontend dev: docker compose --profile dev up
```

### Demo credentials
| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Employee | `employee1` | `emp123` |

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/login` | — | JWT login |
| `POST` | `/ask` | User | Full AI response |
| `POST` | `/ask/stream` | User | SSE streaming response |
| `POST` | `/feedback` | User | Rate a response (1–5) |
| `GET` | `/actions/mine` | User | My pending actions |
| `GET` | `/actions/pending` | Admin | All pending actions |
| `POST` | `/actions/{id}/approve` | Admin | Approve an action |
| `POST` | `/actions/{id}/reject` | Admin | Reject an action |
| `GET` | `/admin/stats` | Admin | Usage analytics |
| `GET` | `/admin/cost` | Admin | Daily + lifetime LLM cost |
| `GET` | `/admin/logs` | Admin | Recent workflow logs |
| `POST` | `/admin/documents` | Admin | Upload PDF to knowledge base |
| `DELETE` | `/session/{id}/memory` | User | Clear conversation memory |
| `GET` | `/webhook/whatsapp` | — | Meta webhook verification |
| `POST` | `/webhook/whatsapp` | — | Inbound WhatsApp messages |
| `GET` | `/health` | — | Health check |

Interactive docs: `http://localhost:8000/docs`

---

## Load Test Results

Run against local stack with `docker compose up`:

```bash
# Smoke test (1 VU, 30s)
k6 run tests/load/smoke.js

# Load test (ramp to 50 VU, 10m total)
k6 run tests/load/load_test.js

# Stress test (ramp to 100 VU)
k6 run tests/load/stress_test.js
```

Target thresholds:
- p95 latency < 3s under 50 concurrent users
- Error rate < 2%

---

## Project Structure

```
enterprise-ai-workforce/
├── app/
│   ├── agents/          # HR, IT, Finance agents (keyword + RAG)
│   ├── api/             # FastAPI server, all routes
│   ├── auth/            # JWT creation, dependency injection
│   ├── core/            # Config, logger, constants, middleware
│   ├── cost/            # Redis-based cost tracker (per-company)
│   ├── db/              # SQLAlchemy models, repositories, engine
│   ├── evaluation/      # LLM-as-judge evaluator
│   ├── feedback/        # User feedback repository
│   ├── memory/          # Redis multi-turn conversation memory
│   ├── rag/             # Hybrid retriever, CRAG, ChromaDB client
│   ├── schemas/         # Pydantic request/response models
│   ├── utils/           # Guardrails, confidence scoring, multi-intent
│   ├── whatsapp/        # Meta Cloud API client + message handler
│   └── workflows/       # LangGraph graph, nodes, state
├── frontend/            # React + TypeScript + Tailwind CSS app
│   ├── src/
│   │   ├── api/         # Fetch client, SSE consumer, TypeScript types
│   │   ├── components/  # Chat, Admin, Shared components
│   │   ├── context/     # Auth + RTL context providers
│   │   └── pages/       # Login, Chat, Admin pages
│   └── vercel.json
├── tests/
│   ├── load/            # k6 load test scripts
│   └── test_*.py        # Pytest unit tests
├── alembic/             # Database migrations
├── scripts/             # seed_db.py, run_evaluation.py
├── data/                # PDF knowledge base source files
├── .github/workflows/   # CI (lint + test + build) + Deploy pipeline
├── docker-compose.yml   # Full local stack
├── Dockerfile           # Multi-stage Python 3.12 image
└── railway.json         # Railway deployment config
```

---

## Deployment

### Railway (Backend API)
1. Push to GitHub
2. Connect repo in Railway dashboard → New Project → Deploy from GitHub
3. Set environment variables from `.env.example`
4. Railway auto-detects `railway.json` and deploys on every push to `main`

### Vercel (Frontend)
1. Import `frontend/` folder in Vercel dashboard
2. Set `VITE_API_URL` to your Railway URL
3. Update `vercel.json` rewrites to point to your Railway URL
4. Vercel auto-deploys on push to `main`

### GitHub Actions (Automated)
Set these repository secrets:
- `RAILWAY_TOKEN` — from Railway account settings
- `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` — from Vercel

Then every push to `main` runs CI → Deploy automatically.

---

## WhatsApp Setup

1. Create a Meta Developer account and app at [developers.facebook.com](https://developers.facebook.com)
2. Add WhatsApp product → get Phone Number ID and permanent token
3. Set webhook URL to `https://your-api.railway.app/webhook/whatsapp`
4. Set verify token to `enterprise_ai_verify` (or your custom value in `.env`)
5. Add to `.env`: `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`

---

## License

MIT © 2026
