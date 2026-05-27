#!/usr/bin/env python3
"""sync_wedgetest_patterns.py — P3-WT 2026-05-27.

Mac launchd 每 5 min 跑:
- 读 ~/.wedgetest/patterns.json (wedgetest exec-module 累积的 automation
  feasibility)
- 把 (platform, action, tier, successCount, failureCount, lastOk, ...)
  字段写进 `om-world-private/patterns/reference-omw-automation-feasibility/
  SKILL.md` 的 frontmatter `metadata.automation_paths`
- (可选) 同步 rsync 到 hetzner-ash:/opt/om-world-private/patterns/

为何不让 wedgetest 直接写 Pattern:wedgetest TS 不应碰 Python om-world-
private 文件结构;Mac 端单一同步 daemon 维护单向数据流(.json → Pattern
frontmatter)更清晰。

Idempotent:同 patterns.json 反复跑只更新 timestamp,不变。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WEDGETEST_PATTERNS_PATH = Path(os.environ.get(
    "WEDGETEST_PATTERNS_PATH",
    str(Path.home() / ".wedgetest" / "patterns.json"),
))
OMW_ROOT = Path(os.environ.get("OMW_ROOT",
    str(Path(__file__).resolve().parent.parent)))
PRIVATE_ROOT = OMW_ROOT.parent / "om-world-private"
TARGET = (PRIVATE_ROOT / "patterns" / "reference-omw-automation-feasibility"
          / "SKILL.md")

SERVER_HOST = os.environ.get("OMW_SERVER_HOST", "root@87.99.153.204")
SSH_KEY = os.environ.get("OMW_SERVER_SSH_KEY",
                         str(Path.home() / ".ssh" / "hetzner_ash_key"))
SERVER_PRIVATE = "/opt/om-world-private/patterns/"


def _load_wedgetest_patterns() -> list[dict]:
    if not WEDGETEST_PATTERNS_PATH.exists():
        return []
    raw = json.loads(WEDGETEST_PATTERNS_PATH.read_text())
    # raw 是 {key: {platform, action, tier, ...}} → list
    return list(raw.values())


def _update_frontmatter(text: str, automation_paths: list[dict],
                       synced_at: str) -> str:
    """读 SKILL.md 全文,替换/插入 metadata.automation_paths_synced_at +
    metadata.automation_paths 两字段。其他 frontmatter 保持原样。"""
    import yaml  # pyyaml
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md 缺 leading ---")
    end = None
    for i, ln in enumerate(lines[1:], 1):
        if ln.strip() == "---":
            end = i
            break
    if end is None:
        raise ValueError("SKILL.md 缺 closing ---")
    fm_text = "".join(lines[1:end])
    fm = yaml.safe_load(fm_text) or {}
    fm.setdefault("metrics", {})
    fm["metrics"]["automation_paths_synced_at"] = synced_at
    fm["metrics"]["automation_paths"] = automation_paths
    fm["metrics"]["last-validated"] = synced_at.split("T")[0]
    new_fm = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False,
                            default_flow_style=False)
    body = "".join(lines[end + 1:])
    return "---\n" + new_fm + "---\n" + body


def main() -> int:
    if not TARGET.exists():
        print(f"target Pattern not found: {TARGET}", file=sys.stderr)
        return 1
    paths_raw = _load_wedgetest_patterns()
    # 标准化为可读字段,且裁剪长 error
    automation_paths = [{
        "platform":     p.get("platform"),
        "action":       p.get("action"),
        "tier":         p.get("tier"),
        "successCount": p.get("successCount", 0),
        "failureCount": p.get("failureCount", 0),
        "lastOk":       p.get("lastOk"),
        "lastError":    (p.get("lastError") or "")[:200] or None,
        "lastTokenCost": p.get("lastTokenCost", 0),
        "firstSeenAt":  p.get("firstSeenAt"),
        "lastRunAt":    p.get("lastRunAt"),
    } for p in paths_raw]

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = TARGET.read_text(encoding="utf-8")
    new_text = _update_frontmatter(text, automation_paths, now_iso)

    if new_text == text:
        print(f"no change (already up to date, {len(automation_paths)} paths)")
        return 0
    TARGET.write_text(new_text, encoding="utf-8")
    print(f"wrote {TARGET} — {len(automation_paths)} automation paths")

    # rsync to server (best-effort)
    if os.environ.get("WEDGETEST_SYNC_NO_RSYNC") != "1":
        try:
            r = subprocess.run(
                ["rsync", "-az", "-e", f"ssh -i {SSH_KEY}",
                 str(TARGET.parent), f"{SERVER_HOST}:{SERVER_PRIVATE}"],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0:
                print("rsynced to server")
            else:
                print(f"rsync failed: {r.stderr[:200]}", file=sys.stderr)
        except Exception as e:
            print(f"rsync exception: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
