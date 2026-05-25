---
name: compound-architecture-evolution-ab
description: AVA-Director 架构 A/B 演化 —— 12-agent 委员会(v2)→ Solo Writer 单 LLM 调用(v3,2026-05 胜出),成本降 + 质量等价 → A/B 测试是架构选择的硬标准。
schema-version: 0.2
visibility: public

trigger: 架构演化 / A/B 测试 / 12-agent committee / Solo Writer / v3 vs v2 / 架构选择
anti-trigger: 单次架构调优(不涉及 v2 ↔ v3 对照)

domain: ava-trend-douyin
applicable-project-types:
  - AVA-trend

status: active
version: 0.1.0

depends-on:
  - flow-director-pipeline-v3
composes-with:
  - flow-experience-backfeed

provenance:
  source-project: AVA-trend
  source-file: services/committee/data/ab_tests/ab_20260511_154131/
  approved-by: founder
  created: 2026-05-11

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
  domain-specific:
    ab-test-rounds: 3
    winner: "v3 solo_writer"
    cost-reduction: ">50%"
    quality-delta: "~0"
---

## Rules

架构演化决策必须经 A/B 测试硬数据:
1. 提候选架构(例:12-agent vs 1-agent)
2. 同一批 brief 双跑(committee 跑一遍,solo writer 跑一遍)
3. 同一 A12 评审标准评分
4. 比较 cost(LLM tokens × time)+ quality(A12 total)
5. cost 大幅降 + quality 不显著降 → 切

## Heuristics
- 2026-05 实战:12-agent 委员会(roundtrip ~7 个 LLM 调用 + 串行)vs Solo Writer(1 个 LLM 调用)→ solo 胜出
- "委员会能产生 N agent 视角分歧" 假设 = 不成立(LLM 调用之间没记忆,各自 reasoning 类似)
- 一个 prompt 灌足够 brief 比拆成 N 个 sub-prompt 更连贯

## Anti-Pattern
- ❌ 凭直觉切架构(必须有 A/B 数据)
- ❌ A/B 跑 1 个 brief 就下结论(至少 3+ batches)

## Hard-Forbidden
- ❌ 把"理论上更优"当切换理由(必须实测)

## Soft-Avoid
- ⚠ committee 完全删除(保留作对照,见 services/committee/ 仍在仓库)
- ⚠ A/B 不跑就直接全部切

## Judgment
A/B 报告 `services/committee/data/ab_tests/ab_<timestamp>/summary.md` 含完整对比。

## Workflow
```
1. 起 hypothesis(例:"Solo Writer 比 committee 成本低 50%,质量相当")
2. 提取一批共 3 个 topic
3. 双跑 + 用同一 A12 评
4. 写 comparison.md(每 topic)+ summary.md(总)
5. 决定切 / 保留 / 改进
```

## References
- A/B test 数据:`AVA-trend/services/committee/data/ab_tests/`
- 当前架构:[[flow-director-pipeline-v3]]
- 旧架构对照:`AVA-trend/services/committee/`
