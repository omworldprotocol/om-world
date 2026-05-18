#!/usr/bin/env bash
# scripts/deploy/install.sh — one-time bootstrap on hetzner-ash
#
# Run on the SERVER (not local Mac) as root, after:
#   1) Cloudflare zone for omworld.one is active
#   2) cloudflared tunnel om-world-mvp exists and credentials placed at /etc/cloudflared/
#   3) cloudflared-config.yml has the tunnel UUID filled in
#
# This script:
#   - Clones the om-world repo to /root/om-world
#   - npm ci + prisma db push + seed
#   - Installs and starts the systemd unit
#   - Smoke-tests on http://localhost:3001

set -euo pipefail

REPO="https://github.com/omworldprotocol/om-world.git"
DIR="/root/om-world"
SERVICE="/etc/systemd/system/om-world-mvp.service"

if [[ ! -d "$DIR" ]]; then
  echo "→ Cloning om-world to $DIR"
  git clone "$REPO" "$DIR"
fi

cd "$DIR"
git pull --ff-only

if [[ ! -f "$DIR/.env" ]]; then
  cat > "$DIR/.env" <<'ENV'
DATABASE_URL="file:./dev.db"
LLM_BACKEND=openclaw
OPENCLAW_TIMEOUT_MS=180000
DEEPSEEK_API_KEY=""
DEEPSEEK_MODEL=deepseek-chat
OMC_INITIAL_USER_CREDITS=100
OMC_INTENT_SUBMISSION_COST=1
OMC_CAPABILITY_REWARD=10
OMC_PATTERN_CREATION_REWARD=5
OMC_PATTERN_REUSE_REWARD=2
OM_NODE_ID=hetzner-ash-prod
ENV
  echo "→ Wrote default .env (edit if you want DeepSeek fallback enabled)"
fi

echo "→ npm ci"
npm ci --no-audit --no-fund

echo "→ Prisma generate + db push + seed"
npx prisma generate
npx prisma db push --skip-generate --accept-data-loss
npm run db:seed || true   # idempotent; existing rows fine

echo "→ npm run build"
npm run build

cp "$DIR/scripts/deploy/om-world-mvp.service" "$SERVICE"
systemctl daemon-reload
systemctl enable om-world-mvp
systemctl restart om-world-mvp
sleep 3
systemctl is-active om-world-mvp

echo "→ Smoke test"
curl -fsS --max-time 15 http://127.0.0.1:3001/api/summary && echo
echo "✓ om-world-mvp running on :3001"
echo ""
echo "Now make sure the cloudflared service is up:"
echo "    systemctl status cloudflared"
echo "Then verify the public URL:"
echo "    curl https://app.omworld.one/api/summary"
