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

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Enterprise AI Workforce — Railway Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Check railway is logged in ──────────────────────────────────────────────
echo -e "${YELLOW}[1/6] Checking Railway login...${NC}"
if ! railway whoami &>/dev/null; then
  echo -e "${RED}Not logged in. Run: railway login${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Logged in as: $(railway whoami)${NC}"

# ── Init / link project ─────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[2/6] Linking Railway project...${NC}"
echo "Creating project 'enterprise-ai-workforce'..."
railway init --name enterprise-ai-workforce 2>/dev/null || \
  echo "Project may already exist — linking..."
echo -e "${GREEN}✅ Project linked${NC}"

# ── Set environment variables ───────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[3/6] Setting environment variables...${NC}"

# Load from .env file
source .env 2>/dev/null || true

railway variables set \
  OPENAI_API_KEY="$OPENAI_API_KEY" \
  SECRET_KEY="$SECRET_KEY" \
  DEBUG="false" \
  PORT="8000" \
  PYTHONPATH="/app" \
  LANGCHAIN_TRACING_V2="false" \
  LANGCHAIN_PROJECT="enterprise-ai-workforce" \
  ALLOWED_ORIGINS="" 2>&1

echo -e "${GREEN}✅ Base variables set${NC}"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  ACTION REQUIRED — Add database services:${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  1. Open: https://railway.app/dashboard"
echo "  2. Click your 'enterprise-ai-workforce' project"
echo "  3. Click + New → Database → Add PostgreSQL"
echo "     Wait 30s → click PostgreSQL → Variables tab"
echo "     Copy the DATABASE_URL value"
echo ""
echo "  4. Click + New → Database → Add Redis"
echo "     Wait 30s → click Redis → Variables tab"
echo "     Copy the REDIS_URL value"
echo ""
echo -e "${YELLOW}  Then paste them here:${NC}"
echo ""
read -p "  Paste your Railway PostgreSQL DATABASE_URL: " PG_URL
read -p "  Paste your Railway Redis REDIS_URL: " RD_URL

# Convert postgresql:// to the two driver formats needed
ASYNC_URL=$(echo "$PG_URL" | sed 's|^postgresql://|postgresql+asyncpg://|' | sed 's|^postgres://|postgresql+asyncpg://|')
SYNC_URL=$(echo "$PG_URL" | sed 's|^postgresql://|postgresql+psycopg2://|' | sed 's|^postgres://|postgresql+psycopg2://|')

railway variables set \
  DATABASE_URL="$ASYNC_URL" \
  DATABASE_URL_SYNC="$SYNC_URL" \
  REDIS_URL="$RD_URL" 2>&1

echo -e "${GREEN}✅ Database variables set${NC}"

# ── Deploy ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[4/6] Deploying to Railway (this takes 3-5 minutes)...${NC}"
railway up --detach

echo -e "${GREEN}✅ Deployment triggered${NC}"

# ── Get domain ──────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[5/6] Getting your Railway domain...${NC}"
sleep 10
RAILWAY_DOMAIN=$(railway domain 2>/dev/null || echo "")

if [ -z "$RAILWAY_DOMAIN" ]; then
  echo ""
  echo -e "${YELLOW}  Domain not ready yet. Generate it manually:${NC}"
  echo "  Dashboard → API service → Settings → Networking → Generate Domain"
  read -p "  Paste your Railway domain URL (e.g. https://xxx.railway.app): " RAILWAY_DOMAIN
fi

echo -e "${GREEN}✅ Railway URL: $RAILWAY_DOMAIN${NC}"

# ── Update vercel.json with Railway URL ─────────────────────────────────────
echo ""
echo -e "${YELLOW}[6/6] Updating frontend/vercel.json with Railway URL...${NC}"

# Strip trailing slash
RAILWAY_DOMAIN="${RAILWAY_DOMAIN%/}"

# Update the vercel.json rewrite destination
python3 -c "
import json, sys
with open('frontend/vercel.json') as f:
    data = json.load(f)
for r in data.get('rewrites', []):
    if ':path*' in r.get('destination', ''):
        r['destination'] = '${RAILWAY_DOMAIN}/:path*'
with open('frontend/vercel.json', 'w') as f:
    json.dump(data, f, indent=2)
print('Updated destination to: ${RAILWAY_DOMAIN}/:path*')
"

# Update ALLOWED_ORIGINS placeholder — will be filled after Vercel deploy
railway variables set ALLOWED_ORIGINS="" 2>/dev/null || true

# Commit the vercel.json update
git add frontend/vercel.json
git commit -m "config: set Railway URL in Vercel rewrite config" 2>/dev/null || \
  echo "(no change needed)"
git push origin main 2>/dev/null || true

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}  ✅ RAILWAY DEPLOYMENT COMPLETE!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  API URL:   $RAILWAY_DOMAIN"
echo "  Health:    $RAILWAY_DOMAIN/health"
echo "  API Docs:  $RAILWAY_DOMAIN/docs"
echo ""
echo -e "${YELLOW}  Wait 2-3 minutes for build to complete, then test:${NC}"
echo "  curl $RAILWAY_DOMAIN/health"
echo ""
echo -e "${YELLOW}  Next step: run   bash deploy_vercel.sh${NC}"
echo ""
