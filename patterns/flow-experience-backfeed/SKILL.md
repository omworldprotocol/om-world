---
name: flow-experience-backfeed
description: 双向经验回流 —— A12 总分 ≥0.78 → winning_patterns;low_dims < 0.5 → failure_patterns;下次 Solo Writer prompt 自动 inject。
description-en: Bidirectional experience backfeed — A12 total ≥0.78 → winning_patterns; low_dims < 0.5 → failure_patterns; auto-inject next Solo Writer call.
schema-version: 0.2
visibility: public

trigger: 经验回流 / winning_patterns / failure_patterns / experience backfeed / ExperienceStore / solo_writer 经验注入
trigger-en: experience backfeed / winning patterns / failure patterns
anti-trigger: 一次性 prompt 调试(无累积)

domain: ava-trend-douyin
applicable-project-types:
  - AVA-trend

status: active
version: 0.1.0

depends-on:
  - flow-director-pipeline-v3
composes-with:
  - compound-winning-failure-loop

provenance:
  source-project: AVA-trend
  source-file: services/director/pipeline.py:_backfeed_winning / _backfeed_failure
  source-sessions: 2026-05 起每个 brief 都 trigger
  approved-by: founder
  created: 2026-05-11

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
  domain-specific:
    winning-threshold: 0.78
    failure-low-dim-threshold: 0.5
    max-winning-patterns-kept: 8
    inject-top-k-winning: 3
    inject-recent-k-failure: 3
---

## Rules

**winning_patterns 回流**(A12 total ≥ 0.78):
```
[<total>/<decision>] hook: <hook_line>  |  story: <story_core>  |  analogy: <cross_domain_analogy>
```
保留 8 条最近,FIFO 替换。

**failure_patterns 回流**(low_dims 任一 < 0.5):
```json
{
  "brief_id": "...",
  "low_dims": {"dim": score, ...},
  "bad_hook": "...",
  "bad_decision": {"hook": "...", "beats": [...], "cta": "..."},
  "a12_reason": "前 3 项 revise_suggestions",
  "a12_total": float
}
```

**下次 Solo Writer prompt inject**:
- 取 top 3 winning_patterns,以 "## 历史高分脚本(参考风格,不要照抄)" 注入
- 取最近 3 failure_patterns,以 "## 近期被 A12 扣分的反例(避免重蹈)" 注入

## Heuristics

- winning 阈值 0.78 < GO 阈值 0.85 —— 故意稍宽,捕捉接近通过的优质 polish/revise 输出
- failure 阈值 0.5 = REVISE 下限 —— 标记真正的"低质量错误"而非"次优"
- "参考风格,不要照抄" 提示防 LLM 直接复读(增加变体)

## Anti-Pattern

- ❌ winning_patterns 无去重 → 同一脚本被 pinned 多次(膨胀)
- ❌ failure_patterns 不带 a12_reason → 下次 prompt 只看到"避免"但不知为何
- ❌ inject 时不区分 winning vs failure → LLM 混淆

## Hard-Forbidden

- ❌ 把 NO_GO 脚本写进 winning_patterns(规则禁,代码强制 total >= 0.78)
- ❌ winning_patterns 跨 niche / 跨 channel 混入(应按 SOLO_AGENT_NAME 隔离)

## Soft-Avoid

- ⚠ winning_patterns 超 8 条不裁剪(prompt context 膨胀)
- ⚠ failure_patterns 永久累积(应有 30 天 / 100 条 windowed 淘汰)

## Judgment

代码层闭环(无 LLM 判断):
- `_backfeed_winning(audit_report, script, store, brief_id)` 自动判 total >= 0.78
- `_backfeed_failure(audit_report, script, store, brief_id, threshold=0.5)` 自动收集 low_dims
- `solo_writer._format_experience(store, k=3)` 在每次 Solo Writer 调用前自动 inject

## Workflow

```
Brief 完成 (audit_report) →
  if audit_report.total >= 0.78:
    _backfeed_winning(...)
  if any dim < 0.5:
    _backfeed_failure(...)

下次 Solo Writer 调用 →
  store.top_winning_patterns(SOLO_AGENT_NAME, k=3) → "## 历史高分脚本"
  store.recent_failure_patterns(SOLO_AGENT_NAME, k=3) → "## 近期被 A12 扣分的反例"
  → 注入 prompt
```

## References

- 主文件:`AVA-trend/services/director/pipeline.py` (`_backfeed_winning` + `_backfeed_failure`)
- 注入逻辑:`AVA-trend/services/director/solo_writer.py:_format_experience`
- 存储:`AVA-trend/services/director/data/experiences/solo_writer.json`
- 与策略数据关系:[[flow-strategy-real-data-feedback]]
