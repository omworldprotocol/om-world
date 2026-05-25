---
name: flow-m7-strategy-bridge
description: M7 strategist 把 M6 真实 engagement 数据聚合成 strategy_latest.json,回灌 M2 priority boost + M3 winning hooks —— 闭环复利。
schema-version: 0.2
visibility: public

trigger: M7 strategist / strategy_latest.json / strategy bridge / M2 priority / M3 winning hooks / 闭环反馈
trigger-en: M7 strategist / strategy bridge / strategy_latest.json
anti-trigger: 单次 M2 选题 / 单次 M3 创作

domain: ai-traffic-x
applicable-project-types:
  - SOVEREIGN-X

status: active
version: 0.1.0

depends-on:
  - flow-9-stage-pipeline
composes-with:
  - compound-strategy-bridge-loop
  - flow-strategy-real-data-feedback

provenance:
  source-project: SOVEREIGN-X
  source-file: AGENTS.md §Key Invariants + strategist/pipeline.py
  approved-by: founder
  created: 2026-05-24

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
  domain-specific:
    bridge-file: "data/strategy_latest.json"
    consumers: ["M2_priority_boost", "M3_winning_hooks"]
---

## Rules

`data/strategy_latest.json` 是 M7 → M2/M3 的**唯一**反馈通道:

```jsonc
{
  "generated_at": "<ISO>",
  "sample_count": int,
  "winning_topics": [...],       // M2 priority boost 输入
  "winning_hooks": [...],        // M3 prompt inject
  "judge_vs_reality_pearson": float
}
```

M2 / M3 启动时读此文件;不存在 / 过期(>14 天) / 样本不足(<2) → 不用(冷启动 safe)。

## Heuristics

- 与 AVA-trend 的 [[flow-strategy-real-data-feedback]] 完全同构 —— 跨项目通用
- M7 每 24h 跑一次(避免数据噪声)
- bridge file 是 atomic write(tmp + rename)避免 M2/M3 读到部分写

## Anti-Pattern

- ❌ M2/M3 用 LLM 预测分代替真实数据(违反 [[meta-ava-create-traffic]] 真实流量定义)
- ❌ strategy_latest.json 同步覆盖(应 tmp + rename)

## Hard-Forbidden

- ❌ M7 用模拟 / mock engagement 数据(必须 M6 真抓)
- ❌ Pearson < 0 还用 winning(应停用)

## Soft-Avoid

- ⚠ strategy_latest.json 字段名漂移(M2/M3 会断)
- ⚠ M7 sample window 太小(<2 → 不可信)

## Judgment

```python
report = json.loads(Path("data/strategy_latest.json").read_text())
if report["sample_count"] < 2: skip
if (now - report["generated_at"]).days > 14: skip
```

## Workflow

```
M6 monitor → DB engagement rows →
M7 strategist (every 24h):
  read DB → aggregate → Pearson(predicted, real) →
  atomic write strategy_latest.json
M2 planner (next run):
  read strategy_latest.json → priority_boost(winning_topics)
M3 creator (next run):
  read strategy_latest.json → inject winning_hooks to prompt
```

## References

- 原文:`SOVEREIGN-X/AGENTS.md` §Key Invariants
- 实现:`SOVEREIGN-X/strategist/pipeline.py`
- 跨项目对应:[[flow-strategy-real-data-feedback]] (AVA-trend)
- 元校准:[[compound-judge-vs-reality-pearson]]
