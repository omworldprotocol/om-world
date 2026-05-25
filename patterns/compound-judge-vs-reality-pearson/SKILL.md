---
name: compound-judge-vs-reality-pearson
description: Judge vs Reality 相关性自校准 —— 计算 A12 预测分 vs 抖音真实完播率的 Pearson r,作为"判官质量"元信号注入下游 prompt。
schema-version: 0.2
visibility: public

trigger: Pearson / judge vs reality / 判官校准 / 预测 vs 真实 / 元信号 / 自校准
anti-trigger: 单次 A12 评分

domain: ava-trend-douyin
applicable-project-types:
  - AVA-trend

status: active
version: 0.1.0

depends-on:
  - flow-strategy-real-data-feedback
composes-with:
  - compound-winning-failure-loop

provenance:
  source-project: AVA-trend
  source-file: services/strategy/(M7 服务)+ solo_writer._format_strategy
  approved-by: founder
  created: 2026-05-23

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
  domain-specific:
    metric: "Pearson r (A12.total vs real_completion_rate)"
---

## Rules

每个周期(每天 / 每周):
1. 取过去 N 天发布视频
2. 对每条:`(A12_total_when_published, real_completion_rate_24h)`
3. 计算 Pearson r
4. 写 `strategy_latest.json:judge_vs_reality_pearson`
5. 下游 Solo Writer prompt 注入:"(Judge 预测分 vs 真实完播率 相关性 r=0.42)"

## Heuristics
- r > 0.7:Judge 高度可信 → winning_takes 强信号
- 0.3 < r ≤ 0.7:中等 → 可参考但不照搬
- r ≤ 0.3:Judge 信号弱 → 人工 review 调 A12 prompt
- r < 0:Judge 反向相关 → **停用 winning 注入**,触发警报

## Anti-Pattern
- ❌ 不告诉 LLM r 值(失去元信号)
- ❌ 用 Spearman 不用 Pearson(强行换 metric 不告 LLM)

## Hard-Forbidden
- ❌ 用模拟数据算 Pearson(必须真实平台数据)
- ❌ r < 0 还继续用 A12 winning 当指导(必须停用 + 警报)

## Soft-Avoid
- ⚠ N 太小(< 10 条)算 Pearson(噪声极大,应等更多样本)
- ⚠ Pearson 跨 niche 混算(应按 topic_type / channel 分别算)

## Judgment
Pearson 公式确定性,但 N 不够时不可信。

## Workflow
```
strategy 服务每天:
  N = 过去 7 天发布且监控到完播率的视频
  if N >= 10:
    r = pearson([(a12, real) for v in videos])
    strategy_latest.json:judge_vs_reality_pearson = r
  else:
    skip (留 null)

Solo Writer 调用:
  if r is not None: inject "Pearson r=..."
```

## References
- M7 strategy 服务:`AVA-trend/services/strategy/`
- 注入逻辑:`director/solo_writer.py:_format_strategy`
- 与 experience 关系:[[compound-winning-failure-loop]] 是预测层闭环;本 Pattern 是预测 vs 真实的元校准
