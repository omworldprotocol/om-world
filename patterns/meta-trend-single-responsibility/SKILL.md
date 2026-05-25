---
name: meta-trend-single-responsibility
description: Trend 模块 single responsibility —— 只回答"注意力流向 / 情绪共振 / 信息缺口";不做 tone / format / 平台决策 / 文案 / 摘要。
description-en: Trend module single responsibility — only answer "attention flow / emotion resonance / info gap"; does NOT do tone / format / platform / copy / summary.
schema-version: 0.2
visibility: public

trigger: trend 模块 / Snapshot v3.1 / attention / emotion / information_gap / 三大段输出 / 不做清单
trigger-en: trend module / Snapshot v3.1 / attention / emotion / information gap / not-do list
anti-trigger: 下游 Planner / Creator / Publisher / 仪表盘

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
  source-file: trend_docs/trend_module_contract_v3.md §一 + §二
  source-sessions: v3.1 schema 2026-05 起 authoritative
  approved-by: founder
  created: 2026-05-11

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
---

## Rules

Trend 模块只回答一个问题:**此刻全球集体注意力正在往哪里流动?它背后蕴含的情绪共振是什么?我能不能从中找到信息缺口?**

三大输出段对应三个子问题:
- `attention` —— 注意力流向(流到哪里)
- `emotion` —— 情绪共振(为什么能点燃)
- `information_gap` —— 信息缺口(抢先讲的护城河)

## Heuristics

- **直接判据**:snapshot 字段如以 `optimal_*` / `suggested_*` / `action_*` 开头 = 越界,砍掉
- v3.1 在 v3.0 上扩展 7 字段:narrative_framework / depth / resonance_score / diffusion_pattern / media_signature / canonical_entity LLM enrich / seed_accounts auto-derive

## Anti-Pattern

- ❌ trend 直接调 LLM 做 likely_causes / amplification 增强(信号留给下游)

## Hard-Forbidden

下面这些事 **trend 模块不做**:
- ❌ 决定用什么 tone / perspective / format → Planner
- ❌ 生成视觉风格 / color / motion → Creator
- ❌ 写文案 / 钩子 / 标题 → Creator
- ❌ 决定发布哪个平台 / 时段 → Publisher
- ❌ 生成 highlights / risks / action_suggestions → 拼装层
- ❌ 调 LLM 做 likely_causes / amplification(trend 不调 LLM)

## Soft-Avoid

- ⚠ snapshot 字段命名带主观词("好" / "差" / "应该") —— 应客观信号

## Judgment

字段名 prefix 检查:
- ✅ 客观信号(`score`, `momentum`, `breadth`, `freshness`...)
- ❌ 建议性字段(`optimal_*`, `suggested_*`, `action_*`)

## Workflow

```
13 平台 collector → raw_item dict →
  trend_sense scan → Snapshot v3.1 dict →
    交给下游(Planner / Creator / Publisher)
```

## References

- 原文:`AVA-trend/trend_docs/trend_module_contract_v3.md` §一+§二
- v3.1 schema:同上 §四
- 13 渠道:[[scope-13-collect-channels]]
- 三波形:[[playbook-trend-3-waveforms]]
- 5 叙事框架:[[playbook-narrative-frameworks]]
