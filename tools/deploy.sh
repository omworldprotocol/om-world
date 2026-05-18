#!/usr/bin/env bash
# tools/deploy.sh — OM World MVP deployment
#
# Flow: local commit → push GitHub → server git pull → npm ci + build → restart systemd → smoke test
#
# Usage:
#   ./tools/deploy.sh                  # full deploy to default server (hetzner-ash)
#   ./tools/deploy.sh --dry-run        # print steps, do not execute
#   ./tools/deploy.sh --skip-install   # skip npm ci (code-only change)
#   ./tools/deploy.sh --skip-build     # skip next build (rare; only for non-code changes)
#   ./tools/deploy.sh --skip-rollback  # do not auto-rollback on smoke failure
#
# Required server state (first time only — see scripts/deploy/README.md):
#   - /root/om-world cloned from https://github.com/omworldprotocol/om-world
#   - /root/om-world/.env populated
#   - systemd unit om-world-mvp.service installed
#   - cloudflared tunnel installed and ingress mapped to localhost:3001

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
GITHUB_REPO="omworldprotocol/om-world"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

SERVER="${SERVER:-hetzner-ash}"
REMOTE_DIR="/root/om-world"
SYSTEMD_SERVICE="om-world-mvp"
SMOKE_URL="http://127.0.0.1:3001/api/summary"

# ── Args ──────────────────────────────────────────────────────────────────────
DRY_RUN=false
SKIP_INSTALL=false
SKIP_BUILD=false
SKIP_ROLLBACK=false

for arg in "$@"; do
  case "$arg" in
    --dry-run)       DRY_RUN=true ;;
    --skip-install)  SKIP_INSTALL=true ;;
    --skip-build)    SKIP_BUILD=true ;;
    --skip-rollback) SKIP_ROLLBACK=true ;;
    *) echo "Unknown option: $arg"; exit 2 ;;
  esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────
STEP=0
TOTAL=5
step() {
  STEP=$((STEP + 1))
  echo ""
  echo "═══ [$STEP/$TOTAL] $* ═══"
}

run() {
  if $DRY_RUN; then
    echo "    DRY: $*"
  else
    eval "$@"
  fi
}

ssh_remote() {
  if $DRY_RUN; then
    echo "    DRY: ssh $SERVER '$*'"
  else
    ssh "$SERVER" "$@"
  fi
}

# ── Step 1: pre-flight ────────────────────────────────────────────────────────
step "Pre-flight checks"

cd "$LOCAL_DIR"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "✗ Uncommitted changes detected. Commit or stash first."
  git status --short
  exit 2
fi

LOCAL_SHA="$(git rev-parse HEAD)"
LOCAL_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo "  local branch: $LOCAL_BRANCH @ ${LOCAL_SHA:0:8}"
echo "  server:       $SERVER:$REMOTE_DIR"

if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$SERVER" 'true' 2>/dev/null; then
  echo "✗ Cannot SSH to $SERVER (check ~/.ssh/config)"
  exit 2
fi
echo "  ✓ SSH to $SERVER OK"

# ── Step 2: push to GitHub ────────────────────────────────────────────────────
step "Push to GitHub"

run "git push origin $LOCAL_BRANCH"
echo "  ✓ pushed $LOCAL_SHA to origin/$LOCAL_BRANCH"

# ── Step 3: server pull + install + build ─────────────────────────────────────
step "Server: git pull + npm ci + build"

REMOTE_PREV_SHA=$(ssh_remote "cd $REMOTE_DIR && git rev-parse HEAD" 2>/dev/null || echo "unknown")
echo "  remote previous: ${REMOTE_PREV_SHA:0:8}"

INSTALL_CMD="echo skip-install"
BUILD_CMD="echo skip-build"
if ! $SKIP_INSTALL; then INSTALL_CMD="npm ci --no-audit --no-fund"; fi
if ! $SKIP_BUILD;   then BUILD_CMD="npm run build"; fi

ssh_remote "set -e; cd $REMOTE_DIR && \
  git fetch origin && \
  git checkout $LOCAL_BRANCH && \
  git reset --hard origin/$LOCAL_BRANCH && \
  $INSTALL_CMD && \
  npx prisma generate && \
  npx prisma db push --skip-generate --accept-data-loss && \
  $BUILD_CMD"
echo "  ✓ server now at ${LOCAL_SHA:0:8}"

# ── Step 4: restart service ───────────────────────────────────────────────────
step "Restart $SYSTEMD_SERVICE"

ssh_remote "systemctl restart $SYSTEMD_SERVICE"
ssh_remote "sleep 3 && systemctl is-active $SYSTEMD_SERVICE"
echo "  ✓ $SYSTEMD_SERVICE is active"

# ── Step 5: smoke test ────────────────────────────────────────────────────────
step "Smoke test ($SMOKE_URL)"

set +e
SMOKE_OUT=$(ssh_remote "curl -fsS --max-time 15 $SMOKE_URL" 2>&1)
SMOKE_RC=$?
set -e

if [[ $SMOKE_RC -ne 0 ]]; then
  echo "✗ Smoke test failed:"
  echo "$SMOKE_OUT"
  if $SKIP_ROLLBACK || [[ "$REMOTE_PREV_SHA" == "unknown" ]]; then
    echo "  (skipping rollback)"
  else
    echo "  Rolling back to ${REMOTE_PREV_SHA:0:8}…"
    ssh_remote "cd $REMOTE_DIR && git reset --hard $REMOTE_PREV_SHA && npm ci --no-audit --no-fund && npm run build && systemctl restart $SYSTEMD_SERVICE"
    echo "  ✓ rolled back"
  fi
  exit 1
fi

echo "  ✓ smoke OK"
echo "    $SMOKE_OUT"

echo ""
echo "✓ Deploy complete. Public URL (after Cloudflare Tunnel): https://app.omworld.one/"
