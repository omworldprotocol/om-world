# OM World Pattern Library · INDEX (public)

> Schema: [PATTERN_SCHEMA.md](PATTERN_SCHEMA.md) v0.2.1
> 提炼时间:持续累积
> Visibility:本索引**只列 visibility=public 的 Pattern**(private Pattern 在私有 overlay 仓库,通过 `OMW_PATTERN_PATH` 环境变量加载)

## 本索引说明

OMW Pattern 库的分层模型:

- **本仓库(`om-world/patterns/`)** 只承载 **visibility=public 的 Pattern + 协议层**
- 业务私有 Pattern 通过 `OMW_PATTERN_PATH=<public>:<private>` 多目录 overlay 在客户端加载
- 这与 Git 协议公开 / 你的 private repo 永远 private 是同一类模型

详细分层架构见 [ARCHITECTURE.md](../ARCHITECTURE.md)。

---

## 元 Pattern(战略定位 + 通用框架)

| ID | 描述 |
|---|---|
| meta-ava-create-traffic | "AI 创造流量" 系列项目的核心目标定义(真实平台 traffic ≠ 内容生成) |
| meta-trend-single-responsibility | Trend 模块 single-responsibility:只回答 attention / emotion / info_gap 三段 |
| meta-x-free-tier-budget | X API Free Tier 硬预算(50/24h 写;日预算 20 ops 分配) |
| meta-three-tier-connector | 外部 API connector 三级 fallback(real → fallback → mock) |

## 流程 Pattern(通用反馈机制 + 跨项目桥)

| ID | 描述 |
|---|---|
| flow-experience-backfeed | 双向经验回流(winning + failure patterns 自动 inject 下次 prompt) |
| flow-strategy-real-data-feedback | 真实平台数据 → strategy_latest.json → 回灌 prompt(冷启动 safe) |
| flow-m7-strategy-bridge | M7 strategist 把实测 engagement 聚合 → M2/M3 反馈通道 |

## Playbook Pattern(平台 / 工具集成)

| ID | 描述 |
|---|---|
| playbook-openclaw-x-bypass | OpenClaw + Chrome CDP 绕过 X API(无 X API key 也能发推) |
| playbook-rate-limit-window | X Free Tier 写配额本地 DB 管理(rate_limit_windows 表) |

## Tech Pattern(通用工程模式)

| ID | 描述 |
|---|---|
| tech-fire-and-forget-hermes | Hermes 通知 fire-and-forget(失败绝不阻塞主流程) |
| tech-mock-mode-pattern | MOCK_MODE=true env 全 mock(CI / smoke test / 无 key 开发) |
| tech-no-hardcoded-secrets | 所有 secrets 走 env(python-dotenv),never hardcoded |

## Scope Pattern(范围 + 平台约束)

| ID | 描述 |
|---|---|
| scope-13-collect-channels | 13 个流量采集渠道分类(短视频 / 搜索 / 文本 / 图文 / 长文 / 新闻) |
| scope-x-platform-constraints | X 平台完整约束(Free Tier + Search 不可用 + Monitor 范围) |
| scope-characterfile-persona | characterfile.yaml 驱动 persona 模式(content 与 governance 都读 yaml) |

## Compound Pattern(复利机制)

| ID | 描述 |
|---|---|
| compound-winning-failure-loop | AI 创造流量的复利引擎(A12 评分双向回流) |
| compound-architecture-evolution-ab | 12-agent committee → Solo Writer A/B 演化(架构选择必须 A/B 数据驱动) |
| compound-judge-vs-reality-pearson | Judge 预测 vs 真实数据 Pearson 元校准 |
| compound-strategy-bridge-loop | M6 monitor → M7 strategist → M2/M3 完整反馈闭环 |

## 统计

- **19 个 public Pattern**,涉及 6 个层级
- 内容覆盖:AI 流量创造通用框架 + X 平台公开约束 + 通用工程模式 + 反馈复利机制
- **0 public Pack**(所有 Pack 都因含 private Pattern 而归 private overlay)

## 加载方式

```bash
# 仅 public Pattern(默认)
export OMW_PATTERN_PATH=/path/to/om-world/patterns

# Public + Private overlay(本地开发者私有库)
export OMW_PATTERN_PATH=/path/to/om-world/patterns:/path/to/your-private/patterns
```

加载逻辑见 [sdk/README.md](../sdk/README.md)。

---

**贡献新 public Pattern**:见 PATTERN_SCHEMA.md。提交 PR 时,Pattern frontmatter 必须含 `visibility: public` 且通过 SDK 加载验证。
