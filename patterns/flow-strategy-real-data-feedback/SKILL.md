---
name: flow-strategy-real-data-feedback
description: 抖音实测数据(完播率)→ M7 strategy_latest.json → Solo Writer prompt;A12 预测分 vs 真实完播率的 Pearson 相关性自校准。
description-en: Real Douyin data (completion rate) → M7 strategy_latest.json → Solo Writer prompt; Pearson correlation between A12 predicted score and real completion as self-calibration.
schema-version: 0.2
visibility: public

trigger: 真实数据反馈 / strategy_latest / 完播率 / Pearson / winning_topic_types / winning_takes / Judge vs reality
trigger-en: real data feedback / strategy report / completion rate / Pearson correlation / Judge calibration
anti-trigger: A12 LLM 自评分(那是 [[flow-director-pipeline-v3]] 的 A12)

domain: ava-trend-douyin
applicable-project-types:
  - AVA-trend

status: active
version: 0.1.0

depends-on:
  - flow-director-pipeline-v3
  - flow-experience-backfeed
composes-with:
  - compound-judge-vs-reality-pearson

provenance:
  source-project: AVA-trend
  source-file: services/director/solo_writer.py:_format_strategy
  source-sessions: M7 strategy 服务每日聚合
  approved-by: founder
  created: 2026-05-23

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
  domain-specific:
    min-sample-count: 2
    max-report-age-days: 14
    inject-fields: ["winning_topic_types", "winning_takes", "judge_vs_reality_pearson"]
---

## Rules

`STRATEGY_REPORT_PATH` (默认 `data/strategy_latest.json`)结构:
```json
{
  "generated_at": "<ISO timestamp>",
  "sample_count": int,
  "winning_topic_types": ["meme_phone", "tech_product_news"],
  "winning_takes": ["诙谐爆料"],
  "judge_vs_reality_pearson": 0.42
}
```

**注入条件(全部满足才 inject)**:
- 文件存在
- `sample_count >= 2`(冷启动安全)
- `(now - generated_at).days <= 14`(过期数据不用)
- `winning_topic_types` 或 `winning_takes` 至少一个非空

**注入格式**:
```
## 真实数据反馈(抖音实测跑赢的方向,优先靠拢)
- 完播率跑赢的选题类型:meme_phone、tech_product_news
- 跑赢视频的编辑态度参考:诙谐爆料
- (Judge 预测分 vs 真实完播率 相关性 r=0.42)
```

## Heuristics

- M7 = strategy 服务每日聚合抖音监控数据
- 这是 [[flow-experience-backfeed]] 的"真实信号"补充:experience 是 A12 预测;strategy 是平台真实反馈
- Pearson r 是元信息(告诉 LLM "A12 现在多可信")—— 不直接驱动行为,但提示
- "冷启动安全":只少于 2 个真实样本时静默(不 inject)

## Anti-Pattern

- ❌ sample_count 不检查直接 inject(冷启动 = noise)
- ❌ 过期报告(>14 天)继续 inject(平台算法可能已变)
- ❌ 用 A12 自评分代替真实完播率(Judge ≠ Reality)

## Hard-Forbidden

- ❌ 把模拟数据写进 strategy_latest.json(必须真平台 API 回抓,违反 [[meta-ava-create-traffic]] 核心定义)
- ❌ Pearson r < 0 时还信 winning_topic_types(Judge 反向相关 → 应停用 winning 注入)

## Soft-Avoid

- ⚠ winning_topic_types 列 > 5 个(过宽 → 无方向感)
- ⚠ inject 时不告诉 LLM "优先靠拢"(应明示 directive)

## Judgment

代码层(无 LLM):
```python
_format_strategy() →
  if not report.exists or sample_count < 2 or (now - generated_at).days > 14:
    return ""
  if not winning_topic_types and not winning_takes:
    return ""
  return "## 真实数据反馈\n..."
```

Pearson r 的判读(LLM 看到后调整置信度):
- r > 0.7:Judge 高度准确,winning_takes 强信号
- 0.3 < r ≤ 0.7:中等,可参考但不照搬
- r ≤ 0.3:Judge 信号弱,人工 review 调 prompt

## Workflow

```
M7 strategy 服务(每日):
  抓 24h 内发布视频 → 拿真实 view_count / completion_rate / engagement →
  聚合 by topic_type / editorial take →
  rank top winning →
  Pearson(A12_total, real_completion) →
  写 strategy_latest.json

Solo Writer 调用(每个 brief):
  _format_strategy() inject prompt 段
```

## References

- 主文件:`AVA-trend/services/director/solo_writer.py:_format_strategy`
- 上游:`AVA-trend/services/strategy/` (M7 strategy 服务)
- Pearson 含义:[[compound-judge-vs-reality-pearson]]
- 与 experience 关系:[[flow-experience-backfeed]] 是预测层,本 Pattern 是真实层
