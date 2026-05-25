---
name: scope-x-platform-constraints
description: X 平台完整约束 —— Free Tier 写 50/24h、Search API 不可用、Monitor 只读自家 + mention;OpenClaw bypass 路径与 X API 路径互斥。
schema-version: 0.2
visibility: public

trigger: X 平台约束 / X API / Free Tier 限制 / Search 不可用 / Monitor 范围
trigger-en: X platform constraints / X API Free Tier
anti-trigger: 非 X 平台(抖音/IG/小红书)

domain: ai-traffic-x
applicable-project-types:
  - SOVEREIGN-X
  - OM-WORLD-X

status: active
version: 0.1.0

depends-on:
  - meta-x-free-tier-budget
composes-with:
  - playbook-openclaw-x-bypass
  - playbook-rate-limit-window

provenance:
  source-project: SOVEREIGN-X
  source-file: AGENTS.md §X API Free Tier Constraints
  approved-by: founder
  created: 2026-05-24

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
---

## Rules

| 维度 | Free Tier 限制 |
|---|---|
| 写 | 50 ops/24h |
| Search | **不可用** |
| Monitor read | 只能读自家 tweets + mentions |
| Reply | 计入 50/24h 写额度 |
| Quote / Retweet | 同上 |
| Media | 单 tweet 4 张图;视频要 chunked upload |
| Poll | 单 tweet 一个 poll(2-4 选项,5min-7day) |

## Heuristics

- Search 不可用 → 走 [[playbook-openclaw-x-bypass]] 的 web-search / browse skill
- Monitor 限制 → 不能监控竞品账号(只能爬公开页面)
- 写额度紧张 → 部分用 OpenClaw 浏览器发(不占 API 额度)

## Anti-Pattern

- ❌ 用 X API search → 直接失败
- ❌ 同账号同时用 X API + OpenClaw 发(数据重复)
- ❌ 不计 reply 入额度(实际是写)

## Hard-Forbidden

- ❌ 突破 50/24h(账号锁)
- ❌ 用第三方账号代发(违反 X ToS)

## Soft-Avoid

- ⚠ 同 token 多 process 并发(rate limit 计数错乱)
- ⚠ poll 时长设太短(用户没看到就过期)

## Judgment

每次 publisher 调用前先查约束矩阵 → 选 API 还是 OpenClaw 路径。

## Workflow

```
publisher.decide_path(draft):
  if draft.kind == "search":
    return "openclaw-web-search"
  if draft.kind == "post":
    if X_API_quota OK and api_path_available:
      return "x-api"
    elif openclaw daemon up:
      return "openclaw-x-poster"
    else:
      skip
```

## References

- 原文:`SOVEREIGN-X/AGENTS.md` §X API Free Tier Constraints
- 实现:`SOVEREIGN-X/connectors/x_client.py`
