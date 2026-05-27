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

# P3-D 2026-05-27: parameterized via GROWTH_PROJECT (default sovereign_x for back-compat).
# 改 GROWTH_PROJECT=om_world_x 即跑 OM-WORLD-X 同款日报。
_PROJECT = os.environ.get("GROWTH_PROJECT", "sovereign_x")
_PROJECT_BRANDS = {
    "sovereign_x": {
        "display": "SOVEREIGN-X",
        "handle_default": "invaribreak",
        "remote_db_default": "/root/SOVEREIGN-X/data/sovereign_x.db",
        "out_subdir": "sovereign_x_growth",
        "kind": "x_text",  # bookmark/depth/KOL
    },
    "om_world_x": {
        "display": "OM-WORLD-X",
        "handle_default": "OmWorldprotocol",
        "remote_db_default": "/root/OM-WORLD-X/data/om_world_x.db",
        "out_subdir": "om_world_x_growth",
        "kind": "x_text",
    },
    "ava_trend": {
        "display": "AVA-trend (Chigu_channel)",
        "handle_default": "Chigu_channel",
        "remote_db_default": "/Users/feiyang/all_bots/AVA-trend/data/publish.db",  # Mac local
        "out_subdir": "ava_trend_growth",
        "kind": "douyin_video",  # completion / hook / subscribe
    },
}
_BRAND = _PROJECT_BRANDS.get(_PROJECT, _PROJECT_BRANDS["sovereign_x"])

OUT_DIR = OMW_ROOT / "runtime" / _BRAND["out_subdir"]
OUT_DIR.mkdir(parents=True, exist_ok=True)

SSH_KEY = os.environ.get("OMW_SERVER_SSH_KEY",
                         str(Path.home() / ".ssh" / "hetzner_ash_key"))
SERVER_HOST = os.environ.get("OMW_SERVER_HOST", "root@87.99.153.204")
# back-compat: SOVEREIGN_X_DB env 仍优先(老 plist 还在用),否则按 GROWTH_PROJECT 选默认
REMOTE_DB = (os.environ.get("SOVEREIGN_X_DB") if _PROJECT == "sovereign_x" else None) \
            or os.environ.get("REMOTE_DB") \
            or _BRAND["remote_db_default"]


def _q(sql: str) -> list[dict]:
    # 本地 db 走 sqlite3 直读;远端走 ssh
    if Path(REMOTE_DB).exists():
        cmd = ["sqlite3", "-json", REMOTE_DB, sql]
    else:
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
    """P3-D 2026-05-27 真涨流量 3 大指标:bookmark / KOL eng / conversation depth.
    旧 likes/retweets/replies/impressions 保留作 context,但**判定真涨流量看新 3 个**。
    """
    # bookmark + impression + likes (tweet_stats per-tweet)
    rows = _q(
        f"SELECT tweet_id, MAX(impression_count) max_imp, "
        f"MAX(like_count + retweet_count + reply_count) max_eng, "
        f"MAX(COALESCE(bookmark_count,0)) max_bookmark, "
        f"MAX(COALESCE(max_reply_depth,0)) max_depth "
        f"FROM tweet_stats "
        f"WHERE fetched_at > datetime('now','-{days} days') "
        f"GROUP BY tweet_id"
    )
    if not rows:
        return {"n": 0, "avg_imp": 0.0, "avg_engagement_rate": 0.0,
                "total_imp": 0, "total_eng": 0,
                "total_bookmarks": 0, "bookmark_rate": 0.0,
                "n_with_bookmark": 0, "n_with_depth_ge2": 0,
                "kol_eng_7d": 0, "kol_eng_distinct_handles": 0}
    total_imp = sum(r.get("max_imp") or 0 for r in rows)
    total_eng = sum(r.get("max_eng") or 0 for r in rows)
    total_bookmarks = sum(r.get("max_bookmark") or 0 for r in rows)
    n = len(rows)
    n_with_bookmark = sum(1 for r in rows if (r.get("max_bookmark") or 0) > 0)
    n_with_depth = sum(1 for r in rows if (r.get("max_depth") or 0) >= 2)

    # KOL engagement (kol_engagement 表)
    kol_rows = _q(
        f"SELECT kol_handle, COUNT(*) n FROM kol_engagement "
        f"WHERE engaged_at > datetime('now','-{days} days') GROUP BY kol_handle"
    )
    kol_eng_7d = sum(r.get("n") or 0 for r in kol_rows)
    kol_distinct = len(kol_rows)

    return {
        "n": n,
        "avg_imp": round(total_imp / n, 1) if n else 0,
        "avg_engagement_rate": round(total_eng / max(total_imp, 1), 4),
        "total_imp": total_imp,
        "total_eng": total_eng,
        # P3-D 真涨流量指标
        "total_bookmarks": total_bookmarks,
        "bookmark_rate": round(total_bookmarks / max(total_imp, 1), 5),
        "n_with_bookmark": n_with_bookmark,
        "n_with_depth_ge2": n_with_depth,
        "kol_eng_7d": kol_eng_7d,
        "kol_eng_distinct_handles": kol_distinct,
    }


def _by_content_type(days: int = 7) -> list[dict]:
    """P3-D 2026-05-27: per content_type breakdown — article vs single vs thread vs reply.

    Returns list[dict] sorted by n_posts desc:
      {content_type, n_posts, avg_imp, avg_bookmark_rate, avg_max_reply_depth, kol_eng}
    """
    rows = _q(
        f"SELECT pp.content_type, "
        f"COUNT(DISTINCT ts.tweet_id) n_posts, "
        f"AVG(ts.impression_count) avg_imp, "
        f"AVG(CASE WHEN ts.impression_count > 0 "
        f"          THEN CAST(COALESCE(ts.bookmark_count,0) AS FLOAT) / ts.impression_count "
        f"          ELSE 0 END) avg_bookmark_rate, "
        f"AVG(COALESCE(ts.max_reply_depth,0)) avg_max_reply_depth "
        f"FROM tweet_stats ts "
        f"JOIN published_posts pp ON pp.tweet_ids LIKE '%' || ts.tweet_id || '%' "
        f"WHERE pp.published_at > datetime('now','-{days} days') "
        f"  AND ts.fetched_at = (SELECT MAX(ts2.fetched_at) FROM tweet_stats ts2 WHERE ts2.tweet_id = ts.tweet_id) "
        f"GROUP BY pp.content_type"
    )
    if not rows:
        return []
    # KOL eng per content_type
    kol_rows = _q(
        f"SELECT pp.content_type, COUNT(*) n FROM kol_engagement ke "
        f"JOIN published_posts pp ON pp.tweet_ids LIKE '%' || ke.source_tweet_id || '%' "
        f"WHERE ke.engaged_at > datetime('now','-{days} days') "
        f"GROUP BY pp.content_type"
    )
    kol_map = {r.get("content_type") or "unknown": int(r.get("n") or 0) for r in kol_rows}
    out: list[dict] = []
    for r in rows:
        ct = r.get("content_type") or "unknown"
        out.append({
            "content_type": ct,
            "n_posts": int(r.get("n_posts") or 0),
            "avg_imp": round(float(r.get("avg_imp") or 0), 1),
            "avg_bookmark_rate": round(float(r.get("avg_bookmark_rate") or 0), 5),
            "avg_max_reply_depth": round(float(r.get("avg_max_reply_depth") or 0), 2),
            "kol_eng": kol_map.get(ct, 0),
        })
    out.sort(key=lambda x: -x["n_posts"])
    return out


def _douyin_account_snapshots() -> list[dict]:
    """AVA-trend account_stats 表 schema 不同:follower_count / aweme_count
    (vs SOVX/OMX 的 followers / total_tweets)。"""
    return _q(
        "SELECT fetched_at, follower_count AS followers, "
        "following_count AS following, aweme_count AS total_tweets, "
        "total_favorited "
        "FROM account_stats ORDER BY fetched_at ASC"
    )


def _douyin_engagement_window(days: int = 7) -> dict:
    """AVA-trend 真涨流量信号:completion/hook/subscribe(完播率/2s跳出/转粉)。"""
    # per video latest stats — 只取每条最新一行,跳 P3-AVA fix 之前的旧行(bounce 等 NULL)
    rows = _q(
        f"SELECT ts.queue_id, ts.plays, ts.likes, "
        f"ts.completion_rate, ts.completion_rate_5s, ts.bounce_rate_2s, "
        f"ts.avg_view_proportion, ts.like_rate, "
        f"COALESCE(ts.subscribe_count,0) sub_n, "
        f"COALESCE(ts.dislike_count,0) dis_n "
        f"FROM video_stats ts "
        f"WHERE ts.fetched_at > datetime('now','-{days} days') "
        f"  AND ts.fetched_at = (SELECT MAX(fetched_at) FROM video_stats ts2 "
        f"                         WHERE ts2.queue_id = ts.queue_id) "
        f"  AND ts.bounce_rate_2s IS NOT NULL"
    )
    # 字段重命名 + clamp(向下兼容老 helper 期望的 max_X 名字)
    rows = [{
        "max_plays": r.get("plays") or 0,
        "max_likes": r.get("likes") or 0,
        "max_cr": r.get("completion_rate") or 0,
        "max_cr5": r.get("completion_rate_5s") or 0,
        "max_bounce": r.get("bounce_rate_2s") if r.get("bounce_rate_2s") is not None else 1,
        "max_avp": r.get("avg_view_proportion") or 0,
        "max_lr": r.get("like_rate") or 0,
        "sub_n": r.get("sub_n") or 0,
        "dis_n": r.get("dis_n") or 0,
    } for r in rows]
    if not rows:
        return {"n": 0, "avg_completion": 0.0, "avg_bounce_2s": 0.0,
                "avg_completion_5s": 0.0, "avg_avp": 0.0,
                "total_subscribe": 0, "total_dislike": 0,
                "n_with_completion_ge5pct": 0, "n_with_bounce_le40": 0,
                "n_with_subscribe": 0,
                "total_plays": 0, "total_likes": 0,
                "avg_like_rate": 0.0}
    n = len(rows)
    avg_completion = sum((r.get("max_cr") or 0) for r in rows) / n
    avg_cr5 = sum((r.get("max_cr5") or 0) for r in rows) / n
    avg_bounce = sum((r.get("max_bounce") or 0) for r in rows) / n
    avg_avp = sum((r.get("max_avp") or 0) for r in rows) / n
    avg_lr = sum((r.get("max_lr") or 0) for r in rows) / n
    total_sub = sum((r.get("sub_n") or 0) for r in rows)
    total_dis = sum((r.get("dis_n") or 0) for r in rows)
    total_plays = sum((r.get("max_plays") or 0) for r in rows)
    total_likes = sum((r.get("max_likes") or 0) for r in rows)
    return {
        "n": n,
        "avg_completion": round(avg_completion, 4),
        "avg_completion_5s": round(avg_cr5, 4),
        "avg_bounce_2s": round(avg_bounce, 4),
        "avg_avp": round(avg_avp, 4),
        "avg_like_rate": round(avg_lr, 5),
        "total_subscribe": total_sub,
        "total_dislike": total_dis,
        "net_subscribe": total_sub - total_dis,
        "n_with_completion_ge5pct": sum(1 for r in rows if (r.get("max_cr") or 0) >= 0.05),
        "n_with_bounce_le40": sum(1 for r in rows if (r.get("max_bounce") or 1) <= 0.40),
        "n_with_subscribe": sum(1 for r in rows if (r.get("sub_n") or 0) > 0),
        "total_plays": total_plays,
        "total_likes": total_likes,
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
    if _BRAND.get("kind") == "douyin_video":
        return _main_douyin()
    snaps = _account_snapshots()
    eng = _engagement_window(7)
    pace = _publish_pace(7)
    delta = _follower_delta(snaps)
    by_ct = _by_content_type(7)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = OUT_DIR / f"{today}.md"
    L: list[str] = []
    L.append(f"# {_BRAND['display']} Growth Report — {today}")
    L.append("")
    L.append(f"> 衡量 OMW 接入(governance/compliance.py check_omw_guards 2026-05-27 起)")
    L.append(f"> 是否真帮 @{os.environ.get('X_USERNAME', _BRAND['handle_default'])} 涨流量。")
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

    L.append("## P3-D 真涨流量 3 大指标(7d)")
    L.append("")
    L.append(f"### 🔴 1. Bookmark(X 算法 2024+ 核心信号)")
    L.append(f"- 7d 总 bookmarks:**{eng['total_bookmarks']}**")
    L.append(f"- bookmark rate (bookmarks/impressions):{eng['bookmark_rate']}")
    L.append(f"- 有 ≥1 bookmark 的推 / 总推:{eng['n_with_bookmark']} / {eng['n']}")
    L.append("")
    L.append(f"### 🔴 2. KOL Engagement(高杠杆受众捕获)")
    L.append(f"- 7d KOL 互动总数:**{eng['kol_eng_7d']}**")
    L.append(f"- 7d 不同 KOL 数:{eng['kol_eng_distinct_handles']}")
    L.append("")
    L.append(f"### 🔴 3. Conversation Depth(真受众想接着聊)")
    L.append(f"- 7d 有 ≥2 round reply 的推:**{eng['n_with_depth_ge2']}** / {eng['n']}")
    L.append("")
    L.append("## P3-D content_type 拆分(article vs single vs thread vs reply)")
    L.append("")
    if not by_ct:
        L.append("_无 per content_type 数据 — 等 monitor 跑一次新 schema_")
    else:
        L.append("| content_type | n_posts | avg_imp | bookmark_rate | avg_depth | kol_eng |")
        L.append("|---|---|---|---|---|---|")
        for r in by_ct:
            L.append(
                f"| **{r['content_type']}** | {r['n_posts']} | {r['avg_imp']:.1f} "
                f"| {r['avg_bookmark_rate']*100:.3f}% | {r['avg_max_reply_depth']:.2f} | {r['kol_eng']} |"
            )
        # 对比 article vs single 一线判定
        ct_map = {r["content_type"]: r for r in by_ct}
        if "article" in ct_map and "single" in ct_map:
            a, s = ct_map["article"], ct_map["single"]
            if s["avg_imp"] > 0:
                ratio = a["avg_imp"] / s["avg_imp"]
                L.append("")
                L.append(f"**article vs single reach 比**:{ratio:.2f}× "
                         f"({'article 占优' if ratio >= 1.2 else 'single 占优' if ratio <= 0.83 else '持平'}) — "
                         f"若 ≥1.5× 持续 14d → article 路径 invest 加倍")
    L.append("")
    L.append("## 内容节奏 + 旧指标(context)")
    L.append("")
    L.append(f"- 发推数:{pace}")
    L.append(f"- 7d 推 (有 stats):{eng['n']}")
    L.append(f"- 7d 平均 impressions:{eng['avg_imp']}")
    L.append(f"- 7d 平均 engagement_rate:{eng['avg_engagement_rate']}")
    L.append(f"- 7d 总 impressions:{eng['total_imp']}")
    L.append(f"- 7d 总 engagements:{eng['total_eng']}")
    L.append("")

    L.append("## OMW 接入价值评估(P3-D 标准)")
    L.append("")
    L.append("**真涨流量判定**(替代 followers 这个滞后虚荣指标):")
    L.append("- 接入后 14 天:total_bookmarks > 0 OR kol_eng_7d > 0 OR n_with_depth_ge2 > 0 = OMW 正向迹象")
    L.append("- 接入后 30 天:bookmark_rate ≥ 0.005 (0.5%) OR kol_eng_distinct ≥ 3 OR avg_depth ≥ 0.3 = OMW 真生效")
    L.append("- 接入后 30 天:3 指标全 0 = winning Pattern 没真改变 LLM 行为 → 加 enforcement")
    L.append("- 接入后 60 天:全 0 = OMW 这个方向错 / SOVEREIGN-X niche X 无受众 → 撤回")
    L.append("")
    L.append("**当前 baseline(2026-05-27 OMW P3-D 接入起点)**:")
    L.append(f"- total_bookmarks (7d): {eng['total_bookmarks']}")
    L.append(f"- kol_eng_7d: {eng['kol_eng_7d']}")
    L.append(f"- n_with_depth_ge2: {eng['n_with_depth_ge2']}")
    L.append(f"- followers: {delta.get('current')} (虚荣,仅 context)")
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


def _main_douyin() -> int:
    """AVA-trend / douyin video 路径 — 真涨流量 3 大信号 completion/hook/subscribe。"""
    snaps = _douyin_account_snapshots()
    delta = _follower_delta(snaps)
    eng = _douyin_engagement_window(7)
    pace = _publish_pace(7)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = OUT_DIR / f"{today}.md"
    L: list[str] = []
    L.append(f"# {_BRAND['display']} Growth Report — {today}")
    L.append("")
    L.append(f"> 衡量 AVA-trend → OMW Pattern 演化是否真帮 @{_BRAND['handle_default']} 涨流量。")
    L.append(f"> 真涨流量信号:**completion_rate / bounce_rate_2s / subscribe** 三件,不是 plays(plays 是 cold-start 抽奖)。")
    L.append("")

    L.append("## 账号增长(account_stats 抓取)")
    L.append("")
    if delta["current"] is None:
        L.append("_无 account_stats 数据 — 等 monitor 跑过一次再看_")
    else:
        L.append(f"- **当前 followers**:{delta['current']}")
        L.append(f"- 24h Δ:{delta['d1']}")
        L.append(f"- 7d Δ:{delta['d7']}")
        L.append(f"- 30d Δ:{delta['d30']}")
        L.append(f"- 持平天数:{delta['stagnant_days']}")
        if delta["stagnant_days"] and delta["stagnant_days"] >= 7:
            L.append("- 🔴 **GROWTH GAP**:7+ 天 followers 无变化,触发 propose_evolutions § E 信号")
    L.append("")

    L.append("## P3-AVA 真涨流量 3 大指标(7d)")
    L.append("")
    L.append(f"### 🔴 1. Completion(抖音算法 2024+ 核心信号)")
    L.append(f"- 7d 平均 completion_rate:**{eng['avg_completion']*100:.2f}%** (target ≥ 5%)")
    L.append(f"- 7d 平均 completion_rate_5s:{eng['avg_completion_5s']*100:.2f}% (target ≥ 30%)")
    L.append(f"- 7d 平均 avg_view_proportion:{eng['avg_avp']*100:.2f}%")
    L.append(f"- 完播 ≥ 5% 的视频 / 总视频:{eng['n_with_completion_ge5pct']} / {eng['n']}")
    L.append("")
    L.append(f"### 🔴 2. Hook strength(0-2s 钩子)")
    L.append(f"- 7d 平均 bounce_rate_2s:**{eng['avg_bounce_2s']*100:.2f}%** (target ≤ 35%)")
    L.append(f"- 2s 跳出 ≤ 40% 的视频 / 总视频:{eng['n_with_bounce_le40']} / {eng['n']}")
    L.append("")
    L.append(f"### 🔴 3. Subscribe conversion(转粉)")
    L.append(f"- 7d 总 subscribe:**{eng['total_subscribe']}** (target ≥ 1/week)")
    L.append(f"- 7d 总 dislike:{eng['total_dislike']}")
    L.append(f"- 7d 净涨粉 (subscribe-dislike):{eng['net_subscribe']}")
    L.append(f"- 有 subscribe 的视频 / 总视频:{eng['n_with_subscribe']} / {eng['n']}")
    L.append("")
    L.append("## 内容节奏 + 旧指标(context)")
    L.append("")
    L.append(f"- 发推数(7d):{pace}")
    L.append(f"- 7d 视频 (有 stats):{eng['n']}")
    L.append(f"- 7d 总 plays:{eng['total_plays']}(注:plays 受 cold-start 抽奖 影响 ≫ 内容质量)")
    L.append(f"- 7d 总 likes:{eng['total_likes']}")
    L.append(f"- 7d 平均 like_rate:{eng['avg_like_rate']*100:.3f}%")
    L.append("")

    L.append("## OMW 接入价值评估(P3-AVA 标准)")
    L.append("")
    L.append("**真涨流量判定**(替代 plays/followers 虚荣指标):")
    L.append("- 14 天:avg_completion ≥ 5% OR n_with_subscribe > 0 = OMW 正向迹象")
    L.append("- 30 天:avg_completion ≥ 10% AND avg_bounce_2s ≤ 35% AND total_subscribe ≥ 3 = OMW 真生效")
    L.append("- 30 天:3 指标全无改善 = winning Pattern 没真改变 director 行为 → 升级 enforcement")
    L.append("- 60 天:全无改善 = OMW 方向错 / 频道选题或风格 nichefit 错 → 重选 niche")
    L.append("")
    L.append("**当前 baseline(2026-05-27 P3-AVA 接入起点)**:")
    L.append(f"- avg_completion (7d): {eng['avg_completion']*100:.2f}%")
    L.append(f"- avg_bounce_2s (7d): {eng['avg_bounce_2s']*100:.2f}%")
    L.append(f"- total_subscribe (7d): {eng['total_subscribe']}")
    L.append(f"- followers: {delta.get('current')}")
    L.append("")

    L.append("## 历史快照(account_stats)")
    L.append("")
    L.append("| Day | followers | following | total_works | total_favorited |")
    L.append("|---|---|---|---|---|")
    by_day: dict[str, dict] = {}
    for s in snaps:
        d = (s.get("fetched_at") or "")[:10]
        if d:
            by_day[d] = s
    for d in sorted(by_day.keys()):
        s = by_day[d]
        L.append(f"| {d} | {s.get('followers')} | {s.get('following')} | {s.get('total_tweets')} | {s.get('total_favorited')} |")
    L.append("")

    out_path.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {out_path}")
    if delta["current"] is not None:
        print(f"followers={delta['current']} d7={delta['d7']} stagnant={delta['stagnant_days']}d")
    print(f"completion_avg={eng['avg_completion']*100:.2f}% "
          f"bounce_2s_avg={eng['avg_bounce_2s']*100:.2f}% "
          f"subscribe_7d={eng['total_subscribe']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
