"""
Generate a comprehensive PDF document covering the entire
Enterprise AI Workforce project — architecture, tech stack,
agents, features, day-by-day timeline, and everything in between.

Run: python3 generate_project_pdf.py
Output: Enterprise_AI_Workforce_Complete_Reference.pdf
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.colors import HexColor
from datetime import datetime

OUTPUT = "Enterprise_AI_Workforce_Complete_Reference.pdf"

# ─── Colour palette ──────────────────────────────────────────────────────────
NAVY      = HexColor("#0F172A")
INDIGO    = HexColor("#4F46E5")
INDIGO_LT = HexColor("#818CF8")
SLATE     = HexColor("#334155")
SLATE_LT  = HexColor("#64748B")
SLATE_XLT = HexColor("#CBD5E1")
EMERALD   = HexColor("#059669")
AMBER     = HexColor("#D97706")
RED       = HexColor("#DC2626")
WHITE     = colors.white
BG_LIGHT  = HexColor("#F8FAFC")
BG_CODE   = HexColor("#1E293B")
ROW_ALT   = HexColor("#F1F5F9")

# ─── Document setup ──────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=A4,
    rightMargin=2*cm,
    leftMargin=2*cm,
    topMargin=2.2*cm,
    bottomMargin=2.2*cm,
    title="Enterprise AI Workforce — Complete Reference",
    author="Enterprise AI Workforce",
)

W, H = A4
CONTENT_WIDTH = W - 4*cm

# ─── Styles ──────────────────────────────────────────────────────────────────
base_styles = getSampleStyleSheet()

def style(name, **kw):
    s = ParagraphStyle(name, **kw)
    return s

Cover_Title = style("CoverTitle",
    fontName="Helvetica-Bold", fontSize=32, textColor=WHITE,
    leading=40, alignment=TA_CENTER, spaceAfter=12)

Cover_Sub = style("CoverSub",
    fontName="Helvetica", fontSize=14, textColor=HexColor("#CBD5E1"),
    leading=20, alignment=TA_CENTER, spaceAfter=6)

Cover_Tag = style("CoverTag",
    fontName="Helvetica-BoldOblique", fontSize=11, textColor=INDIGO_LT,
    leading=16, alignment=TA_CENTER)

H1 = style("H1",
    fontName="Helvetica-Bold", fontSize=20, textColor=NAVY,
    leading=26, spaceBefore=22, spaceAfter=10,
    borderPad=0)

H2 = style("H2",
    fontName="Helvetica-Bold", fontSize=14, textColor=INDIGO,
    leading=20, spaceBefore=14, spaceAfter=6)

H3 = style("H3",
    fontName="Helvetica-Bold", fontSize=11, textColor=SLATE,
    leading=16, spaceBefore=10, spaceAfter=4)

Body = style("Body",
    fontName="Helvetica", fontSize=10, textColor=SLATE,
    leading=16, spaceBefore=4, spaceAfter=4, alignment=TA_JUSTIFY)

Bullet = style("Bullet",
    fontName="Helvetica", fontSize=10, textColor=SLATE,
    leading=15, leftIndent=16, firstLineIndent=-10, spaceBefore=2)

Code = style("Code",
    fontName="Courier", fontSize=8.5, textColor=HexColor("#E2E8F0"),
    backColor=BG_CODE, leading=13, leftIndent=10, rightIndent=10,
    spaceBefore=6, spaceAfter=6)

Caption = style("Caption",
    fontName="Helvetica-Oblique", fontSize=8.5, textColor=SLATE_LT,
    leading=12, alignment=TA_CENTER, spaceAfter=8)

Phase_Label = style("PhaseLabel",
    fontName="Helvetica-Bold", fontSize=10, textColor=WHITE,
    leading=14, alignment=TA_CENTER)

TOC_H1 = style("TOCH1",
    fontName="Helvetica-Bold", fontSize=11, textColor=NAVY,
    leading=16, spaceBefore=6)

TOC_H2 = style("TOCH2",
    fontName="Helvetica", fontSize=10, textColor=SLATE,
    leading=14, leftIndent=16, spaceBefore=2)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def hr(color=SLATE_XLT, thickness=0.5):
    return HRFlowable(width="100%", thickness=thickness, color=color,
                      spaceAfter=6, spaceBefore=6)

def sp(h=6):
    return Spacer(1, h)

def p(text, s=Body):
    return Paragraph(text, s)

def h1(text):
    return Paragraph(text, H1)

def h2(text):
    return Paragraph(text, H2)

def h3(text):
    return Paragraph(text, H3)

def bullet(text):
    return Paragraph(f"• {text}", Bullet)

def bullets(items):
    return [bullet(i) for i in items]

def code_block(text):
    # Split into lines, wrap in Courier paragraphs
    lines = text.strip().split("\n")
    paras = []
    for line in lines:
        paras.append(Paragraph(line.replace(" ", "&nbsp;").replace("<","&lt;").replace(">","&gt;"), Code))
    return paras


def make_table(headers, rows, col_widths=None, header_color=NAVY, alt=True):
    data = [headers] + rows
    if col_widths is None:
        col_widths = [CONTENT_WIDTH / len(headers)] * len(headers)

    h_style = ParagraphStyle("TH", fontName="Helvetica-Bold", fontSize=9,
                              textColor=WHITE, leading=13)
    c_style = ParagraphStyle("TD", fontName="Helvetica", fontSize=9,
                              textColor=SLATE, leading=13)

    formatted = []
    for ri, row in enumerate(data):
        frow = []
        for cell in row:
            s = h_style if ri == 0 else c_style
            frow.append(Paragraph(str(cell), s))
        formatted.append(frow)

    style_cmds = [
        ("BACKGROUND", (0,0), (-1,0), header_color),
        ("TEXTCOLOR",  (0,0), (-1,0), WHITE),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("ROWBACKGROUND", (0,1), (-1,-1), [WHITE, ROW_ALT]),
        ("GRID",       (0,0), (-1,-1), 0.3, SLATE_XLT),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING",(0,0), (-1,-1), 8),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
    ]
    if alt:
        for i in range(1, len(data), 2):
            style_cmds.append(("BACKGROUND", (0,i), (-1,i), ROW_ALT))
        for i in range(2, len(data), 2):
            style_cmds.append(("BACKGROUND", (0,i), (-1,i), WHITE))

    t = Table(formatted, colWidths=col_widths)
    t.setStyle(TableStyle(style_cmds))
    return t


class ColorBand(Flowable):
    """A full-width colored band with white text — used for phase headers."""
    def __init__(self, text, bg=INDIGO, height=26):
        Flowable.__init__(self)
        self.text = text
        self.bg = bg
        self.height = height
        self.width = CONTENT_WIDTH

    def draw(self):
        self.canv.setFillColor(self.bg)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        self.canv.setFillColor(WHITE)
        self.canv.setFont("Helvetica-Bold", 10)
        self.canv.drawCentredString(self.width / 2, self.height / 2 - 4, self.text)


class CoverPage(Flowable):
    """Full-page cover with gradient background."""
    def __init__(self):
        Flowable.__init__(self)
        self.width = CONTENT_WIDTH
        self.height = 0   # zero-height so it doesn't consume space; drawing is absolute

    def draw(self):
        c = self.canv
        # Background — covers full page
        c.setFillColor(NAVY)
        c.rect(-2*cm, -2.2*cm, W, H + 1*cm, fill=1, stroke=0)
        # Top accent bar
        c.setFillColor(INDIGO)
        c.rect(-2*cm, H - 4.8*cm, W, 0.55*cm, fill=1, stroke=0)
        # Bottom accent bar
        c.setFillColor(INDIGO)
        c.rect(-2*cm, -2.2*cm, W, 0.4*cm, fill=1, stroke=0)


# ─── Content builder ─────────────────────────────────────────────────────────

story = []

# ══════════════════════════════════════════════════════════════════════════════
# COVER
# ══════════════════════════════════════════════════════════════════════════════

story.append(CoverPage())
story.append(sp(80))
story.append(p("ENTERPRISE AI WORKFORCE", Cover_Title))
story.append(sp(8))
story.append(p("Complete Project Reference", Cover_Sub))
story.append(sp(4))
story.append(p("Architecture · Agents · Tech Stack · Day-by-Day Build", Cover_Sub))
story.append(sp(16))
story.append(hr(INDIGO_LT, thickness=1))
story.append(sp(16))
story.append(p("Production-grade multi-agent AI platform built for enterprise HR, IT, and Finance automation.", Cover_Sub))
story.append(sp(8))
story.append(p("LangGraph · GPT-4o-mini · ChromaDB · BM25 · RRF · CRAG · FastAPI · React · PostgreSQL · Redis", Cover_Tag))
story.append(sp(60))

date_style = style("DateS", fontName="Helvetica", fontSize=10,
                   textColor=HexColor("#94A3B8"), leading=14, alignment=TA_CENTER)
story.append(p(f"Generated {datetime.now().strftime('%B %Y')} | 63-Day Build | Full Production Deployment", date_style))

story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# TABLE OF CONTENTS
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("Table of Contents"))
story.append(hr())

toc = [
    ("1", "Problem Statement", []),
    ("2", "Executive Summary", []),
    ("3", "Engineering Priorities", []),
    ("4", "Architectural Separation", []),
    ("5", "System Architecture", []),
    ("6", "Tech Stack — Full Reference", []),
    ("7", "Workflow Execution Engine", ["7.1 Action Lifecycle", "7.2 What Actions Enable"]),
    ("8", "Core Features", ["8.1 Multi-Agent Routing", "8.2 Hybrid RAG (CRAG + RRF)", "8.3 Conversation Memory",
                             "8.4 Real-Time SSE Streaming", "8.5 Admin Dashboard", "8.6 Profile & KB Management",
                             "8.7 PDF Generation", "8.8 Internationalization (Arabic/RTL)"]),
    ("9", "Security & Reliability", ["9.1 Authentication", "9.2 Input Validation", "9.3 Secrets Management",
                                      "9.4 Rate Limiting"]),
    ("10", "Failure Handling & Resilience", []),
    ("11", "Retrieval Architecture — CRAG + RRF", []),
    ("12", "Observability", []),
    ("13", "AI Evaluation System", []),
    ("14", "Data Residency & Privacy", []),
    ("15", "Business Outcomes", []),
    ("16", "Deployment Guide", ["16.1 Local Development", "16.2 Docker Full Stack",
                                 "16.3 Railway + Vercel Production"]),
    ("17", "Scalability Roadmap", []),
    ("18", "Full Day-by-Day Timeline — Days 1–63", [
        "Phase 1: Foundation (Days 1–12)",
        "Phase 2: AI Core (Days 13–19)",
        "Phase 3: RAG System (Days 20–27)",
        "Phase 4: LangGraph Orchestration (Days 28–30)",
        "Phase 5: Production Backend (Days 31–43)",
        "Phase 6: Frontend (Days 44–58)",
        "Phase 7: Deploy & Audit (Days 59–63)",
    ]),
    ("19", "Project Metrics", []),
    ("20", "Future Roadmap", []),
]

for num, title, subs in toc:
    story.append(p(f"<b>{num}. {title}</b>", TOC_H1))
    for sub in subs:
        story.append(p(f"    — {sub}", TOC_H2))

story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 1. PROBLEM STATEMENT
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("1. Problem Statement"))
story.append(hr())
story.append(p(
    "Enterprise SMEs across the UAE and GCC operate with fragmented internal knowledge. "
    "Policy documents live in email chains. IT support answers the same questions daily. "
    "HR approval workflows run through informal messaging channels. Finance queries go "
    "unresolved for days. The cost is not visible on a balance sheet — but it compounds "
    "across every department, every week."
))
story.append(sp(8))
story.append(h2("Core Problems Addressed"))
story.extend(bullets([
    "Fragmented knowledge — policy documents scattered across drives, inboxes, and tribal memory",
    "Repetitive support burden — HR, IT, and Finance teams answering identical questions daily",
    "Inconsistent policy communication — different employees receive different answers",
    "Slow approval workflows — multi-step actions have no structured execution path or audit trail",
    "High enterprise AI costs — SaaS AI tools charge per seat with no data ownership",
    "Data residency concerns — regulated industries cannot send internal documents to external APIs",
    "Language barriers — enterprise AI tools rarely support Arabic natively",
]))
story.append(sp(8))
story.append(h2("The Platform Response"))
story.append(p(
    "Enterprise AI Workforce addresses these as an integrated system — not as a chatbot, "
    "but as an enterprise operational layer: centralised retrieval, agentic workflow automation, "
    "self-hosted deployment, role-aware action systems, and multilingual enterprise support."
))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 2. EXECUTIVE SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("2. Executive Summary"))
story.append(hr())
story.append(p(
    "Enterprise AI Workforce is a modular, extensible enterprise AI platform with production "
    "deployment architecture. The platform is designed around the transition from AI assistants "
    "to AI agents capable of executing enterprise workflows."
))
story.append(sp(6))
story.append(p(
    "It combines LangGraph multi-agent orchestration, hybrid Retrieval-Augmented Generation, "
    "role-based access control, a structured workflow execution engine with approval gating, "
    "real-time token streaming, Redis-backed conversation memory, PostgreSQL auditability, and a "
    "React frontend with Arabic/RTL support — all deployable on-premises or in the cloud inside "
    "the customer's own infrastructure."
))
story.append(sp(6))
story.append(p(
    "The system does not merely answer questions. It routes intent, retrieves grounded context, "
    "gates action execution through approval workflows, logs every decision, and makes every "
    "step inspectable. That is the difference between an AI assistant and an enterprise "
    "operating system."
))
story.append(sp(12))

summary_table = make_table(
    ["Dimension", "Value"],
    [
        ["Build timeline", "63 days"],
        ["LLM", "OpenAI GPT-4o-mini"],
        ["Orchestration", "LangGraph StateGraph"],
        ["Retrieval", "ChromaDB (dense) + BM25 (sparse) + RRF fusion"],
        ["Backend", "FastAPI + PostgreSQL + Redis"],
        ["Frontend", "React 18 + TypeScript + Tailwind CSS"],
        ["Languages", "English + Arabic (RTL)"],
        ["Deployment", "Docker / Railway / Vercel / self-hosted"],
        ["Knowledge documents", "100"],
        ["Specialist agents", "4 (Planner, HR, IT, Finance)"],
        ["API endpoints", "25+"],
    ],
    col_widths=[CONTENT_WIDTH*0.38, CONTENT_WIDTH*0.62],
)
story.append(summary_table)
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 3. ENGINEERING PRIORITIES
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("3. Engineering Priorities"))
story.append(hr())
story.append(p(
    "Every architectural decision in this platform traces back to this priority hierarchy. "
    "These are not preferences — they are constraints that shaped every technical choice."
))
story.append(sp(8))

story.append(make_table(
    ["Priority", "Principle", "How It Manifests in the System"],
    [
        ["1", "Reliability", "Graceful degradation for every dependency failure; no single point of collapse"],
        ["2", "Security", "JWT + bcrypt + path validation + secret guard + role enforcement at every layer"],
        ["3", "Observability", "LangSmith tracing + structured logs + evaluation scoring + health endpoint"],
        ["4", "Explainability", "Every response carries: agent, confidence, source, execution steps, eval score"],
        ["5", "Retrieval quality", "CRAG grading + RRF fusion + automatic query rewrite before any answer generated"],
        ["6", "Workflow safety", "PENDING → APPROVED → EXECUTING → COMPLETED; no action runs without human gate"],
        ["7", "User experience", "SSE streaming, RTL/Arabic, skeleton loaders, empty states, error boundaries"],
        ["8", "Cost efficiency", "GPT-4o-mini, BM25 sparse retrieval reduces embedding calls, Redis caching"],
    ],
    col_widths=[CONTENT_WIDTH*0.08, CONTENT_WIDTH*0.20, CONTENT_WIDTH*0.72],
))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 4. ARCHITECTURAL SEPARATION
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("4. Architectural Separation"))
story.append(hr())
story.append(p(
    "Each layer has a single defined responsibility. No layer reaches across two boundaries. "
    "This separation makes each component independently testable, replaceable, and scalable."
))
story.append(sp(8))

story.append(make_table(
    ["Layer", "Responsibility", "Components"],
    [
        ["Presentation", "User interaction and rendering",
         "React 18, Vite, Tailwind, RTLContext"],
        ["API", "Authentication, validation, transport",
         "FastAPI, JWT middleware, Pydantic schemas, SSE"],
        ["Orchestration", "Workflow routing and execution",
         "LangGraph StateGraph, conditional edges, guardrail"],
        ["Agent", "Domain-specific reasoning",
         "HR Agent, IT Agent, Finance Agent, Planner"],
        ["Retrieval", "Context acquisition and grading",
         "ChromaDB, BM25, RRF, CRAG grader, query rewriter"],
        ["Workflow Engine", "Action lifecycle management",
         "Action model, approval gate, execution tracker, audit log"],
        ["Persistence", "Long-term state and auditability",
         "PostgreSQL 16, Alembic migrations, conversation logs"],
        ["Memory", "Short-term conversational continuity",
         "Redis 7, per-session TTL, UUID4 session scoping"],
    ],
    col_widths=[CONTENT_WIDTH*0.20, CONTENT_WIDTH*0.30, CONTENT_WIDTH*0.50],
))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 5. SYSTEM ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("5. System Architecture"))
story.append(hr())
story.append(h2("5.1 High-Level Pipeline"))
story.append(p(
    "Every user query passes through a deterministic, inspectable pipeline. "
    "Each node has a single job. Failures at any node are caught and degraded gracefully."
))
story.append(sp(8))

arch_rows = [
    ["Step", "Node / Component", "Input", "Output"],
    ["1", "React Frontend", "User types question", "POST /ask with JWT token"],
    ["2", "FastAPI API Layer", "Authenticated HTTP request", "Routed to LangGraph pipeline"],
    ["3", "Planner Agent", "Raw question text", "Intent label (hr/it/finance/unknown)"],
    ["4", "Guardrail", "Intent + question", "Pass or BLOCK with reason"],
    ["5", "Router", "Intent label", "Agent selection + conditional edge"],
    ["6", "CRAG Retrieval", "Question", "Graded context chunks (relevant/ambiguous)"],
    ["7", "Specialist Agent", "Question + context chunks", "Draft answer"],
    ["8", "Report Node", "Draft answer + metadata", "Final JSON with confidence + eval score"],
    ["9", "SSE Stream", "Final response", "Token-by-token stream to React UI"],
    ["10", "PostgreSQL", "Complete response", "Logged to conversation_logs table"],
]
arch_table = make_table(arch_rows[0], arch_rows[1:],
    col_widths=[CONTENT_WIDTH*0.07, CONTENT_WIDTH*0.22, CONTENT_WIDTH*0.33, CONTENT_WIDTH*0.38])
story.append(arch_table)

story.append(sp(14))
story.append(h2("5.2 Database Schema"))
story.append(make_table(
    ["Table", "Purpose", "Key Columns"],
    [
        ["users", "Authentication + roles", "id, username, email, hashed_password, role, company_id"],
        ["sessions", "Chat sessions", "id, user_id, title, created_at"],
        ["conversation_logs", "Full audit of every response", "session_id, agent, question, answer, confidence, evaluation_score, response_time, source"],
        ["actions", "Workflow engine", "id, session_id, type, payload, status (PENDING/APPROVED/EXECUTING/COMPLETED/REJECTED/FAILED), created_at, executed_at"],
        ["companies", "Multi-tenant scoping", "id, name, domain, created_at"],
        ["kb_documents", "Knowledge base index", "id, category, filename, uploaded_at, company_id"],
        ["profiles", "User profile data", "user_id, department, updated_at"],
        ["alembic_version", "Schema version tracking", "version_num"],
    ],
    col_widths=[CONTENT_WIDTH*0.22, CONTENT_WIDTH*0.25, CONTENT_WIDTH*0.53],
))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 6. TECH STACK
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("6. Tech Stack — Full Reference"))
story.append(hr())

story.append(make_table(
    ["Layer", "Technology", "Version / Config", "Rationale"],
    [
        ["LLM", "OpenAI GPT-4o-mini", "gpt-4o-mini", "Cost-efficient, low latency, capable for RAG"],
        ["Orchestration", "LangGraph", "StateGraph", "Explicit graph; conditional edges; inspectable pipeline"],
        ["Dense Retrieval", "ChromaDB", "Persistent collection", "Self-hosted, no external service dependency"],
        ["Sparse Retrieval", "BM25", "rank-bm25", "Zero embedding cost; language-agnostic; resilience fallback"],
        ["Fusion", "RRF", "Custom implementation", "No calibration required; merges retrieval modes cleanly"],
        ["RAG Grading", "CRAG", "LLM-based grader", "Prevents hallucination from poor retrieved context"],
        ["Chunking", "RecursiveCharacterTextSplitter", "800 tokens, 120 overlap", "Consistent across all ingestion paths"],
        ["Backend", "FastAPI", "Async + Pydantic", "High throughput; type-safe schemas; OpenAPI docs"],
        ["ORM", "SQLAlchemy", "Async (asyncpg)", "Non-blocking DB queries; transaction safety"],
        ["Migrations", "Alembic", "Head tracking", "Schema versioning with rollback support"],
        ["Database", "PostgreSQL", "v16 Alpine", "ACID compliance; relational integrity; audit trail"],
        ["Cache / Memory", "Redis", "v7 Alpine, AOF", "Sub-ms session reads; TTL-based cleanup; rate limiting"],
        ["Auth", "JWT HS256 + bcrypt", "Cost factor 12", "Industry standard; stateless; role-aware"],
        ["Rate Limiting", "Redis sliding window", "Per-user thresholds", "Production-grade protection without DB writes"],
        ["Frontend", "React 18 + Vite", "TypeScript strict", "Type-safe; component model; fast HMR builds"],
        ["Styling", "Tailwind CSS", "v3", "Utility-first; consistent design system; RTL compatible"],
        ["Streaming", "SSE", "Native EventSource", "No WebSocket overhead; native browser support"],
        ["HTTP Client", "Axios", "JWT interceptor", "Auto-attach token; 401 redirect on expiry"],
        ["Charts", "Recharts", "Cell-based coloring", "Composable; BarChart with per-bar Cell component"],
        ["Routing", "React Router v6", "Protected routes", "Role guards; nested layout routes"],
        ["PDF Generation", "ReportLab", "Word-wrap + pagination", "Server-side; paginated; no silent truncation"],
        ["Tracing", "LangSmith", "LANGCHAIN_TRACING_V2", "End-to-end pipeline observability per node"],
        ["Load Testing", "k6", "p(95)/p(99) thresholds", "Scriptable; CI-integrable; VU ramp profiles"],
        ["CI/CD", "GitHub Actions", "pytest + eslint + tsc", "Lint, type-check, test on every push"],
        ["Containerisation", "Docker + Compose", "Healthcheck-gated", "Portable; reproducible; secret guard (:?)"],
        ["Deployment — API", "Railway", "Env vars in dashboard", "Zero-ops cloud; auto-deploy from git"],
        ["Deployment — UI", "Vercel", "VITE_API_URL set", "CDN; preview deploys; zero config"],
    ],
    col_widths=[CONTENT_WIDTH*0.18, CONTENT_WIDTH*0.20, CONTENT_WIDTH*0.20, CONTENT_WIDTH*0.42],
))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 7. WORKFLOW EXECUTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("7. Workflow Execution Engine"))
story.append(hr())
story.append(p(
    "This is the feature that separates the platform from an AI chatbot. The platform supports "
    "structured enterprise workflows: action creation by AI agents, human approval gating, "
    "tracked execution, and post-action audit logging. No action touches any real system "
    "without passing through an authorised human."
))
story.append(sp(8))
story.append(h2("7.1 Action Lifecycle"))

story.append(make_table(
    ["State", "Triggered By", "Description"],
    [
        ["PENDING", "Specialist Agent", "Action created during conversation; stored in DB; awaits admin review in dashboard"],
        ["APPROVED", "Admin", "Admin reviews context and approves; execution queued immediately"],
        ["EXECUTING", "System", "Execution begins; locked against duplicate processing"],
        ["COMPLETED", "System", "Execution successful; outcome and timestamp logged"],
        ["REJECTED", "Admin", "Admin rejects with reason; logged for full audit trail"],
        ["FAILED", "System", "Execution error caught; reason stored; state set to FAILED; no silent discard"],
    ],
    col_widths=[CONTENT_WIDTH*0.18, CONTENT_WIDTH*0.20, CONTENT_WIDTH*0.62],
))

story.append(sp(10))
story.append(h2("7.2 What Actions Enable"))

story.append(make_table(
    ["Department", "Action Example", "Workflow"],
    [
        ["HR", "Leave approval request", "Agent creates PENDING action → Admin approves → HR system updated → COMPLETED"],
        ["IT", "Access provisioning ticket", "Agent creates PENDING action → Admin approves → Ticket created → COMPLETED"],
        ["Finance", "Expense claim submission", "Agent creates PENDING action → Finance admin approves → Claim processed → COMPLETED"],
        ["Admin", "User role change", "Admin triggers directly → EXECUTING → COMPLETED with audit entry"],
    ],
    col_widths=[CONTENT_WIDTH*0.15, CONTENT_WIDTH*0.30, CONTENT_WIDTH*0.55],
))

story.append(sp(8))
story.append(p(
    "Every state transition is timestamped and stored. No action is ever in an unknown state. "
    "The complete lifecycle is queryable from the Admin dashboard or via the /actions API endpoint."
))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 8. CORE FEATURES
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("8. Core Features"))
story.append(hr())

story.append(h2("8.1 Multi-Agent Routing"))
story.append(make_table(
    ["Agent", "Role", "Capabilities"],
    [
        ["Planner", "Intent classification", "Keyword trie (fast path) → LLM fallback (edge cases); returns intent label"],
        ["Guardrail", "Safety gate", "Blocks: out-of-scope, multi-intent ambiguity, harmful content, prompt injection"],
        ["HR Agent", "HR domain reasoning", "Leave policy (UAE law), onboarding, employee handbook, EOSB gratuity"],
        ["IT Agent", "IT domain reasoning", "Password reset, VPN access, device support, access provisioning"],
        ["Finance Agent", "Finance domain reasoning", "Salary review, expense reimbursement, budget queries, VAT/corporate tax"],
        ["Report Node", "Response assembly", "Confidence score, source attribution, evaluation score, execution steps"],
    ],
    col_widths=[CONTENT_WIDTH*0.18, CONTENT_WIDTH*0.22, CONTENT_WIDTH*0.60],
))

story.append(sp(10))
story.append(h2("8.2 Hybrid RAG — CRAG + RRF"))
story.extend(bullets([
    "100 knowledge base documents across 5 categories: HR, IT, Finance, General, Company",
    "Dual retrieval: ChromaDB cosine similarity (dense) + BM25 keyword (sparse)",
    "RRF (Reciprocal Rank Fusion) merges both ranked lists without requiring score calibration",
    "CRAG grader scores each chunk: relevant / ambiguous / irrelevant",
    "Only relevant and ambiguous chunks are passed to the specialist agent",
    "If all chunks score irrelevant: query is automatically rewritten and retrieval retried once",
    "Chunking: RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)",
    "BM25 index invalidated on every KB change: upload, delete, rebuild",
]))

story.append(sp(10))
story.append(h2("8.3 Conversation Memory"))
story.extend(bullets([
    "Per-session Redis storage with configurable TTL",
    "Session ID scoped per browser tab using UUID4 — no cross-session contamination",
    "Multi-turn context maintained across full conversation length",
    "Graceful degradation: if Redis is unavailable, conversation continues without memory context",
]))

story.append(sp(10))
story.append(h2("8.4 Real-Time SSE Streaming"))
story.extend(bullets([
    "Token-by-token streaming via /ask/stream endpoint",
    "Frontend renders MessageSkeleton component while first token is still in-flight",
    "No polling — persistent SSE connection per chat session",
    "Native EventSource API; no WebSocket infrastructure required",
]))

story.append(sp(10))
story.append(h2("8.5 Admin Dashboard"))
story.extend(bullets([
    "Document upload with KB management (safe path validation, extension enforcement)",
    "User management: create users, assign roles (user / admin)",
    "Pending action approval queue with full context visible",
    "Department analytics chart (Recharts BarChart with Cell-based per-bar coloring)",
    "System health indicators (DB, Redis, vector store)",
]))

story.append(sp(10))
story.append(h2("8.6 Profile & KB Management"))
story.extend(bullets([
    "Profile page: update email and department, change password with current-password verification",
    "Gradient avatar banner with role badge (user / admin)",
    "KB manager: upload .txt files by category, delete files, trigger full rebuild",
    "All KB endpoints protected by path traversal guard (_safe_path using .resolve())",
]))

story.append(sp(10))
story.append(h2("8.7 PDF Generation"))
story.extend(bullets([
    "ReportLab-based server-side PDF export",
    "Word-wrap loop using stringWidth() — no content truncation on long lines",
    "showPage() called when y position drops below margin — full multi-page support",
    "Consistent font, margins, and line height across all generated documents",
]))

story.append(sp(10))
story.append(h2("8.8 Internationalisation — Arabic / RTL"))
story.extend(bullets([
    "RTLContext.tsx toggles dir='rtl' on the document root",
    "All UI labels available in both English and Arabic",
    "Sidebar, chat messages, buttons, and navigation switch simultaneously",
    "Language preference persists across sessions via React context",
]))

story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 9. SECURITY & RELIABILITY
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("9. Security & Reliability"))
story.append(hr())

story.append(h2("9.1 Authentication & Authorisation"))
story.extend(bullets([
    "JWT tokens signed with HS256; expiry enforced on every protected route by FastAPI dependency",
    "bcrypt password hashing at cost factor 12 — industry standard; timing-safe comparison",
    "Role-based access control: user vs admin enforced at the route level, not just the UI",
    "SECRET_KEY uses Docker Compose :? syntax — container refuses to start if unset; no insecure default",
    "Refresh token groundwork in place; short-lived access tokens with re-authentication path",
]))

story.append(sp(8))
story.append(h2("9.2 Input Validation & Path Safety"))
story.extend(bullets([
    "All KB uploads: .txt extension required, filename non-null validated before path resolution",
    "_safe_path() uses .resolve() + startswith() to block path traversal (../../) at OS level",
    "Filename null check executed before _safe_path() call to prevent TypeError crash",
    "Pydantic schemas validate all request bodies; malformed payloads rejected before business logic",
    "Guardrail agent intercepts prompt injection, harmful content, and multi-intent ambiguity",
]))

story.append(sp(8))
story.append(h2("9.3 Secrets Management"))
story.extend(bullets([
    ".env is git-ignored; .env.example contains only placeholder values — committed safely",
    "No credentials hardcoded anywhere in codebase (verified across all 67 Python files)",
    "Seed credentials (employee1/emp123) match README, load tests, and LoginPage demo hints",
    "All Docker image versions pinned (postgres:16-alpine, redis:7-alpine, node:22-alpine)",
    "Alembic handles all schema changes — no manual SQL patches with embedded secrets",
]))

story.append(sp(8))
story.append(h2("9.4 Rate Limiting"))
story.extend(bullets([
    "Redis-backed sliding window limiter applied to all /ask endpoints",
    "Per-user request thresholds configurable via RATE_LIMIT_RPM environment variable",
    "Admin accounts carry elevated limits; operator override capability reserved",
    "Returns 429 Too Many Requests with Retry-After header on threshold breach",
    "No DB writes required for rate limit checks — Redis atomic operations only",
]))

story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 10. FAILURE HANDLING & RESILIENCE
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("10. Failure Handling & Resilience"))
story.append(hr())
story.append(p(
    "Every external dependency has an explicit failure strategy. The system degrades gracefully "
    "— it never collapses completely. This is the primary engineering priority."
))
story.append(sp(8))

story.append(make_table(
    ["Failure Scenario", "Immediate Behaviour", "User Impact", "Recovery"],
    [
        ["LLM (OpenAI) unavailable",
         "Exponential backoff retry ×3 (1s/2s/4s delays)",
         "Receives graceful unavailability message; no stack trace exposed",
         "LangSmith trace captures failure node for post-incident review"],
        ["Redis unavailable",
         "Conversation memory disabled for affected session",
         "Core question-answering continues; no memory context this session",
         "Memory resumes automatically when Redis reconnects; health endpoint flags degraded"],
        ["ChromaDB unavailable",
         "Dense retrieval skipped; BM25 sparse retrieval continues independently",
         "Answer still grounded in KB documents via BM25; confidence metadata reflects reduced retrieval",
         "Health endpoint flags vector store as degraded; admin notified"],
        ["PostgreSQL unavailable",
         "Request rejected with 503 Service Unavailable; transaction rolled back",
         "User sees service error; no partial data written",
         "Filesystem logger receives audit fallback entry; no silent data loss"],
        ["Empty retrieval (all chunks irrelevant)",
         "CRAG triggers automatic query rewrite; retrieval retried once",
         "Transparent fallback message if second retrieval also fails",
         "User never receives silent empty response"],
        ["Invalid / duplicate action",
         "Pydantic schema rejects malformed payloads; idempotency check on duplicate submission",
         "Clear validation error returned",
         "Failed execution sets state to FAILED with reason logged; not discarded silently"],
        ["Unauthorised action execution",
         "Approval workflow blocks EXECUTING state without explicit admin APPROVED",
         "Action remains in PENDING until reviewed",
         "Admin dashboard surfaces all pending actions with full context"],
    ],
    col_widths=[CONTENT_WIDTH*0.22, CONTENT_WIDTH*0.25, CONTENT_WIDTH*0.27, CONTENT_WIDTH*0.26],
))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 11. RETRIEVAL ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("11. Retrieval Architecture — CRAG + RRF"))
story.append(hr())
story.append(p(
    "Retrieval quality is a first-order engineering concern, not an afterthought. "
    "The dual-retrieval architecture with LLM-based grading ensures answers are grounded "
    "in verified source documents before any generation occurs."
))
story.append(sp(8))

story.append(h2("11.1 Retrieval Pipeline Steps"))
story.append(make_table(
    ["Step", "Component", "Description"],
    [
        ["1", "Dense Retrieval", "ChromaDB cosine similarity search using text-embedding-ada-002; returns top-K candidates"],
        ["2", "Sparse Retrieval", "BM25 keyword frequency index; no embedding cost; fully independent from dense path"],
        ["3", "RRF Fusion", "Reciprocal Rank Fusion: score(d) = sum(1/(k+rank)); merges lists without calibration"],
        ["4", "CRAG Grader", "LLM assesses each fused chunk: relevant / ambiguous / irrelevant"],
        ["5", "Filter", "Only relevant and ambiguous chunks proceed to the specialist agent"],
        ["6", "Query Rewrite", "If all chunks score irrelevant: question is rephrased by LLM; retrieval retried once"],
        ["7", "Agent Reasoning", "Specialist agent receives graded context; generates grounded answer"],
    ],
    col_widths=[CONTENT_WIDTH*0.07, CONTENT_WIDTH*0.20, CONTENT_WIDTH*0.73],
))

story.append(sp(10))
story.append(h2("11.2 Knowledge Base Structure"))
story.append(make_table(
    ["Category", "Document Count", "Content Coverage"],
    [
        ["HR", "20+", "Leave policy (UAE Labour Law), onboarding, handbook, EOSB gratuity, payroll"],
        ["IT", "20+", "Password reset, VPN, device support, access provisioning, security policy"],
        ["Finance", "20+", "Salary review, expense reimbursement, budget process, VAT 5%, corporate tax 9%"],
        ["General", "20+", "Code of conduct, compliance, workplace safety, training policy"],
        ["Company", "20+", "Company overview, org structure, office locations, department contacts"],
    ],
    col_widths=[CONTENT_WIDTH*0.18, CONTENT_WIDTH*0.20, CONTENT_WIDTH*0.62],
))

story.append(sp(10))
story.append(h2("11.3 Chunking Configuration"))
story.append(make_table(
    ["Parameter", "Value", "Rationale"],
    [
        ["chunk_size", "800 tokens", "Captures full policy clauses without truncation"],
        ["chunk_overlap", "120 tokens", "Preserves context at chunk boundaries"],
        ["separators", '[\"\\n\\n\", \"\\n\", \". \", \" \", \"\"]', "Paragraph-first splitting; falls back to sentence, then word"],
        ["Applied to", "All ingestion paths", "Upload API, PDF ingestion endpoint, build_vector_db.py script — consistent everywhere"],
        ["BM25 cache", "Invalidated on every KB change", "Prevents stale sparse retrieval after document updates"],
    ],
    col_widths=[CONTENT_WIDTH*0.20, CONTENT_WIDTH*0.28, CONTENT_WIDTH*0.52],
))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 12. OBSERVABILITY
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("12. Observability"))
story.append(hr())

story.append(h2("12.1 LangSmith Tracing"))
story.extend(bullets([
    "Every LangGraph pipeline run traced end-to-end: planner → guardrail → router → crag → report",
    "Token counts, latency per node, intermediate outputs, and final response all captured",
    "Enabled via LANGCHAIN_TRACING_V2=true; scoped by LANGCHAIN_PROJECT",
    "Traces queryable in LangSmith dashboard for debugging and performance analysis",
    "Failure nodes captured with full context for post-incident review",
]))

story.append(sp(8))
story.append(h2("12.2 Response Metadata"))
story.append(p(
    "Every /ask response includes a full metadata payload, making the system's reasoning "
    "transparent and auditable on every single query:"
))
story.append(sp(4))
story.append(make_table(
    ["Field", "Type", "Description"],
    [
        ["answer", "string", "The generated response text"],
        ["agent", "string", "Which specialist agent handled the query (hr/it/finance/guardrail)"],
        ["confidence", "integer 0-100", "Dynamic confidence score computed in Report node"],
        ["confidence_reason", "string", "Natural language explanation of confidence level"],
        ["source", "string", "Source document filename attribution"],
        ["evaluation_score", "integer 0-100", "Post-generation answer quality score"],
        ["response_time", "float (seconds)", "End-to-end pipeline latency"],
        ["steps", "string[]", "Full execution trace: Planner → Router → Agent → Report"],
        ["status", "string", "success / error / multi_intent / guardrail"],
    ],
    col_widths=[CONTENT_WIDTH*0.22, CONTENT_WIDTH*0.20, CONTENT_WIDTH*0.58],
))

story.append(sp(8))
story.append(h2("12.3 Structured Logging"))
story.extend(bullets([
    "Per-request logs include: timestamp, session_id, agent, question, answer, confidence, evaluation_score, response_time",
    "Written to /app/logs/ with Docker volume persistence across container restarts",
    "BM25 cache invalidation logged on every KB change event",
    "Health endpoint aggregates DB, Redis, and vector store status in single response",
]))

story.append(sp(8))
story.append(h2("12.4 Confidence Levels"))
story.append(make_table(
    ["Level", "Score Range", "UI Display", "Meaning"],
    [
        ["High", "80 – 100", "Green success indicator", "Answer found directly in authoritative source document"],
        ["Medium", "60 – 79", "Blue info indicator", "Answer grounded in relevant context with minor uncertainty"],
        ["Low", "40 – 59", "Amber warning indicator", "Partial match; answer may be incomplete"],
        ["Very Low", "0 – 39", "Red error indicator", "Weak grounding; recommend consulting HR/IT/Finance directly"],
    ],
    col_widths=[CONTENT_WIDTH*0.12, CONTENT_WIDTH*0.18, CONTENT_WIDTH*0.25, CONTENT_WIDTH*0.45],
))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 13. AI EVALUATION SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("13. AI Evaluation System"))
story.append(hr())

story.append(h2("13.1 Dual Scoring Architecture"))
story.append(p(
    "The system runs two independent quality signals on every response. "
    "Confidence measures retrieval and grounding strength. "
    "Evaluation score measures post-generation answer quality. "
    "Both are stored per turn for longitudinal analysis."
))
story.append(sp(8))
story.append(make_table(
    ["Signal", "Computed By", "Factors", "Storage"],
    [
        ["Confidence (0-100)", "Report node (LangGraph)", "Source relevance, chunk grading results, retrieval depth", "conversation_logs.confidence"],
        ["Evaluation score (0-100)", "Evaluation module", "Completeness, grounding, confidence alignment", "conversation_logs.evaluation_score"],
    ],
    col_widths=[CONTENT_WIDTH*0.22, CONTENT_WIDTH*0.23, CONTENT_WIDTH*0.32, CONTENT_WIDTH*0.23],
))

story.append(sp(8))
story.append(h2("13.2 CRAG Grading Detail"))
story.extend(bullets([
    "Each retrieved chunk independently assessed by LLM before reaching the specialist agent",
    "Three-label system: relevant (passes) / ambiguous (passes with reduced weight) / irrelevant (blocked)",
    "LLM grader prompt is structured and deterministic — not freeform evaluation",
    "All-irrelevant result triggers one automatic query rewrite cycle before fallback",
    "Fallback response explicitly acknowledges knowledge limit — no hallucinated answer",
]))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 14. DATA RESIDENCY & PRIVACY
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("14. Data Residency & Privacy"))
story.append(hr())
story.append(p(
    "Data residency is a non-negotiable requirement for enterprise adoption in the UAE, "
    "Saudi Arabia, and the wider GCC. Every architecture decision has been made with "
    "this constraint in mind."
))
story.append(sp(8))

story.append(make_table(
    ["Requirement", "How the Platform Addresses It"],
    [
        ["Self-hosted deployment", "Full stack runs on Docker inside the customer's own infrastructure — no cloud vendor lock-in"],
        ["Document storage", "Knowledge base .txt files stored on-disk inside the container; never sent to third-party storage services"],
        ["Vector embeddings", "ChromaDB persists on a Docker volume inside the deployment; no embeddings leave the environment"],
        ["Conversation data", "All conversation logs written to customer's own PostgreSQL instance; not shared externally"],
        ["Redis memory", "Session state stored in customer's own Redis instance; TTL ensures automatic cleanup"],
        ["OpenAI API", "Only the question text and retrieved context chunks leave the environment; no KB documents sent in full"],
        ["Azure OpenAI compatible", "Base URL configurable to point to UAE North or other GCC-compliant Azure OpenAI regions"],
        ["GDPR / regulatory alignment", "Self-hosted model allows customers to meet regional data residency regulations independently"],
    ],
    col_widths=[CONTENT_WIDTH*0.30, CONTENT_WIDTH*0.70],
))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 15. BUSINESS OUTCOMES
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("15. Business Outcomes"))
story.append(hr())

story.append(make_table(
    ["Business Problem", "Platform Response", "Measurable Outcome"],
    [
        ["Repetitive HR support queries", "HR Agent answers policy questions instantly from authoritative KB", "HR team handles fewer inbound support tickets"],
        ["Inconsistent policy communication", "All answers sourced from single KB; same document every time", "Policy consistency across all employees"],
        ["Slow approval workflows", "Structured action lifecycle with mandatory gating", "Approvals tracked from creation to completion; none lost"],
        ["IT helpdesk overload", "IT Agent handles password, VPN, access queries autonomously", "Self-service resolution for most-common IT queries"],
        ["Untracked internal requests", "Every action logged: PENDING → APPROVED → COMPLETED", "Full audit trail; compliance-ready history"],
        ["Enterprise AI cost barriers", "Self-hosted; GPT-4o-mini; BM25 reduces embedding costs", "Significantly lower per-query cost than SaaS alternatives"],
        ["Language access barriers", "Native Arabic/RTL support; language toggle persists", "Arabic-speaking employees served without overhead"],
        ["Data sovereignty concerns", "Fully self-hosted; documents never leave infrastructure", "GCC data residency requirements compatible"],
        ["Fragmented knowledge", "100-document structured KB; hybrid retrieval", "Single source of truth; searchable in natural language"],
    ],
    col_widths=[CONTENT_WIDTH*0.28, CONTENT_WIDTH*0.38, CONTENT_WIDTH*0.34],
))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 16. DEPLOYMENT GUIDE
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("16. Deployment Guide"))
story.append(hr())

story.append(h2("16.1 Local Development"))
story.append(make_table(
    ["Step", "Command / Action"],
    [
        ["1. Copy env file", "cp .env.example .env"],
        ["2. Set required vars", "OPENAI_API_KEY=sk-... and SECRET_KEY=$(openssl rand -hex 32)"],
        ["3. Start infrastructure", "docker compose up postgres redis -d"],
        ["4. Run migrations", "alembic upgrade head"],
        ["5. Seed database", "python scripts/seed_db.py  (creates employee1/emp123 and admin/admin123)"],
        ["6. Build knowledge base", "python build_vector_db.py  (ingests all 100 .txt files into ChromaDB + BM25)"],
        ["7. Start API", "uvicorn app.api.server:app --reload --port 8000"],
        ["8. Start frontend", "cd frontend && npm install && npm run dev"],
        ["9. Access UI", "http://localhost:5173"],
        ["10. Access API docs", "http://localhost:8000/docs (Swagger UI auto-generated)"],
    ],
    col_widths=[CONTENT_WIDTH*0.28, CONTENT_WIDTH*0.72],
))

story.append(sp(10))
story.append(h2("16.2 Docker Full Stack"))
story.append(make_table(
    ["Command", "Purpose"],
    [
        ["docker compose up --build", "Build and start all services (postgres, redis, api)"],
        ["docker compose --profile migrate up migrate", "Run Alembic migrations as one-shot container"],
        ["docker compose --profile dev up frontend", "Start frontend in dev mode with hot reload"],
        ["docker compose logs -f api", "Stream API logs in real time"],
        ["docker compose down -v", "Stop all services and remove volumes (full reset)"],
    ],
    col_widths=[CONTENT_WIDTH*0.45, CONTENT_WIDTH*0.55],
))

story.append(sp(10))
story.append(h2("16.3 Railway + Vercel Production"))
story.extend(bullets([
    "API deployed to Railway: connect GitHub repo, set all env vars in Railway dashboard",
    "Frontend deployed to Vercel: set VITE_API_URL to Railway public domain",
    "GitHub Actions: runs pytest + eslint + tsc --noEmit on every push to any branch",
    "Deploy workflow triggers on merge to main: Railway auto-deploys; Vercel auto-deploys",
    "k6 load test suite: VU ramp to 50 virtual users; enforces p(95)<3s and p(99)<6s thresholds",
]))

story.append(sp(8))
story.append(h2("16.4 Environment Variables Reference"))
story.append(make_table(
    ["Variable", "Required", "Description"],
    [
        ["OPENAI_API_KEY", "Yes", "OpenAI API key for LLM and embedding calls"],
        ["SECRET_KEY", "Yes", "JWT signing secret; generate: openssl rand -hex 32"],
        ["DATABASE_URL", "Yes", "Async PostgreSQL URL (postgresql+asyncpg://...)"],
        ["DATABASE_URL_SYNC", "Yes", "Sync PostgreSQL URL for Alembic (postgresql+psycopg2://...)"],
        ["REDIS_URL", "Yes", "Redis connection URL (redis://host:6379)"],
        ["LANGCHAIN_TRACING_V2", "Optional", "Set true to enable LangSmith tracing"],
        ["LANGCHAIN_API_KEY", "Optional", "LangSmith API key"],
        ["LANGCHAIN_PROJECT", "Optional", "LangSmith project name for grouping traces"],
        ["WHATSAPP_TOKEN", "Optional", "WhatsApp Business API token"],
        ["WHATSAPP_PHONE_NUMBER_ID", "Optional", "WhatsApp sender phone number ID"],
        ["WHATSAPP_VERIFY_TOKEN", "Optional", "Webhook verify token for WhatsApp"],
        ["PORT", "Optional", "API server port (default: 8000)"],
        ["DEBUG", "Optional", "Set true for development; false in production"],
    ],
    col_widths=[CONTENT_WIDTH*0.30, CONTENT_WIDTH*0.14, CONTENT_WIDTH*0.56],
))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 17. SCALABILITY ROADMAP
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("17. Scalability Roadmap"))
story.append(hr())
story.append(p(
    "The current architecture is designed for vertical scaling and moderate horizontal load. "
    "The following scaling path is planned and architecturally compatible with the existing "
    "codebase — no breaking schema changes required."
))
story.append(sp(8))

story.append(make_table(
    ["Phase", "Capability", "Approach", "Prerequisite"],
    [
        ["Current", "Single-server deployment", "Docker Compose; all services on one host", "None — live today"],
        ["Near-term", "Horizontal API scaling", "Multiple FastAPI replicas behind NGINX load balancer", "Stateless API confirmed (JWT, Redis session)"],
        ["Near-term", "Async action workers", "Celery or ARQ workers for action execution; decoupled from API", "Redis Streams or RabbitMQ as broker"],
        ["Medium-term", "Distributed task queues", "Redis Streams for inter-service messaging", "Worker pool deployed"],
        ["Medium-term", "Vector DB sharding", "ChromaDB collection sharding by company_id", "company_id already on all tables"],
        ["Long-term", "Multi-region deployment", "DB read replicas; regional Redis clusters; CDN for frontend", "Traffic justification"],
        ["Long-term", "Kubernetes orchestration", "Helm chart for enterprise on-premise installation", "DevOps resource availability"],
    ],
    col_widths=[CONTENT_WIDTH*0.15, CONTENT_WIDTH*0.22, CONTENT_WIDTH*0.38, CONTENT_WIDTH*0.25],
))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 18. FULL DAY-BY-DAY TIMELINE
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("18. Full Day-by-Day Timeline — Days 1 to 63"))
story.append(hr())
story.append(p(
    "Complete record of every build day, the engineering focus for that day, "
    "and the specific deliverable produced. Organised into 7 phases."
))
story.append(sp(10))

# Phase 1
story.append(ColorBand("PHASE 1 — FOUNDATION  |  Days 1–12", NAVY))
story.append(sp(4))
story.append(make_table(
    ["Day", "Focus Area", "Key Deliverable"],
    [
        ["1", "Project setup", "Folder structure, venv, requirements.txt, .gitignore with all patterns"],
        ["2", "FastAPI skeleton", "app/api/server.py, /health endpoint, CORS middleware configuration"],
        ["3", "PostgreSQL + Alembic", "Async DB connection pool, first migration, declarative base model class"],
        ["4", "User model", "users table, role enum (user/admin), email unique constraint, timestamps"],
        ["5", "JWT auth", "/login endpoint, token generation with expiry, get_current_user dependency"],
        ["6", "bcrypt passwords", "Password hashing on user creation, timing-safe verification on login"],
        ["7", "Protected routes", "Auth middleware, role guards on all sensitive endpoints, 403 on role mismatch"],
        ["8", "Redis setup", "Async Redis connection pool, ping healthcheck, reconnect logic"],
        ["9", "Conversation session", "sessions table, create/read/list endpoints, session title auto-generation"],
        ["10", "Environment config", "app/config/settings.py, Pydantic Settings class, .env.example template"],
        ["11", "Structured logging", "app/config/logger.py, per-request log context with session_id injection"],
        ["12", "Health endpoint v2", "DB + Redis + vector store status aggregated in /health single response"],
    ],
    col_widths=[CONTENT_WIDTH*0.07, CONTENT_WIDTH*0.25, CONTENT_WIDTH*0.68],
))

story.append(sp(12))
story.append(ColorBand("PHASE 2 — AI CORE  |  Days 13–19", HexColor("#1E3A5F")))
story.append(sp(4))
story.append(make_table(
    ["Day", "Focus Area", "Key Deliverable"],
    [
        ["13", "OpenAI client", "Wrapper with retry logic (×3 exponential backoff), timeout handling, error normalisation"],
        ["14", "Planner agent", "Keyword trie fast classification, LLM fallback for edge cases, intent label output"],
        ["15", "HR agent", "Leave policy (UAE Labour Law: 21 days years 1-5, 30 days after 5 years), onboarding, EOSB gratuity"],
        ["16", "IT agent", "Password reset workflow, VPN access guide, device support, access provisioning"],
        ["17", "Finance agent", "Salary review process, expense reimbursement, budget queries, VAT 5%, corporate tax 9%"],
        ["18", "Guardrail", "Out-of-scope detection, multi-intent disambiguation, harmful content blocking, prompt injection guard"],
        ["19", "Router", "Agent dispatch logic, conditional LangGraph edges based on Planner intent label"],
    ],
    col_widths=[CONTENT_WIDTH*0.07, CONTENT_WIDTH*0.25, CONTENT_WIDTH*0.68],
))

story.append(sp(12))
story.append(ColorBand("PHASE 3 — RAG SYSTEM  |  Days 20–27", HexColor("#065F46")))
story.append(sp(4))
story.append(make_table(
    ["Day", "Focus Area", "Key Deliverable"],
    [
        ["20", "ChromaDB setup", "Vector store initialisation, collection management, persistent Docker volume mount"],
        ["21", "Document ingestion", "Text loader pipeline, RecursiveCharacterTextSplitter(800, 120), separator hierarchy"],
        ["22", "Dense retrieval", "text-embedding-ada-002 embedding generation, cosine similarity top-K search"],
        ["23", "BM25 retrieval", "Sparse keyword index, app/rag/hybrid_retriever.py, BM25 cache invalidation logic"],
        ["24", "RRF fusion", "Reciprocal Rank Fusion: score=sum(1/(k+rank)), merges dense+sparse ranked lists without calibration"],
        ["25", "Knowledge base", "100 .txt documents written across 5 categories; UAE Labour Law facts verified"],
        ["26", "CRAG grader", "LLM chunk scoring (relevant/ambiguous/irrelevant), automatic query rewrite on all-irrelevant"],
        ["27", "KB admin API", "Upload endpoint, delete endpoint, rebuild endpoint; _safe_path() path traversal protection"],
    ],
    col_widths=[CONTENT_WIDTH*0.07, CONTENT_WIDTH*0.25, CONTENT_WIDTH*0.68],
))

story.append(sp(12))
story.append(ColorBand("PHASE 4 — LANGGRAPH ORCHESTRATION  |  Days 28–30", HexColor("#4C1D95")))
story.append(sp(4))
story.append(make_table(
    ["Day", "Focus Area", "Key Deliverable"],
    [
        ["28", "StateGraph setup", "planner → guardrail → router → crag → report pipeline with typed state dict"],
        ["29", "Conditional edges", "Dynamic routing based on Planner classification output; error edge fallbacks per node"],
        ["30", "Graph compilation", "End-to-end pipeline test; execution step list captured for response metadata"],
    ],
    col_widths=[CONTENT_WIDTH*0.07, CONTENT_WIDTH*0.25, CONTENT_WIDTH*0.68],
))

story.append(sp(12))
story.append(ColorBand("PHASE 5 — PRODUCTION BACKEND  |  Days 31–43", HexColor("#7C2D12")))
story.append(sp(4))
story.append(make_table(
    ["Day", "Focus Area", "Key Deliverable"],
    [
        ["31", "/ask endpoint", "Full pipeline wired: auth → LangGraph → flat JSON response"],
        ["32", "Response schema", "Flat JSON: answer, agent, confidence, source, steps, evaluation_score, response_time, status"],
        ["33", "Auth hardening", "Token expiry enforcement, bcrypt verification confirmed, refresh token groundwork"],
        ["34", "Redis memory", "Per-session conversation history, TTL configuration, UUID4 session scoping (no cross-contamination)"],
        ["35", "Conversation logs", "conversation_logs table; all response fields persisted per turn for audit and analytics"],
        ["36", "Workflow engine", "actions table; agents create PENDING actions during conversation; admin approves in dashboard; system executes APPROVED→EXECUTING→COMPLETED; full timestamp audit trail at every state"],
        ["37", "Report node", "Dynamic confidence scorer, source attribution, evaluation score, response_time attached to every response"],
        ["38", "LangSmith", "LANGCHAIN_TRACING_V2 env var, project name scoping, node-level trace capture, token counting"],
        ["39", "Evaluation system", "Per-response quality scorer 0-100, stored in conversation_logs for longitudinal analysis"],
        ["40", "SSE streaming", "Token-by-token /ask/stream endpoint; EventSource connection; MessageSkeleton in UI during first token"],
        ["41", "PDF generation", "ReportLab with word-wrap loop using stringWidth(), showPage() for multi-page documents"],
        ["42", "Multi-tenant", "company_id on users table, scoped queries, company_id in JWT claim"],
        ["43", "Actions API", "Full CRUD: create, list, approve, execute, reject endpoints; admin-only approval gate enforced"],
    ],
    col_widths=[CONTENT_WIDTH*0.07, CONTENT_WIDTH*0.22, CONTENT_WIDTH*0.71],
))

story.append(PageBreak())
story.append(ColorBand("PHASE 6 — FRONTEND  |  Days 44–58", HexColor("#0369A1")))
story.append(sp(4))
story.append(make_table(
    ["Day", "Focus Area", "Key Deliverable"],
    [
        ["44", "Vite + React + TS", "Project scaffold, Tailwind v3, ESLint, TypeScript strict mode, path aliases configured"],
        ["45", "API client", "frontend/src/api/client.ts, axios with JWT Bearer interceptor, 401 auto-redirect"],
        ["46", "Auth context", "AuthContext.tsx, login/logout functions, role storage in context, token lifecycle management"],
        ["47", "Login page", "Form validation, error states (invalid credentials, network error), role-based redirect on success"],
        ["48", "Chat layout", "Sidebar + ChatPage split layout, session list rendering, new conversation button"],
        ["49", "MessageBubble", "User/assistant bubble styling, timestamp display, streaming indicator, MessageSkeleton component"],
        ["50", "Sidebar", "Session list with active state, role badge (purple for admin), admin nav, profile link, language toggle"],
        ["51", "RTL support", "RTLContext.tsx, dir=rtl on document root, all UI labels in Arabic and English, toggle persists"],
        ["52", "Admin dashboard", "Document upload with progress, user management table, action approval queue with context display"],
        ["53", "Department chart", "Recharts BarChart, Cell component for per-bar coloring (correct Recharts API — not raw SVG rect)"],
        ["54", "Profile page", "Email/department editor, password change with current-password verification, gradient avatar banner with role badge"],
        ["55", "React Router", "Protected routes, role guards, /chat /admin /profile /login routes, 404 fallback"],
        ["56", "Error handling", "Global error boundary, toast notifications, 401 redirect, network error display"],
        ["57", "Responsive design", "Mobile breakpoints, sidebar collapse on small screens, Tailwind responsive prefix utilities"],
        ["58", "UI polish", "Favicon (vite.svg), page titles, skeleton loading states, empty states, layout transitions"],
    ],
    col_widths=[CONTENT_WIDTH*0.07, CONTENT_WIDTH*0.22, CONTENT_WIDTH*0.71],
))

story.append(sp(12))
story.append(ColorBand("PHASE 7 — DEPLOY & AUDIT  |  Days 59–63", HexColor("#374151")))
story.append(sp(4))
story.append(make_table(
    ["Day", "Focus Area", "Key Deliverable"],
    [
        ["59", "Docker + Compose", "Dockerfile, docker-compose.yml with service healthchecks, volume mounts, SECRET_KEY :? enforcement, pinned image versions"],
        ["60", "Railway + Vercel", "API live on Railway with all env vars set in dashboard; frontend on Vercel with VITE_API_URL pointing to Railway; CORS configured for prod domain"],
        ["61", "GitHub Actions CI/CD", "pytest on every push, eslint + tsc --noEmit type checking, deploy workflow triggers on main merge"],
        ["62", "k6 load tests", "tests/load/load_test.js VU ramp to 50 users, p(95)<3s and p(99)<6s thresholds enforced, duplicate object key bug fixed"],
        ["63", "Full production audit", "All 67 Python files, all .tsx/.ts frontend files, all 100 data documents, all config files read and audited; 14 bugs found and fixed across codebase"],
    ],
    col_widths=[CONTENT_WIDTH*0.07, CONTENT_WIDTH*0.22, CONTENT_WIDTH*0.71],
))

story.append(sp(12))
story.append(h2("Summary of All 14 Bugs Found and Fixed in Production Audit"))
story.append(make_table(
    ["#", "File", "Bug", "Fix"],
    [
        ["1", "app/tools/file_generator.py", "Long content silently truncated at page boundary", "Word-wrap loop with showPage() for pagination"],
        ["2", "app/api/kb_manager.py", "_safe_path() called before filename null check → TypeError", "Moved filename validation before path resolution"],
        ["3", "app/api/kb_manager.py", "BM25 cache not invalidated after KB changes", "Added invalidate_bm25_cache() to all 3 endpoints"],
        ["4", "app/api/server.py", "PDF ingestion used chunk_size=500 — inconsistent with codebase", "Changed to chunk_size=800, chunk_overlap=120"],
        ["5", "frontend/src/pages/AdminPage.tsx", "useCallback + useEffect called after conditional return null — React hooks violation", "Moved all hooks before the conditional return"],
        ["6", "frontend/src/components/admin/DepartmentChart.tsx", "Raw SVG rect inside Bar — Recharts API violation; colors didn't apply", "Replaced with Cell component from recharts"],
        ["7", "frontend/src/pages/ChatPage.tsx", "Empty bubble shown during streaming before first token", "Added MessageSkeleton when msg.streaming && !msg.content"],
        ["8", "frontend/index.html", "Title was 'frontend'; favicon path broken (/favicon.svg missing)", "Title → 'Enterprise AI Workforce'; favicon → /src/assets/vite.svg"],
        ["9", "data/Company/company_23.txt", "Annual leave stated as '30 days after 1 year' — wrong UAE law", "Corrected to 21 days years 1-5; 30 days after 5 years of service"],
        ["10", "scripts/seed_db.py", "Created username='user'/password='user123' mismatching all docs", "Changed to employee1/emp123 matching README and load tests"],
        ["11", "scripts/generate_kb.py", "Unconditional file write would overwrite 100 KB files on re-run", "Added os.path.exists() check; --force flag for intentional overwrite"],
        ["12", "tests/load/config.js + load_test.js", "Duplicate JS object keys for http_req_duration — p95 threshold silently dropped", "Combined both conditions: ['p(95)<3000', 'p(99)<6000']"],
        ["13", "app_ui.py", "Hardcoded session_id='user1' — all Streamlit users shared same Redis memory slot", "Added uuid.uuid4() per session initialisation in session_state"],
        ["14", "docker-compose.yml", "SECRET_KEY had insecure default string — JWT secret silently set to known weak value", "Changed to :? syntax — startup fails if SECRET_KEY not set"],
    ],
    col_widths=[CONTENT_WIDTH*0.04, CONTENT_WIDTH*0.23, CONTENT_WIDTH*0.38, CONTENT_WIDTH*0.35],
))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 19. PROJECT METRICS
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("19. Project Metrics"))
story.append(hr())

story.append(make_table(
    ["Metric", "Value"],
    [
        ["Total build timeline", "63 days"],
        ["Python source files audited", "67"],
        ["TypeScript/TSX files audited", "All frontend files"],
        ["Knowledge base documents", "100"],
        ["KB categories", "5 (HR, IT, Finance, General, Company)"],
        ["Specialist agents", "4 (Planner, HR, IT, Finance)"],
        ["LangGraph pipeline nodes", "5 (planner, guardrail, router, crag, report)"],
        ["Action lifecycle states", "6 (PENDING, APPROVED, EXECUTING, COMPLETED, REJECTED, FAILED)"],
        ["API endpoints", "25+"],
        ["Database tables", "8"],
        ["Frontend pages", "6 (Login, Chat, Admin, Profile, 404, Loading)"],
        ["React components", "20+"],
        ["Languages supported", "2 (English, Arabic with RTL)"],
        ["Confidence levels", "4 (High / Medium / Low / Very Low)"],
        ["Retrieval methods", "2 (ChromaDB dense + BM25 sparse)"],
        ["Fusion algorithm", "RRF (Reciprocal Rank Fusion)"],
        ["CRAG grade labels", "3 (relevant / ambiguous / irrelevant)"],
        ["Chunking configuration", "800 tokens, 120 overlap, 5 separators"],
        ["Docker services", "4 (postgres, redis, api, frontend)"],
        ["CI pipeline checks per push", "3 (pytest, eslint, tsc --noEmit)"],
        ["Load test thresholds enforced", "2 (p95 < 3s, p99 < 6s)"],
        ["Bugs found in production audit", "14 (all fixed)"],
        ["Orphaned .pyc files cleaned", "11"],
        ["UAE Labour Law facts verified", "Across all 100 KB documents"],
    ],
    col_widths=[CONTENT_WIDTH*0.55, CONTENT_WIDTH*0.45],
))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 20. FUTURE ROADMAP
# ══════════════════════════════════════════════════════════════════════════════

story.append(h1("20. Future Roadmap"))
story.append(hr())

story.append(h2("Near-Term (Next 30 Days)"))
story.append(make_table(
    ["Feature", "Description"],
    [
        ["WhatsApp integration", "Webhook receiver already scaffolded; wire incoming messages to LangGraph pipeline; format responses for WhatsApp"],
        ["Voice input", "Whisper API transcription endpoint; microphone button in React chat UI"],
        ["Ticket system integration", "Actions trigger Jira or Freshservice ticket creation via REST; status synced back to conversation"],
        ["Analytics dashboard", "Weekly query trends by agent, confidence distribution over time, evaluation score trends"],
        ["Email notifications", "SendGrid integration; action approval alerts sent to admin inbox with deep-link to dashboard"],
    ],
    col_widths=[CONTENT_WIDTH*0.28, CONTENT_WIDTH*0.72],
))

story.append(sp(10))
story.append(h2("Medium-Term (60–90 Days)"))
story.append(make_table(
    ["Feature", "Description"],
    [
        ["Multi-company SaaS", "company_id already on all DB tables; add company registration, billing, per-company KB isolation"],
        ["Fine-tuned intent classifier", "Replace Planner keyword trie + GPT-4o-mini with fine-tuned model for lower latency and cost"],
        ["Document Q&A", "User uploads PDF; temporary per-session ChromaDB collection; private document queries"],
        ["Compliance audit log UI", "Searchable, filterable view of all conversation logs and action history; date range export"],
        ["SAML / SSO", "Okta and Azure AD integration for corporate identity providers; role mapping from IdP groups"],
    ],
    col_widths=[CONTENT_WIDTH*0.28, CONTENT_WIDTH*0.72],
))

story.append(sp(10))
story.append(h2("Long-Term (90+ Days)"))
story.append(make_table(
    ["Feature", "Description"],
    [
        ["Agent builder UI", "Admin creates new specialist agents via form; defines KB categories, prompt templates, action types; no code deployment"],
        ["Multi-step workflow chains", "Approval chains across departments: HR approval → Finance approval → payroll system update"],
        ["KB auto-refresh", "Scheduled crawler ingests updated policy documents; triggers ChromaDB rebuild and BM25 invalidation automatically"],
        ["LLM model selector", "Swap GPT-4o-mini for Mistral, Llama 3, or Claude via dropdown in Admin dashboard; no code change"],
        ["GCC policy packs", "Saudi Labour Law, DIFC regulations, Kuwait/Bahrain/Qatar policy documents as structured KB extensions"],
        ["Kubernetes deployment", "Helm chart for enterprise on-premise installation; namespace isolation per company; horizontal pod autoscaling"],
    ],
    col_widths=[CONTENT_WIDTH*0.28, CONTENT_WIDTH*0.72],
))

story.append(sp(16))
story.append(hr(INDIGO, thickness=1))
story.append(sp(10))

closing = style("Closing",
    fontName="Helvetica-Bold", fontSize=13, textColor=NAVY,
    leading=20, alignment=TA_CENTER, spaceAfter=6)
closing_sub = style("ClosingSub",
    fontName="Helvetica", fontSize=10, textColor=SLATE_LT,
    leading=16, alignment=TA_CENTER)

story.append(p("Enterprise AI Workforce", closing))
story.append(p(
    "Designed for enterprise operations. Built for production deployment. "
    "Architected for the transition from AI assistants to AI agents that execute.",
    closing_sub,
))
story.append(sp(6))
story.append(p(
    "LangGraph · GPT-4o-mini · ChromaDB · BM25 · RRF · CRAG · FastAPI · React 18 · "
    "PostgreSQL · Redis · Docker · Railway · Vercel · GitHub Actions · k6",
    closing_sub,
))

# ─── Page number callback ─────────────────────────────────────────────────────

def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(SLATE_LT)
    # Footer line
    canvas.setStrokeColor(SLATE_XLT)
    canvas.setLineWidth(0.3)
    canvas.line(2*cm, 1.6*cm, W - 2*cm, 1.6*cm)
    canvas.drawString(2*cm, 1.1*cm, "Enterprise AI Workforce — Complete Project Reference")
    canvas.drawRightString(W - 2*cm, 1.1*cm, f"Page {doc.page}")
    canvas.restoreState()

# ─── Build ────────────────────────────────────────────────────────────────────

doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
print(f"PDF generated: {OUTPUT}")
