---
name: playbook-rate-limit-window
description: X Free Tier 写配额窗口本地 DB 管理 —— rate_limit_windows 表追踪每窗口已用 ops;publisher 调用前必 check;保守计数(不依赖 X header)。
schema-version: 0.2
visibility: public

trigger: rate limit / rate_limit_windows / 配额窗口 / 24h rolling / publisher gate / X API 写限制
trigger-en: rate limit / rate_limit_windows / daily quota gate
anti-trigger: 无 rate limit 的 API / read API

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

provenance:
  source-project: SOVEREIGN-X
  source-file: AGENTS.md §Key Invariants + publisher/pipeline.py
  approved-by: founder
  created: 2026-05-24

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
---

## Rules

DB 表 `rate_limit_windows`:
- 每行 = 一次窗口快照(window_start_ts, ops_used, window_kind)
- window_kind: `daily` (24h rolling) / `hourly` 等
- publisher 调用前查最近窗口 ops_used,超 → skip + Hermes notify
- thread 算 N 条 ops(每 tweet 1 次)

**保守计数原则**:只信本地 DB,不信 X header(X 不返回所有 windows,且有滞后)。

## Heuristics

- daily 上限 50,日 budget 20(余量 30 应对突发)
- thread 5 tweets 算 5 ops;quote 1 ops;reply 1 ops
- monitor 不算写(GET),不计 rate

## Anti-Pattern

- ❌ post 前不 check rate_limit_windows → 触 429
- ❌ thread 只算 1 ops(实际是 5,会突破)
- ❌ 信任 X response header 做配额管理(可能滞后)

## Hard-Forbidden

- ❌ 突破 50/24h 上限(账号锁定)
- ❌ 关闭 rate gate 跑 production

## Soft-Avoid

- ⚠ window 粒度只有 daily(应加 hourly 防burst)
- ⚠ rate counter 不带 publisher_method 标签(混 X API + OpenClaw 数据混乱)

## Judgment

```sql
SELECT SUM(ops_used) FROM rate_limit_windows
WHERE window_start_ts > NOW() - INTERVAL '24h'
```

返回值 ≥ 50 → HARD STOP;≥ 20 → daily budget 用完。

## Workflow

```
M5 publish:
  used_24h = SELECT SUM ...
  if used_24h + tweets_to_post > 50: HARD STOP
  if used_24h + tweets_to_post > 20: warn + skip non-essential
  post →
    INSERT INTO rate_limit_windows (now(), tweets_count, 'daily')
```

## References

- 原文:`SOVEREIGN-X/AGENTS.md` §Key Invariants
- 实现:`SOVEREIGN-X/publisher/pipeline.py` + `SOVEREIGN-X/connectors/x_client.py`
- 日预算:[[meta-x-free-tier-budget]]
