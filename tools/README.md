# tools/

Cold-start outreach automation. Each script outputs to `outreach/` (which is
gitignored — contains real candidate names, DM drafts, CRM data).

## Pipeline

```
scout-github.py        →  outreach/targets/YYYY-MM-DD.md      (top 20 candidates)
       │
       └──> human picks 5 by hand
              │
              ▼
personalize.py <login> →  outreach/dm-drafts/YYYY-MM-DD-@<h>.md  (DM scaffold)
              │
              └──> human fills `[TBD]` slots based on candidate profile
                     │
                     ▼
              human sends via X DM (or GitHub mention if no X)
                     │
                     └──> append to outreach/crm.md
```

## Scripts

### `scout-github.py`

Searches GitHub for users who recently pushed to repos tagged with OM World–
relevant topics (AI agents, account abstraction, MCP, ZK, intent protocols),
scores their relevance, and emits a daily ranked candidate list.

```bash
python3 tools/scout-github.py
python3 tools/scout-github.py --limit 30 --recent-days 45
```

Configure `TRACK_TOPICS` at the top of the script to add/remove search axes.

Relevance score = `10·tracks_hit + 5·repos_hit + stars_top5`. Higher means more
cross-cutting plus more proven track record.

Output: `outreach/targets/YYYY-MM-DD.md`.

### `personalize.py`

Given a GitHub username, fetches their profile + top repos and emits a DM
scaffold with explicit `[TBD]` slots. The script does **not** LLM-generate the
final personalized sentence — that's deliberate. The human sender must read at
least one of the candidate's READMEs and write a specific observation. This
keeps the DM from being spam.

```bash
python3 tools/personalize.py <github-username>
python3 tools/personalize.py vitalik
```

Output: `outreach/dm-drafts/YYYY-MM-DD-@<handle>.md`.

### `check-replies.py`

Daily reply monitor for outreach threads already logged in `outreach/crm.md`.

```bash
python3 tools/check-replies.py              # since last run
python3 tools/check-replies.py --since 2026-05-14
python3 tools/check-replies.py --dry-run    # report only, no CRM write
```

**Coverage — designed so no reply is missed:**

1. Every GitHub issue / PR / discussion URL found in each active CRM row's
   notes (all of them, not just the first — a row may reference side-threads).
2. A full sweep of `omworldprotocol/om-world`'s own issues, pull requests,
   and discussions, so co-builder replies on our own repo (welcome threads,
   Genesis Review Sprint issues, integration proposals) are never missed.
3. Discussion threads are read with their nested replies, not just top-level
   comments.
4. State-change events on every checked thread — a silently merged PR, a
   silently closed or reopened issue — read from the GitHub timeline, not
   just comments. A maintainer acting on our thread without writing a word
   is reported, flagged `⚠ STATE CHANGE`. (Reported but never auto-escalates
   a row — a silent close is not a stated opinion. For a PR to be tracked
   here, its full `https://github.com/.../pull/N` URL must be in the row's
   notes.)

**Which rows are checked:** every row *except* `bounce` (explicit
not-interested — outreach stopped). `committed`, `engaged`, `silent` and
`sent` rows are all checked — a committed co-builder's ongoing reply and a
silent contact's late re-engagement both matter.

**Dedup guarantee:** each distinct thread is fetched and reported at most once
per run (a run-wide set covers both the per-row pass and the own-repo sweep).
Across runs the `since` timestamp advances, so a comment is reported in exactly
one run. `since` is saved as the run's *start* time, so a comment landing
mid-run is re-checked next run rather than missed.

**Status escalation:** a `sent` or `silent` row escalates to `engaged` only
when a new comment comes from a commenter affiliated with that repo
(`author_association` of OWNER / MEMBER / COLLABORATOR / CONTRIBUTOR — the
maintainer / outreach target). Comments from unaffiliated accounts (drive-by
commenters, vendors pitching services) are still reported but flagged
`⚠ unaffiliated` and do **not** escalate the row. `engaged` and `committed`
rows are reported on new activity but never auto-change status.

om-world sweep threads not referenced by any CRM row are report-only — they
need manual triage, since they cannot be auto-mapped to a row.

**Known bounds:** discussion comments + nested replies are read 100-at-a-time
(no pagination); inline PR *review* comments are not read (PR conversation
comments are). Neither matters at current thread sizes.

State (last-run timestamp) is kept in `outreach/.check-replies-state.json`.

## Dependencies

- `gh` CLI authenticated (no extra Python packages)
- Python 3.10+

## Operational notes

- `outreach/` is gitignored. Do not push real candidate data to GitHub.
- Run `scout-github.py` once a day (manually or via cron). It hits ~25 GitHub
  search calls + ~50–200 user calls; well under the 5000/hour authenticated
  rate limit.
- Daily DM cadence: 5–7 for the first 2 weeks, ramp to 10/day only after
  reply rate is established at ≥ 5%. Verified X accounts get higher DM
  ceilings (~100/day) but speed kills personalization.
- Do not send the DM scaffold without filling every `[TBD]`. That's the
  whole point of this workflow.
