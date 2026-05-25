---
name: compound-winning-failure-loop
description: AI 创造流量的复利引擎 —— 每条 brief 的 A12 评分双向回流(winning_patterns + failure_patterns),下次 Solo Writer 自动注入;Pattern 库每天加厚。
schema-version: 0.2
visibility: public

trigger: 复利引擎 / 双向回流 / winning failure loop / experience compound / pattern 积累 / 每天加厚
anti-trigger: 一次性 prompt / 无累积

domain: ava-trend-douyin
applicable-project-types:
  - AVA-trend
  - AVA-MI
  - ACVA
  - SOVEREIGN-X
  - OM-WORLD-X

status: active
version: 0.1.0

depends-on:
  - flow-experience-backfeed
composes-with:
  - flow-strategy-real-data-feedback
  - compound-judge-vs-reality-pearson

provenance:
  source-project: AVA-trend
  source-file: services/director/data/experiences/solo_writer.json + pipeline.py 回流逻辑
  approved-by: founder
  created: 2026-05-11

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
---

## Rules

复利闭环:
```
每条 brief 完成 →
  A12.total ≥ 0.78 → winning_patterns(top 8 FIFO)
  A12.low_dims < 0.5 → failure_patterns
  → 写到 data/experiences/<agent>.json

下次 Solo Writer 调用 →
  inject top 3 winning + recent 3 failure
  → LLM 学到 "什么风格被通过 / 什么被扣分"
  → 输出质量单调上升(理论)
```

## Heuristics
- winning vs failure 双向 = 解决 "只记成功 LLM 会变保守" 问题
- top 3 / recent 3 = context 预算约束(再多会膨胀)
- "参考风格不要照抄" 提示 = 防 LLM 直接复读
- 与 [[flow-strategy-real-data-feedback]] 互补:experience 是 A12 预测,strategy 是真实平台

## Anti-Pattern
- ❌ 只记 winning 不记 failure(LLM 不知该避什么)
- ❌ failure_patterns 不带 reason(下次 prompt 注入但不知为何被扣)
- ❌ winning_patterns 无 niche / agent 隔离(跨频道混入污染)

## Hard-Forbidden
- ❌ 把 LLM 自评分代替真实平台数据当 winning 信号(违反 [[meta-ava-create-traffic]] 核心)

## Soft-Avoid
- ⚠ winning 阈值过严(0.85+ → 太少样本,LLM 学不到模式)
- ⚠ failure window 不淘汰(累积 100+ 条 → context 爆炸)

## Judgment
- winning entries 数 ≥ 8 触发 FIFO 淘汰
- failure entries 应有 windowed(30 天 / 100 条)淘汰(目前未实现,改进项)

## Workflow
```
Day 1: 第一批 brief 跑 → 0 winning + 0 failure
Day 2: 部分 brief A12 通过 → winning 累积
Day N: prompt 注入逐渐变厚 → 输出质量单调上升
```

## References
- 主文件:`AVA-trend/services/director/data/experiences/solo_writer.json`
- 回流逻辑:`director/pipeline.py:_backfeed_winning / _backfeed_failure`
- 注入逻辑:`director/solo_writer.py:_format_experience`
- 真实数据补充:[[flow-strategy-real-data-feedback]]
