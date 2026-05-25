---
name: tech-mock-mode-pattern
description: MOCK_MODE=true env 全 mock 模式 —— pipeline 不调任何真 API,返回写死的合理 mock,用于 CI / smoke test / 无 key 开发。
schema-version: 0.2
visibility: public

trigger: MOCK_MODE / smoke test / CI / mock 模式 / 无 API key 开发
trigger-en: MOCK_MODE / smoke test / mock mode
anti-trigger: production / real API 调试

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
  source-file: AGENTS.md §Code Standards + scripts/smoke_test.py
  approved-by: founder
  created: 2026-05-24

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
---

## Rules

- env `MOCK_MODE=true` → 所有 connector 跳过真 API,返回 mock
- mock 数据带 `_is_mock: true` 标记(便于下游识别)
- CI 用 MOCK_MODE 跑完整 pipeline:`MOCK_MODE=true python scripts/smoke_test.py`
- 生产 env **绝不** MOCK_MODE=true(deploy 脚本 assert env != mock)

## Heuristics

- mock 返回应是真实数据的结构同构 sample(便于发现 schema 漂移)
- mock 应模拟 happy path,异常路径走单元测试 mock(更细)
- CI run 时间应 < 60s(快速反馈)

## Anti-Pattern

- ❌ mock 数据不带 `_is_mock` 标记
- ❌ MOCK_MODE 在 production 偶发启动(没 assert)
- ❌ mock 返回空 dict(下游报错)

## Hard-Forbidden

- ❌ 生产 deploy 不 assert `MOCK_MODE != true`(灾难)
- ❌ mock 数据混入 DB / analytics(污染指标)

## Soft-Avoid

- ⚠ mock 数据长期不更新(与真 API schema 漂移)
- ⚠ mock 只覆盖部分 connector(全或无)

## Judgment

```python
# 每个 connector 入口
if os.getenv("MOCK_MODE") == "true":
    return _mock_response()  # 带 _is_mock: true
return _real_response()
```

## Workflow

```bash
# CI
MOCK_MODE=true python scripts/smoke_test.py

# 本地开发(无 API key)
MOCK_MODE=true python -m orchestrator.pipeline --dry-run
```

## References

- 原文:`SOVEREIGN-X/AGENTS.md` §Build Commands
- 实现:`SOVEREIGN-X/scripts/smoke_test.py`
- 与三级 connector:[[meta-three-tier-connector]] 的 tier 3
