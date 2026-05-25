---
name: meta-three-tier-connector
description: 所有外部 connector 必须三级 fallback —— real API → fallback/warning → mock(MOCK_MODE=true);单 API 挂不能停 pipeline。
description-en: All external connectors must follow 3-tier fallback — real API → fallback → mock; single API outage must never stop pipeline.
schema-version: 0.2
visibility: public

trigger: connector / three-tier / fallback / MOCK_MODE / DeepSeek SerpAPI fal.ai / 外部 API 容错
trigger-en: connector / three-tier fallback / MOCK_MODE / external API resilience
anti-trigger: 内部模块调用 / 数据库 client

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
  - tech-mock-mode-pattern
  - tech-fire-and-forget-hermes

provenance:
  source-project: SOVEREIGN-X
  source-file: AGENTS.md §Code Standards
  approved-by: founder
  created: 2026-05-24

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
  domain-specific:
    tiers: ["real", "fallback", "mock"]
---

## Rules

每个外部 API connector 三级 fallback:

| Tier | 描述 | 何时触发 |
|---|---|---|
| 1 real | 真 API 调用 | 默认 |
| 2 fallback | 替代源 / 降级模式(如 RSS 替 SerpAPI、cached response) | real 失败 + 有 fallback 可用 |
| 3 mock | 写死的合理 mock 返回 | `MOCK_MODE=true` env / 所有上游挂 |

connector 永远不能抛 unhandled exception 给 pipeline,只允许返回带 warning 的 fallback。

## Heuristics

- MOCK_MODE 用于 CI / smoke test / 开发时无 API key
- fallback 应是真实可用的替代源(不是空 dict),例:`feedparser RSS` 替 SerpAPI
- Hermes 在 fallback 触发时 fire-and-forget 通知(见 [[tech-fire-and-forget-hermes]])

## Anti-Pattern

- ❌ connector 失败直接抛异常给上层(应 catch + fallback)
- ❌ fallback 是空 dict / None(下游会再炸)
- ❌ 把 MOCK_MODE 当生产开关(应是开发环境 only)

## Hard-Forbidden

- ❌ mock 数据混进真生产(MOCK_MODE 在生产 env 必须 false)
- ❌ 在 fallback / mock 模式下假装是 real(必须显式 log / metric)

## Soft-Avoid

- ⚠ fallback 链 >2 层(real → fallback1 → fallback2 → mock)—— 太复杂
- ⚠ mock 返回不带 `_is_mock: true` 标记(下游难判)

## Judgment

每个 connector 单元测试覆盖 3 tier:
- real: 用 vcr.py 录回放
- fallback: mock real 失败
- mock: MOCK_MODE=true

## Workflow

```python
# 标准三级模板
def fetch_news(query):
    if os.getenv("MOCK_MODE") == "true":
        return _mock_news(query)
    try:
        return _real_serpapi(query)
    except Exception as e:
        hermes.notify(f"SerpAPI down: {e}", fire_and_forget=True)
        try:
            return _fallback_rss(query)
        except Exception as e2:
            hermes.notify(f"RSS also down: {e2}", fire_and_forget=True)
            return _mock_news(query)
```

## References

- 原文:`SOVEREIGN-X/AGENTS.md` §Code Standards
- 实现:`SOVEREIGN-X/connectors/*.py` 每个都遵循
- 相关:[[tech-mock-mode-pattern]] / [[tech-fire-and-forget-hermes]]
