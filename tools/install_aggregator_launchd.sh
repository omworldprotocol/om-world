#!/usr/bin/env bash
# install_aggregator_launchd.sh — 装 OMW metrics aggregator 的 launchd job
#
# 每 30 分钟跑一次 om-world/tools/aggregate_metrics.py。
# 日志在 ~/Library/Logs/world.omworld.aggregator.{out,err}.log。
#
# 这是 Stage 1 (Local) 的运行配置。Stage 2 切到服务器后改用 systemd timer。
#
# 用法:
#   ./tools/install_aggregator_launchd.sh           # install + load
#   ./tools/install_aggregator_launchd.sh uninstall # unload + remove
#   ./tools/install_aggregator_launchd.sh status    # 查看运行情况

set -euo pipefail

LABEL="world.omworld.aggregator"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
OMW_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGGREGATOR="${OMW_ROOT}/tools/aggregate_metrics.py"
PYTHON="$(which python3)"
INTERVAL=1800  # 30 min
LOG_DIR="$HOME/Library/Logs"

# v0.2.1: aggregator 需要扫两个目录(public + private overlay),
# 让 wedgetest/defi/ava 等 private patterns 的 metrics 也被聚合写回 PACK.md frontmatter。
OMW_PRIVATE_ROOT="${OMW_PRIVATE_ROOT:-$(cd "${OMW_ROOT}/../om-world-private" 2>/dev/null && pwd || echo '')}"
if [[ -d "$OMW_PRIVATE_ROOT/patterns" ]]; then
  PATTERN_PATH="${OMW_ROOT}/patterns:${OMW_PRIVATE_ROOT}/patterns"
  echo "📂 detected om-world-private at $OMW_PRIVATE_ROOT — will aggregate overlay"
else
  PATTERN_PATH="${OMW_ROOT}/patterns"
  echo "📂 no om-world-private detected — public-only aggregation"
fi

cmd="${1:-install}"

case "$cmd" in
  install)
    mkdir -p "$LOG_DIR" "$(dirname "$PLIST_PATH")"
    cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON}</string>
    <string>${AGGREGATOR}</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${OMW_ROOT}</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>OMW_ROOT</key>
    <string>${OMW_ROOT}</string>
    <key>OMW_PATTERN_PATH</key>
    <string>${PATTERN_PATH}</string>
    <key>OMW_RUNTIME_PATH</key>
    <string>${OMW_ROOT}/runtime</string>
    <key>OMW_AGENT_ID</key>
    <string>omw-aggregator-launchd</string>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>

  <key>StartInterval</key>
  <integer>${INTERVAL}</integer>

  <key>RunAtLoad</key>
  <true/>

  <key>StandardOutPath</key>
  <string>${LOG_DIR}/${LABEL}.out.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/${LABEL}.err.log</string>
</dict>
</plist>
PLIST
    # macOS Sonoma+ 推荐 bootstrap;不可用时回退到 launchctl load
    if launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null; then
      echo "✓ aggregator launchd job bootstrapped: $LABEL (interval ${INTERVAL}s)"
    else
      # 兼容旧 launchctl
      launchctl unload "$PLIST_PATH" 2>/dev/null || true
      launchctl load "$PLIST_PATH"
      echo "✓ aggregator launchd job loaded (legacy mode): $LABEL"
    fi
    echo "plist: $PLIST_PATH"
    echo "logs:  $LOG_DIR/${LABEL}.{out,err}.log"
    echo "管理:  ./tools/install_aggregator_launchd.sh {status,uninstall}"
    ;;

  uninstall)
    launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null \
      || launchctl unload "$PLIST_PATH" 2>/dev/null || true
    rm -f "$PLIST_PATH"
    echo "✓ aggregator launchd job removed"
    ;;

  status)
    echo "=== launchctl print ==="
    launchctl print "gui/$(id -u)/${LABEL}" 2>&1 | head -20 || \
      echo "(not loaded)"
    echo
    echo "=== recent out.log ==="
    tail -20 "$LOG_DIR/${LABEL}.out.log" 2>/dev/null || echo "(no log yet)"
    echo
    echo "=== recent err.log ==="
    tail -20 "$LOG_DIR/${LABEL}.err.log" 2>/dev/null || echo "(no errors)"
    ;;

  *)
    echo "Usage: $0 {install|uninstall|status}"
    exit 1
    ;;
esac
