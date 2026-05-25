---
name: meta-ava-create-traffic
description: AVA-trend 系列的核心目标 —— 用 AI 创造真实平台流量(完播 / 涨粉 / engagement),不是只生成内容。
description-en: Core goal of the AVA-trend family — use AI to create real platform traffic (completion / followers / engagement), not just generate content.
schema-version: 0.2
visibility: public

trigger: AI 创造流量 / AVA-trend / AVA-MI / ACVA / SOVEREIGN-X / OM-WORLD-X / 抖音 / TikTok / X / IG / 小红书 / 短视频 / 内容生成 / 涨粉 / 完播率
trigger-en: AI traffic creation / Douyin / TikTok / Instagram / Reels / short video / content generation / view count / completion rate / followers
anti-trigger: 一次性内容外包 / 离线 PPT / 不上平台的内容

domain: ava-trend-douyin
applicable-project-types:
  - AVA-trend
  - AVA-MI
  - ACVA
  - SOVEREIGN-X
  - OM-WORLD-X

status: active
version: 0.1.0

depends-on: []
extends: []
composes-with:
  - meta-eight-traffic-principles
  - compound-winning-failure-loop

provenance:
  source-project: AVA-trend
  source-file: README.md + founder 战略对话(2026-05-24)
  source-sessions: 5 个项目(AVA-trend/AVA-MI/ACVA/SOVEREIGN-X/OM-WORLD-X)全部在跑
  approved-by: founder
  created: 2026-05-24

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
  domain-specific:
    target-platforms: ["Douyin", "TikTok", "X", "Instagram", "Xiaohongshu"]
    success-definition: "completion_rate > median(niche) AND followers_delta > 0"
---

## Rules

- AI 创造流量 = AI 自动产出**真实平台上**有完播 / 涨粉 / engagement 的内容流
- "完成"的硬定义:**视频/帖子真的发布到平台 + 24h 内有真实数据回报** —— 生成不算完成、本地不算完成
- 5 个生产项目共享此目标:AVA-trend(抖音 hub)/ AVA-MI(IG)/ ACVA(候选)/ SOVEREIGN-X(X 英文)/ OM-WORLD-X(X OMW 主号)
- 不是流量生意的(如 defi-auto-audit)不归本 Pattern 服务

## Heuristics

- 当前阶段:**生成 ≠ 流量** —— 5 个项目都能生成内容,但**还产生不了流量**(founder 自述)
- 短视频 reach ~70% 由前 3 秒决定 → hook 是第一优先级(见 [[flow-hook-gate-3sec]])
- 内容生成成本快速归零 → 区分度在 **私有判定**("什么能爆")+ **真实反馈循环**(发出去看数据)
- AI 越强 → 内容供给越饱和 → 真实流量越稀缺 → "怎么爆"的私有 judgment 越值钱

## Anti-Pattern

- ❌ 把"生成 N 条 / 天"当 KPI(应该是"发出去且跑赢同类 N 条 / 天")
- ❌ 不接平台数据回流(等于盲打)
- ❌ 多平台同一份内容平铺(每平台调性 + 算法都不同,见 [[scope-topic-type-fit]])

## Hard-Forbidden

- ❌ 把"AI 生成完一个视频"等同于"流量目标达成" —— 违反核心目标定义
- ❌ 用 LLM 自评分代替平台真实数据(LLM 自评 ≠ 算法判定)
- ❌ 模拟流量数据当训练信号(必须真实平台反馈)

## Soft-Avoid

- ⚠ 选题与账号人设不一致(算法降权,长期掉粉)
- ⚠ 一次发太多内容(刷屏 → 单条 reach 降低)
- ⚠ 不跟评 / 不回评 —— 损失 engagement 信号

## Judgment

判定一个"AI 创造流量"动作是否真完成:
- 发布:`publisher` 服务确认平台 returned 200 + 拿到 platform_video_id
- 24h 监控:`monitor` 服务回抓 view_count / completion_rate / likes / comments / followers_delta
- 跑赢同类:用 `strategy` 服务的 `judge_vs_reality_pearson`(见 [[compound-judge-vs-reality-pearson]])

主观判定:见 [[meta-eight-traffic-principles]] 8 流量第一性原理。

## Workflow

```
Snapshot(trend) → 选题 → 创作(灌 8 原理) → 评审 → 发布 → 监控 → 数据回流
       ↑                                                         ↓
       └───────────── Pattern 复利 + 策略反馈 ────────────────────┘
```

5 项目共用此 workflow,差别在 niche / 平台 / 调性。

## References

- 战略对话:OMW 进阶讨论 2026-05-24
- 5 项目仓库:`/Users/feiyang/all_bots/{AVA-trend,AVA-MI,ACVA,SOVEREIGN-X,OM-WORLD-X}/`
- 8 原理:[[meta-eight-traffic-principles]]
- 反馈机制:[[compound-winning-failure-loop]] + [[compound-judge-vs-reality-pearson]]
