# OMW · Agent Execution Guide (形态 A — agent-led sessions)

> **Audience**: Claude Code / GPT / any LLM agent that drives a long-running
> task (DeFi audit, content creation, etc) **inside a chat window** with
> founder-in-the-loop. This is the **default** OMW usage mode.
>
> Not for cron / one-shot batch — that's `omw run <pack>` (CLI mode, see
> PATTERN_SCHEMA.md §五).

## Why you (the agent) should care

OMW Pattern Library is the founder's accumulated playbook for "how to do X
correctly". If you ignore OMW and freestyle, you reinvent + bypass guardrails
that already caught real bugs. If you call OMW, you:

1. **Get the rulebook** for the task type (e.g. all the anti-patterns for
   DeFi audit that founder already learned the hard way).
2. **Verify your output** against rules BEFORE founder sees it (cheap LLM
   check, fewer wasted rounds).
3. **Contribute to the flywheel**: every check/judge call you make produces
   fine-grained event data → aggregator → Pattern metrics → future Pattern
   evolution.

Without you calling OMW, the Pattern library is dead documentation.

## When you should open a Session

At the **start of any task that maps to a Pack** (defi audit / X content
creation / video pipeline / sovereign-X pipeline). Look at the founder's
opening message:

| Founder says | Open session with |
|---|---|
| "审计 X 协议" / "audit X protocol" | `pack-defi-audit-<category>` (CDP / lending / yield-vault / algo-stable) |
| "为 invaribreak 写一条推" | `pack-sovereign-x-full` |
| "为 OmWorldprotocol 写一条推" | `pack-om-world-x-full` |
| "做一个抖音视频" / "AVA-trend 视频" | `pack-ava-trend-content-creation` |

If unclear which pack, `omw search` (or `omw.search()` SDK call) by domain
keyword first.

## How — the canonical agent flow

```python
from sdk import OMW

omw = OMW()
# (env: OMW_BACKEND=server + OMW_SERVER_URL + OMW_API_TOKEN already set)

with omw.session(
    pack_id="pack-defi-audit-cdp",
    intent={"protocol_slug": "sky-money", "category": "CDP",
            "target_contracts": ["0x...", "0x..."]},
) as sess:

    # 1. Load the pack's body — this is YOUR rulebook for this session.
    #    Read every pattern's Rules / Heuristics / Anti-Pattern / Hard-Forbidden.
    #    Internalize before doing any work.
    pack = omw.load_pack("pack-defi-audit-cdp")
    for p in pack.patterns:
        rules = p.body_sections.get("Rules", "")
        anti  = p.body_sections.get("Anti-Pattern", "") or p.body_sections.get("Negative", "")
        # ... read these as your in-context guidance ...

    # 2. At each significant decision, sanity-check with omw.
    #
    # Example: you found a candidate vulnerability. Before you mark it as a real
    # finding, ask OMW whether it passes the honest-0 discipline:
    finding_text = open("docs/sky-money/poc/finding-1.md").read()
    v = sess.check("meta-honest-0-discipline", subject=finding_text)
    if v.hard_violations:
        # founder told you not to claim hygiene-only as success. Don't.
        rework_or_drop(finding_text, reasons=v.hard_violations)
    elif v.warnings:
        log_caveats(v.warnings)

    # 3. At end of major artifact, judge it.
    audit_report = open("docs/sky-money/audit-report.md").read()
    score = sess.judge("pack-defi-audit-cdp", subject=audit_report)
    # score.score ∈ [0, 1]; score.improvements is a list of LLM-suggested fixes.
    if score.score < 0.7:
        # iterate, address improvements, re-judge.
        ...

    # 4. ANY ad-hoc decision you want tracked as a Pattern invocation:
    with sess.invoke("playbook-cdp",
                     context={"edge_id": "L-3 redeem invariant"},
                     step_kind="manual_edge_eval") as inv:
        # ... agent reasoning + tool calls ...
        inv.record_outcome(success=True, metrics={"edge_covered": True})

    # 5. At task end — explicit outcome.
    sess.record_outcome(
        success=True,
        metrics={"findings_count": 5, "honest_0_rate": "5/5", "stage_reached": "S5"},
        notes="alto-style audit, all findings core-target-level",
    )
```

## Rules of engagement (hard)

1. **Always open a Session at task start.** Bare `omw.check()` / `omw.judge()`
   without a session work but lose the parent_invocation_id chain — the
   aggregator can't roll them up as a single audit/session.

2. **Don't fake outcomes.** If the audit failed / you dropped findings /
   the protocol is uninteresting, call `record_outcome(success=False, ...)`.
   Fake `success=True` poisons future success_rate metrics and breaks the
   flywheel for everyone.

3. **Call check() BEFORE committing to a path, not after.** Pre-emptive LLM
   guard catches problems while they're cheap. Post-hoc is just damage report.

4. **Subject can be: a string, a file path (auto-read), or {"file": path} /
   {"data": dict}.** Pick the form that gives OMW the smallest readable
   subject. Don't pass 50K tokens of raw RPC dump.

5. **Cost awareness.** Each `check()` / `judge()` = 1 LLM call (~10s, openclaw
   gpt-5.5 by default). Use them at *meaningful* decisions, not every line of
   code. Rough budget: ~5-15 check/judge per audit session, not 200.

6. **Hard-forbidden violations should BLOCK you** — back out, don't proceed.
   Anti-Pattern / Negative violations should make you slow down + log. Warns
   = note but proceed.

## When founder is "stuck" — gap signal

If you find yourself thinking "OMW Pattern doesn't cover this case" or
"there's no rule that tells me what to do here" — that's a **gap signal**.
Don't silently improvise. Tell founder:

> "I'm at decision X. Existing patterns [Y, Z] don't cover this. I'll proceed
> with [my best judgment] but flag this as a pattern gap. Want me to draft a
> new Pattern stub for your review after this task?"

Then in your `record_outcome`, include `metrics={"gap_signals": ["case X"]}`.
Aggregator will surface this for founder weekly review.

## Backends — you DON'T need to think about this (P1.6 architecture)

Default architecture (since v0.3.2):

- **Agent calls always use LocalBackend.** Zero setup. No SSH tunnel.
  Never fails on network. Just `omw = OMW()` works.
- **Background launchd job `world.omworld.outbox-push` runs every 5 min**.
  It auto-opens an SSH tunnel, drains `runtime/_outbox.jsonl`, POSTs every
  event to OMW server, closes tunnel. Server-side aggregation + frontmatter
  metrics stay current automatically.
- **You** (agent) never need to set `OMW_BACKEND` or open a tunnel. If env
  vars are set, they're consumed by `push_outbox.py`, not by your session.

Sanity check anytime:
```bash
python3 -m sdk doctor          # exits 0 with healthy report
```

If you see "outbox queue: 200+ pending events", it means push_outbox hasn't
run recently — check `launchctl list | grep outbox-push`. Founder's problem,
not yours; your events are still safe in the outbox.

## Cheat sheet — the 4 calls you'll actually use

```python
# 1. start a session
sess = omw.session(pack_id="pack-X", intent={...}).__enter__()

# 2. read pack body for rules
pack = omw.load_pack("pack-X")
# … internalize pack.patterns[*].body_sections{Rules, Anti-Pattern, ...}

# 3. checkpoint a decision
verdict = sess.check("pattern-id", subject="my draft text")
# verdict.passed (bool) / .hard_violations / .warnings

# 4. final score
score = sess.judge("pack-X", subject="final artifact path or text")
# score.score ∈ [0,1] / .improvements

# 5. close
sess.record_outcome(success=True, metrics={...})
sess.__exit__(None, None, None)   # or use `with` block
```

## Audit-flow special case (defi-auto-audit)

audit_run.py is the **stage-gate state machine**. You (agent) drive the
artifact production for each stage; audit_run.py decides whether to advance.
OMW Session wraps the whole audit:

```
sess = omw.session(pack_id="pack-defi-audit-<category>",
                   intent={"protocol_slug": "sky-money"})

for stage in S0..S5:
    # produce artifacts for current stage (read source, write PoC, etc)
    # ...
    sess.check("meta-honest-0-discipline", subject=current_artifact)
    sess.check("meta-core-target-5dim",    subject=current_artifact)
    # run adversarial verifier (independent agent — separate session)
    # call audit_run.py gate
    subprocess.run(["python", "tools/audit_run.py", "gate", "docs/sky-money/"])

sess.judge("pack-defi-audit-<category>", subject="docs/sky-money/audit-report.md")
sess.record_outcome(success=..., metrics={...})
```

The audit_run.py gate is a tool, NOT the orchestrator. Session is the spine.

## Found a bug in this guide?

Either fix it (this file is editable) or open a session against
`pack-omw-meta` and `record_outcome(success=False, notes="guide gap: ...")` —
that becomes the next iteration's input.
