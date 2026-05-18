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
echo -e "${GREEN}✅ Logged in as: $(railway whoami 2>&1 | head -1)${NC}"

# ── Link to the already-created project ─────────────────────────────────────
echo ""
echo -e "${YELLOW}[2/6] Linking to Railway project...${NC}"
# Project was already created — just confirm it's linked
if railway status &>/dev/null; then
  echo -e "${GREEN}✅ Project already linked${NC}"
else
  echo "Linking to enterprise-ai-workforce project..."
  railway link 2>&1 || true
fi

# ── Set environment variables ───────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[3/6] Setting environment variables...${NC}"

# Load from .env file
set -a
source .env 2>/dev/null || true
set +a

# Set all required vars (no empty values — Railway rejects them)
railway variables set \
  OPENAI_API_KEY="$OPENAI_API_KEY" \
  SECRET_KEY="$SECRET_KEY" \
  DEBUG="false" \
  PORT="8000" \
  PYTHONPATH="/app" \
  LANGCHAIN_TRACING_V2="false" \
  LANGCHAIN_PROJECT="enterprise-ai-workforce"

echo -e "${GREEN}✅ Base variables set${NC}"

# ── Add database services via dashboard ─────────────────────────────────────
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  ACTION REQUIRED — Add PostgreSQL and Redis:${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  1. Open this URL in your browser:"
echo "     https://railway.com/project/0cbe4a1a-2a4a-4298-a332-0ff1a71835e0"
echo ""
echo "  2. Click '+ New'  →  Database  →  'Add PostgreSQL'"
echo "     Wait 30 seconds for it to provision"
echo "     Click the PostgreSQL service → 'Variables' tab"
echo "     Find 'DATABASE_URL' → copy that full value"
echo ""
echo "  3. Click '+ New'  →  Database  →  'Add Redis'"
echo "     Wait 30 seconds"
echo "     Click the Redis service → 'Variables' tab"
echo "     Find 'REDIS_URL' → copy that full value"
echo ""
echo -e "${YELLOW}  Done? Paste the URLs below (press Enter after each):${NC}"
echo ""
read -p "  PostgreSQL DATABASE_URL: " PG_URL
read -p "  Redis REDIS_URL: " RD_URL

# Convert to the two SQLAlchemy driver formats
ASYNC_URL=$(echo "$PG_URL" | sed 's|^postgresql://|postgresql+asyncpg://|' | sed 's|^postgres://|postgresql+asyncpg://|')
SYNC_URL=$(echo "$PG_URL"  | sed 's|^postgresql://|postgresql+psycopg2://|' | sed 's|^postgres://|postgresql+psycopg2://|')

railway variables set \
  DATABASE_URL="$ASYNC_URL" \
  DATABASE_URL_SYNC="$SYNC_URL" \
  REDIS_URL="$RD_URL"

echo -e "${GREEN}✅ Database variables set${NC}"

# ── Deploy ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[4/6] Deploying to Railway (3–5 minutes)...${NC}"
railway up --detach
echo -e "${GREEN}✅ Deployment triggered — building in background${NC}"

# ── Generate / get domain ────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[5/6] Getting your public Railway domain...${NC}"
echo ""
echo "  In your Railway dashboard:"
echo "  → Click your API service"
echo "  → 'Settings' tab  →  'Networking' section"
echo "  → Click 'Generate Domain'"
echo "  → Copy the URL  (looks like: https://xxx.up.railway.app)"
echo ""
read -p "  Paste your Railway public URL: " RAILWAY_DOMAIN

# Strip trailing slash
RAILWAY_DOMAIN="${RAILWAY_DOMAIN%/}"

echo -e "${GREEN}✅ Railway URL: $RAILWAY_DOMAIN${NC}"

# ── Update vercel.json with Railway URL ─────────────────────────────────────
echo ""
echo -e "${YELLOW}[6/6] Updating frontend/vercel.json with Railway URL...${NC}"

python3 - <<PYEOF
import json
with open('frontend/vercel.json') as f:
    data = json.load(f)
for r in data.get('rewrites', []):
    if ':path*' in r.get('destination', ''):
        r['destination'] = '${RAILWAY_DOMAIN}/:path*'
with open('frontend/vercel.json', 'w') as f:
    json.dump(data, f, indent=2)
print('  Updated vercel.json rewrite → ${RAILWAY_DOMAIN}/:path*')
PYEOF

git add frontend/vercel.json
git commit -m "config: set Railway backend URL in Vercel rewrite" 2>/dev/null || echo "  (vercel.json unchanged)"
git push origin main 2>/dev/null && echo -e "${GREEN}  ✅ Pushed to GitHub${NC}" || true

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}  ✅ RAILWAY DEPLOYMENT COMPLETE!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  API URL:   $RAILWAY_DOMAIN"
echo "  Health:    $RAILWAY_DOMAIN/health"
echo "  API Docs:  $RAILWAY_DOMAIN/docs"
echo ""
echo -e "${YELLOW}  Build takes ~3 min. Test with:${NC}"
echo "  curl $RAILWAY_DOMAIN/health"
echo ""
echo -e "${YELLOW}  After build completes, seed the database:${NC}"
echo "  → Railway dashboard → API service → Settings → Shell"
echo "  → Run: python scripts/seed_db.py"
echo "  → Run: python build_vector_db.py"
echo ""
echo -e "${YELLOW}  Then deploy frontend:  bash deploy_vercel.sh${NC}"
echo ""
