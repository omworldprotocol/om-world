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
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

OMW_ROOT = Path(os.environ.get("OMW_ROOT",
    str(Path(__file__).resolve().parent.parent)))
OUT_DIR = OMW_ROOT / "runtime" / "pattern_evolution"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# v1.1 (P1.7 2026-05-27): pattern version-aware clustering.
# 每个 Pattern 有它的 effective_since 时间(SKILL.md 文件 mtime),
# 早于该时间的 violation 标 historic — 旧版可能已被修;
# 晚于该时间的 violation 标 active — 真当前问题,候选演化。
PATTERN_PATH = os.environ.get(
    "OMW_PATTERN_PATH",
    str(OMW_ROOT / "patterns") + ":" + str(OMW_ROOT.parent / "om-world-private" / "patterns"))
PATTERN_DIRS = [Path(p.strip()) for p in PATTERN_PATH.split(":") if p.strip()]

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


def _load_pattern_effective_since() -> dict[str, tuple[str, int]]:
    """For each Pattern in PATTERN_DIRS, parse frontmatter version + take file
    mtime. Returns {pattern_id: (version_str, effective_since_ts)}.

    Rationale: Pattern body edits change file mtime — that's "when this version
    became active". Events with ts < mtime are from a prior Pattern version and
    may already have been addressed by the evolution. Treat them as historic.
    """
    out: dict[str, tuple[str, int]] = {}
    fm_re = re.compile(r"^---\s*\n(.*?)\n---", re.S)
    ver_re = re.compile(r"^version:\s*(\S+)", re.M)
    for base in PATTERN_DIRS:
        if not base.is_dir():
            continue
        for f in list(base.glob("*/SKILL.md")) + list(base.glob("packs/*/PACK.md")):
            pid = f.parent.name
            try:
                text = f.read_text(encoding="utf-8")
                m = fm_re.match(text)
                if not m:
                    continue
                vm = ver_re.search(m.group(1))
                version = vm.group(1).strip().strip("'\"") if vm else "?"
                mtime = int(f.stat().st_mtime)
                # 后写优先(overlay)— private 覆盖 public
                out[pid] = (version, mtime)
            except OSError:
                continue
    return out


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


def _cluster_violations(events: list[dict],
                        pattern_versions: dict[str, tuple[str, int]] | None = None,
                        ) -> dict[tuple, dict]:
    """Cluster violations by (pattern, section, rule_first_60).

    v1.1 (P1.7): when pattern_versions provided, each cluster carries
    active_count / historic_count breaking down evidence into "after current
    Pattern version effective" vs "before". Pure-historic clusters get tagged
    so the markdown writer can archive them rather than re-propose evolution.
    """
    pv = pattern_versions or {}
    clusters: dict[tuple, dict] = defaultdict(lambda: {
        "count": 0, "hard": 0, "soft": 0,
        "first_seen": None, "last_seen": None,
        "evidence": [],
        "active_evidence": [],     # v1.1: post-effective_since 证据样本
        "active_count": 0,         # v1.1: ts >= effective_since 的 violation 数
        "historic_count": 0,       # v1.1: ts < effective_since
        "pattern_version": None,   # v1.1
        "pattern_effective_since": None,  # v1.1
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
            # v1.1: active vs historic split
            pver = pv.get(pattern)
            if pver:
                c["pattern_version"], c["pattern_effective_since"] = pver
                if ts and ts >= pver[1]:
                    c["active_count"] += 1
                else:
                    c["historic_count"] += 1
            ev_evidence = (g.get("evidence") or "").strip()
            if ev_evidence:
                if len(c["evidence"]) < 4:
                    c["evidence"].append({
                        "protocol": ev.get("protocol"),
                        "evidence": ev_evidence[:280], "ts": ts,
                    })
                # v1.1 separately keep active-only evidence for active proposals
                if pver and ts and ts >= pver[1] and len(c["active_evidence"]) < 4:
                    c["active_evidence"].append({
                        "protocol": ev.get("protocol"),
                        "evidence": ev_evidence[:280], "ts": ts,
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
                    total_events: int,
                    pattern_versions: dict[str, tuple[str, int]] | None = None) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = OUT_DIR / f"{today}.md"
    pv = pattern_versions or {}
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
    L(f"> v1.1: Pattern version-aware — cluster 按是否在当前 Pattern 版本"
      f"生效后(SKILL.md mtime)分 active vs historic")
    L("")

    # v1.1: split clusters into active (true current problems) vs historic (likely already evolved)
    sortable_all = sorted(
        ((k, v) for k, v in clusters.items()
         if v["count"] >= MIN_VIOLATION_COUNT),
        key=lambda kv: kv[1]["active_count"] if pv else kv[1]["count"],
        reverse=True)
    # active = at least MIN_VIOLATION_COUNT events after Pattern version effective
    active_clusters = [(k, v) for k, v in sortable_all
                       if v["active_count"] >= MIN_VIOLATION_COUNT]
    # historic = all events predate current Pattern version (or no version info)
    historic_clusters = [(k, v) for k, v in sortable_all
                         if (k, v) not in active_clusters]

    # === Section A: ACTIVE proposals (真当前演化候选) ===
    L("## A. 当前版本生效后真触发的演化候选 (建议立即 review)")
    L("")
    L("> 这一节列出在 Pattern **当前版本生效之后**(SKILL.md mtime ≥ 之后)反复"
      f"触发的 violation cluster,即旧版演化没修住或新出现的真问题。**优先读这一节。**")
    L("")
    if not active_clusters:
        L(f"_无 cluster 在当前 Pattern 版本生效后触发 ≥ {MIN_VIOLATION_COUNT} 次。_")
        L(f"_= 最近一次 Pattern 演化把已知 cluster 都修住了。下一次新 audit 出新模式再看。_")
    for i, ((pattern, section, rule), c) in enumerate(active_clusters, 1):
        vinfo = (f" (Pattern v{c['pattern_version']} since {_ts(c['pattern_effective_since'])})"
                 if c.get('pattern_version') else "")
        L(f"### A.{i}  `{pattern}` · `{section}` · 当前版本后触发 **{c['active_count']}** 次"
          f"{vinfo}")
        L("")
        L(f"**规则原文**:{c['full_rule']}")
        L("")
        L(f"- active 时段:{_ts(c['first_seen']) if c['active_count'] else '?'} ~ {_ts(c['last_seen'])}")
        L(f"- active 严重度:{c['hard']} hard / {c['soft']} soft (总 cluster {c['count']})")
        L(f"- 涉及协议:{', '.join(sorted(c['protocols'])) or '(unknown)'}")
        L("")
        L(f"**active 证据({len(c['active_evidence'])} 条)**:")
        for s in c["active_evidence"]:
            L(f"- 协议={s['protocol']}: _{s['evidence']}_")
        L("")
        L("**演化候选**:")
        if c["hard"] >= c["soft"]:
            L("- 🔴 主要 hard → 现 Hard-Forbidden 段已严,问题在 agent 反复忽视 → 加具体反例 / 调 audit_run.py enforcement")
        else:
            L("- 🟡 主要 soft → 表述模糊 → Rules / Heuristics 段加判定示例")
        if len(c["protocols"]) >= 2:
            L(f"- 跨多协议({len(c['protocols'])} 个)→ 真 Pattern body 问题,不是协议特例")
        L("")
        L("---")
        L("")

    # === Section B: Historic archive (仅参考) ===
    L("## B. 历史 cluster 归档 (Pattern 当前版本生效前,可能已修)")
    L("")
    L("> 这一节列在 Pattern **当前版本生效之前**出现的 violation cluster。")
    L("> 多数已被对应版本的 Pattern 演化修住;**仅参考,无需 action**。")
    L("> 若同 rule 在 § A 也出现 = 当前版本没修住 → 需新一轮演化。")
    L("")
    if not historic_clusters:
        L(f"_无历史 cluster。_")
    for i, ((pattern, section, rule), c) in enumerate(historic_clusters, 1):
        ver = c.get('pattern_version') or "?"
        eff = _ts(c.get('pattern_effective_since')) if c.get('pattern_effective_since') else "?"
        L(f"### B.{i}  `{pattern}` · `{section}` · 历史触发 **{c['historic_count']}** 次 "
          f"(Pattern v{ver} since {eff})")
        L(f"- 规则:{c['full_rule'][:120]}")
        L(f"- 时段:{_ts(c['first_seen'])} ~ {_ts(c['last_seen'])}")
        L(f"- 严重度:{c['hard']} hard / {c['soft']} soft")
        L("")

    # === Section C: Gap signals (LLM said "no pattern guides this") ===
    L("## C. Gap signals — agent / LLM 卡壳缺指引")
    L("")
    gap_sorted = sorted(((k, v) for k, v in gaps.items()
                         if v["count"] >= MIN_GAP_COUNT),
                        key=lambda kv: kv[1]["count"], reverse=True)
    if not gap_sorted:
        L(f"_(无 gap_signal 超过 {MIN_GAP_COUNT} 次阈值)_")
    for i, (key, v) in enumerate(gap_sorted, 1):
        kind, pattern = key.split("|", 1)
        L(f"### C.{i}  kind=`{kind}` pattern=`{pattern}` · 触发 **{v['count']}** 次")
        for d in v["details"]:
            L(f"- {d}")
        L("")
        L(f"**演化候选**:写新 Pattern 覆盖此类决策点,或扩展 `{pattern}` 的 Heuristics 段")
        L("")
        L("---")
        L("")

    # === Section D: Patterns with chronically low judgment scores ===
    L(f"## D. Judgment 持续偏低的 Pattern (avg < {LOW_JUDGMENT_CUTOFF})")
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


def _check_growth_gaps() -> list[dict]:
    """v1.2 (P3-C 2026-05-27): cross-reference SOVEREIGN-X account_stats. If
    followers stagnant ≥ 7d → growth gap signal — distinct from violation
    cluster. Tells founder "OMW guard 防降权可能不够,需要正向 winning Pattern"."""
    sql = (
        "SELECT fetched_at, followers FROM account_stats "
        "ORDER BY fetched_at DESC LIMIT 60"
    )
    cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
           SERVER_HOST,
           f"sqlite3 -json /root/SOVEREIGN-X/data/sovereign_x.db \"{sql}\""]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0 or not r.stdout.strip():
        return []
    try:
        rows = json.loads(r.stdout)
    except json.JSONDecodeError:
        return []
    if not rows:
        return []
    current = rows[0].get("followers")
    if current is None:
        return []
    stagnant_days = 0
    last_day = rows[0].get("fetched_at", "")[:10]
    for r in rows:
        f = r.get("followers")
        day = r.get("fetched_at", "")[:10]
        if day != last_day and f != current:
            break
        if day != last_day:
            stagnant_days += 1
            last_day = day
    gaps: list[dict] = []
    if stagnant_days >= 7:
        gaps.append({
            "project": "SOVEREIGN-X",
            "metric": "followers",
            "current": current,
            "stagnant_days": stagnant_days,
            "severity": "high" if stagnant_days >= 14 else "medium",
            "detail": (
                f"@invaribreak followers 停 {stagnant_days} 天在 {current};"
                f"OMW 防降权 guard 可能不够,需 P3-A'/B' "
                f"(strategist cold-start mode + winning Pattern body)。"
            ),
        })
    return gaps


def main() -> int:
    events = _ssh_fetch_events()
    if not events:
        print("no events fetched (SSH fail or empty server.db)", file=sys.stderr)
        return 1
    pattern_versions = _load_pattern_effective_since()
    clusters = _cluster_violations(events, pattern_versions=pattern_versions)
    gaps = _cluster_gaps(events)
    low_judge = _aggregate_judgment(events)
    growth_gaps = _check_growth_gaps()
    out_path = _write_markdown(clusters, gaps, low_judge, len(events),
                                pattern_versions=pattern_versions)
    if growth_gaps:
        # Append growth-gap section to the same daily proposal file
        with out_path.open("a", encoding="utf-8") as fp:
            fp.write("\n## E. 增长趋势 gap(P3-C 2026-05-27 真飞轮信号)\n\n")
            fp.write("> 真衡量 OMW 是否帮项目涨流量。\n")
            fp.write("> followers 持平 ≥ 7 天 = OMW 当前防降权 guard 不够,需要正向 Pattern。\n\n")
            for g in growth_gaps:
                fp.write(f"### E.1  {g['project']} · {g['metric']} stagnant {g['stagnant_days']}d "
                         f"(severity={g['severity']})\n")
                fp.write(f"- 当前值:{g['current']}\n")
                fp.write(f"- {g['detail']}\n\n")
    active = sum(1 for v in clusters.values()
                 if v["active_count"] >= MIN_VIOLATION_COUNT)
    total = sum(1 for v in clusters.values() if v['count'] >= MIN_VIOLATION_COUNT)
    print(f"wrote {out_path}")
    print(f"  events analyzed: {len(events)}")
    print(f"  patterns loaded with version: {len(pattern_versions)}")
    print(f"  active proposals: {active} (post Pattern-version-effective, ≥{MIN_VIOLATION_COUNT})")
    print(f"  historic archive: {total - active}")
    print(f"  gap clusters: {sum(1 for v in gaps.values() if v['count'] >= MIN_GAP_COUNT)}")
    print(f"  low-judgment patterns: {len(low_judge)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
