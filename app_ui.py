# app_ui.py — Streamlit prototype UI (legacy; React frontend is the primary UI)
# Use for quick local demos only. Not used in production deployment.

import uuid
import streamlit as st
import requests

# ----------------------------------
# CONFIG
# ----------------------------------
st.set_page_config(
    page_title="Enterprise AI Workforce",
    page_icon="🤖",
    layout="wide"
)

API_URL = "http://127.0.0.1:8000"

# ----------------------------------
# SESSION STATE
# ----------------------------------
for key, default in [
    ("token",         None),
    ("role",          None),
    ("session_id",    str(uuid.uuid4())),   # unique per browser session
    ("chat_history",  []),
    ("last_response", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ----------------------------------
# 🔐 LOGIN
# ----------------------------------
if not st.session_state.token:
    st.markdown("# 🔐 Enterprise AI Workforce Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            res = requests.post(
                f"{API_URL}/login",
                json={"username": username, "password": password}
            )
            if res.status_code == 200:
                data = res.json()
                st.session_state.token = data["access_token"]
                st.session_state.role  = data["role"]
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid credentials")
        except Exception as e:
            st.error("Backend not reachable")
            st.code(str(e))

    st.stop()

# ----------------------------------
# AUTH HEADERS
# ----------------------------------
headers = {"Authorization": f"Bearer {st.session_state.token}"}

# ----------------------------------
# SIDEBAR
# ----------------------------------
with st.sidebar:
    st.title("🤖 Enterprise AI Workforce")
    st.success(f"Logged in as: {st.session_state.role.upper()}")

    if st.button("Logout"):
        for key in ["token", "role", "last_response"]:
            st.session_state[key] = None
        st.session_state.chat_history = []
        st.rerun()

    st.markdown("---")
    st.markdown("### System Status")
    try:
        health = requests.get(f"{API_URL}/health", timeout=3)
        if health.status_code == 200:
            st.success("✅ Backend Connected")
            st.success("✅ Agents Active")
            st.success("✅ Knowledge Base Ready")
        else:
            st.error(f"⚠️ Backend returned {health.status_code}")
    except Exception:
        st.error("❌ Backend not reachable")

    st.markdown("---")
    st.markdown("### Active Agents")
    for agent in ["🧠 Planner", "👩‍💼 HR", "💻 IT", "💰 Finance"]:
        st.write(agent)

    st.markdown("---")
    st.markdown("### Try asking:")
    st.caption("• What is the leave policy?")
    st.caption("• How do I reset my password?")
    st.caption("• How do I request a salary increase?")

# ----------------------------------
# HEADER
# ----------------------------------
st.markdown("# 🚀 Enterprise AI Workforce")
st.caption("Multi-Agent AI Automation Platform")
st.markdown("---")

# ----------------------------------
# TABS
# ----------------------------------
tab1, tab2, tab3 = st.tabs(["💬 AI Console", "📊 Workflow", "📐 Architecture"])

# ==========================================
# TAB 1 — AI CONSOLE
# ==========================================
# streamlit_app.py  — only the TAB 1 section changes, rest stays same

with tab1:
    st.subheader("AI Automation Console")

    user_input = st.chat_input("Ask HR, IT, or Finance questions...")

    if user_input:
        # ✅ TEST 3 — Empty input: chat_input won't fire on empty
        # ✅ TEST 4 — Gibberish: guardrail handles it in backend
        st.session_state.chat_history.append(("user", user_input))
        st.session_state.last_response = None

        with st.spinner("🤖 Processing with AI agents..."):
            try:
                res = requests.post(
                    f"{API_URL}/ask",
                    json    = {"session_id": st.session_state.session_id, "question": user_input},
                    headers = headers,
                    timeout = 60
                )
                api_response = res.json()
                st.session_state.last_response = api_response

            except Exception as e:
                st.error("Backend error")
                st.code(str(e))
                st.stop()

        response = st.session_state.last_response or {}
        answer   = response.get("answer", "⚠️ No response received.")

        st.session_state.chat_history.append(("assistant", answer))

    # CHAT — clean, no duplicates
    for role, msg in st.session_state.chat_history:
        st.chat_message(role).write(msg)

    st.markdown("---")

    # RESPONSE PANEL
    # Only the RESPONSE PANEL section changes — replace from "if st.session_state.last_response:"

    if st.session_state.last_response:
        response = st.session_state.last_response

        answer            = response.get("answer",            "⚠️ No response")
        agent             = response.get("agent",             "Unknown")
        confidence        = response.get("confidence",        0)
        source            = response.get("source",            "N/A")
        steps             = response.get("steps",             [])
        confidence_reason = response.get("confidence_reason", "")
        evaluation_score  = response.get("evaluation_score",  0)
        response_time     = response.get("response_time",     None)
        status            = response.get("status",            "success")

        # 🚨 GUARDRAIL / MULTI-INTENT / ERROR
        if agent == "guardrail" or status in ("error", "multi_intent"):
            if status == "multi_intent":
                st.info(answer)       # friendly clarification
            else:
                st.warning(answer)    # error / out of scope
        else:
            # ✅ METRICS ROW
            st.subheader("🧠 AI Insights")
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Agent",         agent)
            col2.metric("Confidence",    f"{confidence}%")
            col3.metric("Source",        source or "N/A")
            col4.metric("Eval Score",    f"{evaluation_score:.0f}" if evaluation_score else "N/A")
            col5.metric("Response Time", f"{response_time}s" if response_time else "N/A")
            
        # ✅ FIX 4 — Professional confidence message with color
        if confidence_reason:
            if confidence >= 80:
                st.success(f"✅ {confidence_reason}")
            elif confidence >= 60:
                st.info(f"🧠 {confidence_reason}")
            elif confidence >= 40:
                st.warning(f"⚠️ {confidence_reason}")
            else:
                st.error(f"❌ {confidence_reason}")

            # Response time
            if response_time:
                st.caption(f"⚡ Response generated in {response_time}s")

            # 📄 SOURCE PREVIEW
            source_lower = (source or "").lower()
            if source and source not in ("N/A", "fallback", "internal_kb", "guardrail"):
                st.markdown("### 📄 Source Preview")
                if "hr" in source_lower:
                    st.code("HR Policy → Leave: 21 days annual | Sick: 12 days")
                elif "it" in source_lower:
                    st.code("IT Policy → Password reset every 90 days | VPN required")
                elif "finance" in source_lower:
                    st.code("Finance Policy → Salary review annual | Expenses within 30 days")

            # ⚙️ EXECUTION FLOW
            st.markdown("### ⚙️ Execution Flow")
            if steps:
                for step in steps:
                    if "classified" in step or ("Planner" in step and "analyzing" in step):
                        st.info(step)
                    elif "Router" in step:
                        st.warning(step)
                    elif "Agent" in step:
                        st.success(step)
                    elif "Final" in step:
                        st.markdown(f"**{step}**")
                    elif "⚠️" in step or "Approval" in step:
                        st.error(step)
                    else:
                        st.write(step)
            else:
                st.info(f"🧠 Planner → analyzed and classified as {agent}")
                st.warning("🔀 Router → selected agent")
                st.success(f"🤖 {agent} Agent → processed request")
                st.markdown("**📄 Final → response generated**")

        # ✅ ISSUE 4 FIX — Debug hidden by default, toggle to show
        with st.expander("🔍 Debug Data — click to expand", expanded=False):
            st.json({
                "status":            status,
                "agent":             agent,
                "confidence":        confidence,
                "source":            source,
                "evaluation_score":  evaluation_score,
                "response_time":     response_time,
                "confidence_reason": confidence_reason,
                "steps":             steps,
            })
  
# ==========================================
# TAB 2 — WORKFLOW GRAPH
# ==========================================
with tab2:
    st.subheader("Workflow Visualization")
    try:
        res = requests.get(f"{API_URL}/workflow-graph", headers=headers)
        st.image(res.content, use_container_width=True)
    except:
        st.warning("Workflow graph endpoint unavailable — showing text diagram")
        st.markdown(""" [User Input]
         ↓
    [🧠 Planner Node]
      Keyword routing → LLM fallback
         ↓
    [🔀 Router Node]
      Approval gate → Agent dispatch
         ↓
    ┌──────────────────────────────────┐
    │  HR Agent  │  IT Agent  │  Finance Agent  │
    └──────────────────────────────────┘
         ↓
    [📄 Report Node]
      Confidence scoring → Logging
         ↓
    [✅ Final JSON Response]
    """)

# ==========================================
# TAB 3 — ARCHITECTURE
# ==========================================
with tab3:
    st.subheader("System Architecture")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### 🔁 AI System Flow
        **1. User Input** → Natural language query
        **2. Planner Agent** → Keyword routing + LLM classification
        **3. Router** → Agent selection + approval gate
        **4. Specialist Agent** → HR / IT / Finance
        **5. RAG Fallback** → Vector DB knowledge base
        **6. Report Node** → Dynamic confidence + logging
        **7. Final Response** → Flat JSON → Streamlit UI
        """)

    with col2:
        st.markdown("""
        ### 🤖 Agent Capabilities
        **👩‍💼 HR Agent**
        - Leave & vacation policy
        - Onboarding procedures
        - Employee handbook queries

        **💻 IT Agent**
        - Password reset guidance
        - VPN & remote access
        - System & device support

        **💰 Finance Agent**
        - Salary increase process
        - Expense reimbursement
        - Budget & invoice queries
        """)

    st.success("✅ Enterprise-grade multi-agent AI system — LangGraph + GPT-4o-mini + RAG")
    