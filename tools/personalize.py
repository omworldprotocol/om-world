#!/usr/bin/env python3
"""
OM World cold-start: per-candidate DM draft.

Given a GitHub username, fetch their public profile and most relevant repos,
then emit a candidate brief + DM scaffold with explicit personalization
placeholders [TBD] that the human sender must fill before sending.

This script intentionally does NOT LLM-generate the final sentence — that
forces the sender to actually look at the candidate's work, which is the
whole point of a non-spammy cold DM.

Usage:
    python3 tools/personalize.py <github-username>

Output: outreach/dm-drafts/YYYY-MM-DD-@{handle}.md  (gitignored)
"""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path


OMW_HOOK = "OM World — a decentralized intent economy protocol where AI executes and crypto verifies"
OMW_URL = "https://omworld.one"
OMW_GITHUB = "https://github.com/omworldprotocol/om-world"
OMW_X = "@OmWorldprotocol"

# Map each protocol primitive to a one-line ASK the DM can request critique on.
PRIMITIVES = {
    "intent-schema": (
        "Intent Schema",
        "what fields should describe a human intent so an AI agent can act on it safely",
        "https://github.com/omworldprotocol/om-world/issues/3",
    ),
    "agent-mandate": (
        "Agent Mandate",
        "how an agent should receive permission to act, spend, and call tools",
        "https://github.com/omworldprotocol/om-world/issues/4",
    ),
    "execution-proof": (
        "Execution Proof",
        "what counts as proof that an agent actually did what it claimed",
        "https://github.com/omworldprotocol/om-world/issues/5",
    ),
    "tool-registry": (
        "Tool Registry",
        "how tools should be published, discovered, and held accountable",
        "https://github.com/omworldprotocol/om-world/issues/6",
    ),
}


def gh(*args):
    r = subprocess.run(["gh"] + list(args), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return json.loads(r.stdout) if r.stdout.strip() else None


def fetch_profile_and_repos(login):
    profile = gh("api", f"users/{login}")
    repos = gh("api",
        f"users/{login}/repos?sort=pushed&direction=desc&per_page=10&type=owner") or []
    repos = [r for r in repos if not r.get("fork")][:6]
    repos.sort(key=lambda r: -r.get("stargazers_count", 0))
    return profile, repos


def render(login, profile, repos):
    primary_repo = repos[0] if repos else None
    out_dir = Path("outreach/dm-drafts")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{date.today().isoformat()}-@{login}.md"

    with open(out_file, "w") as f:
        f.write(f"# DM draft · @{login}\n\n")
        f.write(f"Generated {date.today().isoformat()}.\n\n")

        # Profile
        f.write("## Candidate profile\n\n")
        f.write(f"- **GitHub**: https://github.com/{login}\n")
        if profile.get("name"):
            f.write(f"- **Name**: {profile['name']}\n")
        if profile.get("bio"):
            f.write(f"- **Bio**: {profile['bio']}\n")
        if profile.get("company"):
            f.write(f"- **Company**: {profile['company']}\n")
        if profile.get("location"):
            f.write(f"- **Location**: {profile['location']}\n")
        x = profile.get("twitter_username")
        if x:
            f.write(f"- **X**: https://x.com/{x}\n")
        else:
            f.write("- **X**: ⚠ not listed on GitHub — find via web search before DMing\n")
        if profile.get("blog"):
            f.write(f"- **Web**: {profile['blog']}\n")
        f.write(f"- **Followers**: {profile.get('followers', 0)} · "
                f"**Following**: {profile.get('following', 0)} · "
                f"**Repos**: {profile.get('public_repos', 0)}\n")
        f.write(f"- **Account age**: created {(profile.get('created_at') or '')[:10]}\n\n")

        if repos:
            f.write("### Recent / top repos\n\n")
            for r in repos[:5]:
                topics = r.get("topics") or []
                f.write(f"- [{r['full_name']}]({r['html_url']}) "
                        f"⭐ {r.get('stargazers_count', 0)} · "
                        f"pushed {(r.get('pushed_at') or '')[:10]}\n")
                if r.get("description"):
                    f.write(f"  - {r['description']}\n")
                if topics:
                    f.write(f"  - topics: `{', '.join(topics[:10])}`\n")
            f.write("\n")

        # DM scaffold
        f.write("## DM scaffold — fill `[TBD]` before sending\n\n")
        f.write("Pick the SINGLE OM World primitive most relevant to their work:\n\n")
        for key, (name, _, url) in PRIMITIVES.items():
            f.write(f"- **{name}** — {url}\n")
        f.write("\n```text\n")
        name = (profile.get("name") or "").split()[0] or login
        f.write(f"Hi {name} — \n\n")
        if primary_repo:
            f.write(f"saw your work on {primary_repo['full_name']}. ")
            f.write("[TBD: one specific sentence about what's interesting in their design — "
                    "read the README, do NOT use the GitHub description verbatim]\n\n")
        else:
            f.write("[TBD: open their best repo, read the README, write one specific sentence "
                    "about a design choice that caught your eye]\n\n")
        f.write(f"I'm working on {OMW_HOOK}. We're drafting four core primitives — Intent "
                "Schema, Agent Mandate, Execution Proof, Tool Registry.\n\n")
        f.write("[TBD: name the ONE primitive most relevant to their work in a single sentence, "
                "e.g.: 'The Agent Mandate piece is the closest to what you've been working on with "
                "<their_project>.']\n\n")
        f.write("Would you be willing to give 3 critical comments on the current draft? No "
                "commitment beyond that — I'm specifically looking for sharp critique from "
                "people who've actually built in this space.\n\n")
        f.write(f"Site: {OMW_URL}\n")
        f.write(f"GitHub: {OMW_GITHUB}\n")
        f.write("```\n\n")

        # Checklist
        f.write("## Pre-send checklist\n\n")
        f.write("- [ ] Opened their top repo, read README, filled `[TBD: specific sentence]`\n")
        f.write("- [ ] Picked THE ONE primitive most relevant and filled `[TBD: primitive sentence]`\n")
        f.write("- [ ] Confirmed they have an X account "
                f"(profile.twitter_username = `{x or '(empty — search manually)'}`)\n")
        f.write("- [ ] Voice check: no hype, no token language, no 'we're revolutionizing'\n")
        f.write("- [ ] Length check: 4–6 short sentences max, no walls of text\n")
        f.write("- [ ] After sending, append to `outreach/crm.md`:\n\n")
        x_for_crm = f"@{x}" if x else f"@{login}(no-x)"
        f.write("```\n")
        f.write(f"| {date.today().isoformat()} | {x_for_crm} | github | {login} "
                "| TBD | TBD | yes | - | sent | - |\n")
        f.write("```\n")

    return out_file


def main():
    if len(sys.argv) != 2:
        print("Usage: personalize.py <github-username>", file=sys.stderr)
        sys.exit(1)
    login = sys.argv[1].lstrip("@")
    profile, repos = fetch_profile_and_repos(login)
    if not profile:
        print(f"User {login} not found", file=sys.stderr)
        sys.exit(2)
    out = render(login, profile, repos)
    print(out)


if __name__ == "__main__":
    main()
