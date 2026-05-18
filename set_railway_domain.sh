#!/bin/bash
# Usage: bash set_railway_domain.sh https://your-app.up.railway.app
# Run this after generating a domain in the Railway dashboard.

set -e
export PATH="/Users/hussainbold/.npm-global/bin:$PATH"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

RAILWAY_DOMAIN="${1%/}"  # strip trailing slash

if [[ "$RAILWAY_DOMAIN" != https://* ]]; then
  echo -e "${RED}Usage: bash set_railway_domain.sh https://your-app.up.railway.app${NC}"
  exit 1
fi

echo ""
echo -e "${YELLOW}Updating frontend/vercel.json with Railway domain...${NC}"

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
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ Domain configured!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  API URL:   $RAILWAY_DOMAIN"
echo "  Health:    $RAILWAY_DOMAIN/health"
echo "  API Docs:  $RAILWAY_DOMAIN/docs"
echo ""
echo -e "${YELLOW}  Once build completes, test:${NC}"
echo "  curl $RAILWAY_DOMAIN/health"
echo ""
echo -e "${YELLOW}  Then seed the database (Railway dashboard → service → Shell):${NC}"
echo "  python scripts/seed_db.py"
echo "  python build_vector_db.py"
echo ""
echo -e "${YELLOW}  Then deploy the frontend:${NC}"
echo "  bash deploy_vercel.sh"
echo ""
