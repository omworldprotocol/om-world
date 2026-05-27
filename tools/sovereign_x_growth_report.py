#!/usr/bin/env python3
"""sovereign_x_growth_report.py — P3-C 2026-05-27 真衡量 OMW 是否帮 SOVEREIGN-X
涨流量。读取 hetzner-ash:/root/SOVEREIGN-X/data/sovereign_x.db 的 account_stats +
tweet_stats + published_posts,生成日报 markdown 到
om-world/runtime/sovereign_x_growth/<date>.md。

核心指标(决定 OMW 价值的真信号):
  - followers 增量(日/周/月)
  - total_tweets 节奏
  - 每日 avg_impressions / avg_engagement_rate 趋势(7d rolling)
  - 增长无变化连续天数 → 触发 propose_evolutions growth-gap 信号

OMW 接入 SOVEREIGN-X 是否有用 = 接入后 followers 真涨 / engagement 真涨。
若 4 周后无变化 = OMW 这个方向错。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

OMW_ROOT = Path(os.environ.get("OMW_ROOT",
    str(Path(__file__).resolve().parent.parent)))
OUT_DIR = OMW_ROOT / "runtime" / "sovereign_x_growth"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SSH_KEY = os.environ.get("OMW_SERVER_SSH_KEY",
                         str(Path.home() / ".ssh" / "hetzner_ash_key"))
SERVER_HOST = os.environ.get("OMW_SERVER_HOST", "root@87.99.153.204")
REMOTE_DB = os.environ.get("SOVEREIGN_X_DB", "/root/SOVEREIGN-X/data/sovereign_x.db")


def _q(sql: str) -> list[dict]:
    cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
           SERVER_HOST, f"sqlite3 -json {REMOTE_DB} \"{sql}\""]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0 or not r.stdout.strip():
        return []
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return []


def _account_snapshots() -> list[dict]:
    return _q(
        "SELECT fetched_at, followers, following, total_tweets "
        "FROM account_stats ORDER BY fetched_at ASC"
    )


def _publish_pace(days: int = 7) -> int:
    rows = _q(
        f"SELECT COUNT(*) as n FROM published_posts "
        f"WHERE published_at > datetime('now','-{days} days')"
    )
    return rows[0].get("n", 0) if rows else 0


def _engagement_window(days: int = 7) -> dict:
    """Latest stats per tweet in last N days, then avg impression / engagement_rate."""
    rows = _q(
        f"SELECT tweet_id, MAX(impression_count) max_imp, "
        f"MAX(like_count + retweet_count + reply_count) max_eng "
        f"FROM tweet_stats "
        f"WHERE fetched_at > datetime('now','-{days} days') "
        f"GROUP BY tweet_id"
    )
    if not rows:
        return {"n": 0, "avg_imp": 0.0, "avg_engagement_rate": 0.0,
                "total_imp": 0, "total_eng": 0}
    total_imp = sum(r.get("max_imp") or 0 for r in rows)
    total_eng = sum(r.get("max_eng") or 0 for r in rows)
    n = len(rows)
    return {
        "n": n,
        "avg_imp": round(total_imp / n, 1) if n else 0,
        "avg_engagement_rate": round(total_eng / max(total_imp, 1), 4),
        "total_imp": total_imp,
        "total_eng": total_eng,
    }


def _follower_delta(snaps: list[dict]) -> dict:
    """Compute followers delta over 1d / 7d / 30d windows."""
    if not snaps:
        return {"current": None, "d1": None, "d7": None, "d30": None,
                "stagnant_days": None}
    by_day: dict[str, int] = {}
    for s in snaps:
        ts = s.get("fetched_at", "")[:10]
        if ts and s.get("followers") is not None:
            by_day[ts] = max(by_day.get(ts, 0), int(s["followers"]))
    if not by_day:
        return {"current": None, "d1": None, "d7": None, "d30": None,
                "stagnant_days": None}
    days_sorted = sorted(by_day.keys())
    today = days_sorted[-1]
    current = by_day[today]

    def _delta(offset_days: int) -> int | None:
        from datetime import datetime as _dt, timedelta as _td
        target = (_dt.strptime(today, "%Y-%m-%d") - _td(days=offset_days)).strftime("%Y-%m-%d")
        # find closest day at or before target
        candidates = [d for d in days_sorted if d <= target]
        if not candidates:
            return None
        return current - by_day[candidates[-1]]

    # stagnant days = how many consecutive days followers stayed flat
    stagnant = 0
    for d in reversed(days_sorted):
        if by_day[d] == current:
            stagnant += 1
        else:
            break

    return {
        "current": current,
        "d1": _delta(1),
        "d7": _delta(7),
        "d30": _delta(30),
        "stagnant_days": stagnant,
    }


def main() -> int:
    snaps = _account_snapshots()
    eng = _engagement_window(7)
    pace = _publish_pace(7)
    delta = _follower_delta(snaps)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = OUT_DIR / f"{today}.md"
    L: list[str] = []
    L.append(f"# SOVEREIGN-X Growth Report — {today}")
    L.append("")
    L.append(f"> 衡量 OMW 接入(governance/compliance.py check_omw_guards 2026-05-27 起)")
    L.append(f"> 是否真帮 @{os.environ.get('X_USERNAME','invaribreak')} 涨流量。")
    L.append(f"> 若 4 周后 followers / engagement 无显著变化 = OMW 这个方向错。")
    L.append("")

    L.append("## 账号增长(account_stats 抓取)")
    L.append("")
    if delta["current"] is None:
        L.append("_无 account_stats 数据 — 等 monitor cron 跑过一次再看_")
    else:
        L.append(f"- **当前 followers**:{delta['current']}")
        L.append(f"- 24h Δ:{delta['d1']}")
        L.append(f"- 7d Δ:{delta['d7']}")
        L.append(f"- 30d Δ:{delta['d30']}")
        L.append(f"- 持平天数:{delta['stagnant_days']}")
        if delta["stagnant_days"] and delta["stagnant_days"] >= 7:
            L.append("- 🔴 **GROWTH GAP**:7+ 天 followers 无变化,触发 propose_evolutions 增长信号")
    L.append("")

    L.append("## 内容节奏(过去 7 天)")
    L.append("")
    L.append(f"- 发推数:{pace}")
    L.append(f"- 7d 推 (有 stats 的):{eng['n']}")
    L.append(f"- 7d 平均 impressions:{eng['avg_imp']}")
    L.append(f"- 7d 平均 engagement_rate:{eng['avg_engagement_rate']}")
    L.append(f"- 7d 总 impressions:{eng['total_imp']}")
    L.append(f"- 7d 总 engagements:{eng['total_eng']}")
    L.append("")
    if eng["avg_engagement_rate"] == 0 and eng["n"] >= 5:
        L.append("- 🟡 **engagement_rate=0**:winning_hooks 仅是 0 engagement 池里相对最高,")
        L.append("  反馈环 garbage-in;P3-A' (strategist cold-start mode) 待做")
    L.append("")

    L.append("## OMW 接入价值评估")
    L.append("")
    L.append("**判定标准**(对比 OMW 接入前 baseline followers=3):")
    L.append("- 接入后 14 天:followers 增 +1~+3 = OMW 至少不害,继续观察")
    L.append("- 接入后 30 天:followers 增 +5 + engagement_rate > 0 = OMW 真有正向贡献")
    L.append("- 接入后 30 天:followers 无变化 = OMW 防降权可能有效但不够,需 P3-A'/B' 跟上")
    L.append("- 接入后 60 天:无变化 = OMW 方向错,撤回")
    L.append("")

    L.append("## 历史快照(account_stats)")
    L.append("")
    L.append("| Day | followers | following | total_tweets |")
    L.append("|---|---|---|---|")
    by_day: dict[str, dict] = {}
    for s in snaps:
        d = s.get("fetched_at", "")[:10]
        if d:
            # take latest of day
            by_day[d] = s
    for d in sorted(by_day.keys()):
        s = by_day[d]
        L.append(f"| {d} | {s.get('followers')} | {s.get('following')} | {s.get('total_tweets')} |")
    L.append("")

    out_path.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {out_path}")
    if delta["current"] is not None:
        print(f"followers={delta['current']} (d1={delta['d1']} d7={delta['d7']} d30={delta['d30']} stagnant={delta['stagnant_days']}d)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
