#!/usr/bin/env python3
"""sync_server_metrics.py — pull invocation events from hetzner-ash OMW
Stage 3 server into Mac-local patterns/<id>/invocations.server.jsonl files.

Why: Stage 3 server (hetzner-ash:8765, omw_server.db) collects all events
from SOVEREIGN-X / OM-WORLD-X / future server-side agents. Mac aggregator
needs those events to write merged metrics into Pattern frontmatter.

How: SSH exec `sqlite3 omw_server.db .dump` is too heavy; we use the
table's JSON export trick instead — sqlite3's `-json` mode returns
already-shaped rows, one per invocation. We split by pattern_id and
overwrite per-pattern .server.jsonl (full snapshot each run; aggregator
dedupes via invocation_id pairing).

Auth: uses ssh key + server is 127.0.0.1-bound, so we just shell out.

Usage:
  python tools/sync_server_metrics.py                   # use defaults
  OMW_SERVER_HOST=other.host python tools/sync_server_metrics.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

SERVER_HOST = os.environ.get("OMW_SERVER_HOST", "root@87.99.153.204")
SSH_KEY = os.environ.get("OMW_SERVER_SSH_KEY",
                         os.path.expanduser("~/.ssh/hetzner_ash_key"))
REMOTE_DB = os.environ.get("OMW_SERVER_DB_PATH",
                           "/opt/om-world/server/omw_server.db")

OMW_ROOT = Path(os.environ.get(
    "OMW_ROOT",
    str(Path(__file__).resolve().parent.parent),
))
PRIVATE_ROOT = OMW_ROOT.parent / "om-world-private"

# Mirror aggregate_metrics._all_pattern_dirs strategy.
PATTERN_BASES: list[Path] = [OMW_ROOT / "patterns"]
if (PRIVATE_ROOT / "patterns").is_dir():
    PATTERN_BASES.append(PRIVATE_ROOT / "patterns")


def _ssh_dump_invocations() -> list[dict]:
    """Pull all invocation rows from the remote SQLite DB as JSON."""
    sql = (
        "SELECT ts, agent_id, pattern_id, invocation_id, phase, success, "
        "duration_s, context, metrics, notes, "
        # v0.3.0 step-level columns (may be NULL on old rows pre-migration)
        "parent_invocation_id, step_id, step_kind, guards_triggered, "
        "judgment_score, gap_signal "
        "FROM invocations ORDER BY id"
    )
    cmd = [
        "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
        SERVER_HOST,
        f"sqlite3 -json {REMOTE_DB} '{sql}'",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        sys.stderr.write(f"SSH dump failed:\n{proc.stderr}\n")
        return []
    out = proc.stdout.strip()
    if not out:
        return []
    rows = json.loads(out)
    # Normalize: server stores context/metrics as JSON strings.
    # success column may be 0/1/None (SQLite). 0/1 → bool, None unchanged.
    normalized = []
    for r in rows:
        ev = {
            "ts": r.get("ts"),
            "agent_id": r.get("agent_id"),
            "pattern_id": r.get("pattern_id"),
            "invocation_id": r.get("invocation_id"),
            "phase": r.get("phase"),
        }
        if r.get("success") is not None:
            ev["success"] = bool(r["success"])
        if r.get("duration_s") is not None:
            ev["duration_s"] = r["duration_s"]
        for json_field in ("context", "metrics"):
            raw = r.get(json_field)
            if raw:
                try:
                    parsed = json.loads(raw)
                    if parsed:
                        ev[json_field] = parsed
                except (json.JSONDecodeError, TypeError):
                    pass
        if r.get("notes"):
            ev["notes"] = r["notes"]
        # v0.3.0 step-level passthrough
        for field in ("parent_invocation_id", "step_id", "step_kind"):
            if r.get(field):
                ev[field] = r[field]
        for json_field in ("guards_triggered", "gap_signal"):
            raw = r.get(json_field)
            if raw:
                try:
                    parsed = json.loads(raw)
                    if parsed:
                        ev[json_field] = parsed
                except (json.JSONDecodeError, TypeError):
                    pass
        if r.get("judgment_score") is not None:
            ev["judgment_score"] = r["judgment_score"]
        normalized.append(ev)
    return normalized


def _find_pattern_dir(pattern_id: str) -> Path | None:
    """Locate pattern_id dir across all PATTERN_BASES (overlay)."""
    for base in PATTERN_BASES:
        cand = base / pattern_id
        if (cand / "SKILL.md").is_file():
            return cand
        pack_cand = base / "packs" / pattern_id
        if (pack_cand / "PACK.md").is_file():
            return pack_cand
    return None


def _write_server_jsonl(pat_dir: Path, events: list[dict]) -> None:
    """Overwrite invocations.server.jsonl with snapshot of server events."""
    out_path = pat_dir / "invocations.server.jsonl"
    if not events:
        # remove stale file if no events for this pattern
        if out_path.exists():
            out_path.unlink()
        return
    with out_path.open("w", encoding="utf-8") as fp:
        for ev in events:
            fp.write(json.dumps(ev, ensure_ascii=False) + "\n")


def main() -> int:
    events = _ssh_dump_invocations()
    if not events:
        print("no invocations on server (or SSH failed)")
        return 1
    by_pattern: dict[str, list[dict]] = defaultdict(list)
    for ev in events:
        pid = ev.get("pattern_id")
        if pid:
            by_pattern[pid].append(ev)

    written = 0
    skipped = 0
    for pid, evs in by_pattern.items():
        pat_dir = _find_pattern_dir(pid)
        if pat_dir is None:
            skipped += 1
            continue
        _write_server_jsonl(pat_dir, evs)
        written += 1
        print(f"  [sync] {pid}: {len(evs)} events → {pat_dir.relative_to(OMW_ROOT.parent)}/invocations.server.jsonl")
    print(f"\n✓ synced {written} pattern(s) from server "
          f"({skipped} unknown pattern_ids skipped, {len(events)} total events)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
