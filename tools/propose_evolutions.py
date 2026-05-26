#!/usr/bin/env python3
"""propose_evolutions.py — turn fine-grained OMW events into Pattern
evolution proposals for founder review.

Inputs (via SSH from hetzner-ash:omw_server.db):
  - guards_triggered (per-event JSON list of {pattern, section, rule, result, evidence})
  - judgment_score (per-event float, low scores = rubric mismatch)
  - gap_signal (per-event "LLM had no Pattern guidance")
  - metrics.violations / metrics.warnings counts

Output:
  - runtime/pattern_evolution/<date>.md — human-readable proposal doc
  - cluster violations by (pattern, section, rule_first_80) → propose
    Pattern body edits / new sub-Pattern / clarifying examples
  - flag gap_signals where LLM said "no rule covers this"
  - flag patterns with consistently low judgment scores

Founder reviews the markdown weekly; approves → manually patches Pattern body
(or future automation drafts the patch). This is the *evolution feedback loop*
that turns OMW from "Pattern archive" into "Pattern compounding asset".
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

OMW_ROOT = Path(os.environ.get("OMW_ROOT",
    str(Path(__file__).resolve().parent.parent)))
OUT_DIR = OMW_ROOT / "runtime" / "pattern_evolution"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SSH_KEY = os.environ.get("OMW_SERVER_SSH_KEY",
                         str(Path.home() / ".ssh" / "hetzner_ash_key"))
SERVER_HOST = os.environ.get("OMW_SERVER_HOST", "root@87.99.153.204")
REMOTE_DB = os.environ.get("OMW_SERVER_DB_PATH",
                           "/opt/om-world/server/omw_server.db")

# Threshold knobs (env-overridable).
MIN_VIOLATION_COUNT  = int(os.environ.get("OMW_EVO_MIN_VIOLATIONS", "3"))
MIN_GAP_COUNT        = int(os.environ.get("OMW_EVO_MIN_GAPS", "2"))
LOW_JUDGMENT_CUTOFF  = float(os.environ.get("OMW_EVO_LOW_JUDGMENT", "0.6"))
LOW_JUDGMENT_MIN_N   = int(os.environ.get("OMW_EVO_LOW_JUDGMENT_MIN_N", "3"))
LOOKBACK_DAYS        = int(os.environ.get("OMW_EVO_LOOKBACK_DAYS", "14"))


def _ssh_fetch_events() -> list[dict]:
    sql = (
        f"SELECT ts, pattern_id, guards_triggered, judgment_score, gap_signal, "
        f"metrics, agent_id, json_extract(context,'$.intent.protocol_slug') protocol "
        f"FROM invocations "
        f"WHERE recv_at > strftime('%s','now','-{LOOKBACK_DAYS} days') "
        f"AND (guards_triggered IS NOT NULL OR judgment_score IS NOT NULL "
        f"     OR gap_signal IS NOT NULL) "
        f"ORDER BY ts"
    )
    cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
           SERVER_HOST, f"sqlite3 -json {REMOTE_DB} \"{sql}\""]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        sys.stderr.write(f"SSH fetch failed: {r.stderr[:500]}\n")
        return []
    out = r.stdout.strip()
    if not out:
        return []
    rows = json.loads(out)
    return rows


def _cluster_violations(events: list[dict]) -> dict[tuple, dict]:
    """Cluster violations by (pattern, section, rule_first_60)."""
    clusters: dict[tuple, dict] = defaultdict(lambda: {
        "count": 0, "hard": 0, "soft": 0,
        "first_seen": None, "last_seen": None,
        "evidence": [],
        "protocols": set(),
        "agents": set(),
        "full_rule": "",
    })
    for ev in events:
        raw = ev.get("guards_triggered")
        if not raw:
            continue
        try:
            gs = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        for g in gs:
            if g.get("result") != "violation":
                continue
            pattern  = g.get("pattern", "?")
            section  = g.get("section", "?")
            rule     = (g.get("rule") or "")[:60]
            full     = g.get("rule") or ""
            severity = g.get("severity", "soft")
            key = (pattern, section, rule)
            c = clusters[key]
            c["count"] += 1
            c["full_rule"] = full
            if severity == "hard":
                c["hard"] += 1
            else:
                c["soft"] += 1
            ts = ev.get("ts")
            if ts:
                c["first_seen"] = min(c["first_seen"] or ts, ts)
                c["last_seen"]  = max(c["last_seen"] or 0, ts)
            ev_evidence = (g.get("evidence") or "").strip()
            if ev_evidence and len(c["evidence"]) < 4:
                c["evidence"].append({
                    "protocol": ev.get("protocol"),
                    "evidence": ev_evidence[:280],
                })
            if ev.get("protocol"):
                c["protocols"].add(ev["protocol"])
            if ev.get("agent_id"):
                c["agents"].add(ev["agent_id"])
    return clusters


def _cluster_gaps(events: list[dict]) -> dict[str, dict]:
    """Cluster gap_signals by kind + pattern."""
    clusters: dict[str, dict] = defaultdict(lambda: {
        "count": 0, "details": [], "protocols": set(),
    })
    for ev in events:
        raw = ev.get("gap_signal")
        if not raw:
            continue
        try:
            g = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(g, dict):
            continue
        key = f"{g.get('kind', '?')}|{g.get('pattern', '?')}"
        c = clusters[key]
        c["count"] += 1
        if g.get("detail") and len(c["details"]) < 4:
            c["details"].append(g["detail"][:200])
        if ev.get("protocol"):
            c["protocols"].add(ev["protocol"])
    return clusters


def _aggregate_judgment(events: list[dict]) -> dict[str, dict]:
    """Group judgment scores by pattern."""
    by_pat: dict[str, list[float]] = defaultdict(list)
    for ev in events:
        s = ev.get("judgment_score")
        if s is None:
            continue
        try:
            f = float(s)
        except (TypeError, ValueError):
            continue
        by_pat[ev.get("pattern_id") or "?"].append(f)
    out: dict[str, dict] = {}
    for p, scores in by_pat.items():
        if len(scores) < LOW_JUDGMENT_MIN_N:
            continue
        avg = sum(scores) / len(scores)
        if avg < LOW_JUDGMENT_CUTOFF:
            out[p] = {"avg": round(avg, 3), "n": len(scores),
                      "low": sum(1 for s in scores if s < LOW_JUDGMENT_CUTOFF)}
    return out


def _ts(ts: int | None) -> str:
    if not ts:
        return "?"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def _write_markdown(clusters: dict, gaps: dict, low_judge: dict,
                    total_events: int) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = OUT_DIR / f"{today}.md"
    lines: list[str] = []
    L = lines.append
    L(f"# OMW Pattern Evolution Proposals — {today}")
    L("")
    L(f"> Auto-generated from `tools/propose_evolutions.py` against "
      f"hetzner-ash:omw_server.db, lookback {LOOKBACK_DAYS} days.")
    L(f"> Source events analyzed: {total_events}")
    L(f"> Thresholds: violations≥{MIN_VIOLATION_COUNT}  "
      f"gaps≥{MIN_GAP_COUNT}  judgment<{LOW_JUDGMENT_CUTOFF} "
      f"(n≥{LOW_JUDGMENT_MIN_N})")
    L("")
    L("Founder action: read each proposal, decide → "
      "(a) patch Pattern body to address; (b) write new sub-Pattern stub; "
      "(c) dismiss as agent error not pattern problem.")
    L("")

    # === Section 1: Repeat violations (highest signal) ===
    L("## 1. 反复触发的 Pattern 违规(按次数排,候选演化提议)")
    L("")
    sortable = sorted(
        ((k, v) for k, v in clusters.items() if v["count"] >= MIN_VIOLATION_COUNT),
        key=lambda kv: kv[1]["count"], reverse=True)
    if not sortable:
        L(f"_(无 cluster 超过 {MIN_VIOLATION_COUNT} 次阈值)_")
    for i, ((pattern, section, rule), c) in enumerate(sortable, 1):
        L(f"### 1.{i}  `{pattern}` · `{section}` · 触发 **{c['count']}** 次"
          f" ({c['hard']} hard, {c['soft']} soft)")
        L("")
        L(f"**规则原文**:{c['full_rule']}")
        L("")
        L(f"- 出现时段:{_ts(c['first_seen'])} ~ {_ts(c['last_seen'])}")
        L(f"- 涉及协议:{', '.join(sorted(c['protocols'])) or '(unknown)'}")
        L(f"- 涉及 agent:{', '.join(sorted(c['agents'])) or '(unknown)'}")
        L("")
        L(f"**证据样本({len(c['evidence'])} 条)**:")
        for s in c["evidence"]:
            L(f"- 协议={s['protocol']}: _{s['evidence']}_")
        L("")
        L("**演化候选**:")
        if c["hard"] >= c["soft"]:
            L(f"- 🔴 主要是 hard violation → Pattern 的 Hard-Forbidden 段已足够严,"
              f"问题在 agent 反复忽视;考虑加 1 个具体反例到 Anti-Pattern 段")
        else:
            L(f"- 🟡 主要是 soft violation → Pattern 表述可能模糊导致 agent 误判,"
              f"考虑在 Rules / Heuristics 段加更具体的判定示例")
        if len(c["protocols"]) >= 2:
            L(f"- 跨多个协议(`{len(c['protocols'])}` 个)反复出现 → "
              f"不是协议特例,确实是 Pattern body 缺失或表述问题")
        else:
            L(f"- 仅在 1 个协议出现 → 可能是该协议特殊性,先观察更多 audit 再演化")
        L("")
        L("---")
        L("")

    # === Section 2: Gap signals (LLM said "no pattern guides this") ===
    L("## 2. Gap signals — agent / LLM 卡壳缺指引")
    L("")
    gap_sorted = sorted(((k, v) for k, v in gaps.items()
                         if v["count"] >= MIN_GAP_COUNT),
                        key=lambda kv: kv[1]["count"], reverse=True)
    if not gap_sorted:
        L(f"_(无 gap_signal 超过 {MIN_GAP_COUNT} 次阈值)_")
    for i, (key, v) in enumerate(gap_sorted, 1):
        kind, pattern = key.split("|", 1)
        L(f"### 2.{i}  kind=`{kind}` pattern=`{pattern}` · 触发 **{v['count']}** 次")
        for d in v["details"]:
            L(f"- {d}")
        L("")
        L(f"**演化候选**:写新 Pattern 覆盖此类决策点,或扩展 `{pattern}` 的 Heuristics 段")
        L("")
        L("---")
        L("")

    # === Section 3: Patterns with chronically low judgment scores ===
    L(f"## 3. Judgment 持续偏低的 Pattern (avg < {LOW_JUDGMENT_CUTOFF})")
    L("")
    if not low_judge:
        L("_(无 Pattern 触发低 judgment 阈值)_")
    for p, d in sorted(low_judge.items(), key=lambda kv: kv[1]["avg"]):
        L(f"- **`{p}`**:avg={d['avg']}, n={d['n']}, low={d['low']}")
        L(f"  - 演化候选:① Judgment 段 rubric 过严; ② Pattern 主体内容跟 rubric 脱节; "
          f"③ agent 喂的 subject 不完整")
    L("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def main() -> int:
    events = _ssh_fetch_events()
    if not events:
        print("no events fetched (SSH fail or empty server.db)", file=sys.stderr)
        return 1
    clusters = _cluster_violations(events)
    gaps = _cluster_gaps(events)
    low_judge = _aggregate_judgment(events)
    out_path = _write_markdown(clusters, gaps, low_judge, len(events))
    print(f"wrote {out_path}")
    print(f"  events analyzed: {len(events)}")
    print(f"  violation clusters: {sum(1 for v in clusters.values() if v['count'] >= MIN_VIOLATION_COUNT)} (threshold ≥{MIN_VIOLATION_COUNT})")
    print(f"  gap clusters: {sum(1 for v in gaps.values() if v['count'] >= MIN_GAP_COUNT)}")
    print(f"  low-judgment patterns: {len(low_judge)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
