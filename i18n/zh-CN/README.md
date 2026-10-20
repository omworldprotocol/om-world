# OM World

[English](../../README.md) | 简体中文

> 翻译基准：[英文 README（提交 e58c207）](https://github.com/omworldprotocol/om-world/blob/e58c207f03d1a98c03b1ed8b7a96a50662cf7b12/README.md)。本页仅翻译 README，所链接的其他项目文档仍为英文。下文关于部署、性能和评审日期的内容保留英文源版本的历史限定，不构成本次重新验证。

**One Mind, One World.**

OM World 是一个自增长的意图实现网络。

它将人们想要实现的目标与能够交付结果的能力连接起来，并把每次实现过程转化为可复用的模式（Pattern），让下一次同类意图更容易、更快、以更低成本实现。

我们认为，人的意图不应归 AI 平台所有，不应被中心化系统拍卖，也不应由黑箱替人决定。意图属于表达它的人。

## 协作重启 — 2026-10-20

OM World 正在准备恢复开源维护及现有协议规范的评审。首要工作是审查开放的拉取请求（PR）、澄清文档状态，并让贡献路径更清楚。参见[重启范围](../../docs/collaboration-restart.md)。

下文描述的部署、性能观察和评审日期属于项目的历史陈述，本次重启尚未重新验证。不能将其理解为当前服务保证或可推广的性能结论。

[MSEC](https://github.com/omworldprotocol/msec) 是独立维护的研究子项目，拥有自己的仓库和范围。建立仓库不等于取得科学结果。现有 OM World 贡献者的署名对应其已记录的 OM World 工作，不能据此推定他们参与或支持 MSEC。

## 什么是 OM World？

OM World 是连接以下三方的开放协议：

- **意图需求（Intent demand）**——人们想要实现什么。
- **实现供给（Realization supply）**——能够交付结果的工具、代理和人。
- **持续增长的模式库（Pattern Library）**——记录每次成功实现，供后续复用。

AI 提供执行能力。
Crypto 与可验证记录提供规则、结算和审计轨迹。
人保留对自身意图的主权，并拥有自己创建的模式。

成功标准很直接：**任何一类意图的第二次实现，都应比第一次更容易。**

## 核心原则

1. **意图主权（Intent Sovereignty）**
   每个意图都属于表达它的人或实体。

2. **可验证执行（Verifiable Execution）**
   如果无法证明一个结果，就不视为它已经发生。

3. **开放协议，而非封闭平台**
   OM World 的设计目标是公共协议，而不是由一家公司控制的应用。

4. **AI 为引擎，Crypto 为法则（AI as Engine, Crypto as Law）**
   AI 将意图转化为行动。Crypto 让授权、支付、执行和结果可以验证。

5. **可组合的意图工具**
   构建者可以创建接入同一意图经济的工具、代理、注册表、验证器和界面。

## 意图生命周期

1. **表达（Declare）**——用户表达一个意图。
2. **绑定（Bind）**——意图转化为经签名的 Mandate（代理承诺）。
3. **路由（Route）**——AI 代理选择工具和执行路径。
4. **执行（Execute）**——工具和代理执行所需行动。
5. **证明（Prove）**——对结果进行哈希处理、生成 attestation（证明材料），或进行验证。
6. **结算（Settle）**——完成支付、奖励、声誉及记录的结算。
7. **记忆（Remember）**——意图、Mandate、证明与结果成为用户拥有的意图历史的一部分。

## 生态角色

- 意图发起者（Intent Originators）
- AI 代理构建者（AI Agent Builders）
- 工具创建者（Tool Creators）
- 算力提供者（Compute Providers）
- 验证者（Verifiers）
- 资本提供者（Capital Providers）
- 界面构建者（Interface Builders）
- 治理参与者（Governance Participants）

## 核心文档

- **[SELF_GROWTH_ENGINE.md](../../SELF_GROWTH_ENGINE.md)**——OM World 如何让意图实现随时间变得更容易：自增长引擎、模式库、双边世界及最小核心规则。**要了解系统的预期运作方式，请从这里开始。**
- [MANIFESTO.md](../../MANIFESTO.md)——理念基础。
- [LITEPAPER.md](../../LITEPAPER.md)——协议概览。
- [GOVERNANCE.md](../../GOVERNANCE.md)——OM World 的治理方式。
- [GENESIS-BUILDERS.md](../../GENESIS-BUILDERS.md)——早期贡献者的共同构建者制度。
- [CONTRIBUTORS.md](../../CONTRIBUTORS.md)——对参与塑造 OM World 的贡献者的公开署名。
- [docs/](../../docs/)——Intent Schema（意图数据结构）、Agent Mandate（代理承诺）、Execution Proof（执行证明）和 Tool Registry（工具注册表）的规范草稿。

## Genesis MVP——试用入口（历史部署说明）

英文源版本记载，一个可运行的最小 MVP 部署于 **https://app.omworld.one**：
包含“提交意图（Submit an Intent）”与“贡献能力（Contribute a Capability）”两个入口、基于大语言模型（LLM）分类的意图路由器、记录每次实现的模式库，以及内部 OM Credit（OMC）**贡献账本**。参见下方 OMC 说明。

## OMC——它是什么，以及不是什么

OM Credit（OMC）是**不可转让的内部贡献记录**。它记录谁贡献了哪次实现、谁构建了哪个模式，以及模式复用有多少次确实节省了时间。它：

- **不是代币。** 没有链上表示，也没有智能合约。
- **不是货币。** 不能在协议内外兑换任何东西。
- **不是承诺。** 无论现在还是协议的任何未来状态，都没有设想相关分配、归属安排或未来兑换。
- **不是可消费余额。** “获得”OMC 意味着留下公开贡献记录；除此记录之外，不赋予接收者任何权益。

仪表盘使用“已记录的贡献（Contributions recorded）”，而不是“OMC 余额（OMC balance）”，以准确表达其含义。内部记账计算（每个事件的数量、总量）保留用于记录和未来重新设计，但所有对外标签都使用“贡献”，而不是“货币”。

模式复用的奖励记录尤其**以实际降低实现阻力为条件**（Phase 3.5 加固）：只有适配复用的实际耗时低于全新生成基线的 85%，**并且**复用者不是该模式的创建者，才记录一次“成功复用”（防止自我刷取记录）。在滚动时间窗口内被过于频繁匹配的模式会进入冷却期，防止泛化模式滥占匹配机会。

源码布局：`app/`（Next.js App Router）、`lib/`（LLM 路由、匹配、模式与贡献记账），以及 `prisma/schema.prisma`（按规范定义的 7 张表）。英文源版本记载，LLM 调用经由 OpenClaw GPT-5.5 路由，并自动回退至 DeepSeek。部署说明见 [`scripts/deploy/README.md`](../../scripts/deploy/README.md)。上述运行描述同样受前文历史状态限定约束。

**单代理运行时示例。** OM World 在代理层不限定具体实现：按英文源版本的设计描述，能够生成经签名的 Mandate 和有效执行轨迹（Execution trace）的运行时可以接入。英文原文举出的生产示例是 [Nolpak14/agorio](https://github.com/Nolpak14/agorio)，一个覆盖 UCP、ACP、MCP、AP2 四种协议的代理工具包，可在 OM World Mandate 下组合使用。参见 `docs/agent-mandate.md` 的 Composition 章节，了解 agorio 评审所推动的跨协议维度划分。此处保留原文引用，不构成本次互操作性重新验证。

## 项目状态（英文源版本中的历史记载）

OM World 处于 Genesis 阶段。英文源版本记载，Genesis MVP 于 2026-05-18 发布。

原文所记载的“现已上线”：

- **Genesis MVP**：https://app.omworld.one ——意图需求入口、能力供给入口、匹配引擎、模式库 v0、OM Credit 账本 v0。
- **首个预置能力**：Genesis Builder Recruitment Generator（Genesis 构建者招募生成器），对应首个意图类型 `community_growth.builder_recruitment`。
- **“自增长循环已验证”这一历史陈述**：在同类意图的并排运行中，第二次实现通过适配已有模式、而非从头重新生成，实际耗时约减少 20%。该陈述未经本次重新验证，不应视为可推广的性能结论。

原文所记载的“已发布”：

- Manifesto v0.1、Litepaper v0.1、Brand v0.1。
- SELF_GROWTH_ENGINE.md v0.1——规范性的引擎架构说明。
- Genesis Builder 贡献框架（GENESIS-BUILDERS、CO-BUILDER-ONBOARDING）。
- `docs/` 中的规范草稿（Intent Schema、Agent Mandate、Execution Proof、Tool Registry、Intent Lifecycle、Economic Model）：描述协议层的长期目标，MVP 当时实现的是简化子集。

原文所记载的“进行中”：

- 将能力供给扩展到预置招募生成器之外。
- 预置第二个模式（第二种意图类型待定）。
- Genesis Builder 基础规范冻结工作（Intent Schema 与 Execution Proof 的评审）。这些属于历史评审安排，不能据此认定当前已经冻结或贡献者重新承诺参与。

## 加入 Genesis

英文源版本邀请以下角色参与：

- AI 代理构建者
- Crypto 协议工程师
- 智能合约开发者
- 设计师
- 研究人员
- 写作者
- 社区构建者
- 治理设计者
- 安全研究人员

如果你认为人的意图应拥有主权、可以验证，并能在开放世界中执行，欢迎参与构建 OM World。

## Genesis Issues

英文源版本记载，首批 OM World Genesis issues 已开放，并邀请构建者、研究人员、设计师、写作者和协议贡献者加入。各项任务的当前状态以 [GitHub Issues](https://github.com/omworldprotocol/om-world/issues) 为准；这段历史说明不表示所有早期 issue 目前仍开放。

## 许可与贡献署名

OM World 采用双许可证：规范与文字材料使用 [CC-BY-4.0](../../LICENSE-DOCS)，代码与参考实现使用 [Apache-2.0](../../LICENSE-CODE)。`assets/` 下的品牌和视觉识别资产不在这两种许可证的覆盖范围内。许可范围详见 [LICENSE](../../LICENSE)；贡献条款详见 [GOVERNANCE.md 的 Licensing 章节](../../GOVERNANCE.md#licensing)（贡献采用与相应文件相同的许可，即 inbound=outbound；无需另行签署 CLA）。

本页是英文 README 的中文翻译与改编，原项目贡献署名保留于 [CONTRIBUTORS.md](../../CONTRIBUTORS.md)，中文版本由 flyoung588 维护。除语言、中英导航、相对链接及明确保留历史语气外，不增加实现或科研结论。

© OM World Protocol contributors, licensed under CC-BY-4.0.
Source: [OM World](https://github.com/omworldprotocol/om-world) · [固定版本英文 README](https://github.com/omworldprotocol/om-world/blob/e58c207f03d1a98c03b1ed8b7a96a50662cf7b12/README.md)

**One Mind, One World.**
