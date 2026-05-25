---
name: tech-fire-and-forget-hermes
description: Hermes 通知 fire-and-forget —— 通知失败绝不阻塞主 pipeline;async + timeout + 错误吞掉只 log。
schema-version: 0.2
visibility: public

trigger: Hermes / 通知 / fire-and-forget / async notification / 不阻塞
trigger-en: Hermes / notification / fire-and-forget
anti-trigger: 同步 critical 信息(应走主流程,不是通知)

domain: ai-traffic-x
applicable-project-types:
  - SOVEREIGN-X
  - AVA-trend
  - OM-WORLD-X
  - AVA-MI
  - ACVA

status: active
version: 0.1.0

composes-with:
  - meta-three-tier-connector

provenance:
  source-project: SOVEREIGN-X
  source-file: AGENTS.md §Code Standards + connectors/hermes.py
  approved-by: founder
  created: 2026-05-24

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
---

## Rules

`hermes.notify(message, **opts)`:
- 异步(用 threading / asyncio task)
- timeout 严格(默认 5s)
- 任何异常吞掉只 log,never raise
- 不影响调用方返回值

## Heuristics

- 用于:rate limit 触发、fallback 触发、stage failure、deploy 完成
- 不用于:critical 流程信号(那走主流程 return)
- 高频通知(>10/min)聚合发送(避免 spam)

## Anti-Pattern

- ❌ `hermes.notify()` 抛异常 propagate(违反 fire-and-forget)
- ❌ 同步等 hermes return 才继续(阻塞主流程)
- ❌ hermes 失败导致 pipeline 失败

## Hard-Forbidden

- ❌ hermes 用于流程 critical 信号(应走主返回值)

## Soft-Avoid

- ⚠ 单次任务通知 >5 条(应聚合)
- ⚠ 不带 module 标签(下游难分类)

## Judgment

`hermes.notify()` 实现:
- 启 daemon thread → POST 到 Telegram / webhook
- 主 thread 立即 return
- thread 内任何异常吞 + log

## Workflow

```python
# 标准用法 — 永不影响主流程
def publisher_post(draft):
    try:
        result = x_client.post(draft.text)
    except RateLimitError as e:
        hermes.notify(f"⚠ rate limit: {e}", module="publisher")
        return None  # 不抛出
    return result
```

## References

- 原文:`SOVEREIGN-X/AGENTS.md` §Code Standards
- 实现:`SOVEREIGN-X/connectors/hermes.py`
- 与三级 connector:[[meta-three-tier-connector]] fallback 时常触发 hermes
