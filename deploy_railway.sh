#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Enterprise AI Workforce — Railway Deployment Script
# Run this AFTER: railway login
# Usage: bash deploy_railway.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e
export PATH="/Users/hussainbold/.npm-global/bin:$PATH"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Known IDs (set during first run — do not change)
API_SERVICE_ID="265d25cf-68a6-4067-acf1-2772b6ad4f49"
POSTGRES_SERVICE_ID="148f2429-0635-49b4-a3b7-8080124dc8f8"
REDIS_SERVICE_ID="badc8081-c267-4fc6-9ae0-8bfc70632da5"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Enterprise AI Workforce — Railway Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Check railway is logged in ──────────────────────────────────────────────
echo -e "${YELLOW}[1/5] Checking Railway login...${NC}"
if ! railway whoami &>/dev/null; then
  echo -e "${RED}Not logged in. Run: railway login${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Logged in as: $(railway whoami 2>&1 | head -1)${NC}"

# ── Link to project + service ────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[2/5] Linking to Railway project and service...${NC}"
railway service link "$API_SERVICE_ID" 2>/dev/null || true
echo -e "${GREEN}✅ Linked to service: enterprise-ai-workforce${NC}"

# ── Pull DB URLs directly from Railway service variables ─────────────────────
echo ""
echo -e "${YELLOW}[3/5] Reading database URLs from Railway...${NC}"

PG_RAW=$(railway variables --service "$POSTGRES_SERVICE_ID" --json 2>/dev/null \
  | python3 -c "import json,sys; print(json.load(sys.stdin).get('DATABASE_URL',''))")
RD_URL=$(railway variables --service "$REDIS_SERVICE_ID" --json 2>/dev/null \
  | python3 -c "import json,sys; print(json.load(sys.stdin).get('REDIS_URL',''))")

if [ -z "$PG_RAW" ] || [ -z "$RD_URL" ]; then
  echo -e "${RED}Could not read DB URLs. Make sure PostgreSQL and Redis are added in the dashboard.${NC}"
  echo "  Dashboard: https://railway.com/project/0cbe4a1a-2a4a-4298-a332-0ff1a71835e0"
  exit 1
fi

ASYNC_URL=$(echo "$PG_RAW" | sed 's|^postgresql://|postgresql+asyncpg://|' | sed 's|^postgres://|postgresql+asyncpg://|')
SYNC_URL=$(echo "$PG_RAW"  | sed 's|^postgresql://|postgresql+psycopg2://|' | sed 's|^postgres://|postgresql+psycopg2://|')

echo -e "${GREEN}✅ PostgreSQL: ${PG_RAW:0:40}...${NC}"
echo -e "${GREEN}✅ Redis:      ${RD_URL:0:40}...${NC}"

# ── Set all environment variables ────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[4/5] Setting all environment variables...${NC}"

set -a; source .env 2>/dev/null || true; set +a

railway variables set \
  OPENAI_API_KEY="$OPENAI_API_KEY" \
  SECRET_KEY="$SECRET_KEY" \
  DEBUG="false" \
  PORT="8000" \
  PYTHONPATH="/app" \
  LANGCHAIN_TRACING_V2="false" \
  LANGCHAIN_PROJECT="enterprise-ai-workforce" \
  DATABASE_URL="$ASYNC_URL" \
  DATABASE_URL_SYNC="$SYNC_URL" \
  REDIS_URL="$RD_URL"

echo -e "${GREEN}✅ All variables set${NC}"

# ── Deploy ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[5/5] Deploying to Railway (3–5 minutes)...${NC}"
railway up --detach
echo -e "${GREEN}✅ Deployment triggered${NC}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}  ✅ DEPLOYMENT TRIGGERED!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Watch build logs at:"
echo "  https://railway.com/project/0cbe4a1a-2a4a-4298-a332-0ff1a71835e0"
echo ""
echo -e "${YELLOW}  While it builds (3-5 min), generate your public domain:${NC}"
echo "  → Click 'enterprise-ai-workforce' service in dashboard"
echo "  → 'Settings' tab  →  'Networking' section"
echo "  → Click 'Generate Domain'"
echo "  → Copy the URL (https://xxx.up.railway.app)"
echo ""
echo -e "${YELLOW}  Then run:  bash set_railway_domain.sh <your-domain-url>${NC}"
echo ""
