<div align="center">

# Enterprise AI Workforce

### An AI operating system for HR, IT and Finance — not another chatbot.

Employees talk to one assistant. The platform classifies intent, executes workflows,
involves the right humans for approval, and ships a full audit trail.

[![Live demo](https://img.shields.io/badge/Live%20demo-Vercel-000000?logo=vercel)](https://frontend-syedhussain23s-projects.vercel.app/)
[![API docs](https://img.shields.io/badge/API%20docs-Railway-7c3aed?logo=railway)](https://enterprise-ai-workforce-production.up.railway.app/docs)
[![Python](https://img.shields.io/badge/Python-3.12-3776ab?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=black)](https://react.dev)
[![Postgres](https://img.shields.io/badge/Postgres-15-336791?logo=postgresql&logoColor=white)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)

</div>

---

## Why this exists

Enterprise teams burn hours on the same low-value loop:

> *Employee asks a question → HR/IT/Finance reads it → looks up a policy → replies →
> often a form follows → manager approves → another team executes → notifies the employee.*

Most "AI" deployments solve the first hop and stop — answer the question. That is a chatbot.

This platform solves the **entire loop**: the same conversation that answers a policy question
can submit a request, route it to the right approver, capture comments, notify the employee,
execute the downstream action, and write to the audit log.

---

## What you actually get

| Capability | What it means |
|---|---|
| **Multi-agent orchestration** | Specialised HR / IT / Finance agents share a planner; the router picks one or splits a multi-intent request. |
| **Real workflow engine** | Pending → approved/rejected/cancelled → completed. State transitions are persisted and reflected in the UI. |
| **Human in the loop** | Managers (not just admins) can approve from the dedicated `/approvals` page with notes. Employees can cancel from `/requests`. |
| **In-app notifications** | Bell with unread count. Approvers get a notification when a request lands; employees get one when their request is decided or commented on. |
| **Threaded comments** | Every request has a comment thread for back-and-forth without leaving the platform. |
| **Audit trail** | Append-only `audit_logs` table records every state transition, login, and policy change. |
| **RAG with hybrid retrieval** | Dense vectors (Chroma) + BM25 with cross-encoder rerank, scoped per tenant. |
| **Production guardrails** | Word-boundary phrase detection, prompt-injection blocklist, PII detection, gibberish filter, profanity filter. |
| **Streaming UX** | SSE token streaming with status hints, cancel button, retry, and regenerate. |
| **Bilingual** | English + Arabic with RTL toggle. |
| **Multi-tenant** | Every table is `company_id`-scoped; users, conversations, and requests can never leak across tenants. |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              React 19 + TypeScript                          │
│  Chat · Requests · Approvals · Admin · Notifications · Profile · RTL/Arabic │
└─────────────────────────────────────────┬───────────────────────────────────┘
                                          │   HTTPS · SSE · Bearer JWT
┌─────────────────────────────────────────▼───────────────────────────────────┐
│                                FastAPI gateway                              │
│  Guardrails · Rate limiter · Semantic cache · JWT + JTI blocklist · CORS    │
└───────────┬─────────────────────────────┬───────────────────────┬───────────┘
            │                             │                       │
   ┌────────▼────────┐         ┌──────────▼─────────┐    ┌────────▼────────┐
   │  Planner agent  │         │ Lifecycle service  │    │ Notification     │
   │  routes intent  │         │ pending/approved/  │    │ emit on every    │
   │  HR · IT · Fin  │         │ rejected/cancelled │    │ state transition │
   └────────┬────────┘         └──────────┬─────────┘    └────────┬────────┘
            │                             │                       │
   ┌────────▼────────┐         ┌──────────▼─────────┐    ┌────────▼────────┐
   │ Hybrid RAG      │         │ Postgres           │    │ Redis             │
   │ Chroma + BM25   │◄────────┤ Users · Companies  │◄───┤ Memory · Cache    │
   │ Cross-encoder   │         │ Conversations      │    │ Rate limiter      │
   │ rerank          │         │ Actions · Audit    │    │ JTI blocklist     │
   └────────┬────────┘         │ Notifications      │    └───────────────────┘
            │                  └────────────────────┘
            │
   ┌────────▼────────┐
   │  LLM provider   │
   │  OpenAI · GPT-4 │
   └─────────────────┘
```

---

## The request lifecycle

Every approval flows through the same state machine, no matter the action type.

```
                       employee asks AI
                              │
                              ▼
                  ┌──────────────────────┐
                  │   AI classifies      │
                  │ ┌──────────────────┐ │
                  │ │ information      │ │──► answer + cite source
                  │ │ action           │ │──► create pending request
                  │ │ approval-status  │ │──► explain process
                  │ │ security         │ │──► refuse with reason
                  │ └──────────────────┘ │
                  └──────────┬───────────┘
                             │
                  ┌──────────▼───────────┐
                  │  pending             │ ←── notify approvers
                  └──────────┬───────────┘
                  ┌──────────┼───────────┐
       cancel ◄───┤          ▼           ├───► reject ─► notify requester
                  │     approve          │
                  └──────────┬───────────┘
                             ▼
                  ┌──────────────────────┐
                  │  completed (auto-    │ ─► notify requester
                  │  execute downstream) │
                  └──────────────────────┘
```

Every transition writes to `audit_logs` with `event_type`, `entity_id`, `payload`,
and the actor's user ID. The `/requests/{id}` endpoint reconstructs the full
timeline from those rows.

---

## Tech stack

**Backend**
- FastAPI 0.115 · Pydantic v2 · SQLAlchemy 2 (async) · Alembic
- PostgreSQL 15 · Redis 7
- Chroma (vector DB) · BM25 · sentence-transformers cross-encoder
- OpenAI GPT-4o / 4o-mini · LangChain · LangGraph
- structlog · Prometheus-ready metrics · CORS + security headers

**Frontend**
- React 19 · TypeScript · Vite + Rolldown
- TailwindCSS v4 · lucide-react · react-hot-toast · react-router

**Infrastructure**
- Railway (backend) · Vercel (frontend) · Docker / docker-compose for local
- GitHub Actions CI · pytest test matrix · auto-skip when local services missing

---

## Repo layout

```
app/
  agents/          HR / IT / Finance / Planner — intent + answer synthesis
  api/
    routes/        Thin route handlers, one file per resource
      ai.py            chat, streaming, file extraction
      actions.py       approve / reject / pending listings
      requests.py      lifecycle: detail, comments, cancel, timeline
      approvals.py     (lives in actions.py — alias namespace for managers)
      notifications.py inbox + read state
      admin.py         users, audit log, KB upload, stats
      conversations.py server-side chat history
      auth.py          login / logout / refresh
      health.py        liveness + deep health
  auth/            JWT, password hashing, role dependencies
  core/            config, logger, rate limiter, semantic cache, constants
  db/
    models/        SQLAlchemy 2 typed models
    repositories/  single source of truth for queries; never inline in routes
  llm/             OpenAI provider abstraction
  memory/          Redis conversation memory
  rag/             Chroma client, hybrid retriever, CRAG, document loader
  utils/           guardrails, multi-intent, fuzzy matching, confidence
  workflows/       LangGraph workflow assembly
  schemas/         Pydantic request/response models

frontend/src/
  pages/           ChatPage · RequestsPage · ApprovalsPage · AdminPage · …
  components/
    chat/          MessageBubble, Sidebar, ChatInput, AgentTrace
    requests/      StatusBadge, RequestDetail
    shared/        WorkspaceLayout, NotificationBell, Spinner, ErrorBoundary
    admin/         ApprovalQueue, StatsCards, CostPanel, DocumentUpload
  context/         AuthContext, RTLContext
  api/             client.ts, types.ts — single typed surface

tests/             unit + DB-integration with graceful-skip when local Postgres absent
alembic/versions/  every schema change reviewed and reversible
```

---

## API surface

All endpoints are JSON, JWT-authenticated, and tenant-scoped.

### Chat & RAG
| Method | Path | Purpose |
|---|---|---|
| POST | `/ask` | One-shot answer (non-streaming) |
| POST | `/ask/stream` | SSE — token stream, status events |
| POST | `/ask/extract` | Extract text from PDF/DOCX/CSV for the next message |

### Request lifecycle
| Method | Path | Purpose |
|---|---|---|
| GET  | `/requests/mine` | Paginated list of my requests (filterable by status) |
| GET  | `/requests/{id}` | Full detail: payload + comments + timeline |
| POST | `/requests/{id}/comments` | Add a comment (requester or approver) |
| POST | `/requests/{id}/cancel` | Cancel my own pending request |

### Approvals (manager + admin)
| Method | Path | Purpose |
|---|---|---|
| GET  | `/approvals/pending` | Tenant-wide queue, filterable by department |
| GET  | `/approvals/stats` | `{pending: N}` for nav badge |
| POST | `/actions/{id}/approve` | Approve, optional note, auto-executes downstream |
| POST | `/actions/{id}/reject` | Reject with note |

### Notifications (self)
| Method | Path | Purpose |
|---|---|---|
| GET  | `/notifications` | Inbox list, paginated |
| GET  | `/notifications/unread/count` | Badge number |
| POST | `/notifications/{id}/read` | Mark single read |
| POST | `/notifications/read-all` | Bulk mark read |

### Admin & analytics
| Method | Path | Purpose |
|---|---|---|
| GET  | `/admin/stats` | Query volume, confidence, agent distribution |
| GET  | `/admin/users` | Paginated user list |
| PATCH | `/admin/users/{id}` | Change role/department/is_active |
| GET  | `/admin/audit` | Append-only audit log |
| POST | `/admin/documents` | PDF upload into the KB |

Full Swagger UI: `<your-backend-url>/docs`.

---

## Security model

- **JWT with JTI blocklist** — logout/password-change immediately invalidates the token, not at expiry.
- **Tenant isolation** — every query joins on `company_id`; cross-tenant access is impossible by design.
- **Role gating** — three roles (employee / manager / admin); each route has the minimum required dep injected.
- **Guardrails** — word-boundary phrase matcher (no more `'ty'` matching `'maternity'`), prompt-injection blocklist, PII regex (Emirates ID / IBAN / credit card / passport), profanity, gibberish filter with single-token check.
- **Append-only audit** — `audit_logs` is never updated or deleted. Every approval, login, document upload, and user change is recorded.
- **CORS lockdown in prod** — explicit allow-list from `ALLOWED_ORIGINS`; dev defaults to localhost only.
- **No secrets in logs** — structured logger redacts JWT tokens, password fields, and authorisation headers.

---

## Run it locally

```bash
git clone https://github.com/SyedHussain23/enterprise-ai-workforce
cd enterprise-ai-workforce

# Backend
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in OPENAI_API_KEY, SECRET_KEY, DATABASE_URL, REDIS_URL
alembic upgrade head
uvicorn app.api.server:app --reload

# Frontend (in a second shell)
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

Run the test suite:

```bash
pytest tests/ --ignore=tests/load -q
```

Tests gracefully skip DB-backed cases when Postgres isn't reachable; pure-logic
tests always run.

---

## Deploy

### Backend → Railway
1. Push to GitHub.
2. New Railway project → connect repo. The `railway.toml` and `Procfile` are already in place.
3. Add the Postgres + Redis plugins.
4. Set env vars: `OPENAI_API_KEY`, `SECRET_KEY`, `ALLOWED_ORIGINS=https://your-vercel-domain`.
5. Railway runs `alembic upgrade head` on every deploy via the start command.

### Frontend → Vercel
1. New Vercel project → `frontend/` as the root.
2. Set `VITE_API_BASE` to your Railway URL.
3. Deploy.

Helper scripts: [`deploy_railway.sh`](./deploy_railway.sh), [`deploy_vercel.sh`](./deploy_vercel.sh).

---

## Design principles

1. **One canonical implementation per concept.** Department keywords live in one constants file. State transitions live in one repo method. Phrase matching uses one helper. No duplicate logic across modules.
2. **Repository pattern, not ORM-in-routes.** Every query lives in `app/db/repositories/`. Route handlers stay thin.
3. **Action vs information is a first-class distinction.** Only specific intent patterns create a pending `Action`; informational queries never do. This prevents the platform from creating false workflows.
4. **Humans approve workflows, not the AI.** The AI clearly explains that only managers/admins can approve, and the API enforces it with `require_approver`. No hallucinated approvals.
5. **Audit everything.** Every state change writes an `audit_logs` row. The request timeline is reconstructed from that table — there is no separate "history" model to keep in sync.
6. **Fail closed.** Guardrails block on uncertainty (gibberish, profanity, prompt injection). Cross-account credential requests trigger a security alert, not a policy answer.
7. **Skip gracefully in tests.** Local development works without Postgres/Redis; CI runs the full suite when services are available.

---

## Roadmap

- [ ] SLA timer + automatic escalation when an approval is pending too long
- [ ] Email + Slack notification delivery (current shape is in-app only)
- [ ] Per-department approver routing (HR requests → HR manager, not any manager)
- [ ] Frontend wire-up of server-side conversation history (API exists)
- [ ] Native iOS/Android wrapper around the PWA
- [ ] Voice + multimodal input in the chat
- [ ] Dashboard analytics: approval throughput, avg time to decide, requester volume by department

---

## Contributing

PRs welcome. Please:
1. Read [`CONTRIBUTING.md`](./CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md).
2. Add tests for any new behaviour.
3. Run `pytest` and `cd frontend && npm run build` before pushing.
4. Migrations live in `alembic/versions/`; never edit a shipped migration — write a new one.

---

## License

MIT. See [`LICENSE`](./LICENSE).

---

<div align="center">
<sub>Built in the UAE · designed for HR / IT / Finance teams who want to stop forwarding emails.</sub>
</div>
