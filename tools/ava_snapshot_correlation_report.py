#!/usr/bin/env python3
"""ava_snapshot_correlation_report.py — P3-SNAP 2026-05-28.

Snapshot v3.1 信号 vs 真实 video perf 的相关性分析。让 v3.1 飞轮真转起来。

链路:
  snapshot_built event   (pattern=flow-snapshot-v3-collect, id=trend_<id>)
       ↓ parent_invocation_id
  brief_selected event   (pattern=flow-snapshot-v3-collect, id=brief_<bid>)
       ↓ parent_invocation_id
  video_perf event       (pattern=meta-ava-trend-thesis, id=video_<qid>)

本脚本 join 三 event 按 trend_id ↔ brief_id 链路,算:
  1. Pearson(snapshot signal X, video Y) for each X∈{gap_score, attention_score,
     novelty, obscurity, spike, stream, shift, resonance, breadth}
                                Y∈{completion_rate, completion_rate_5s,
                                   bounce_rate_2s (反向), like_rate, subscribe_count}
  2. cluster_state 分组 mean completion_rate
  3. waveform type (max strength) 分组 mean
  4. 自动写 weights JSON:任何 signal r ≥ 0.3 + n ≥ 8 → weight=r;否则 0.0

输出:
  runtime/ava_snapshot_growth/<date>.md             (周报 markdown)
  runtime/ava_snapshot_weights.json                (director 下次读)

director 读 weights 调整 topic 选择(让一轮比一轮真好)。

跑法:
  python3 tools/ava_snapshot_correlation_report.py
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

OMW_ROOT = Path(os.environ.get("OMW_ROOT",
    str(Path(__file__).resolve().parent.parent)))
OUT_DIR = OMW_ROOT / "runtime" / "ava_snapshot_growth"
OUT_DIR.mkdir(parents=True, exist_ok=True)
WEIGHTS_PATH = OMW_ROOT / "runtime" / "ava_snapshot_weights.json"

SERVER_HOST = os.environ.get("OMW_SERVER_HOST", "root@87.99.153.204")
SSH_KEY = os.environ.get("OMW_SERVER_SSH_KEY",
                         str(Path.home() / ".ssh" / "hetzner_ash_key"))
OMW_DB = "/opt/om-world/server/omw_server.db"

# 信号阈值 — 多少样本 + 多大相关性才算"可信号"
MIN_SAMPLES = 8
MIN_R_FOR_WEIGHT = 0.30

SNAPSHOT_SIGNALS = [
    "gap_score", "novelty_score", "obscurity_score",
    "attention_score", "breadth", "platform_count",
    "spike_strength", "stream_strength", "shift_strength",
    "resonance_potential", "valence", "arousal", "cycles_seen",
]
PERF_SIGNALS = [
    "completion_rate", "completion_rate_5s",
    "bounce_rate_2s",  # inverted before correlation (1-x = good hook)
    "avg_view_proportion", "like_rate", "subscribe_count", "plays",
]
INVERTED = {"bounce_rate_2s"}  # higher = worse


def _ssh_json(sql: str) -> list[dict]:
    cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
           SERVER_HOST, f"sqlite3 -json {OMW_DB} \"{sql}\""]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0 or not r.stdout.strip():
        return []
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return []


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def _pull_chain() -> list[dict]:
    """三表 join:snapshot → brief_selected → video_perf。"""
    sql = """
    SELECT
      v.invocation_id   AS video_inv,
      json_extract(v.context,'$.brief_id')     AS brief_id,
      json_extract(v.context,'$.queue_id')     AS queue_id,
      v.metrics                                AS video_metrics,
      b.invocation_id   AS brief_inv,
      json_extract(b.context,'$.trend_id')     AS trend_id,
      b.metrics                                AS brief_metrics,
      s.invocation_id   AS snap_inv,
      s.metrics                                AS snap_metrics,
      s.context                                AS snap_context
    FROM invocations v
    JOIN invocations b ON b.invocation_id = v.parent_invocation_id
    JOIN invocations s ON s.invocation_id = b.parent_invocation_id
    WHERE v.step_kind = 'video_perf'
      AND b.step_kind = 'brief_selected'
      AND s.step_kind = 'snapshot_built'
    """
    rows = _ssh_json(sql.replace("\n", " "))
    out: list[dict] = []
    for r in rows:
        try:
            snap_m = json.loads(r.get("snap_metrics") or "{}")
            vid_m = json.loads(r.get("video_metrics") or "{}")
            snap_ctx = json.loads(r.get("snap_context") or "{}")
            out.append({
                "trend_id": r["trend_id"],
                "brief_id": r["brief_id"],
                "queue_id": r["queue_id"],
                "snap": snap_m,
                "vid": vid_m,
                "cluster_state": snap_ctx.get("cluster_state"),
                "discoverability": snap_ctx.get("discoverability"),
                "momentum": snap_ctx.get("momentum"),
            })
        except Exception:
            pass
    return out


def _correlations(rows: list[dict]) -> dict:
    """两两 Pearson:每个 snapshot signal × 每个 perf signal。"""
    out = {}
    for sig in SNAPSHOT_SIGNALS:
        out[sig] = {}
        for perf in PERF_SIGNALS:
            xs, ys = [], []
            for r in rows:
                x = (r["snap"] or {}).get(sig)
                y = (r["vid"] or {}).get(perf)
                if x is None or y is None:
                    continue
                if perf in INVERTED:
                    y = 1 - y
                xs.append(float(x))
                ys.append(float(y))
            r_val = _pearson(xs, ys)
            out[sig][perf] = {
                "r": round(r_val, 3) if r_val is not None else None,
                "n": len(xs),
            }
    return out


def _group_means(rows: list[dict], key: str, perf: str = "completion_rate") -> dict:
    groups: dict[str, list[float]] = {}
    for r in rows:
        k = r.get(key) or "unknown"
        y = (r["vid"] or {}).get(perf)
        if y is None:
            continue
        groups.setdefault(str(k), []).append(float(y))
    return {
        k: {"mean": round(sum(v) / len(v), 4), "n": len(v)}
        for k, v in groups.items()
    }


def _compute_weights(corr: dict) -> dict:
    """从相关性自动出 director 选 topic 用的 weights。
    Rule: r >= MIN_R_FOR_WEIGHT (vs completion_rate as gold) + n >= MIN_SAMPLES → weight=r
    否则 weight=0。weight 0 = director 选 topic 时该 signal 不参与。
    """
    weights: dict[str, float] = {}
    for sig, perfs in corr.items():
        # 主 gold = completion_rate;弱辅 = avg_view_proportion
        cr = perfs.get("completion_rate") or {}
        avp = perfs.get("avg_view_proportion") or {}
        best_r, best_n = None, 0
        for src in (cr, avp):
            r, n = src.get("r"), src.get("n", 0)
            if r is None or n < MIN_SAMPLES:
                continue
            if best_r is None or abs(r) > abs(best_r):
                best_r, best_n = r, n
        if best_r is None or abs(best_r) < MIN_R_FOR_WEIGHT:
            weights[sig] = 0.0
        else:
            # 负相关也是信号(eg 高 obscurity → 低 completion),但 director 用 abs
            # 时按方向调整(正 r → 加权正 selection,负 r → 加权 avoid)
            weights[sig] = round(best_r, 3)
    return weights


def main() -> int:
    rows = _pull_chain()
    print(f"chained events: {len(rows)} (snapshot→brief→video)")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = OUT_DIR / f"{today}.md"
    L: list[str] = []
    L.append(f"# AVA-trend Snapshot v3.1 → Reality Correlation — {today}")
    L.append("")
    L.append(f"> 把 v3.1 飞轮真转起来 — snapshot 信号 vs 真表现 Pearson。")
    L.append(f"> 链路 sample 数:**{len(rows)}**;有信任 r 需 n ≥ {MIN_SAMPLES}。")
    L.append("")

    if len(rows) < 3:
        L.append("## ⚠ 样本太少")
        L.append("")
        L.append(f"目前 chained event = {len(rows)} 条。需 ≥ {MIN_SAMPLES} 才能算稳定相关性。")
        L.append("下次新视频发布后,monitor 跑完会自动累加。继续等。")
        out_path.write_text("\n".join(L), encoding="utf-8")
        # 写 baseline weights (全 0)
        WEIGHTS_PATH.write_text(json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_samples": len(rows),
            "ready": False,
            "weights": {s: 0.0 for s in SNAPSHOT_SIGNALS},
        }, indent=2))
        print(f"wrote {out_path} (baseline, not enough samples)")
        return 0

    corr = _correlations(rows)
    weights = _compute_weights(corr)

    L.append("## A. Pearson correlation (snapshot signal × video perf)")
    L.append("")
    L.append(f"r ≥ ±{MIN_R_FOR_WEIGHT} + n ≥ {MIN_SAMPLES} = 有信任信号。bounce_rate_2s 已 invert(显示 1-bounce)。")
    L.append("")
    L.append("| signal \\ perf | " + " | ".join(PERF_SIGNALS) + " |")
    L.append("|---|" + "---|" * len(PERF_SIGNALS))
    for sig in SNAPSHOT_SIGNALS:
        cells = []
        for perf in PERF_SIGNALS:
            cell = corr[sig][perf]
            r, n = cell["r"], cell["n"]
            if r is None:
                cells.append(f"— (n={n})")
            else:
                emoji = "✅" if abs(r) >= MIN_R_FOR_WEIGHT and n >= MIN_SAMPLES else ""
                cells.append(f"{emoji} **{r}** n={n}")
        L.append(f"| `{sig}` | " + " | ".join(cells) + " |")
    L.append("")

    L.append("## B. 分组 mean(cluster_state / momentum / discoverability)")
    L.append("")
    for key in ("cluster_state", "momentum", "discoverability"):
        L.append(f"### by `{key}` — mean completion_rate")
        L.append("")
        gm = _group_means(rows, key)
        for k, v in sorted(gm.items(), key=lambda kv: -kv[1]["mean"]):
            L.append(f"- **{k}**: mean={v['mean']*100:.2f}% (n={v['n']})")
        L.append("")

    L.append("## C. 自动权重(director 下次选 topic 用)")
    L.append("")
    L.append(f"写入 `{WEIGHTS_PATH}`。director 选 topic 时按这权重 composite,让一轮比一轮真好。")
    L.append("")
    L.append("| signal | weight | 解读 |")
    L.append("|---|---:|---|")
    for sig, w in sorted(weights.items(), key=lambda kv: -abs(kv[1])):
        if w > 0:
            interp = f"正相关 — 高 {sig} 真 perf 高 → 加权选"
        elif w < 0:
            interp = f"负相关 — 高 {sig} 反而低 perf → 反向避"
        else:
            interp = "无信任信号(样本不够或 r 太低)"
        L.append(f"| `{sig}` | {w} | {interp} |")
    L.append("")

    L.append("## D. 飞轮判定")
    L.append("")
    nontrivial = sum(1 for w in weights.values() if abs(w) >= MIN_R_FOR_WEIGHT)
    L.append(f"- 真有信号的维度数:**{nontrivial} / {len(SNAPSHOT_SIGNALS)}**")
    if nontrivial == 0:
        L.append("- ⚠ **全 noise**:跟 AVA Judge r=-0.11 同款。v3.1 score 公式当前对真表现无预测能力。")
        L.append("  - 可能原因:样本太少 / score 公式抓的维度跟抖音算法不对齐 / cold-start 噪声压过信号")
        L.append("  - 短期:积累 ≥30 样本再判;长期:重审 score 公式各分量的设计前提")
    elif nontrivial < 3:
        L.append(f"- 部分有效。{nontrivial} 维度有信号,其他仍 noise — 这是健康起点。")
        L.append("  - director 已开始按这 {} 个有效信号选 topic,下轮 perf 应可观察")
    else:
        L.append(f"- 飞轮真在转:{nontrivial} 个 signal 真预测 perf。继续累 sample 收敛。")
    L.append("")

    out_path.write_text("\n".join(L), encoding="utf-8")
    WEIGHTS_PATH.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(rows),
        "ready": nontrivial > 0,
        "weights": weights,
        "report_path": str(out_path),
    }, indent=2, ensure_ascii=False))
    print(f"wrote {out_path}")
    print(f"wrote {WEIGHTS_PATH}")
    print(f"chain={len(rows)} nontrivial_signals={nontrivial}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
