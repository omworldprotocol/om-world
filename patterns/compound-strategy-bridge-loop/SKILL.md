---
name: compound-strategy-bridge-loop
description: SOVEREIGN-X 完整反馈闭环 —— M6 monitor 真数据 → M7 strategist 聚合 → strategy_latest.json → M2 priority boost / M3 winning hooks 注入;实测复利。
schema-version: 0.2
visibility: public

trigger: 反馈闭环 / strategy loop / M6-M7-M2-M3 loop / 实测复利 / 真实数据反哺
trigger-en: feedback loop / strategy bridge / real data backfeed
anti-trigger: 单次评分 / 单次反馈

domain: ai-traffic-x
applicable-project-types:
  - SOVEREIGN-X

status: active
version: 0.1.0

depends-on:
  - flow-m7-strategy-bridge
composes-with:
  - compound-winning-failure-loop
  - compound-judge-vs-reality-pearson

provenance:
  source-project: SOVEREIGN-X
  source-file: AGENTS.md §Key Invariants + 整 pipeline
  approved-by: founder
  created: 2026-05-24

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
---

## Rules

```
M6 monitor (每天) → DB.engagement_metrics
                  ↓
M7 strategist (每天) → strategy_latest.json:
                          - winning_topics (top engagement)
                          - winning_hooks  (top engagement first lines)
                          - judge_vs_reality_pearson
                  ↓
M2 planner (下次 run) → 读 winning_topics → priority_boost(类别 +0.2)
M3 creator (下次 run) → 读 winning_hooks → inject prompt
                  ↓
M5 publish → 流量 → M6 → ... 循环
```

## Heuristics

- 闭环周期:24h(M6 + M7 each)+ 下次 pipeline run
- 与 AVA-trend [[compound-winning-failure-loop]] 同构(跨项目通用模式)
- "判官质量" 自校准用 [[compound-judge-vs-reality-pearson]]

## Anti-Pattern

- ❌ M6 / M7 不跑(闭环断,M2/M3 退化为冷启动)
- ❌ M2/M3 不读 strategy_latest.json(忽视反馈)
- ❌ Pearson < 0 还信 winning(应停用 + 警报)

## Hard-Forbidden

- ❌ 用 mock engagement 数据(违反 [[meta-ava-create-traffic]])
- ❌ M7 写 strategy_latest.json 非 atomic(M2/M3 读到坏文件)

## Soft-Avoid

- ⚠ winning 列 >5 个(太宽)
- ⚠ strategy 不分 niche / topic_type(汇总过粗)

## Judgment

Pearson r 是元信号:
- r > 0.7:高度可信
- 0.3 < r ≤ 0.7:中等
- r ≤ 0.3:弱 → 调 LLM 评审 prompt

## Workflow

闭环每日运行,跨 24h 周期累积复利。

## References

- 原文:`SOVEREIGN-X/AGENTS.md` §Key Invariants
- bridge 文件:`SOVEREIGN-X/data/strategy_latest.json`
- 跨项目同构:[[compound-winning-failure-loop]] (AVA-trend)
- 元校准:[[compound-judge-vs-reality-pearson]]
