---
name: scope-13-collect-channels
description: 13 个采集渠道分类 —— 短视频 / 搜索 / 文本社交 / 图文 / 长文 / 新闻。
schema-version: 0.2
visibility: public

trigger: 13 渠道 / collector / TikTok / Douyin / YouTube Shorts / Google Trends / Reddit / Twitter / Xiaohongshu / Instagram / Pinterest / Zhihu / Bilibili / GDELT
anti-trigger: 单平台 collector 实现细节

domain: ava-trend-douyin
applicable-project-types:
  - AVA-trend

status: active
version: 0.3.1

depends-on: []
composes-with:
  - flow-snapshot-v3-collect

provenance:
  source-project: AVA-trend
  source-file: README.md "13 个采集渠道" 章节
  approved-by: founder
  created: 2026-05-11

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
  domain-specific:
    channels-count: 13
---

## Rules

| 渠道类别 | 平台 |
|---|---|
| 短视频(3) | TikTok / Douyin / YouTube Shorts |
| 搜索行为(2) | Google Trends (SerpAPI 池) / Baidu Index |
| 文本社交(3) | Reddit (PRAW + subreddit pool) / Twitter/X / Weibo |
| 图文视觉(3) | Xiaohongshu / Instagram / Pinterest |
| 长文叙事(2) | Zhihu / Bilibili |
| 新闻媒体(2) | GDELT / Google News RSS |

**总计 13** 个独立 collector。

## Heuristics
- 三个需要登录的平台:`python -m trend_sense login all` 一次性走完(Playwright cookies 写到 ~/.ava/)
- 新闻媒体(GDELT / Google News)无 cookies,API key only
- 跨语言聚类自动合并同一现象(英文 Reddit + 中文 Weibo 可在同 cluster_id)

## Anti-Pattern
- ❌ 单平台采集后直接生 snapshot(应跨平台聚类)
- ❌ 同一现象的不同语言不合并(膨胀冗余 cluster)

## Hard-Forbidden
- ❌ 用 LLM 生成假 raw_item 当采集结果(违反 [[meta-trend-single-responsibility]])

## Soft-Avoid
- ⚠ 13 渠道不平均跑(某些渠道连续失败应降权,不能盲调)

## Judgment
collector 健康度:`tools/ava_health.py` 跑通各渠道 ping(API key 是否有效、cookies 是否过期)。

## Workflow
```bash
# 一次性登录
python -m trend_sense login all

# 全量 scan
python -m trend_sense scan --top 10

# 健康检查
python tools/ava_health.py
```

## References
- 完整 collector 实现:`AVA-trend/services/trend_sources/`
- 一句话定位:`README.md` "13 个采集渠道"
