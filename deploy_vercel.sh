#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Enterprise AI Workforce — Vercel Deployment Script
# Run this AFTER: deploy_railway.sh completes AND vercel login
# Usage: bash deploy_vercel.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e
export PATH="/Users/hussainbold/.npm-global/bin:$PATH"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Enterprise AI Workforce — Vercel Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Check vercel login ──────────────────────────────────────────────────────
echo -e "${YELLOW}[1/4] Checking Vercel login...${NC}"
if ! vercel whoami &>/dev/null; then
  echo -e "${RED}Not logged in. Run: vercel login${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Logged in as: $(vercel whoami)${NC}"

# ── Check vercel.json has Railway URL ───────────────────────────────────────
echo ""
echo -e "${YELLOW}[2/4] Checking Railway URL in vercel.json...${NC}"
DEST=$(python3 -c "
import json
with open('frontend/vercel.json') as f:
    data = json.load(f)
for r in data.get('rewrites', []):
    if ':path*' in r.get('destination', ''):
        print(r['destination'])
        break
")

if echo "$DEST" | grep -q "your-app.railway.app"; then
  echo -e "${RED}ERROR: vercel.json still has the placeholder URL.${NC}"
  echo "  Run deploy_railway.sh first to set the real Railway URL."
  exit 1
fi

echo -e "${GREEN}✅ Railway URL set: $DEST${NC}"

# ── Deploy frontend to Vercel ───────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[3/4] Deploying frontend to Vercel...${NC}"
echo "  (Answering prompts automatically)"

cd frontend

# Deploy to production — yes to all prompts
vercel --prod --yes 2>&1 | tee /tmp/vercel_output.txt

# Extract the production URL from output
VERCEL_URL=$(grep -oE 'https://[a-zA-Z0-9._-]+\.vercel\.app' /tmp/vercel_output.txt | tail -1)

cd ..

if [ -z "$VERCEL_URL" ]; then
  echo ""
  read -p "  Paste your Vercel deployment URL: " VERCEL_URL
fi

echo -e "${GREEN}✅ Vercel URL: $VERCEL_URL${NC}"

# ── Update Railway CORS with Vercel URL ─────────────────────────────────────
echo ""
echo -e "${YELLOW}[4/4] Updating Railway CORS to allow Vercel origin...${NC}"
export PATH="/Users/hussainbold/.npm-global/bin:$PATH"
railway variables set ALLOWED_ORIGINS="$VERCEL_URL" 2>/dev/null && \
  echo -e "${GREEN}✅ CORS updated${NC}" || \
  echo -e "${YELLOW}  Update manually in Railway dashboard → Variables → ALLOWED_ORIGINS = $VERCEL_URL${NC}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}  ✅ FULL DEPLOYMENT COMPLETE!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  🌐 Frontend (Vercel):  $VERCEL_URL"
echo "  🚂 Backend (Railway):  $(cat frontend/vercel.json | python3 -c "import json,sys; d=json.load(sys.stdin); [print(r['destination'].replace('/:path*','')) for r in d.get('rewrites',[]) if ':path*' in r.get('destination','')]")"
echo ""
echo "  Test login:    $VERCEL_URL  →  employee1 / emp123"
echo "  Admin panel:   $VERCEL_URL/admin  →  admin / admin123"
echo "  API docs:      $(cat frontend/vercel.json | python3 -c "import json,sys; d=json.load(sys.stdin); [print(r['destination'].replace('/:path*','')) for r in d.get('rewrites',[]) if ':path*' in r.get('destination','')]")/docs"
echo ""
echo -e "${YELLOW}  Note: If login fails, wait 2 min for Railway to finish seeding${NC}"
echo "  Then run inside Railway terminal:"
echo "    python scripts/seed_db.py"
echo "    python build_vector_db.py"
echo ""
