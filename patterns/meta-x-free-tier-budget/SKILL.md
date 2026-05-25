---
name: meta-x-free-tier-budget
description: X API Free Tier 硬预算 —— 50 写/24h 上限;日预算 = 2 threads(5 tweets each) + 2
  singles + 8 auto-replies = 20 ops。
description-en: X API Free Tier hard budget — 50 writes/24h cap; daily = 2 threads
  + 2 singles + 8 auto-replies = 20 ops.
schema-version: 0.2
visibility: public
trigger: X API / Free Tier / rate limit / 50 写/24h / 20 ops/day / daily budget / rate_limit_windows
trigger-en: X API Free Tier / rate limit / daily budget
anti-trigger: X API Premium / Enterprise tier / 自部署 X-alternative
domain: ai-traffic-x
applicable-project-types:
- SOVEREIGN-X
- OM-WORLD-X
status: active
version: 0.1.0
depends-on: []
composes-with:
- playbook-rate-limit-window
- scope-x-platform-constraints
provenance:
  source-project: SOVEREIGN-X
  source-file: AGENTS.md §X API Free Tier Constraints
  approved-by: founder
  created: 2026-05-24
metrics:
  auto-tracked: false
  invoked: 2
  measured-success-rate: 1.0
  last-validated: '2026-05-24'
  domain-specific:
    daily-write-cap: 50
    daily-budget-threads: 2
    daily-budget-singles: 2
    daily-budget-auto-replies: 8
    daily-budget-total: 20
    _rolled:
      roundtrip:
        sum: 1
        avg: 1.0
        count: 1
      stage:
        last: final-smoke
        count: 1
---
## Rules

X API Free Tier 硬约束:
- `POST /2/tweets`: **50 写/24h**(rolling window)
- Search API:**完全不可用** — 不能调 `GET /2/tweets/search/recent`
- Monitor:只读自己推 + mentions
- 日预算:2 threads(每 thread 5 tweets) + 2 singles + 8 auto-replies = **20 ops/day**

## Heuristics

- 20 ops < 50 写上限 → 留 30 ops buffer 应对突发(重发 / 回滚)
- thread 算每条 tweet 一次(5 tweets/thread × 2 threads = 10 ops)
- Search 不可用 → 必须走 OpenClaw browser bypass(见 [[playbook-openclaw-x-bypass]])

## Anti-Pattern

- ❌ 不查 rate_limit_windows 就 post → 触发 429,账号被限流
- ❌ thread 计数器把 thread 算 1 次(实际是每 tweet 1 次)
- ❌ 用 X API search(根本不可用,会浪费 API key 测试)

## Hard-Forbidden

- ❌ 突破 50/24h 写上限(账号会被 X 临时锁定)
- ❌ 绕开本地 rate limit DB 计数(只信 X header 不准,X 不返回所有 windows)

## Soft-Avoid

- ⚠ 日预算用 ≥18 ops(余量不足应对 monitor / 紧急修)
- ⚠ thread 全集中一个时段发(分散到不同时段 reach 更广)

## Judgment

`connectors/x_client.py` 内部 `rate_limit_windows` DB 表统计每窗口已用 ops。
publisher 调用前必 check。

## Workflow

```
M5 publisher.post():
  if rate_limit_windows.used_today >= 20:
    skip + Hermes notify
  if rate_limit_windows.used_24h >= 50:
    HARD STOP
  post →
    rate_limit_windows += (1 if single else N for thread)
```

## References

- 原文:`SOVEREIGN-X/AGENTS.md` §X API Free Tier Constraints
- 实现:`SOVEREIGN-X/connectors/x_client.py`
- 绕开 Search 限制:[[playbook-openclaw-x-bypass]]
