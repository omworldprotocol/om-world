#!/usr/bin/env python3
"""
OM World cold-start: GitHub-based candidate discovery.

Searches GitHub for recently-active developers working on topics relevant to
OM World (AI agents, account abstraction, MCP, verifiable AI, intent
protocols), scores each candidate's relevance, and emits a ranked daily
markdown report.

Usage:
    python3 tools/scout-github.py
    python3 tools/scout-github.py --limit 30 --recent-days 45

Output: outreach/targets/YYYY-MM-DD.md  (gitignored)

Dependencies: gh CLI authenticated (no extra Python packages).
"""

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

# unbuffered stderr so progress shows immediately
def log(msg):
    print(msg, file=sys.stderr, flush=True)

# Topics keyed by which OM World primitive/track they map to.
# Add/remove freely — these are the search axes.
TRACK_TOPICS = {
    "intent-schema": [
        "intent-protocol", "intent-engine", "intent-router",
        "intent-resolver", "agentic-commerce",
    ],
    "agent-mandate": [
        "ai-agent", "langgraph", "autogen", "crewai", "mcp-server",
        "mcp-client", "autonomous-agent", "agent-framework",
    ],
    "execution-proof": [
        "zk-proof", "attestation", "verifiable-inference", "zkml",
        "oracle-protocol", "trusted-execution",
    ],
    "tool-registry": [
        "mcp-tools", "agent-tools", "tool-protocol", "function-calling",
    ],
    "ai-x-crypto": [
        "ai-crypto", "onchain-agent", "agentic-wallet", "smart-account",
        "account-abstraction", "erc-4337", "erc-7579", "safe-account",
    ],
}

DEFAULT_RECENT_DAYS = 60
DEFAULT_LIMIT = 20


def gh(*args, timeout=30, retries=3):
    """Run gh CLI with per-call timeout + retries on transient failures."""
    last_err = None
    for attempt in range(retries):
        try:
            r = subprocess.run(
                ["gh"] + list(args),
                capture_output=True, text=True, timeout=timeout,
            )
            if r.returncode != 0:
                # 422 / 404 / etc. are real errors; don't retry
                if "rate limit" in r.stderr.lower() or "timeout" in r.stderr.lower():
                    last_err = r.stderr.strip()
                    import time as _t; _t.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"gh failed: {' '.join(args)}\n{r.stderr.strip()}")
            return json.loads(r.stdout) if r.stdout.strip() else None
        except subprocess.TimeoutExpired:
            last_err = f"timeout after {timeout}s"
            continue
    raise RuntimeError(f"gh exhausted retries: {' '.join(args)}\n{last_err}")


def search_repos(topic, recent_cutoff, per_page=30):
    # GitHub topics use hyphens but the query needs URL-encoded spaces in "pushed:>" clause
    query = f"topic:{topic}+pushed:>{recent_cutoff}"
    try:
        items = gh(
            "api",
            f"search/repositories?q={query}&sort=updated&per_page={per_page}",
            "--jq", ".items",
        )
        return items or []
    except RuntimeError as e:
        log(f"  [warn] search failed for topic:{topic} — {str(e)[:120]}")
        return []


def get_user(login):
    try:
        return gh("api", f"users/{login}")
    except RuntimeError:
        return None


def is_likely_bot(login, profile):
    if login.endswith("[bot]") or login.endswith("-bot"):
        return True
    bio = (profile.get("bio") or "").lower()
    return any(s in bio for s in ["bot account", "automated", "🤖"])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    p.add_argument("--out", default="outreach/targets")
    p.add_argument("--recent-days", type=int, default=DEFAULT_RECENT_DAYS)
    p.add_argument("--min-followers", type=int, default=3)
    args = p.parse_args()

    recent_cutoff = (date.today() - timedelta(days=args.recent_days)).isoformat()

    candidates = defaultdict(
        lambda: {"tracks": set(), "topics": set(), "repos": []}
    )

    total_topics = sum(len(v) for v in TRACK_TOPICS.values())
    log(f"[scout] scanning {total_topics} topics, "
        f"recent window {args.recent_days}d (since {recent_cutoff})")

    for track, topics in TRACK_TOPICS.items():
        for topic in topics:
            repos = search_repos(topic, recent_cutoff)
            log(f"  [{track}] topic:{topic:30s} → {len(repos)} repos")
            for repo in repos:
                owner = repo.get("owner") or {}
                if owner.get("type") != "User":
                    continue
                login = owner.get("login")
                if not login:
                    continue
                c = candidates[login]
                c["tracks"].add(track)
                c["topics"].add(topic)
                c["repos"].append({
                    "name": repo["full_name"],
                    "description": repo.get("description") or "",
                    "stars": repo.get("stargazers_count", 0),
                    "pushed_at": repo.get("pushed_at", ""),
                    "url": repo["html_url"],
                })

    log(f"[scout] {len(candidates)} unique users, fetching profiles in parallel...")

    # Parallel profile fetch (~10× speedup)
    profiles = {}
    done = [0]
    def fetch(login):
        return login, get_user(login)
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(fetch, login) for login in candidates.keys()]
        for f in as_completed(futures):
            login, profile = f.result()
            profiles[login] = profile
            done[0] += 1
            if done[0] % 25 == 0:
                log(f"  fetched {done[0]}/{len(candidates)}")

    log(f"[scout] enriching + scoring {len(profiles)} profiles")
    enriched = []
    for login, data in candidates.items():
        profile = profiles.get(login)
        if not profile:
            continue
        if profile.get("type") != "User":
            continue
        if is_likely_bot(login, profile):
            continue
        if profile.get("followers", 0) < args.min_followers:
            continue

        # Dedup repos by name (a repo can show up via multiple topics)
        seen = set()
        deduped_repos = []
        for r in data["repos"]:
            if r["name"] in seen:
                continue
            seen.add(r["name"])
            deduped_repos.append(r)
        deduped_repos.sort(key=lambda r: -r["stars"])

        score = (
            len(data["tracks"]) * 10
            + min(len(deduped_repos), 5) * 5
            + sum(r["stars"] for r in deduped_repos[:5])
        )

        enriched.append({
            "login": login,
            "name": profile.get("name"),
            "bio": profile.get("bio"),
            "company": profile.get("company"),
            "location": profile.get("location"),
            "blog": profile.get("blog"),
            "twitter": profile.get("twitter_username"),
            "followers": profile.get("followers", 0),
            "public_repos": profile.get("public_repos", 0),
            "tracks": sorted(data["tracks"]),
            "topics_matched": sorted(data["topics"]),
            "relevant_repos": deduped_repos[:3],
            "score": score,
        })

    enriched.sort(key=lambda c: -c["score"])
    top = enriched[: args.limit]

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{date.today().isoformat()}.md"

    with open(out_file, "w") as f:
        f.write(f"# Candidates — {date.today().isoformat()}\n\n")
        f.write(
            f"Scanned {total_topics} GitHub topics, recent window "
            f"{args.recent_days}d (≥ {recent_cutoff}). "
            f"{len(enriched)} viable candidates after dedup + filters, "
            f"showing top {len(top)}.\n\n"
        )
        f.write("Score = 10·tracks_hit + 5·repos_hit + stars_top5. "
                "Higher = more cross-cutting + more proven.\n\n---\n\n")

        for i, c in enumerate(top, 1):
            f.write(f"## #{i} · @{c['login']} · score {c['score']}\n\n")
            if c["name"]:
                f.write(f"- **Name**: {c['name']}\n")
            if c["bio"]:
                f.write(f"- **Bio**: {c['bio']}\n")
            if c["company"]:
                f.write(f"- **Company**: {c['company']}\n")
            if c["location"]:
                f.write(f"- **Location**: {c['location']}\n")
            if c["twitter"]:
                f.write(f"- **X**: [@{c['twitter']}](https://x.com/{c['twitter']})\n")
            else:
                f.write(f"- **X**: (not listed on GitHub profile — search manually)\n")
            if c["blog"]:
                f.write(f"- **Web**: {c['blog']}\n")
            f.write(
                f"- **GitHub stats**: {c['followers']} followers · "
                f"{c['public_repos']} repos\n"
            )
            f.write(f"- **Tracks fit**: {', '.join(c['tracks'])}\n")
            f.write(f"- **Topics matched**: `{', '.join(c['topics_matched'])}`\n")
            f.write(f"- **Profile**: https://github.com/{c['login']}\n\n")
            f.write("**Top relevant repos**:\n")
            for r in c["relevant_repos"]:
                desc = r["description"][:100] if r["description"] else "(no description)"
                f.write(f"- [{r['name']}]({r['url']}) ⭐ {r['stars']} — {desc}\n")
            f.write(f"\n**Next**: `python3 tools/personalize.py {c['login']}`\n\n---\n\n")

    log(f"[scout] wrote {out_file} ({len(top)} of {len(enriched)} viable candidates)")
    print(str(out_file))


if __name__ == "__main__":
    main()
