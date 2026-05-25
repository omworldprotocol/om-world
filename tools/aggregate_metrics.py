#!/usr/bin/env python3
"""aggregate_metrics.py — invocations.jsonl → SKILL.md frontmatter 聚合器。

读取所有 patterns/<id>/invocations.jsonl,按 invocation_id 配对 loaded/completed/errored 事件,
聚合成每 Pattern 的 metrics:
  - invoked: 总调用次数
  - measured-success-rate: success=True 占比
  - last-validated: 最近一次 completed 的日期
  - domain-specific: 由各 outcome 的 metrics 累加 / 取均值(按 Pattern 已有 domain-specific 字段定义)

然后 in-place 更新 patterns/<id>/SKILL.md 的 frontmatter.metrics 块。

用法:
  python tools/aggregate_metrics.py                    # 全部 Pattern
  python tools/aggregate_metrics.py <pattern-id> ...   # 指定 Pattern

可被 cron / systemd timer 周期触发(Stage 1)。Stage 2 之后会移到 server 端或 protocol 节点。

注意:本工具直接改 SKILL.md(in-place),需保证 frontmatter 用 YAML safe-load 可解析。
依赖:pyyaml(系统已装)。
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

# v0.2.1: 支持 OMW_PATTERN_PATH 多目录(冒号分隔, public:private overlay)
import os as _os
_default_dir = str(Path(__file__).resolve().parent.parent / "patterns")
_env_path = _os.environ.get("OMW_PATTERN_PATH", _default_dir)
PATTERN_DIRS: list[Path] = [
    Path(p.strip()) for p in _env_path.split(":") if p.strip()
]
# 保留 PATTERNS_DIR 兼容(第一个目录,用于新写)
PATTERNS_DIR = PATTERN_DIRS[0]

_FRONTMATTER_RE = re.compile(
    r"^(---\s*\n)(?P<fm>.*?)(\n---\s*\n)(?P<body>.*)$", re.DOTALL)


def _load_invocations(pat_dir: Path) -> list[dict]:
    """Load events from both local invocations.jsonl AND invocations.server.jsonl.
    The .server.jsonl is written by tools/sync_server_metrics.py from the
    hetzner-ash OMW server.db; merging both files gives a complete picture
    of events from Mac-local agents + server-side agents (SOVEREIGN-X /
    OM-WORLD-X). Stable invocation_id keys dedupe naturally during pairing."""
    events: list[dict] = []
    for fname in ("invocations.jsonl", "invocations.server.jsonl"):
        f = pat_dir / fname
        if not f.is_file():
            continue
        with f.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def _pair_events(events: list[dict]) -> list[dict]:
    """Pair loaded/completed events by invocation_id. Returns list of complete invocations."""
    by_id: dict[str, dict] = defaultdict(dict)
    for ev in events:
        iid = ev.get("invocation_id")
        if not iid:
            continue
        phase = ev.get("phase", "")
        if phase == "loaded":
            by_id[iid]["loaded"] = ev
        elif phase in ("completed", "errored"):
            by_id[iid]["outcome"] = ev
    paired = []
    for iid, pair in by_id.items():
        if "loaded" in pair and "outcome" in pair:
            paired.append({"invocation_id": iid, **pair})
    return paired


def _aggregate(paired: list[dict]) -> dict[str, Any]:
    """Compute aggregate metrics from paired invocations."""
    invoked = len(paired)
    if invoked == 0:
        return {}
    successes = sum(1 for p in paired
                    if p["outcome"].get("success") is True)
    completed_with_outcome = sum(1 for p in paired
                                 if p["outcome"].get("success") is not None)
    success_rate = (successes / completed_with_outcome
                    if completed_with_outcome else None)
    last_ts = max(p["outcome"].get("ts", 0) for p in paired)
    import datetime as dt
    last_validated = dt.datetime.fromtimestamp(
        last_ts, tz=dt.timezone.utc).date().isoformat() if last_ts else None

    # domain-specific:按 key 累加/取均值(数值)或最近值(字符串)
    domain_specific: dict[str, Any] = defaultdict(list)
    for p in paired:
        metrics = p["outcome"].get("metrics") or {}
        for k, v in metrics.items():
            domain_specific[k].append(v)
    rolled: dict[str, Any] = {}
    for k, vs in domain_specific.items():
        nums = [v for v in vs if isinstance(v, (int, float))]
        if nums:
            rolled[k] = {
                "sum": sum(nums),
                "avg": round(sum(nums) / len(nums), 3),
                "count": len(nums),
            }
        else:
            rolled[k] = {"last": vs[-1], "count": len(vs)}

    # v0.3.0: step-level rollup (only present if events carry step_id field).
    step_rollup: dict[str, dict[str, Any]] = {}
    guard_violations = 0
    guard_warnings = 0
    judgment_sum = 0.0
    judgment_n = 0
    gap_count = 0
    for p in paired:
        out = p["outcome"]
        sid = out.get("step_id")
        if sid:
            sentry = step_rollup.setdefault(sid, {
                "completed": 0, "ok": 0,
                "step_kind": out.get("step_kind"),
            })
            sentry["completed"] += 1
            if out.get("success") is True:
                sentry["ok"] += 1
        for g in out.get("guards_triggered") or []:
            r = g.get("result")
            if r == "violation":
                guard_violations += 1
            elif r == "warn":
                guard_warnings += 1
        jscore = out.get("judgment_score")
        if jscore is not None:
            try:
                judgment_sum += float(jscore)
                judgment_n += 1
            except (TypeError, ValueError):
                pass
        if out.get("gap_signal"):
            gap_count += 1

    result = {
        "invoked": invoked,
        "measured-success-rate": (round(success_rate, 3)
                                  if success_rate is not None else None),
        "last-validated": last_validated,
        "domain-specific-rolled": rolled,
    }
    if step_rollup:
        result["steps"] = {
            sid: {
                "step_kind": s["step_kind"],
                "completed": s["completed"],
                "success_rate": (round(s["ok"] / s["completed"], 3)
                                 if s["completed"] else None),
            }
            for sid, s in step_rollup.items()
        }
    if guard_violations or guard_warnings:
        result["guard-violations"] = guard_violations
        result["guard-warnings"] = guard_warnings
    if judgment_n:
        result["judgment-score-avg"] = round(judgment_sum / judgment_n, 3)
    if gap_count:
        result["gap-signal-count"] = gap_count
    return result


def _update_skill_md(skill: Path, agg: dict[str, Any]) -> bool:
    if not skill.is_file():
        return False
    text = skill.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return False
    fm_text = m.group("fm")
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return False

    metrics = fm.get("metrics") or {}
    # Preserve auto-tracked + domain-specific (manually-set keys);
    # only update invoked / success-rate / last-validated; merge rolled into domain-specific
    if agg.get("invoked", 0) > 0:
        metrics["invoked"] = agg["invoked"]
    if agg.get("measured-success-rate") is not None:
        metrics["measured-success-rate"] = agg["measured-success-rate"]
    if agg.get("last-validated"):
        metrics["last-validated"] = agg["last-validated"]

    rolled = agg.get("domain-specific-rolled", {})
    if rolled:
        ds = metrics.get("domain-specific") or {}
        if not isinstance(ds, dict):
            ds = {}
        # rolled keys go under domain-specific.rolled.<key>
        ds["_rolled"] = rolled
        metrics["domain-specific"] = ds

    # v0.3.0: write step-level + guard/judgment/gap rollups when present
    for key in ("steps", "guard-violations", "guard-warnings",
                "judgment-score-avg", "gap-signal-count"):
        if key in agg:
            metrics[key] = agg[key]

    fm["metrics"] = metrics
    new_fm_text = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False,
                                 default_flow_style=False).rstrip()
    new_text = f"---\n{new_fm_text}\n---\n{m.group('body')}"
    skill.write_text(new_text, encoding="utf-8")
    return True


def _all_pattern_dirs() -> list[Path]:
    """List every Pattern + Pack dir across all PATTERN_DIRS (public + private overlay)."""
    dirs: list[Path] = []
    seen: set[str] = set()
    for base in PATTERN_DIRS:
        if not base.is_dir():
            continue
        for d in base.iterdir():
            if not d.is_dir() or d.name in ("tools", "packs", "__pycache__"):
                continue
            if d.name in seen:
                continue                      # 后写优先(此处保留前者,与 SDK 一致)
            if (d / "SKILL.md").is_file():
                dirs.append(d)
                seen.add(d.name)
        packs_root = base / "packs"
        if packs_root.is_dir():
            for d in packs_root.iterdir():
                if d.is_dir() and d.name not in seen and (d / "PACK.md").is_file():
                    dirs.append(d)
                    seen.add(d.name)
    return dirs


def _md_path(d: Path) -> Path:
    """Return the SKILL.md or PACK.md inside d."""
    return d / ("PACK.md" if (d / "PACK.md").is_file() else "SKILL.md")


def aggregate_one(pat_dir: Path) -> dict[str, Any]:
    events = _load_invocations(pat_dir)
    paired = _pair_events(events)
    agg = _aggregate(paired)
    if agg:
        _update_skill_md(_md_path(pat_dir), agg)
    return agg


def main() -> int:
    targets = sys.argv[1:]
    if targets:
        # 显式指定 id:跨 PATTERN_DIRS 找
        target_dirs: list[Path] = []
        for pid in targets:
            found = False
            for base in PATTERN_DIRS:
                cand = base / pid
                if (cand / "SKILL.md").is_file():
                    target_dirs.append(cand)
                    found = True
                    break
                pack_cand = base / "packs" / pid
                if (pack_cand / "PACK.md").is_file():
                    target_dirs.append(pack_cand)
                    found = True
                    break
            if not found:
                print(f"  [miss] {pid} (not in any of OMW_PATTERN_PATH)")
    else:
        target_dirs = _all_pattern_dirs()
    total = 0
    updated = 0
    for pat_dir in sorted(target_dirs):
        total += 1
        agg = aggregate_one(pat_dir)
        pid = pat_dir.name
        if agg.get("invoked", 0) > 0:
            updated += 1
            print(f"  [agg] {pid}: invoked={agg['invoked']} "
                  f"success_rate={agg.get('measured-success-rate')} "
                  f"last_validated={agg.get('last-validated')}")
    print(f"\n✓ aggregated {updated}/{total} patterns+packs "
          f"(others had no invocations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
