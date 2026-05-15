#!/usr/bin/env python3
"""
check-replies.py — Daily reply monitor for OM World outreach threads.

Reads outreach/crm.md, checks every tracked GitHub thread (issues +
discussions in external repos, plus omworldprotocol/om-world issues) for
new comments since the last run, prints a structured report, and updates
the replied / status columns in crm.md.

Usage:
    python3 tools/check-replies.py              # since last run (default)
    python3 tools/check-replies.py --since 2026-05-14
    python3 tools/check-replies.py --dry-run    # report only, no CRM write

Requirements: gh CLI authenticated as the outreach account.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CRM_PATH  = REPO_ROOT / "outreach" / "crm.md"
STATE_PATH = REPO_ROOT / "outreach" / ".check-replies-state.json"

# GitHub logins that count as "us" — excluded from reply detection.
OWN_LOGINS = {"flyoung588", "omworldprotocol"}

# Threads in these statuses are skipped entirely.
SKIP_STATUSES = {"committed", "bounce", "silent"}


# ── Utilities ─────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def gh_rest(*path_and_args: str, timeout: int = 25) -> list | dict | None:
    """Call gh api <REST path> [extra args] and return parsed JSON."""
    r = subprocess.run(
        ["gh", "api"] + list(path_and_args) + ["--paginate"],
        capture_output=True, text=True, timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return json.loads(r.stdout) if r.stdout.strip() else []


def gh_graphql(query: str, variables: dict | None = None, timeout: int = 25) -> dict:
    """Call gh api graphql and return parsed JSON."""
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    if variables:
        for k, v in variables.items():
            cmd += ["-F", f"{k}={v}"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return json.loads(r.stdout)


# ── State ─────────────────────────────────────────────────────────────────────

def load_since(override: str | None) -> str:
    """Return ISO-8601 UTC timestamp to use as the lower bound for comments."""
    if override:
        return override + "T00:00:00Z"
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text())
        ts = state.get("last_checked", "")
        if ts:
            return ts
    return (date.today() - timedelta(days=1)).isoformat() + "T00:00:00Z"


def save_state() -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    STATE_PATH.write_text(json.dumps({"last_checked": now}, indent=2))


# ── CRM parsing ───────────────────────────────────────────────────────────────

def parse_crm(path: Path) -> list[dict]:
    """
    Parse the tracker markdown table in crm.md.
    Returns a list of dicts keyed by column header, preserving insertion order.
    Also attaches the original line index so we can rewrite it later.
    """
    rows = []
    header: list[str] = []
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.split("|")[1:-1]]
        if not cells:
            continue
        # Header row detection
        if cells[0].lower() == "date" and len(cells) > 1 and cells[1].lower() == "handle":
            header = cells
            continue
        # Separator row
        if header and all(re.match(r"^[-: ]+$", c) for c in cells):
            continue
        if header and len(cells) >= len(header):
            row = dict(zip(header, cells))
            row["_line_idx"] = i
            rows.append(row)
    return rows


def extract_thread_url(notes: str) -> str | None:
    """Extract first GitHub issue or discussion URL from a notes string."""
    m = re.search(
        r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
        r"/(?:issues|discussions)/\d+",
        notes,
    )
    return m.group(0) if m else None


def parse_thread_url(url: str) -> dict | None:
    """
    Parse owner / repo / type / number from a GitHub thread URL.
    Returns None if the URL doesn't match.
    """
    m = re.match(
        r"https://github\.com/([^/]+)/([^/]+)/(issues|discussions)/(\d+)",
        url,
    )
    if not m:
        return None
    return {
        "owner":  m.group(1),
        "repo":   m.group(2),
        "type":   "issue" if m.group(3) == "issues" else "discussion",
        "number": int(m.group(4)),
        "url":    url,
    }


# ── Comment fetching ──────────────────────────────────────────────────────────

def fetch_issue_comments(owner: str, repo: str, number: int, since: str) -> list[dict]:
    try:
        raw = gh_rest(f"repos/{owner}/{repo}/issues/{number}/comments")
        return [
            c for c in (raw or [])
            if c.get("created_at", "") > since
            and c.get("user", {}).get("login") not in OWN_LOGINS
        ]
    except Exception as e:
        log(f"  [warn] issue REST failed {owner}/{repo}#{number}: {e}")
        return []


_DISCUSSION_COMMENTS_QUERY = """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    discussion(number: $number) {
      comments(first: 100) {
        nodes {
          author { login }
          body
          createdAt
          url
        }
      }
    }
  }
}
"""


def fetch_discussion_comments(owner: str, repo: str, number: int, since: str) -> list[dict]:
    try:
        data = gh_graphql(
            _DISCUSSION_COMMENTS_QUERY,
            {"owner": owner, "repo": repo, "number": str(number)},
        )
        nodes = (
            data.get("data", {})
                .get("repository", {})
                .get("discussion", {})
                .get("comments", {})
                .get("nodes", [])
        )
        return [
            n for n in nodes
            if n.get("createdAt", "") > since
            and (n.get("author") or {}).get("login") not in OWN_LOGINS
        ]
    except Exception as e:
        log(f"  [warn] discussion GraphQL failed {owner}/{repo}#{number}: {e}")
        return []


# ── CRM update ────────────────────────────────────────────────────────────────

def update_crm_row(line: str, today: str, new_status: str) -> str:
    """
    Given a raw CRM table row string, update the replied and status columns.
    Columns (1-indexed after pipe split):
      8 = replied   (update "-" → today, leave existing dates alone)
      9 = status    (update "sent" → new_status, leave others alone)
    """
    parts = line.split("|")
    if len(parts) < 11:
        return line
    # replied is index 8, status is index 9 (0 = leading empty from split)
    if parts[8].strip() == "-":
        parts[8] = f" {today} "
    if parts[9].strip() == "sent":
        parts[9] = f" {new_status} "
    return "|".join(parts)


def write_crm_updates(path: Path, updates: dict[int, tuple[str, str]]) -> None:
    """
    Apply line-level updates to crm.md.
    updates: {line_index: (today_date, new_status)}
    """
    lines = path.read_text().splitlines(keepends=True)
    for idx, (today, new_status) in updates.items():
        lines[idx] = update_crm_row(lines[idx].rstrip("\n"), today, new_status) + "\n"
    path.write_text("".join(lines))


# ── Formatting ────────────────────────────────────────────────────────────────

def format_comment(c: dict) -> str:
    login = (
        c.get("user", {}).get("login")
        or (c.get("author") or {}).get("login")
        or "unknown"
    )
    ts = (c.get("created_at") or c.get("createdAt") or "")[:10]
    body = (c.get("body") or "").strip().replace("\r\n", "\n")
    preview = body[:500]
    if len(body) > 500:
        preview += "\n  …(truncated)"
    indented = "\n".join("  " + ln for ln in preview.splitlines())
    return f"  @{login} [{ts}]:\n{indented}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check GitHub thread replies for OM World outreach."
    )
    parser.add_argument(
        "--since", metavar="YYYY-MM-DD",
        help="Check comments since this date (default: timestamp of last run)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print report without updating crm.md or saving state",
    )
    args = parser.parse_args()

    since = load_since(args.since)
    today = date.today().isoformat()

    log(f"[check-replies] since={since}  dry_run={args.dry_run}")

    rows = parse_crm(CRM_PATH)
    active = [r for r in rows if r.get("status", "").strip() not in SKIP_STATUSES]
    log(f"[check-replies] {len(active)}/{len(rows)} rows active")

    sections: list[str] = []
    crm_updates: dict[int, tuple[str, str]] = {}

    for row in active:
        handle = row.get("handle", "").strip()
        notes  = row.get("notes", "")
        status = row.get("status", "").strip()
        track  = row.get("track_fit", "").strip()

        url = extract_thread_url(notes)
        if not url:
            log(f"  [skip] {handle}: no thread URL found in notes")
            continue

        thread = parse_thread_url(url)
        if not thread:
            log(f"  [skip] {handle}: could not parse URL: {url}")
            continue

        owner, repo, number = thread["owner"], thread["repo"], thread["number"]
        log(f"  {handle} → {thread['type']} #{number} in {owner}/{repo}")

        if thread["type"] == "issue":
            comments = fetch_issue_comments(owner, repo, number, since)
        else:
            comments = fetch_discussion_comments(owner, repo, number, since)

        if not comments:
            continue

        # Build report section
        header = f"## {handle}  [{track}]  ({len(comments)} new)"
        lines = [header, f"   {url}", ""]
        for c in comments:
            lines.append(format_comment(c))
            lines.append("")
        sections.append("\n".join(lines))

        # Queue CRM update: only escalate "sent" → "engaged"; leave "engaged" alone
        if status == "sent":
            crm_updates[row["_line_idx"]] = (today, "engaged")

    # ── Print report ──────────────────────────────────────────────────────────
    print(f"# OM World reply report — {today}")
    print(f"# Checking comments since: {since[:10]}")
    print(f"# Active threads checked: {len(active)}")
    print()

    if sections:
        print("\n".join(sections))
    else:
        print("No new replies since last check.")

    # ── Write CRM + save state ────────────────────────────────────────────────
    if not args.dry_run:
        if crm_updates:
            write_crm_updates(CRM_PATH, crm_updates)
            log(f"[check-replies] updated {len(crm_updates)} CRM row(s)")
        save_state()
        log(f"[check-replies] state saved → next run checks from now")
    else:
        log("[check-replies] dry-run: no files written")


if __name__ == "__main__":
    main()
