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


_GROWTH_PROJECTS = [
    {"name": "SOVEREIGN-X", "db": "/root/SOVEREIGN-X/data/sovereign_x.db", "kind": "x_text"},
    {"name": "OM-WORLD-X",  "db": "/root/OM-WORLD-X/data/om_world_x.db",   "kind": "x_text"},
    # AVA-trend DB 在 Mac local(douyin 半自动发布在 Mac)
    {"name": "AVA-trend",   "db": "/Users/feiyang/all_bots/AVA-trend/data/publish.db",
     "kind": "douyin_video"},
]


def _q_remote(db_path: str, sql: str) -> list[dict]:
    # Local path → 直读;否则 SSH
    from pathlib import Path as _P
    if _P(db_path).exists():
        cmd = ["sqlite3", "-json", db_path, sql]
    else:
        cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
               SERVER_HOST,
               f"sqlite3 -json {db_path} \"{sql}\""]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0 or not r.stdout.strip():
        return []
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return []


def _check_growth_gaps() -> list[dict]:
    """v1.4 (P3-D 2026-05-27 OM-WORLD-X 推广): 跨两项目真涨流量 3 大指标 gap.
    旧 followers 指标降级 (虚荣);新 3 大指标:
      - total_bookmarks (7d): 0 持续 ≥ 7 天 = bookmark winning Pattern 没真生效
      - kol_eng_7d:  0 持续 ≥ 14 天 = KOL outreach 没真捕获关系
      - n_with_depth_ge2:  0 持续 ≥ 14 天 = conversation trigger 没生效
    """
    gaps: list[dict] = []
    for proj in _GROWTH_PROJECTS:
        pname, db = proj["name"], proj["db"]
        kind = proj.get("kind", "x_text")

        # P3-AVA douyin_video 分支
        if kind == "douyin_video":
            gaps.extend(_check_ava_gaps(pname, db))
            continue

        # P3-D 1: bookmark gap (7d 总 bookmarks)
        rows = _q_remote(db,
            "SELECT SUM(COALESCE(bookmark_count,0)) total FROM tweet_stats "
            "WHERE fetched_at > datetime('now','-7 days')")
        total_bookmarks_7d = (rows[0].get("total") if rows else 0) or 0
        if total_bookmarks_7d == 0:
            gaps.append({
                "project": pname, "metric": "bookmarks_7d",
                "current": 0, "severity": "high",
                "detail": (
                    "7d 总 bookmarks = 0。playbook-sovereign-x-bookmark-able 没真生效 — "
                    "agent 写出的推无 saveable 锚点。可能 governance 没真 block,"
                    "或 LLM 长 prompt 处理失效。建议:验证 governance check_omw_guards "
                    "对 bookmark-able Pattern 真返 hard_violations。"
                ),
            })

        # P3-D 2: KOL engagement gap (14d distinct KOL count)
        rows = _q_remote(db,
            "SELECT COUNT(DISTINCT kol_handle) n FROM kol_engagement "
            "WHERE engaged_at > datetime('now','-14 days')")
        kol_distinct_14d = (rows[0].get("n") if rows else 0) or 0
        if kol_distinct_14d == 0:
            gaps.append({
                "project": pname, "metric": "kol_distinct_14d",
                "current": 0, "severity": "high",
                "detail": (
                    "14d 0 KOL 互动。playbook-sovereign-x-kol-magnet 没真触达 KOL。"
                    "可能 reply_engine 选 candidate 排序失效 / kol_targets 配置为空 / "
                    "reply 内容仍是 generic。建议:检查 settings.yaml kol_outreach.kol_targets。"
                ),
            })

        # P3-D 3: conversation depth gap
        rows = _q_remote(db,
            "SELECT SUM(CASE WHEN max_reply_depth >= 2 THEN 1 ELSE 0 END) n "
            "FROM tweet_stats WHERE fetched_at > datetime('now','-14 days')")
        depth_ge2_14d = (rows[0].get("n") if rows else 0) or 0
        if depth_ge2_14d == 0:
            gaps.append({
                "project": pname, "metric": "depth_ge2_14d",
                "current": 0, "severity": "high",
                "detail": (
                    "14d 0 推有 ≥ 2 round conversation depth。"
                    "playbook-sovereign-x-conversation-trigger 没真生效。"
                    "可能 LLM 仍写 closed assertion / own-tweet replies 没 follow-up。"
                    "建议:检查 reply_engine 真有 own_post pending reply 在跑。"
                ),
            })

    return gaps


_PROJECT_PATTERN_MAP = {
    # 哪个 project 的真涨流量指标缺口 → 改哪个 Pattern
    "SOVEREIGN-X": {
        "bookmarks_7d": "playbook-sovereign-x-bookmark-able",
        "kol_distinct_14d": "playbook-sovereign-x-kol-magnet",
        "depth_ge2_14d": "playbook-sovereign-x-conversation-trigger",
    },
    "OM-WORLD-X": {
        "bookmarks_7d": "playbook-sovereign-x-bookmark-able",
        "kol_distinct_14d": "playbook-sovereign-x-kol-magnet",
        "depth_ge2_14d": "playbook-sovereign-x-conversation-trigger",
    },
    "AVA-trend": {
        # P3-AVA 2026-05-27:douyin 视频信号映射 3 个 winning Pattern
        "completion_avg_7d_low": "playbook-ava-trend-completion-magnet",
        "bounce_2s_avg_7d_high": "playbook-ava-trend-hook-strength",
        "subscribe_7d_zero": "playbook-ava-trend-subscribe-conversion",
    },
}


def _recipes_for_growth_gap(g: dict) -> list[dict]:
    """Map a § E growth gap to candidate auto-apply recipes."""
    target_pattern = _PROJECT_PATTERN_MAP.get(g["project"], {}).get(g["metric"])
    if not target_pattern:
        return []
    # severity high + zero current value → promote a Soft-Avoid to Hard-Forbidden
    # 14d 内每 Pattern 最多 1 次 R-PROMOTE,apply_evolutions 强制 dedupe
    return [{
        "recipe_id": "R-PROMOTE",
        "target_file": f"patterns/{target_pattern}/SKILL.md",
        "repo": "om-world-private",
        "promote_reason": g["detail"][:120],
    }]


def _recipes_for_ct_signal(s: dict) -> list[dict]:
    """Map a § F content_type signal to candidate auto-apply recipes."""
    out: list[dict] = []
    if s["signal"] == "article_outperforms_single" and s["project"] == "OM-WORLD-X":
        # 加 settings.yaml article cron 一档
        out.append({
            "recipe_id": "R-CONFIG",
            "target_file": "config/settings.yaml",
            "repo": "OM-WORLD-X",
            "config_action": "boost_article_cadence",
            "ratio": s.get("ratio"),
        })
    elif s["signal"] == "article_zero_bookmark_zero_depth":
        # 加 article-format Pattern 一条 Anti-Pattern
        out.append({
            "recipe_id": "R-ADD-AP",
            "target_file": "patterns/playbook-om-world-x-article-format/SKILL.md",
            "repo": "om-world-private",
            "anti_pattern_text": (
                "0 真 bookmark / depth 持续 ≥5 篇 article = article-format Hard-Forbidden "
                "锚点没真生效 — 反查 metric-oriented 3 套策略真注入 article prompt"
            ),
        })
    return out


def _recipes_for_violation_cluster(pid: str, c: dict) -> list[dict]:
    """§ A: 高频 violation cluster → 加 Anti-Pattern。"""
    if c["active_count"] < 5:
        return []
    return [{
        "recipe_id": "R-ADD-AP",
        "target_file": f"patterns/{pid}/SKILL.md",
        "repo": "om-world-private",
        "anti_pattern_text": (
            f"高频 violation cluster ({c['active_count']} 次/period) 自动添加 — "
            f"sample sections: {', '.join(list(c.get('sample_sections') or [])[:3])}"
        ),
    }]


def _check_ava_gaps(pname: str, db: str) -> list[dict]:
    """P3-AVA 2026-05-27 AVA-trend / douyin video 真涨流量 3 大指标 gap。"""
    out: list[dict] = []
    rows = _q_remote(db,
        "SELECT AVG(completion_rate) avg_cr, AVG(bounce_rate_2s) avg_br, "
        "SUM(COALESCE(subscribe_count,0)) sub_n, COUNT(*) n "
        "FROM video_stats WHERE fetched_at > datetime('now','-7 days') "
        "  AND bounce_rate_2s IS NOT NULL")
    if not rows or (rows[0].get("n") or 0) == 0:
        return out
    r = rows[0]
    avg_cr = float(r.get("avg_cr") or 0)
    avg_br = float(r.get("avg_br") or 1)
    sub_n  = int(r.get("sub_n") or 0)
    n = int(r.get("n") or 0)

    # Completion < 5% 持续 7d
    if avg_cr < 0.05:
        out.append({
            "project": pname, "metric": "completion_avg_7d_low",
            "current": round(avg_cr, 4), "severity": "high",
            "detail": (
                f"7d 平均 completion_rate = {avg_cr*100:.2f}% < target 5%。"
                f"playbook-ava-trend-completion-magnet 没真生效 — 视频结构没"
                f"4 招 (payoff promise / hook reset / 末尾埋伏 / 时长 sweet spot)。"
                f"director/solo_writer prompt 注入需要 enforce。"
            ),
        })
    # bounce_rate_2s > 50% 持续 7d
    if avg_br > 0.50:
        out.append({
            "project": pname, "metric": "bounce_2s_avg_7d_high",
            "current": round(avg_br, 4), "severity": "high",
            "detail": (
                f"7d 平均 bounce_rate_2s = {avg_br*100:.2f}% > target ≤ 35%。"
                f"playbook-ava-trend-hook-strength 没真生效 — 0-2s 钩子三轨 "
                f"(视觉锚/反常识/情绪触发词)未齐。"
            ),
        })
    # 7d 0 subscribe
    if sub_n == 0:
        out.append({
            "project": pname, "metric": "subscribe_7d_zero",
            "current": 0, "severity": "high",
            "detail": (
                f"7d 0 subscribe(n={n} 视频)。"
                f"playbook-ava-trend-subscribe-conversion 没真生效 — 缺 series "
                f"期待 / 频道 furniture 持续露出 / 末尾 CTA 三件。"
            ),
        })
    return out


def _check_ava_snapshot_flywheel() -> list[dict]:
    """P3-SNAP 2026-05-28:读 ava_snapshot_weights.json,surface 飞轮状态。

    correlation report 是真信号源(每天 launchd 跑),本函数只 surface。
    """
    weights_path = OMW_ROOT / "runtime" / "ava_snapshot_weights.json"
    if not weights_path.exists():
        return []
    try:
        import json as _j
        data = _j.loads(weights_path.read_text())
    except Exception:
        return []
    n = int(data.get("n_samples") or 0)
    ready = bool(data.get("ready"))
    weights = data.get("weights") or {}
    nontrivial = [(k, v) for k, v in weights.items() if abs(float(v)) >= 0.3]
    out: list[dict] = []
    if n < 8:
        out.append({
            "title": f"AVA-trend Snapshot flywheel cold-start (n={n} < 8)",
            "detail": (
                f"snapshot→brief→video event chain 已有 {n} 条。需 ≥ 8 才能算"
                f"信任 correlation。继续累 — 等下周再判 v3.1 score 公式是否"
                f"真预测 perf。"
            ),
        })
    elif not ready or not nontrivial:
        out.append({
            "title": f"AVA-trend Snapshot flywheel 全 noise(n={n})",
            "detail": (
                f"v3.1 信号 {len(weights)} 维全部 |r| < 0.3。跟 AVA Judge "
                f"r=-0.11 同款 — score 公式当前对真表现无预测能力。"
                f"建议:(a) 等 sample > 30 再判;(b) 重审 _composite_score 公式"
                f"分量;(c) 检查是否 cold-start 噪声压过真信号。"
            ),
        })
    else:
        top = sorted(nontrivial, key=lambda kv: -abs(kv[1]))[:3]
        top_str = ", ".join(f"{k}={v}" for k, v in top)
        out.append({
            "title": f"AVA-trend Snapshot flywheel 真转动(n={n}, {len(nontrivial)} 信号有效)",
            "detail": (
                f"top {len(nontrivial)} 维度 |r| ≥ 0.3 真预测 perf: {top_str}。"
                f"director 已读 ava_snapshot_weights.json 加权 selection,下批"
                f"brief 应见进一步提升。继续累样本 → r 应收敛得更稳。"
            ),
        })
    return out


def _check_content_type_signals() -> list[dict]:
    """v1.4 (P3-D 2026-05-27 OM-WORLD-X article-aware): per content_type 真表现差异
    自动当 evolution candidate。

    场景:
      - article 2× single reach → 加 article 节奏建议
      - article < single reach → article 结构有问题,反查 playbook-om-world-x-article-format
      - article bookmark_rate / depth 仍 0 → article-format Pattern Hard-Forbidden 没真生效
    """
    signals: list[dict] = []
    for proj in _GROWTH_PROJECTS:
        pname, db = proj["name"], proj["db"]
        rows = _q_remote(db,
            "SELECT pp.content_type, COUNT(DISTINCT ts.tweet_id) n_posts, "
            "AVG(ts.impression_count) avg_imp, "
            "AVG(CASE WHEN ts.impression_count > 0 "
            "          THEN CAST(COALESCE(ts.bookmark_count,0) AS FLOAT) / ts.impression_count "
            "          ELSE 0 END) avg_br, "
            "AVG(COALESCE(ts.max_reply_depth,0)) avg_depth "
            "FROM tweet_stats ts "
            "JOIN published_posts pp ON pp.tweet_ids LIKE '%' || ts.tweet_id || '%' "
            "WHERE pp.published_at > datetime('now','-14 days') "
            "  AND ts.fetched_at = (SELECT MAX(ts2.fetched_at) FROM tweet_stats ts2 WHERE ts2.tweet_id = ts.tweet_id) "
            "GROUP BY pp.content_type")
        if not rows:
            continue
        by_ct = {(r.get("content_type") or "unknown"): r for r in rows}

        # article vs single reach 对比(仅 OM-WORLD-X 有 article 路径)
        if "article" in by_ct and "single" in by_ct:
            a, s = by_ct["article"], by_ct["single"]
            if (s.get("avg_imp") or 0) > 0 and (a.get("n_posts") or 0) >= 3 and (s.get("n_posts") or 0) >= 3:
                ratio = (a["avg_imp"] or 0) / (s["avg_imp"] or 1)
                if ratio >= 1.5:
                    signals.append({
                        "project": pname, "signal": "article_outperforms_single",
                        "ratio": round(ratio, 2),
                        "detail": (
                            f"14d article avg_imp={a['avg_imp']:.0f} vs single={s['avg_imp']:.0f} "
                            f"({ratio:.2f}×)。article 路径明显占优 → 建议 settings.yaml schedule.article_cron "
                            f"频率加大(当前 weekday 9am EST,可考虑加 weekend 或 weekday 第 2 篇)。"
                            f"同步加 article hook_angles 探索池。"
                        ),
                    })
                elif ratio <= 0.83:
                    signals.append({
                        "project": pname, "signal": "article_underperforms_single",
                        "ratio": round(ratio, 2),
                        "detail": (
                            f"14d article avg_imp={a['avg_imp']:.0f} vs single={s['avg_imp']:.0f} "
                            f"({ratio:.2f}×)。article 结构有问题 → 反查 playbook-om-world-x-article-format:"
                            f"title 是否含 named primitive / lede 是否真有 2 anchor / "
                            f"每 section 是否真有 1 anchor。"
                        ),
                    })

            # article bookmark_rate 仍 0 → article-format Hard-Forbidden 没真生效
            if (a.get("n_posts") or 0) >= 5 and (a.get("avg_br") or 0) == 0 and (a.get("avg_depth") or 0) == 0:
                signals.append({
                    "project": pname, "signal": "article_zero_bookmark_zero_depth",
                    "ratio": None,
                    "detail": (
                        f"已发 {a['n_posts']} 篇 article,bookmark_rate=0 + depth=0。"
                        f"playbook-om-world-x-article-format Judgment 阈值(bookmark ≥1%/depth ≥1.5)远未达。"
                        f"两种可能:(a) 账号 follower 太小没人 bookmark/reply — 等 followers 到 30+ 再判;"
                        f"(b) article 真没 bookmark-able / depth-trigger 锚点 — 加 article prompt "
                        f"显式 metric-oriented 规则(为 bookmark 这样写、为 depth 这样写)。"
                    ),
                })
    return signals


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
    ct_signals = _check_content_type_signals()
    out_path = _write_markdown(clusters, gaps, low_judge, len(events),
                                pattern_versions=pattern_versions)
    if growth_gaps:
        # P3-D § E:新 3 大真涨流量指标 gap(替代旧 followers stagnant)
        with out_path.open("a", encoding="utf-8") as fp:
            fp.write("\n## E. 真涨流量指标 gap(P3-D 2026-05-27)\n\n")
            fp.write("> 真衡量 OMW 是否帮项目涨流量。**bookmark / KOL eng / conversation depth**\n")
            fp.write("> 这 3 大真信号为 0 持续 ≥ 7-14 天 = winning Pattern 没真生效。\n\n")
            for i, g in enumerate(growth_gaps, 1):
                fp.write(f"### E.{i}  {g['project']} · {g['metric']} = {g['current']} "
                         f"(severity={g['severity']})\n")
                fp.write(f"- {g['detail']}\n\n")
    if ct_signals:
        # P3-D § F:per content_type 真表现差异作 evolution candidate
        with out_path.open("a", encoding="utf-8") as fp:
            fp.write("\n## F. content_type 真表现信号(P3-D 2026-05-27 OM-WORLD-X article-aware)\n\n")
            fp.write("> per content_type 抓真差异 → article vs single reach 比 / article 锚点是否真起效。\n")
            fp.write("> 真有结构差异 → 调度 + Pattern enforcement 跟着改。\n\n")
            for i, s in enumerate(ct_signals, 1):
                ratio_part = f" (ratio={s['ratio']}×)" if s.get("ratio") else ""
                fp.write(f"### F.{i}  {s['project']} · {s['signal']}{ratio_part}\n")
                fp.write(f"- {s['detail']}\n\n")

    # P3-SNAP 2026-05-28 § H: AVA Snapshot v3.1 信号 vs reality 飞轮状态
    h_signals = _check_ava_snapshot_flywheel()
    if h_signals:
        with out_path.open("a", encoding="utf-8") as fp:
            fp.write("\n## H. AVA Snapshot v3.1 信号 vs reality 飞轮(P3-SNAP)\n\n")
            fp.write("> v3.1 score 公式预测能力的真量化(snapshot 信号 vs 真完播率 Pearson)。\n")
            fp.write("> 飞轮转 = 同一公式下相关性 r 越来越正(随 sample 累积);停转 = 全 noise = 公式要改。\n\n")
            for i, s in enumerate(h_signals, 1):
                fp.write(f"### H.{i}  {s['title']}\n")
                fp.write(f"- {s['detail']}\n\n")

    # P3-E 2026-05-27: machine-readable proposals.json sidecar for apply_evolutions.py
    proposals: list[dict] = []
    for i, g in enumerate(growth_gaps, 1):
        proposals.append({
            "id": f"E.{i}",
            "kind": "growth_gap",
            "project": g["project"],
            "metric": g["metric"],
            "current_value": g["current"],
            "severity": g["severity"],
            "detail": g["detail"],
            "recipe_candidates": _recipes_for_growth_gap(g),
        })
    for i, s in enumerate(ct_signals, 1):
        proposals.append({
            "id": f"F.{i}",
            "kind": "content_type_signal",
            "project": s["project"],
            "signal": s["signal"],
            "ratio": s.get("ratio"),
            "detail": s["detail"],
            "recipe_candidates": _recipes_for_ct_signal(s),
        })
    # Pattern violation clusters (§ A) — only emit those with active_count ≥ MIN_VIOLATION_COUNT
    for pid, c in clusters.items():
        if c["active_count"] >= MIN_VIOLATION_COUNT:
            proposals.append({
                "id": f"A.{pid}",
                "kind": "violation_cluster",
                "pattern_id": pid,
                "active_count": c["active_count"],
                "total_count": c["count"],
                "recipe_candidates": _recipes_for_violation_cluster(pid, c),
            })

    proposals_path = out_path.with_suffix(".proposals.json")
    proposals_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_markdown": str(out_path.name),
        "events_analyzed": len(events),
        "proposals": proposals,
    }, indent=2, ensure_ascii=False))

    active = sum(1 for v in clusters.values()
                 if v["active_count"] >= MIN_VIOLATION_COUNT)
    total = sum(1 for v in clusters.values() if v['count'] >= MIN_VIOLATION_COUNT)
    print(f"wrote {out_path}")
    print(f"wrote {proposals_path} ({len(proposals)} proposals)")
    print(f"  events analyzed: {len(events)}")
    print(f"  patterns loaded with version: {len(pattern_versions)}")
    print(f"  active proposals: {active} (post Pattern-version-effective, ≥{MIN_VIOLATION_COUNT})")
    print(f"  historic archive: {total - active}")
    print(f"  gap clusters: {sum(1 for v in gaps.values() if v['count'] >= MIN_GAP_COUNT)}")
    print(f"  low-judgment patterns: {len(low_judge)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
