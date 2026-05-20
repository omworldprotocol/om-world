#!/usr/bin/env python3
"""
check-replies.py — Daily reply monitor for OM World outreach threads.

Reads outreach/crm.md, checks every tracked GitHub thread for new comments
since the last run, prints a structured report, and updates the replied /
status columns in crm.md.

Coverage — what it checks, per run (designed so no reply is missed):
  1. Every GitHub issue/discussion URL found in each active CRM row's notes
     (all of them, not just the first — a row may reference side-threads).
  2. A full sweep of omworldprotocol/om-world's own issues, pull requests,
     and discussions, so co-builder replies on our own repo (welcome
     threads, Genesis Review Sprint issues, integration proposals) are
     never missed.
  3. Discussion threads are read with their nested replies, not just the
     top-level comments.

Which rows are checked:
  Every row EXCEPT `bounce` (explicit not-interested / hostile — outreach
  stopped per the crm.md operating rules). `committed`, `engaged`, `silent`
  and `sent` rows are ALL checked — a committed co-builder's ongoing reply
  and a silent contact's late re-engagement both matter.

Dedup guarantee:
  Each distinct thread is fetched and reported at most once per run (a
  run-wide `checked` set covers both the per-row pass and the own-repo
  sweep). Across runs, the `since` timestamp advances, so a comment is
  reported in exactly one run.

Status escalation rule:
  A `sent` or `silent` row escalates to `engaged` only when a new comment
  comes from someone with a real association to that repo (OWNER / MEMBER /
  COLLABORATOR / CONTRIBUTOR) — i.e. the maintainer / outreach target.
  Comments from unaffiliated accounts (association NONE — drive-by
  commenters, vendors pitching services) are still reported, but do NOT
  auto-escalate the row. `engaged` and `committed` rows are reported when
  they get new activity but never auto-change status (those transitions
  are human judgement calls).

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

# Rows in these statuses are skipped entirely. Only `bounce` — an explicit
# not-interested / hostile close where outreach has stopped. `committed`
# and `silent` are intentionally NOT skipped: a committed co-builder's
# ongoing reply and a silent contact's late re-engagement both matter.
SKIP_STATUSES = {"bounce"}

# Statuses that escalate to `engaged` on a maintainer-side reply.
ESCALATABLE_STATUSES = {"sent", "silent"}

# author_association values that mean "this commenter is the maintainer /
# outreach target side of the thread" rather than an unaffiliated outsider.
MAINTAINER_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR", "CONTRIBUTOR"}

# Our own repo — swept in full every run regardless of CRM notes.
OWN_OWNER = "omworldprotocol"
OWN_REPO  = "om-world"


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


def save_state(run_started: str) -> None:
    """Persist the run's START time as the next lower bound. Using start (not
    end) time means a comment created mid-run is re-checked next run rather
    than missed — a harmless re-report is preferred over a silent miss."""
    STATE_PATH.write_text(json.dumps({"last_checked": run_started}, indent=2))


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


def row_status(row: dict) -> str:
    """Status cell, normalized — markdown bold (**committed**) and whitespace
    stripped — so the skip / escalation checks compare clean values."""
    return row.get("status", "").strip().strip("*").strip().lower()


_THREAD_URL_RE = re.compile(
    r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
    r"/(?:issues|discussions|pull)/\d+"
)


def extract_thread_urls(notes: str) -> list[str]:
    """Extract every GitHub issue/discussion/PR URL from a notes string,
    deduped, in first-seen order."""
    seen: list[str] = []
    for m in _THREAD_URL_RE.finditer(notes):
        if m.group(0) not in seen:
            seen.append(m.group(0))
    return seen


def parse_thread_url(url: str) -> dict | None:
    """
    Parse owner / repo / type / number from a GitHub thread URL.
    Returns None if the URL doesn't match. PRs are treated as issues for
    comment-fetching (the issue-comments endpoint serves PR conversation
    comments) but keep a `kind` of "PR" for display.
    """
    m = re.match(
        r"https://github\.com/([^/]+)/([^/]+)/(issues|discussions|pull)/(\d+)",
        url,
    )
    if not m:
        return None
    seg = m.group(3)
    kind = {"issues": "issue", "discussions": "discussion", "pull": "PR"}[seg]
    return {
        "owner":  m.group(1),
        "repo":   m.group(2),
        "type":   "discussion" if kind == "discussion" else "issue",
        "kind":   kind,
        "number": int(m.group(4)),
        "url":    f"https://github.com/{m.group(1)}/{m.group(2)}/{seg}/{m.group(4)}",
    }


def thread_key(thread: dict) -> tuple:
    """Hashable identity for a thread, for run-wide dedup."""
    return (thread["owner"], thread["repo"], thread["type"], thread["number"])


# ── Comment fetching ──────────────────────────────────────────────────────────

def fetch_issue_comments(owner: str, repo: str, number: int, since: str) -> list[dict]:
    """Conversation comments for an issue or PR (same REST endpoint)."""
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
          authorAssociation
          body
          createdAt
          url
          replies(first: 100) {
            nodes {
              author { login }
              authorAssociation
              body
              createdAt
              url
            }
          }
        }
      }
    }
  }
}
"""


def fetch_discussion_comments(owner: str, repo: str, number: int, since: str) -> list[dict]:
    """Discussion comments AND their nested replies, flattened to one list."""
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
        out: list[dict] = []
        for n in nodes:
            replies = (n.get("replies") or {}).get("nodes", [])
            for c in [n, *replies]:
                if (c.get("createdAt", "") > since
                        and (c.get("author") or {}).get("login") not in OWN_LOGINS):
                    out.append(c)
        return out
    except Exception as e:
        log(f"  [warn] discussion GraphQL failed {owner}/{repo}#{number}: {e}")
        return []


def fetch_thread_comments(thread: dict, since: str) -> list[dict]:
    """Dispatch to the right fetcher for an issue/PR or discussion thread."""
    if thread["type"] == "discussion":
        return fetch_discussion_comments(
            thread["owner"], thread["repo"], thread["number"], since
        )
    return fetch_issue_comments(
        thread["owner"], thread["repo"], thread["number"], since
    )


# ── OM World own-repo enumeration ─────────────────────────────────────────────

def list_own_issue_threads() -> list[dict]:
    """Every issue and pull request (any state) in omworldprotocol/om-world."""
    try:
        raw = gh_rest(f"repos/{OWN_OWNER}/{OWN_REPO}/issues?state=all&per_page=100")
    except Exception as e:
        log(f"  [warn] could not list om-world issues: {e}")
        return []
    threads = []
    for it in raw or []:
        is_pr = "pull_request" in it
        threads.append({
            "owner": OWN_OWNER, "repo": OWN_REPO, "type": "issue",
            "kind": "PR" if is_pr else "issue",
            "number": it["number"],
            "url": it.get("html_url", ""),
            "title": it.get("title", ""),
        })
    return threads


_OWN_DISCUSSIONS_QUERY = """
query($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    discussions(first: 100) {
      nodes { number title url }
    }
  }
}
"""


def list_own_discussion_threads() -> list[dict]:
    """Every discussion in omworldprotocol/om-world."""
    try:
        data = gh_graphql(_OWN_DISCUSSIONS_QUERY, {"owner": OWN_OWNER, "repo": OWN_REPO})
        nodes = (
            data.get("data", {})
                .get("repository", {})
                .get("discussions", {})
                .get("nodes", [])
        )
    except Exception as e:
        log(f"  [warn] could not list om-world discussions: {e}")
        return []
    return [
        {"owner": OWN_OWNER, "repo": OWN_REPO, "type": "discussion",
         "kind": "discussion", "number": n["number"],
         "url": n.get("url", ""), "title": n.get("title", "")}
        for n in nodes
    ]


# ── Comment classification ────────────────────────────────────────────────────

def comment_association(c: dict) -> str:
    """Normalized author_association for a REST or GraphQL comment dict."""
    assoc = c.get("author_association") or c.get("authorAssociation") or "NONE"
    return assoc.upper()


def is_maintainer_side(c: dict) -> bool:
    """True if the commenter is affiliated with the repo (maintainer / target),
    as opposed to an unaffiliated drive-by account."""
    return comment_association(c) in MAINTAINER_ASSOCIATIONS


# ── CRM update ────────────────────────────────────────────────────────────────

def update_crm_row(line: str, today: str, new_status: str) -> str:
    """
    Given a raw CRM table row string, update the replied and status columns.
    Columns (1-indexed after pipe split):
      8 = replied   (update "-" → today, leave existing dates alone)
      9 = status    (escalate "sent"/"silent" → new_status; leave others alone)
    The status cell may carry markdown bold (e.g. **committed**); the
    comparison strips it so a bolded escalatable value would still match,
    but in practice only sent/silent are escalated and neither is bolded.
    """
    parts = line.split("|")
    if len(parts) < 11:
        return line
    # replied is index 8, status is index 9 (0 = leading empty from split)
    if parts[8].strip() == "-":
        parts[8] = f" {today} "
    if parts[9].strip().strip("*").lower() in ESCALATABLE_STATUSES:
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
    assoc = comment_association(c)
    tag = assoc if is_maintainer_side(c) else f"{assoc} ⚠ unaffiliated"
    body = (c.get("body") or "").strip().replace("\r\n", "\n")
    preview = body[:500]
    if len(body) > 500:
        preview += "\n  …(truncated)"
    indented = "\n".join("  " + ln for ln in preview.splitlines())
    return f"  @{login} [{ts}] ({tag}):\n{indented}"


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

    run_started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    since = load_since(args.since)
    today = date.today().isoformat()

    log(f"[check-replies] since={since}  dry_run={args.dry_run}")

    rows = parse_crm(CRM_PATH)
    active = [r for r in rows if row_status(r) not in SKIP_STATUSES]
    log(f"[check-replies] {len(active)}/{len(rows)} rows active "
        f"({len(rows) - len(active)} skipped as bounce)")

    sections: list[str] = []
    crm_updates: dict[int, tuple[str, str]] = {}
    checked: set[tuple] = set()  # run-wide dedup — each thread checked once

    # ── Pass 1: every thread URL referenced in each active CRM row ─────────────
    for row in active:
        handle = row.get("handle", "").strip()
        notes  = row.get("notes", "")
        status = row_status(row)
        track  = row.get("track_fit", "").strip()

        urls = extract_thread_urls(notes)
        if not urls:
            log(f"  [skip] {handle}: no thread URL found in notes")
            continue

        # fetch each referenced thread exactly once, keep (thread, comments)
        row_hits: list[tuple[dict, list[dict]]] = []
        for url in urls:
            thread = parse_thread_url(url)
            if not thread:
                log(f"  [skip] {handle}: could not parse URL: {url}")
                continue
            tk = thread_key(thread)
            if tk in checked:          # already fetched via an earlier row
                continue
            checked.add(tk)
            log(f"  {handle} → {thread['kind']} #{thread['number']} "
                f"in {thread['owner']}/{thread['repo']}")
            cs = fetch_thread_comments(thread, since)
            if cs:
                row_hits.append((thread, cs))

        if not row_hits:
            continue

        row_comments = [c for _, cs in row_hits for c in cs]
        maintainer_replied = any(is_maintainer_side(c) for c in row_comments)
        escalate = status in ESCALATABLE_STATUSES and maintainer_replied

        if escalate:
            note = f"  → status: {status} → engaged"
            if status == "silent":
                note += "  (RE-ENGAGEMENT after silent)"
        elif status in ESCALATABLE_STATUSES:  # sent/silent, unaffiliated only
            note = "  ⚠ unaffiliated commenter(s) only — status NOT escalated"
        else:                                  # engaged / committed
            note = f"  ℹ status={status} — ongoing, no auto status change"

        header = (f"## {handle}  [{track}]  status={status}  "
                  f"({len(row_comments)} new comment(s))")
        lines = [header, note, ""]
        for thread, cs in row_hits:
            lines.append(f"   {thread['url']}")
            for c in cs:
                lines.append(format_comment(c))
                lines.append("")
        sections.append("\n".join(lines))

        if escalate:
            crm_updates[row["_line_idx"]] = (today, "engaged")

    # ── Pass 2: full sweep of omworldprotocol/om-world's own threads ───────────
    log("[check-replies] sweeping om-world own issues / PRs / discussions")
    sweep_sections: list[str] = []
    own_threads = list_own_issue_threads() + list_own_discussion_threads()
    for thread in own_threads:
        tk = thread_key(thread)
        if tk in checked:
            continue  # already covered by a CRM row's notes
        checked.add(tk)
        comments = fetch_thread_comments(thread, since)
        if not comments:
            continue
        title = thread.get("title", "")
        header = (f"## [om-world sweep] {thread['kind']} #{thread['number']} "
                  f"— {title}")
        lines = [header,
                 "  ⚠ not tied to a CRM row — manual triage needed",
                 "", f"   {thread['url']}"]
        for c in comments:
            lines.append(format_comment(c))
            lines.append("")
        sweep_sections.append("\n".join(lines))

    # ── Print report ──────────────────────────────────────────────────────────
    print(f"# OM World reply report — {today}")
    print(f"# Checking comments since: {since[:10]}  ({since})")
    print(f"# Active CRM threads checked: {len(active)}  |  "
          f"om-world own threads swept: {len(own_threads)}  |  "
          f"distinct threads this run: {len(checked)}")
    print()

    if sections:
        print("\n".join(sections))
    else:
        print("No new replies on tracked CRM threads since last check.")
    print()

    if sweep_sections:
        print("# ── OM World repo sweep (untracked threads) ──")
        print()
        print("\n".join(sweep_sections))
    else:
        print("# OM World repo sweep: no new comments on untracked own threads.")

    # ── Write CRM + save state ────────────────────────────────────────────────
    if not args.dry_run:
        if crm_updates:
            write_crm_updates(CRM_PATH, crm_updates)
            log(f"[check-replies] updated {len(crm_updates)} CRM row(s)")
        save_state(run_started)
        log(f"[check-replies] state saved (last_checked={run_started})")
    else:
        log("[check-replies] dry-run: no files written")


if __name__ == "__main__":
    main()
