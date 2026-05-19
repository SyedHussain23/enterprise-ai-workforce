<div align="center">

<img src="https://img.shields.io/badge/Enterprise%20AI-Workforce%20OS-6366f1?style=for-the-badge&logo=openai&logoColor=white" alt="Enterprise AI Workforce OS" height="40"/>

# Enterprise AI Workforce

### The AI that doesn't just answer questions — it *runs* your company's operations.

**Not a chatbot. Not a help desk. An AI operating system for HR, Finance, and IT.**

<br/>

[![Live App](https://img.shields.io/badge/🌐%20Live%20App-Visit%20Now-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://frontend-syedhussain23s-projects.vercel.app/)
[![API Docs](https://img.shields.io/badge/📡%20API%20Docs-Swagger%20UI-7c3aed?style=for-the-badge&logo=railway&logoColor=white)](https://enterprise-ai-workforce-production.up.railway.app/docs)
[![GitHub](https://img.shields.io/badge/⭐%20Star%20on-GitHub-24292e?style=for-the-badge&logo=github)](https://github.com/SyedHussain23/enterprise-ai-workforce)

<br/>

[![CI](https://github.com/SyedHussain23/enterprise-ai-workforce/actions/workflows/ci.yml/badge.svg)](https://github.com/SyedHussain23/enterprise-ai-workforce/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-3776ab?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0-f97316?logo=chainlink&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![React](https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-dc382d?logo=redis&logoColor=white)](https://redis.io)
[![License](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)

</div>

---

## 🎯 What Makes This Different

Most "AI for enterprise" tools are glorified search engines. You ask a question, they retrieve a document and paste it back.

**This platform is fundamentally different.** It understands *operational intent* — the difference between asking *about* a process and asking the system to *execute* it.

```
Employee:  "I need 2 days emergency leave from tomorrow"

❌  Typical AI:   "According to UAE Labour Law Article 61, employees are entitled to..."
                  (dumps 500 words of policy — employee still has to fill a form manually)

✅  This AI:      "Got it! I have: emergency leave, 2 days, starting tomorrow.
                  Could you confirm — is this Annual or Personal leave?
                  Once confirmed I'll file it instantly."
                  → Workflow created → Manager notified → Tracked in dashboard → Audit logged
```

---

## 🔗 Live Links

| | Service | URL |
|---|---------|-----|
| 🌐 | **Frontend App** | [frontend-syedhussain23s-projects.vercel.app](https://frontend-syedhussain23s-projects.vercel.app/) |
| 📡 | **Backend API** | [enterprise-ai-workforce-production.up.railway.app](https://enterprise-ai-workforce-production.up.railway.app) |
| 📖 | **Interactive API Docs** | [/docs (Swagger UI)](https://enterprise-ai-workforce-production.up.railway.app/docs) |
| ❤️ | **Health Check** | [/health](https://enterprise-ai-workforce-production.up.railway.app/health) |
| 💻 | **Source Code** | [github.com/SyedHussain23/enterprise-ai-workforce](https://github.com/SyedHussain23/enterprise-ai-workforce) |

---

## 🧠 The AI Brain — How It Actually Works

This is the core innovation. A **deterministic-first classification pipeline** decides what to do with every message in milliseconds — no wasted API calls, no hallucinated actions, no falling back to policy dumps.

```
User Message
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 1 — GUARDRAIL  (~0 ms, pure Python)              │
│  Profanity · Prompt injection · PII · Out-of-scope?     │
│  → YES: block with explanation                          │
└──────────────────────────┬──────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  LAYER 2 — INTENT CLASSIFIER  (~0 ms, zero API calls)   │
│                                                         │
│  SYSTEM?   "what do you do?"    → capabilities page     │
│  ACTION?   "I need leave"       → workflow intake       │
│  FOLLOWUP? pending workflow     → slot merging          │
│  INFO?     "what is gratuity?"  → RAG retrieval         │
└──────────────────────────┬──────────────────────────────┘
                           │
         ┌─────────────────┼──────────────────┐
         ↓                 ↓                  ↓
    SYSTEM             ACTION/FOLLOWUP        INFO
    ↓                  ↓                     ↓
  Return           Slot collection       Domain agent
  capabilities     engine (multi-turn)   HR / IT / Finance
                   ↓                     ↓
             All slots?               Hybrid RAG
             ↓          ↓             (ChromaDB + BM25)
           Yes          No            CRAG quality gate
           ↓            ↓             GPT-4o synthesis
        Create       Ask              ↓
        workflow     clarifying       Natural policy
        ↓            question        answer
      DB entity      ↓
      Manager        Save state
      notified       to Redis
      Dashboard      (30 min TTL)
      Audit log
```

### Intent Routing Table

| What the employee says | Intent detected | What happens |
|------------------------|-----------------|--------------|
| `"i need 2 days leave"` | ACTION → apply_leave | Asks for leave type + start date |
| `"from tomorrow, annual"` | FOLLOWUP → apply_leave | Merges slots, creates workflow |
| `"im sick today"` | ACTION → sick_leave_report | Asks how many days, notifies manager |
| `"increase my salary by 10%"` | ACTION → salary_increase_request | Starts compensation review |
| `"submit expense AED 500 for lunch"` | ACTION → submit_expense | Asks for receipt + category |
| `"work from home tomorrow"` | ACTION → wfh_request | Creates WFH request |
| `"what is gratuity?"` | INFO → HR | RAG retrieval → policy answer |
| `"how do I apply for leave?"` | INFO → HR | Explains process (does NOT file a request) |
| `"what can you do?"` | SYSTEM | Returns full capabilities overview |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      React 19 + TypeScript  ·  Vercel CDN               │
│   Chat · My Requests · Approvals · Admin · Notifications · RTL/Arabic   │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │  HTTPS · Server-Sent Events · JWT
┌──────────────────────────────────▼──────────────────────────────────────┐
│                    FastAPI 0.115  ·  Railway                             │
│     Rate limiter · Semantic cache · CORS · Security headers              │
└────────────┬──────────────────────────────┬────────────────────────────┘
             │                              │
  ┌──────────▼──────────┐       ┌───────────▼──────────┐
  │  Conversation        │       │  Lifecycle Service   │
  │  Engine  🧠          │       │  pending → approved  │
  │                      │       │  → rejected →        │
  │  classify_intent()   │       │  completed           │
  │  extract_slots()     │       └───────────┬──────────┘
  │  generate_clari()    │                   │
  │  create_workflow()   │       ┌───────────▼──────────┐
  └──────────┬──────────┘       │  Notification Engine │
             │                  │  emit on every state  │
  ┌──────────▼──────────┐       │  change              │
  │   LangGraph          │       └──────────────────────┘
  │   Workflow Graph     │
  │  planner → router    │  ┌──────────────────────────┐
  │  → crag → report     │  │     PostgreSQL 16         │
  └──────────┬──────────┘  │  users · companies        │
             │             │  conversations · actions  │
  ┌──────────▼──────────┐  │  notifications · audit   │
  │   Domain Agents      │  └──────────────────────────┘
  │   HR · IT · Finance  │
  └──────────┬──────────┘  ┌──────────────────────────┐
             │             │       Redis 7             │
  ┌──────────▼──────────┐  │  conv memory · cache     │
  │   Hybrid RAG         │  │  pending workflow state  │
  │  ChromaDB + BM25     │  │  rate limiter            │
  │  Cross-encoder rerank│  └──────────────────────────┘
  │  CRAG quality gate   │
  └──────────┬──────────┘  ┌──────────────────────────┐
             │             │  OpenAI GPT-4o/4o-mini   │
             └────────────►│  (classification only    │
                           │   for ambiguous cases)   │
                           └──────────────────────────┘
```

---

## ✅ Full Request Lifecycle

Every workflow runs through the same production-grade state machine:

```
Employee sends message
        │
        ▼
  AI detects ACTION intent  (pure Python, 0ms)
        │
        ▼
  Slot collection (multi-turn if needed)
        │  All slots collected
        ▼
  ┌─────────────┐
  │   PENDING   │──► Saved to PostgreSQL
  └──────┬──────┘    Manager notified (in-app)
         │           Visible in /requests dashboard
         │
    ┌────┴──────────────────────┐
    │                           │
    ▼                           ▼
┌──────────┐               ┌──────────┐
│ APPROVED │               │ REJECTED │
└────┬─────┘               └────┬─────┘
     │                          │
     ▼                          ▼
 Execute action            Employee notified
 automatically             with reason
     │
     ▼
 ┌───────────┐
 │ COMPLETED │──► Audit trail entry written
 └───────────┘    Employee notified
```

**Every single state transition:**
- Persisted to append-only `audit_logs` (actor + timestamp + payload)
- Triggers in-app notification to all relevant parties
- Reflected immediately on the `/requests` dashboard
- Visible to managers on the `/approvals` queue

---

## 🚀 Supported Workflows

| Workflow | Example Triggers | Collected Information |
|----------|-----------------|----------------------|
| 🏖️ **Leave Request** | "i need 2 days leave", "apply for annual leave" | type, start date, duration |
| 🤒 **Sick Leave** | "im sick", "i have a fever", "not feeling well" | number of days |
| 🏠 **WFH Request** | "work from home tomorrow", "wfh today" | date, optional reason |
| 💰 **Salary Increase** | "increase my salary by 10%", "i want a raise" | percentage, justification |
| 🧾 **Expense Claim** | "submit expense AED 500", "reimburse me" | amount, category, description |
| 💵 **Salary Advance** | "need salary advance", "advance payment" | amount, reason |
| 👶 **Maternity/Paternity** | "i'm pregnant", "need maternity leave" | expected date, duration |
| 📚 **Training Request** | "enroll me in a course", "request training budget" | course name, cost |
| 💻 **IT Ticket** | "my laptop is broken", "network issue" | device, issue description |
| 🔑 **System Access** | "need access to Salesforce", "give me access" | system, reason |
| 📋 **Grievance Report** | "file a complaint", "report harassment" | description, date |
| 👤 **Profile Update** | "update my phone number", "change my IBAN" | field + new value |

---

## 🛠️ Full Tech Stack

### Backend
| Component | Technology | Version |
|-----------|-----------|---------|
| API Framework | FastAPI + Pydantic v2 | 0.115 |
| Database | PostgreSQL + SQLAlchemy 2 (async) + Alembic | 16 |
| Cache / Memory | Redis | 7 |
| AI Orchestration | LangGraph + LangChain | 1.0 / 1.2 |
| LLM | OpenAI GPT-4o + GPT-4o-mini | latest |
| Vector Store | ChromaDB + BM25 + Cross-encoder rerank | — |
| Auth | JWT (HS256) + JTI blocklist + bcrypt | — |
| PDF Generation | ReportLab | 4.x |
| Observability | structlog + audit_logs table | — |
| Testing | pytest + pytest-asyncio | 141 tests |

### Frontend
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | React + TypeScript | 19 |
| Build Tool | Vite + Rolldown | — |
| Styling | TailwindCSS | v4 |
| Routing | react-router | v6 |
| Icons | lucide-react | — |
| Notifications | react-hot-toast | — |
| Streaming | Native EventSource (SSE) | — |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Backend hosting | [Railway](https://railway.app) |
| Frontend hosting | [Vercel](https://vercel.com) |
| Container | Docker (multi-stage build) |
| CI/CD | GitHub Actions (Python 3.12) |
| Local dev | docker-compose |

---

## 📁 Project Structure

```
enterprise-ai-workforce/
│
├── app/                              # FastAPI backend
│   ├── agents/
│   │   ├── hr_agent.py               # Leave, sick, WFH, salary, grievance
│   │   ├── it_agent.py               # Tickets, access, hardware
│   │   ├── finance_agent.py          # Expenses, advances, payroll
│   │   └── planner_agent.py          # Department router (INFO queries)
│   │
│   ├── api/routes/
│   │   ├── ai.py                     # POST /ask · /ask/stream · /ask/extract
│   │   ├── actions.py                # Approve / reject / cancel queue
│   │   ├── requests.py               # Lifecycle: detail, comments, timeline
│   │   ├── notifications.py          # Inbox + mark-read
│   │   ├── admin.py                  # Users, audit log, KB upload
│   │   ├── auth.py                   # Login / logout / refresh
│   │   └── health.py                 # Liveness + dependency check
│   │
│   ├── core/
│   │   ├── conversation_engine.py    # 🧠 THE AI BRAIN
│   │   │                             #   classify_deterministic() — pure Python
│   │   │                             #   extract_slots_simple()   — regex, ~0ms
│   │   │                             #   generate_clarification() — GPT-4o + template
│   │   │                             #   generate_workflow_confirmation()
│   │   ├── semantic_cache.py         # Redis vector cache with ACTION bypass
│   │   ├── openai_client.py          # Resilient client (retry + circuit breaker)
│   │   └── config.py                 # Pydantic settings
│   │
│   ├── db/
│   │   ├── models/                   # SQLAlchemy typed models
│   │   │   ├── user.py               # User + UserRole
│   │   │   ├── company.py            # Company + CompanyPlan (multi-tenant)
│   │   │   ├── action.py             # Workflow request entity
│   │   │   ├── notification.py       # In-app notification
│   │   │   └── audit_log.py          # Append-only audit trail
│   │   └── repositories/             # All DB queries live here (never inline)
│   │
│   ├── memory/
│   │   └── redis_memory.py           # Conv history + pending workflow state
│   │
│   ├── utils/
│   │   ├── workflow_slots.py         # 12 workflow definitions + slot maps
│   │   ├── intent_classifier.py      # is_informational_query() guard
│   │   ├── guardrails.py             # PII, profanity, injection detection
│   │   └── multi_intent.py           # Multi-department query splitting
│   │
│   └── workflows/
│       ├── workflow_graph.py         # LangGraph: planner→router→crag→report
│       └── workflow_state.py         # TypedDict state (short_circuit flag etc)
│
├── frontend/src/
│   ├── pages/
│   │   ├── ChatPage.tsx              # Main AI chat interface
│   │   ├── RequestsPage.tsx          # Employee: my requests + timeline
│   │   ├── ApprovalsPage.tsx         # Manager: approval queue + actions
│   │   ├── AdminPage.tsx             # Admin: users, audit, KB management
│   │   └── ProfilePage.tsx           # User settings
│   └── components/
│       ├── chat/                     # MessageBubble, ChatInput, AgentTrace
│       ├── requests/                 # StatusBadge, RequestDetail, CommentThread
│       └── shared/                   # WorkspaceLayout, NotificationBell
│
├── tests/                            # 141 tests · 17 skipped (DB/Redis)
│   ├── test_conversation_engine.py   # 72 deterministic + slot extraction tests
│   ├── test_guardrails.py
│   ├── test_evaluation.py
│   ├── test_confidence.py
│   └── test_lifecycle.py
│
├── alembic/versions/                 # Database migration history
├── .github/workflows/ci.yml          # GitHub Actions CI (backend + frontend + Docker)
├── Dockerfile                        # Multi-stage production image
├── docker-compose.yml                # Local dev (postgres + redis + backend)
├── requirements.txt                  # All Python dependencies
└── pytest.ini                        # Test configuration
```

---

## ⚡ Getting Started

### Prerequisites
- Python 3.12+ · Node.js 22+ · PostgreSQL 16+ · Redis 7+
- OpenAI API key ([get one here](https://platform.openai.com))

### Option A — Docker (Recommended, quickest)

```bash
git clone https://github.com/SyedHussain23/enterprise-ai-workforce.git
cd enterprise-ai-workforce

# Set your env vars
cp .env.example .env
# Edit .env: OPENAI_API_KEY=sk-... · SECRET_KEY=your-32-char-secret

# Start backend + postgres + redis
docker-compose up --build

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```

Open **[http://localhost:5173](http://localhost:5173)**

### Option B — Manual

```bash
# 1. Clone
git clone https://github.com/SyedHussain23/enterprise-ai-workforce.git
cd enterprise-ai-workforce

# 2. Python environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Environment variables
cp .env.example .env
# Fill in: OPENAI_API_KEY, SECRET_KEY, DATABASE_URL, REDIS_URL

# 4. Database setup
alembic upgrade head

# 5. Start backend
uvicorn app.api.server:app --reload --port 8000

# 6. Start frontend (new terminal)
cd frontend && npm install && npm run dev
```

**Backend:** [http://localhost:8000](http://localhost:8000) · **API docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
**Frontend:** [http://localhost:5173](http://localhost:5173)

### Run Tests

```bash
# Full suite (auto-skips DB tests if PostgreSQL not running)
pytest tests/ -q

# Exact CI command (no services needed)
pytest tests/test_evaluation.py tests/test_guardrails.py tests/test_confidence.py -v

# AI brain tests specifically (72 tests, zero API calls required)
pytest tests/test_conversation_engine.py -v
```

---

## 🌍 Deploy to Production

### Backend → Railway

```bash
# 1. Push to GitHub (CI runs automatically)
git push origin main

# 2. Railway dashboard → New project → Connect GitHub repo
# 3. Add PostgreSQL and Redis plugins
# 4. Set environment variables:
```

```env
OPENAI_API_KEY=sk-...
SECRET_KEY=your-minimum-32-character-secret-key-here
DATABASE_URL=postgresql+asyncpg://...    # auto-set by Railway Postgres plugin
REDIS_URL=redis://...                   # auto-set by Railway Redis plugin
ALLOWED_ORIGINS=https://your-app.vercel.app
```

Railway auto-runs `alembic upgrade head` on every deploy. Zero-downtime deploys by default.

**Live backend:** https://enterprise-ai-workforce-production.up.railway.app

### Frontend → Vercel

```bash
# 1. Vercel dashboard → New project → Import GitHub repo
# 2. Set root directory: frontend/
# 3. Set environment variable:
```

```env
VITE_API_BASE=https://enterprise-ai-workforce-production.up.railway.app
```

Vercel auto-detects Vite. Every push to `main` triggers a deployment.

**Live frontend:** https://frontend-syedhussain23s-projects.vercel.app/

---

## 🔐 Security Features

| Feature | Implementation |
|---------|---------------|
| **JWT Authentication** | HS256 tokens with configurable expiry |
| **Token revocation** | JTI blocklist in Redis — logout invalidates instantly |
| **Password hashing** | bcrypt (work factor 12) |
| **Multi-tenant isolation** | Every DB row is `company_id`-scoped — no cross-tenant data possible |
| **Role-based access** | `employee` / `manager` / `admin` enforced at API level |
| **AI guardrails** | Profanity · PII detection · Prompt-injection blocklist · Gibberish filter |
| **Rate limiting** | Per-IP sliding window in Redis, configurable per endpoint |
| **CORS** | Explicit origin allowlist — wildcard only in `DEBUG=true` |
| **Security headers** | X-Frame-Options · X-Content-Type-Options · Referrer-Policy |
| **Audit trail** | Append-only `audit_logs` — every login, action, and approval recorded |
| **HTTPS** | Enforced at Railway + Vercel CDN level |

---

## 📐 Key Design Principles

**1. Deterministic first, LLM second.**
The intent classifier uses pure Python pattern matching for ~90% of all messages — zero API cost, zero latency. GPT-4o is called only for genuinely ambiguous cases that the pattern engine can't resolve.

**2. ACTION vs INFO is a hard boundary.**
`"How do I apply for leave?"` → policy explanation. `"I need to apply for leave"` → workflow intake. These are treated as fundamentally different operations, never conflated.

**3. Cache bypass for action queries.**
The semantic cache is completely skipped for `ACTION`, `FOLLOWUP`, and `SYSTEM` intents — checked in pure Python before any cache lookup. Stale responses can never block workflow execution.

**4. Multi-turn slot collection.**
Workflows requiring multiple inputs span multiple turns. Partial state lives in Redis with a 30-minute TTL — natural conversation, no forms.

**5. Repository pattern, thin routes.**
Every database query lives in `app/db/repositories/`. Route handlers contain no ORM logic. One implementation per concept, no duplication.

**6. Audit everything.**
`AuditLogRepository.log()` is called on every state transition. The request timeline is reconstructed from that append-only table — no separate history model to desync.

**7. Fail closed.**
Guardrails block on uncertainty. Cross-account credential attempts trigger a security alert, not a policy answer. Tests auto-skip rather than fail when services are unavailable.

---

## 🗺️ Roadmap

- [ ] **SLA timers** — auto-escalate approvals pending beyond configured threshold
- [ ] **Email + Slack** — notification delivery beyond in-app
- [ ] **Per-department approver routing** — HR requests → HR manager (not any manager)
- [ ] **Dashboard analytics** — approval throughput, avg time-to-decision, volume by dept
- [ ] **Voice input** — speech-to-text feeding the same intent pipeline
- [ ] **Receipt photo → expense** — multimodal: photo of receipt auto-populates expense claim
- [ ] **Native mobile** — iOS/Android wrapper around the PWA

---

## 🤝 Contributing

PRs are welcome!

1. Fork the repo and create a feature branch
2. Add tests for any new behavior
3. Run `pytest tests/ -q` and `cd frontend && npm run build` before opening a PR
4. Database migrations live in `alembic/versions/` — never edit a shipped migration, write a new one

---

## 📄 License

MIT — see [`LICENSE`](./LICENSE).

---

<div align="center">

**Built in the UAE · Designed for HR, IT & Finance teams who want to stop forwarding emails.**

<br/>

[![Live App](https://img.shields.io/badge/🌐%20Try%20the%20Live%20App-000000?style=for-the-badge&logo=vercel)](https://frontend-syedhussain23s-projects.vercel.app/)
&nbsp;&nbsp;
[![API Docs](https://img.shields.io/badge/📡%20Explore%20the%20API-7c3aed?style=for-the-badge&logo=railway)](https://enterprise-ai-workforce-production.up.railway.app/docs)
&nbsp;&nbsp;
[![GitHub](https://img.shields.io/badge/⭐%20Star%20on%20GitHub-24292e?style=for-the-badge&logo=github)](https://github.com/SyedHussain23/enterprise-ai-workforce)

</div>
