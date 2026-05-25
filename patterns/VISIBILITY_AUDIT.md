# OMW Pattern Visibility Audit · v0.3(最终版,已 founder 同意)

> **状态:✅ FROZEN —— founder 决策已锁(2026-05-24)**
> v0.2 → v0.3 关键修正:**defi-auto-audit 22 个全部 PRIVATE**(包括 3 个 tech-fork-fuzz-*)
> founder 决策:**defi-auto-audit 整个项目作为内部积累,Pattern 正常跑(SDK overlay),公开仓库不展示任何这个项目的信息**
>
> # 最终总计:om-world public 19 Pattern + 0 Pack;om-world-private 55 Pattern + 12 Pack
>
> v0.3 修正前文(供历史追溯):
> 起稿:2026-05-24
> v0.1 → v0.2 关键修正:**defi-audit 从 22 PUBLIC 大幅改为 19 PRIVATE / 3 PUBLIC**(founder 指出 v0.1 过度公开核心 IP)
>
> **v0.1 → v0.2 反思**:我 v0.1 犯了 4 个错误:
> 1. 混淆"公开知识"和"组织公开知识的体系"(playbook 的 organization 本身是 IP)
> 2. 在 dogfood 阶段过度依赖"声誉价值"(无用户 = 公开没人看 = 全输)
> 3. 低估 audit 行业复制成本(竞品有方法论框架后 ramp up 从 1 月→1 周)
> 4. 错用 OMW 协议公开逻辑套用到 product 上(协议公开是共生,product 方法论公开是削自己差异化)
>
> **修正原则**:**默认 PRIVATE,只有真"纯通用工程坑 / 公开平台约束 / 通用反馈机制"才 PUBLIC**。
>
> **review 方式**:逐条看,同意 → 不改;不同意 → 改 visibility 列 + 写理由;改完告诉我执行 Step 2 迁移。

---

## 一、判断原则

### 推荐 PUBLIC 的 Pattern(满足任一)

- ✅ 内容主要是**已公开知识**的组织(SWC / Solodit / Rekt / OZ docs / 平台官方文档)
- ✅ **抽象架构 / 元规则定义**(不含具体业务 calibration 数字)
- ✅ **通用工程模式**(MOCK_MODE / fire-and-forget / three-tier connector 等)
- ✅ **技术坑 / 失败教训分享**(声誉价值 > IP 价值,被引用反而 OMW 增信)
- ✅ **流程方法论描述**(描述方法本身,实现细节在代码里)

### 必须 PRIVATE 的 Pattern(满足任一即必 private)

- ❌ **业务流量战术 / hook 矩阵 / topic-type fit**(直接给对手能用的 advantage)
- ❌ **具体业务流程实现细节**(Director pipeline / Trend snapshot v3.1 schema 设计)
- ❌ **founder 创作技巧 / 调性 / persona 定义**(账号 IP / 品牌 IP)
- ❌ **真实业务 calibration 数字**(具体的成功阈值、判定 threshold、winning_topic 列表)

### 风险等级

- **L (Low)** — 公开后几乎无负面影响,声誉 / 教育价值高
- **M (Medium)** — 公开会暴露部分思路,但内容多公开知识,影响有限
- **H (High)** — 公开 = 送对手核心 IP / 直接 advantage

---

## 二、总计预览(v0.3 最终)

| 项目 | 总数 | PUBLIC | PRIVATE | 备注 |
|---|---|---|---|---|
| **defi-auto-audit** | 22 | **0** | **22** | **整项目作为内部积累 — 公开仓库不展示任何信息** |
| **ava-trend** | 22 | 8 | 14 | 不变 |
| **sovereign-x** | 14 | 11 | 3 | 不变 |
| **合计 om-world Pattern** | **58** | **19 (33%)** | **39 (67%)** | |
| wedgetest(om-world-private) | 16 | 0 | 16 | 不参审,整库 private |
| **OMW Pattern 库总计** | **74** | **19** | **55** | |

→ **36 个 om-world Pattern 需要物理迁移到 om-world-private**(Step 2)。

**保护的核心 IP(36 个 PRIVATE 概览)**:
- defi-audit 方法论体系(19 个):5 playbook + 5 flow + 3 scope + 2 compound + 3 meta + 1 tech-* 等
- ava-trend 流量战术(14 个):8 原理 + hook 矩阵 + topic-fit + Director + Trend schema
- sovereign-x 账号 IP(3 个):thesis + 9-stage + governance-gate

---

## 三、defi-auto-audit · 22 个(修正后 3 PUBLIC / 19 PRIVATE)

| Pattern ID | Layer | 推荐 visibility | 风险 | 理由 |
|---|---|---|---|---|
| meta-core-target-5dim | meta | **PRIVATE** | **H** | 5 维定义 = audit 业务 framework IP,公开 = 竞品 day-1 起步 |
| meta-vuln-db-3-layer | meta | **PRIVATE** | **H** | 复利机制设计是 IP,公开 = 送方法论 |
| meta-honest-0-discipline | meta | **PRIVATE** | M | 纪律 + 反向卖点,但属 framework IP |
| flow-6-stage-state-machine | flow | **PRIVATE** | **H** | audit_run.py 完整设计,公开 = 送 orchestrator 代码思路 |
| flow-edge-driven-audit | flow | **PRIVATE** | **H** | v10 方法论 = founder 5-9 月演化 IP |
| flow-red-team-pivot-v11 | flow | **PRIVATE** | **H** | v11 红方复盘 = 实战教训 IP |
| flow-adversarial-verifier | flow | **PRIVATE** | M | 对抗 verifier 设计 IP |
| flow-mermaid-3grep | flow | **PRIVATE** | M | LOAD-BEARING #1 强制项 + 3 grep 集合 IP |
| playbook-cross-cutting | playbook | **PRIVATE** | **H** | 15 边 organization + invariant + 命中频率 = 核心 IP(即使每条单 vuln 公开) |
| playbook-cdp | playbook | **PRIVATE** | **H** | 14 CDP 边体系 = 核心 IP |
| playbook-lending | playbook | **PRIVATE** | **H** | 12 Lending 边体系 = 核心 IP |
| playbook-yield-vault | playbook | **PRIVATE** | **H** | 11 Vault 边体系 = 核心 IP |
| playbook-dexs-amm | playbook | **PRIVATE** | **H** | 12 AMM 边体系 = 核心 IP |
| playbook-algo-stable | playbook | **PRIVATE** | **H** | 11 算稳边体系 = 核心 IP |
| **tech-fork-fuzz-anvil-rpc** | tech | **PUBLIC** | L | **保留 PUBLIC** — 纯 anvil 用法分享,对 audit 优势影响极小 |
| **tech-fork-fuzz-warp-oracle** | tech | **PUBLIC** | L | **保留 PUBLIC** — 纯 Chainlink 心跳 + warp 模式,通用工程 |
| **tech-fork-fuzz-no-mint-then-try** | tech | **PUBLIC** | L | **保留 PUBLIC** — 纯 handler 反模式(A0002 教训),社区贡献姿态 |
| scope-A-B-classify | scope | **PRIVATE** | **H** | A/B 分类 + 1463 候选门槛 = 选审计目标策略,IP |
| scope-three-streams | scope | **PRIVATE** | **H** | 新上线/proxy/重审 三流 = 候选发现策略,IP |
| scope-bespoke-priority | scope | **PRIVATE** | **H** | bespoke 优先 + fork 降权 = 排序启发式,IP |
| compound-process-lesson | compound | **PRIVATE** | M | §9.8 复利机制设计,IP |
| compound-scope-sanity-check | compound | **PRIVATE** | M | Unit 1 前 sanity check 流程,IP |

**defi-auto-audit 决策(修正后)**:
- **3 个 PUBLIC**(仅纯技术坑:anvil / warp-oracle / mint-then-try)
- **19 个 PRIVATE**(playbook + 方法论 + scope + 复利 + meta 全部)

**保护核心**:
- 5 playbook(组织体系本身是 IP,不只是 vuln 内容)
- v10 + v11 方法论(founder 多月演化结果)
- 5 维核心目标 + 漏洞库 3 层 + honest-0(framework IP)
- A/B 分类 + bespoke 优先(选审计目标的策略)

**为什么 3 tech-fork-fuzz-* 保留 PUBLIC**:
- 纯工程坑(anvil 用法 / Chainlink 心跳 / handler 反模式),没有 audit 业务 IP
- 对 audit 优势影响极小(知道 anvil 用法不会让对手抢走赏金)
- 公开作"贡献 Foundry 社区"姿态,有少量声誉收益
- 若 founder 仍想 PRIVATE 也行(共 3 条,影响极小)

---

## 四、ava-trend · 22 个(推荐 8 PUBLIC / 14 PRIVATE)

| Pattern ID | Layer | 推荐 visibility | 风险 | 理由 |
|---|---|---|---|---|
| meta-ava-create-traffic | meta | **PUBLIC** | L | 战略定位"我们做什么",公开帮 acquisition |
| meta-eight-traffic-principles | meta | **PRIVATE** | **H** | **8 原理是 founder 总结的核心 framework**,对手白拿即可上手 |
| meta-trend-single-responsibility | meta | **PUBLIC** | L | "trend 模块只回答 3 个子问题",架构思路,公开展示思考深度 |
| flow-director-pipeline-v3 | flow | **PRIVATE** | **H** | Director 完整实现(Solo Writer + A12 + GO/POLISH/REVISE/NO_GO),IP |
| flow-snapshot-v3-collect | flow | **PRIVATE** | **H** | Trend 模块完整 schema 设计(三波形 + 5 叙事 + 信息缺口),IP |
| flow-hook-gate-3sec | flow | **PRIVATE** | **H** | Hook 5 维评分 + 弱钩重写,**hook = 流量护城河** |
| flow-experience-backfeed | flow | **PUBLIC** | L | winning/failure 双向回流,通用机制 |
| flow-strategy-real-data-feedback | flow | **PUBLIC** | L | strategy_latest.json M7→M2/M3,通用反馈机制 |
| playbook-hook-matrix-21 | playbook | **PRIVATE** | **H** | **21 战术 + 4 杠杆,Claude Design handoff,核心 IP** |
| playbook-hook-4-levers | playbook | **PRIVATE** | **H** | 与 hook-matrix-21 配套,IP |
| playbook-trend-3-waveforms | playbook | **PRIVATE** | M | Trend 模块设计细节 |
| playbook-narrative-frameworks | playbook | **PRIVATE** | M | 6 叙事框架,Trend 模块设计细节 |
| tech-hard-checks-script | tech | **PRIVATE** | M | 创作 6 优先级规则,完整规则集是 IP |
| tech-guardrails-banned-words | tech | **PRIVATE** | M | **具体黑名单**是 IP(行话/标题党/合规) |
| tech-cross-domain-analogy | tech | **PRIVATE** | M | founder 创作技巧 |
| tech-meta-word-deletion | tech | **PRIVATE** | M | 创作技巧 |
| scope-topic-type-fit | scope | **PRIVATE** | **H** | 与 hook-matrix-21 配套,核心 IP |
| scope-13-collect-channels | scope | **PUBLIC** | L | 13 渠道都是公开平台,清单本身无 IP |
| scope-tone-chigua-channel | scope | **PRIVATE** | **H** | 吃瓜频道调性 = 账号 persona,IP |
| compound-winning-failure-loop | compound | **PUBLIC** | L | 通用反馈机制(与 sovx 同结构) |
| compound-architecture-evolution-ab | compound | **PUBLIC** | L | 12-agent → Solo Writer A/B 故事,公开有学习价值 |
| compound-judge-vs-reality-pearson | compound | **PUBLIC** | L | 通用元校准机制 |

**ava-trend 决策**:**14 个需迁到 om-world-private**(全部 hook / trend 实现细节 + 创作技巧 + persona)。

**核心护城河保护清单**(必须 private):
- 8 流量原理 framework
- 21 hook 战术矩阵
- topic_type fit map
- Trend v3.1 完整 schema
- 创作 6 优先级规则
- 行话/标题党/合规黑名单
- 吃瓜频道调性

---

## 五、sovereign-x · 14 个(推荐 11 PUBLIC / 3 PRIVATE)

| Pattern ID | Layer | 推荐 visibility | 风险 | 理由 |
|---|---|---|---|---|
| meta-sovereign-x-thesis | meta | **PRIVATE** | M | "AI Ethics Auditor" persona + 论点是账号 IP |
| meta-x-free-tier-budget | meta | **PUBLIC** | L | X Free Tier 50/24h 是**公开知识**(X 文档),我们贡献是 budget 分配 |
| meta-three-tier-connector | meta | **PUBLIC** | L | real → fallback → mock 通用工程模式 |
| flow-9-stage-pipeline | flow | **PRIVATE** | M | SOVEREIGN-X 具体 M1-M9 实现,IP |
| flow-governance-gate | flow | **PRIVATE** | M | 含 characterfile / persona 关联,IP |
| flow-m7-strategy-bridge | flow | **PUBLIC** | L | 与 ava-trend 同构,通用机制 |
| playbook-openclaw-x-bypass | playbook | **PUBLIC** | M | **OpenClaw + Chrome CDP 绕 X API**:OpenClaw 公开,我们的 integration 方法公开有声誉价值,但**轻度暴露我们走这条路** |
| playbook-rate-limit-window | playbook | **PUBLIC** | L | 通用 rate limit 窗口管理,工程模式 |
| tech-fire-and-forget-hermes | tech | **PUBLIC** | L | 通用工程模式 |
| tech-mock-mode-pattern | tech | **PUBLIC** | L | 通用工程模式 |
| tech-no-hardcoded-secrets | tech | **PUBLIC** | L | 通用工程模式(几乎所有项目都这样) |
| scope-x-platform-constraints | scope | **PUBLIC** | L | X 平台约束**公开知识**(X 文档) |
| scope-characterfile-persona | scope | **PUBLIC** | L | "yaml 驱动 persona" 通用模式;**具体 characterfile.yaml 内容才是 IP**(那不在 Pattern 里) |
| compound-strategy-bridge-loop | compound | **PUBLIC** | L | 与 ava-trend 同构,通用机制 |

**sovereign-x 决策**:**3 个迁 private**(thesis + 9-stage + governance-gate)。

**保护清单**:
- AI Ethics Auditor persona / 论点
- 9-stage pipeline 具体实现细节
- governance-gate 与 characterfile 关联(yaml 文件本身在 SOVEREIGN-X repo,本就 private)

---

## 六、Pack 的 visibility 推论

Pack 应继承其所含 Pattern 中**最严**的 visibility(任一 private → Pack private):

| Pack | 含 private Pattern? | 推荐 visibility |
|---|---|---|
| pack-defi-audit-base | 否(全 public) | PUBLIC |
| pack-defi-audit-cdp | 否 | PUBLIC |
| pack-defi-audit-lending | 否 | PUBLIC |
| pack-defi-audit-yield-vault | 否 | PUBLIC |
| pack-defi-audit-dexs-amm | 否 | PUBLIC |
| pack-defi-audit-algo-stable | 否 | PUBLIC |
| pack-ava-trend-base | **是**(eight-principles / topic-fit / chigua-tone / hard-checks 等) | **PRIVATE** |
| pack-ava-trend-content-creation | **是**(hook-matrix-21 / director-pipeline 等) | **PRIVATE** |
| pack-ava-trend-trend-detection | **是**(snapshot-v3-collect / waveforms 等) | **PRIVATE** |
| pack-sovereign-x-base | **是**(thesis) | **PRIVATE** |
| pack-sovereign-x-full | **是**(thesis + 9-stage + governance) | **PRIVATE** |

→ **11 Pack 中:6 PUBLIC + 5 PRIVATE**。私有 Pack 整体迁到 om-world-private/patterns/packs/。

---

## 七、Founder Review Checklist(v0.2 修正后)

请逐条 review 以下决策(重点关注 H 风险的):

### defi-audit 高风险 PRIVATE 决策(13 个 H 级,v0.2 修正后必须同意才能保护)

- [ ] `meta-core-target-5dim` → PRIVATE
- [ ] `meta-vuln-db-3-layer` → PRIVATE
- [ ] `flow-6-stage-state-machine` → PRIVATE
- [ ] `flow-edge-driven-audit` → PRIVATE
- [ ] `flow-red-team-pivot-v11` → PRIVATE
- [ ] `playbook-cross-cutting` → PRIVATE
- [ ] `playbook-cdp` → PRIVATE
- [ ] `playbook-lending` → PRIVATE
- [ ] `playbook-yield-vault` → PRIVATE
- [ ] `playbook-dexs-amm` → PRIVATE
- [ ] `playbook-algo-stable` → PRIVATE
- [ ] `scope-A-B-classify` → PRIVATE
- [ ] `scope-three-streams` → PRIVATE
- [ ] `scope-bespoke-priority` → PRIVATE

### ava-trend 高风险 PRIVATE 决策(8 个 H 级)

- [ ] `meta-eight-traffic-principles` → PRIVATE
- [ ] `flow-director-pipeline-v3` → PRIVATE
- [ ] `flow-snapshot-v3-collect` → PRIVATE
- [ ] `flow-hook-gate-3sec` → PRIVATE
- [ ] `playbook-hook-matrix-21` → PRIVATE
- [ ] `playbook-hook-4-levers` → PRIVATE
- [ ] `scope-topic-type-fit` → PRIVATE
- [ ] `scope-tone-chigua-channel` → PRIVATE

### 边缘案例 — 你可能想再调整

- [ ] `tech-fork-fuzz-anvil-rpc` / `warp-oracle` / `no-mint-then-try` → PUBLIC(3 个纯技术坑)— **若你想全 PRIVATE 告诉我,改为 0 PUBLIC**
- [ ] `meta-honest-0-discipline` → PRIVATE(纪律,M 风险)— 也可考虑 PUBLIC(品牌"诚实"卖点)
- [ ] `playbook-openclaw-x-bypass` (sovx) → PUBLIC(暴露我们绕 X API 路径)— **若你想 PRIVATE 告诉我**
- [ ] `flow-9-stage-pipeline` (sovx) → PRIVATE 还是 PUBLIC(可作"X 自动账号架构示例")

### 你可以做的 3 种回应

1. **"全部同意,执行 Step 2"** — 我立即写迁移脚本 + 跑迁移
2. **"改 X / Y / Z"** — 你列要改的 Pattern + 新 visibility,我更新 audit
3. **"defi 那 3 个 tech 也 PRIVATE,我全保"** — 我把 defi 22 个全 PRIVATE,om-world public 只剩 ava 8 + sovx 11 = 19 个

---

## 八、Step 2 迁移方案(v0.2 修正后,等你同意 audit 后执行)

迁移脚本 `tools/migrate_to_private.py`(待写):

```python
PRIVATE_TARGETS = [
    # defi-auto-audit 19 个(v0.2 新增)
    "meta-core-target-5dim", "meta-vuln-db-3-layer", "meta-honest-0-discipline",
    "flow-6-stage-state-machine", "flow-edge-driven-audit", "flow-red-team-pivot-v11",
    "flow-adversarial-verifier", "flow-mermaid-3grep",
    "playbook-cross-cutting", "playbook-cdp", "playbook-lending",
    "playbook-yield-vault", "playbook-dexs-amm", "playbook-algo-stable",
    "scope-A-B-classify", "scope-three-streams", "scope-bespoke-priority",
    "compound-process-lesson", "compound-scope-sanity-check",
    # ava-trend 14 个
    "meta-eight-traffic-principles",
    "flow-director-pipeline-v3", "flow-snapshot-v3-collect", "flow-hook-gate-3sec",
    "playbook-hook-matrix-21", "playbook-hook-4-levers",
    "playbook-trend-3-waveforms", "playbook-narrative-frameworks",
    "tech-hard-checks-script", "tech-guardrails-banned-words",
    "tech-cross-domain-analogy", "tech-meta-word-deletion",
    "scope-topic-type-fit", "scope-tone-chigua-channel",
    # sovereign-x 3 个
    "meta-sovereign-x-thesis", "flow-9-stage-pipeline", "flow-governance-gate",
]
# 总计 36 个 → 迁到 om-world-private/

PRIVATE_PACKS = [
    # defi-audit 全部 6 个 Pack(因含 private Pattern)
    "pack-defi-audit-base", "pack-defi-audit-cdp", "pack-defi-audit-lending",
    "pack-defi-audit-yield-vault", "pack-defi-audit-dexs-amm", "pack-defi-audit-algo-stable",
    # ava-trend 3 个
    "pack-ava-trend-base", "pack-ava-trend-content-creation", "pack-ava-trend-trend-detection",
    # sovereign-x 2 个
    "pack-sovereign-x-base", "pack-sovereign-x-full",
]
# 总计 11 个 Pack 全 private!(因任一含 private pattern 即整 pack private)

For each in PRIVATE_TARGETS:
  1. 把 om-world/patterns/<id>/ 移到 om-world-private/patterns/<id>/
  2. SKILL.md frontmatter 加 visibility: private(若无)
For each in PRIVATE_PACKS:
  1. 移 om-world/patterns/packs/<id>/ → om-world-private/patterns/packs/<id>/
  2. 加 visibility: private

For 剩余 22 个 PUBLIC Pattern + 0 PUBLIC Pack:
  在 om-world/patterns/ 留原位
  SKILL.md frontmatter 加 visibility: public(显式)

迁移完后:
- om-world/patterns/ = **22 Pattern + 0 Pack**(全 public,可对外)
  - defi-audit 3(纯技术坑)
  - ava-trend 8(通用工程 + 战略定位 + 13 渠道清单)
  - sovereign-x 11(大量通用工程模式 + X 公开约束)
- om-world-private/patterns/ = **16 wedgetest + 36 + 11 Pack = 52 Pattern + 11 Pack**(全 private)
- SDK 用 OMW_PATTERN_PATH=public:private overlay 加载,行为不变
```

**关键变化(v0.2 vs v0.1)**:
- om-world public 从 41 Pattern 缩到 22 Pattern(防核心 IP 泄露)
- **11 个 Pack 全部 PRIVATE**(因任一含 private pattern 即整 pack private —— 这意味着公开 om-world 仓库**不附带任何 ready-to-use Pack**,只有协议层 + 22 个零散 Pattern)
- 这与 OMW "Protocol 公开 + 业务库私有" 的分层逻辑完全吻合

---

## 九、Step 3 公开化 PR(audit 通过 + 迁移完成后)

1. 在 om-world 仓库根写 `LICENSE`(Apache-2.0 for code + CC-BY-4.0 for Pattern docs,与现有 LICENSE-* 一致)
2. 写 `CONTRIBUTING.md` — 外部 PR 流程 + Pattern 提交规范(必填 v0.2.1 schema)
3. 创建 GitHub repo `om-world`(public),push
4. README 突出:**"Protocol 公开,你的 Pattern 你自己决定 visibility"**

---

**等你 review。回复方式见 §七**。
