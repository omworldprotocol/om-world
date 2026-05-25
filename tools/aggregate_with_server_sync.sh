#!/usr/bin/env bash
# Wrapper for launchd: pull server-side invocations into local
# .server.jsonl snapshots, then run the local aggregator (which now merges
# both .jsonl and .server.jsonl sources).
#
# Env (set by launchd plist):
#   OMW_ROOT              — local om-world repo root
#   OMW_PATTERN_PATH      — colon-separated overlay (public:private)
#   OMW_SERVER_HOST       — defaults to root@87.99.153.204
#   OMW_SERVER_SSH_KEY    — defaults to ~/.ssh/hetzner_ash_key
#   OMW_SERVER_DB_PATH    — defaults to /opt/om-world/server/omw_server.db
set -uo pipefail

OMW_ROOT="${OMW_ROOT:-/Users/feiyang/all_bots/om-world}"
PY="${PY:-/Users/feiyang/.pyenv/shims/python3}"

cd "$OMW_ROOT" || exit 1

echo "── $(date '+%Y-%m-%d %H:%M:%S') sync_server_metrics ──"
"$PY" tools/sync_server_metrics.py
echo
echo "── $(date '+%Y-%m-%d %H:%M:%S') aggregate_metrics ──"
"$PY" tools/aggregate_metrics.py
