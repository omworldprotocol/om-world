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
