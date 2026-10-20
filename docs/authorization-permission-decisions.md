# #4/#6 联合决定清单（非规范性）

> **非规范性附录 — 2026-10-21。所有决定均为 UNDECIDED，未选择方案。** 本文记录选项、依赖、字段影响及验收问题，不改变现行规范、字段、哈希或签名公式。#4/#6 保持开放。讨论优先级不是协议采纳、实施承诺或贡献者任务。纸面情景不是执行测试。

## 来源与状态标签

固定来源版本：`426af110cb9eadf18e1b8a2a13c2f7cf973e1341`。主要来源：[Mandate](https://github.com/omworldprotocol/om-world/blob/426af110cb9eadf18e1b8a2a13c2f7cf973e1341/docs/agent-mandate.md)、[Registry](https://github.com/omworldprotocol/om-world/blob/426af110cb9eadf18e1b8a2a13c2f7cf973e1341/docs/tool-registry.md)、[Intent](https://github.com/omworldprotocol/om-world/blob/426af110cb9eadf18e1b8a2a13c2f7cf973e1341/docs/intent-schema.md)、[Proof](https://github.com/omworldprotocol/om-world/blob/426af110cb9eadf18e1b8a2a13c2f7cf973e1341/docs/execution-proof.md)。

联合澄清：[R：#4 责任附录](https://github.com/omworldprotocol/om-world/blob/426af110cb9eadf18e1b8a2a13c2f7cf973e1341/docs/agent-mandate-responsibilities.md)、[Q：#6 权限来源附录](https://github.com/omworldprotocol/om-world/blob/426af110cb9eadf18e1b8a2a13c2f7cf973e1341/docs/tool-registry-permission-sources.md)、[E：#5 证据边界附录](https://github.com/omworldprotocol/om-world/blob/426af110cb9eadf18e1b8a2a13c2f7cf973e1341/docs/execution-proof-evidence-boundaries.md)。这些是已合并的非规范性记录，不代表相关设计已采纳。原 [#4](https://github.com/omworldprotocol/om-world/issues/4)、[#6](https://github.com/omworldprotocol/om-world/issues/6) 正文与评论完整留存。

- **C 现行文字**：固定版本设计草案明确写出的内容，不是运行实测或安全证明。
- **S 建议**：后续讨论/证据准备建议，不是新协议规则。
- **U 未决设计**：存在选择、缺口或冲突；本次不产生 Accepted 状态、schema、签名域或默认行为。

## 现行基线与不可混淆的责任

| 层 | C 现行文字 | U / 不可据此推导 |
|---|---|---|
| Principal | 签署 Intent；constraints 涉预算、时间、辖区和工具等；executor 可创建时或 activation 时绑定，推荐后者。 | constraints 类型、缺省与冲突合成不完整；Agent 自签不证明新增 principal 同意；后填 executor 的签名对象绑定仍不闭合。 |
| Agent | Mandate 是 Agent 的签名接受与承诺，载 intent_id、agent、plan_hash、bond、fee_quote、tools_declared、deadline、signature。 | 报价/保证金不是 principal 预算；没有完整 mandate_id 与签名前像定义。 |
| Operational key | 根身份经链委托给操作密钥；现有要求包括期限、scope、单调收紧及 issuance/action 两层检查。 | scope-covering 语法、strict subset 的维度与撤销传播未完整规定；不等于子任务或多 Agent 设计已完成。 |
| Registry / deployment | 注册表列 tool_id、version、operation_class、confirmation、boundary 等；权限来源仍明确开放。 | 公网可达不等于获权；元数据不是 principal 同意；类序/覆盖、版本固定与部署覆盖没有完整规则。 |
| Proof / reviewer | aggregate 记录执行主张，规范要求身份、计划、工具证据及成功条件检查；哈希/签名公式已有原文。 | 签名不证明之前得到授权，引用不等于取得全部证据；本清单不改公式，不用 #5 接受规则代替权限决定。 |

## 决定项：选项、依赖、字段、兼容性、安全与验收

以下各项的 **Decision 均为 U / UNDECIDED**。提及可能的“引用/凭据/profile”仅表示候选设计，不命名或注册新字段。

### D01 — 授权对象与 activation-time 绑定（P1）

**C**：Intent principal 签名、Agent executor.commitment 与 Mandate 接受分别存在。**U 选项**：(A) 仅在创建时固定 executor 的 profile；(B) 保留推荐 activation-time 模型，以独立、明确绑定的激活工件衔接原 Intent；(C) 在需要时重新签署版本化 Intent，并明确旧对象关系。B/C 均是候选机制；A 若成为唯一默认会改变现有推荐，不能称为编辑修复。

**依赖**：D02 的对象标识与 D03 的权限语义需协同迭代；不把互相引用当作自动解决。**影响面**：Intent.id/signature/executor.commitment，Mandate.intent_id/agent，Proof.intent_id/mandate_id。**兼容性**：修改签名对象可能改变 ID/签名有效性；独立激活工件需要消费端新能力；新旧 Intent 不能静默互换。**安全边界**：不原地修改已签对象后声称原签名仍有效，不把 Agent 接受当作 principal 授权。

**未来验收条件**：逐个签名者、签名输入、对象来源、创建/接受/激活时刻及验证顺序可定位；说明 stale/replay、错误根身份、重签与旧对象处理；不得留下两个“都可视为原 principal 已同意”的含混路径。此条件不指定工件形状或公式。

### D02 — 标识、计划承诺与对象引用（P1）

**C**：Intent.id 表为 UUID、Canonicalization 却给 hash 定义；Proof 引 mandate_id，Mandate 表无该字段；plan_hash 在 Mandate 中，而 Proof 称其先在 intent record 预承诺。**U 选项**：现有语义下显式外部映射/解析 profile；或经版本化协议修订统一对象身份与承诺位置；或保留差异为当前草案限制、暂不声称互操作。不得预选 UUID/hash 或新增 mapping 字段。

**依赖**：D01；结果供 D07/D10 与 #5 使用。**影响面**：I.id、M.intent_id/plan_hash/signature、P.intent_id/mandate_id/plan，首步 prev_hash 的来源。**兼容性**：ID 表达、签名前像、canonical bytes、引用关系任一改变均可能破坏旧工件；不能用无损重命名解释。**安全**：防错绑对象、事后计划替换与跨版本误认。

**验收**：同一对象/不同对象可区分，引用解析来源、版本、缺失结果和计划承诺发生时间可追溯；任何公式调整单独列为版本化设计，**本轮原哈希及签名公式不动**。

### D03 — principal constraints、scope 与具体动作覆盖（P1）

**C**：constraints 较宽泛；M token 子字段为 tool_id/scope/expiry；T 要求声明最高 operation_class，但 M 无明确编码。**U 选项**：(A) 定义 scope 到操作/资源覆盖的映射；(B) 版本化扩展显式操作描述；(C) 独立 profile 解释现有 scope。deny、缺省约束、预算与多层边界组合需要逐项定义，不在本清单使用自动 set-intersection 公式。

**依赖**：D01/D02，并约束 D04/D05。**影响面**：I.constraints，M.tools_declared.scope/expiry，T.operation_class，registry.check_permissions。**兼容性**：新 scope grammar、token 字段或旧 token 解释改变会导致既有 mandate 语义变化。**安全**：匹配字符串不等于覆盖资源；read/write/destructive/admin 不假定全序；预算、bond 与 fee_quote 不混为授权限额。

**验收**：具体动作/资源/时间的允许、禁止、不可比较、缺失与冲突案例都有明确来源；等权与只缩短时间的 strict-subset 解释显式裁定；不能仅提供枚举大小比较或“缺约束即全允”。后一句是 S 安全目标，不是新增现行拒绝规则。

### D04 — 注册值与部署策略的权限来源（P2）

**C**：T 问题仍开放；Q 比较的 A/B/C 仍未选择。**U 选项**：A 注册值固定、严格变体另建 entry（原评论的具体提案）；B 部署定义且版本化策略；C 注册基线加仅收紧限制；也可保留未选并记录适用性问题。所谓“override”不能将 A 的新 entry 与 C 的同 entry 限制层混同。

**依赖**：D03 覆盖关系；D07 版本绑定。**影响面**：T.tool_id/version/operation_class/confirmation/provider/interface；M token 引用；部署策略候选表示；P 的验证依赖。**兼容性**：A 的新 tool_id 不自动继承旧授权；B 的同 ID 跨部署不保证同语义；C 需要正式非扩张谓词及旧工作流处理。**安全**：元数据可错误，固定不等于真实；部署变化不得被描述为自动取得 principal 同意。

**验收**：明确谁声明/签认/更正分类、冲突如何呈现、action 与注册说明如何比较；A/B/C 逐项说明可追溯历史状态、错分/不可比/未知情况，而不是只给偏好。原提案理由及备选保留，最终采纳须另有决定记录。

### D05 — 确认要求、展示与批准证据（P2）

**C**：automatic 不需人类确认；human-in-loop 要求执行前展示计划调用；restricted 要求 principal 带外明确批准并阻止自主调用。**U 选项**：保留展示含义并在部署 profile 规定更强交互；或通过明确版本化提案增加 affirmative approval 要求；或为特定动作 profile 明确审批握手。不是把三个值当线性数字 max。

**依赖**：D01/D03/D04；证据供 D10。**影响面**：T.confirmation、I.constraints、M scope，以及尚未定义的批准证据表示。**兼容性**：展示变为等待同意会改变既有 automatic/交互流；旧批准不能默认跨动作/时间/版本复用。**安全**：执行后证明不是先前同意；同意者、动作/金额/资源、时间与 policy 版本要分开审阅。

**验收**：清楚区分“已展示”“明确批准”“未知”；定义有权主体、绑定、freshness、reuse/replay 和缺失处理；对 human-in-loop 新要求标为提议，不能倒写成当前文本。

### D06 — 操作密钥、授权撤销与生命周期（P2）

**C**：M 根身份链；P Active/Rotated/Compromised；Lifecycle 有取消/到期路径。**U 选项**：独立凭据撤销状态 profile、registry 状态引用、限定寿命/重发设计，或其明确组合；不选择传播机制。

**依赖**：D01/D03/D07。**影响面**：M.agent/signature/token expiry/deadline，I.executor，P.signature/key history，Lifecycle cancel/expire；不引入 revocation_rules 字段。**兼容性**：正常轮换不等于 compromise；principal cancel 不等于瞬时撤销所有凭据；操作密钥不等于另一个根 executor。**安全**：链验证与具体动作验证均需考虑，但 profile、撤销时点/传播时延尚未定。

**验收**：逐类事件列有效时刻、观察来源、历史证明与新调用分别受什么影响；现有单信任域例外不推广到对抗市场；不把密钥链当多 Agent/sub-mandate 已解决。

### D07 — 工具版本、策略 revision 与依赖承诺（P2）

**C**：T.version 存在；M token 与 P.step 无显式 tool version/policy revision 字段；Q 已记录缺口。**U 选项**：版本由不可变 tool entry 引用；外部可追溯 deployment profile；版本化 token/envelope 扩展；或显式限制当前互操作主张。三者绑定位置、signed coverage 均待定。

**依赖**：D02/D04，迭代反馈 D01；结果供 D08–D10。**影响面**：T.tool_id/version，M.tools_declared，P.tool_id/attestation，I.constraints/签名覆盖。**兼容性**：新字段、解析规则或默认 latest 都改变旧消费者行为；无字段不代表现有工具已绑定最新或全部历史版本。**安全**：不能接受时看旧策略、执行时静默换新策略；也不能把保留快照等同版本真实/可取回。

**验收**：标明接受时/执行时/验证时依赖版本、谁承诺、证据如何获取；新版本与已弃用/无法识别/不可取回版本分别列结果；不照搬 P 的 UNSUPPORTED_SPEC_VERSION 给 registry 未定义情况当现行规则。

### D08 — 旧 mandate、变更、deprecation 与重新同意（P3）

**C**：T 说 deprecated 工具的现有 mandate 直到 expiry 仍有效；M 普通 endpoint rotation 可不重签，实质 trust change 需 re-consent。**U 选项**：依赖版本内 grandfather；显式重新同意/重发；旧 mandate 仍有效但部署可阻止具体调用；新 tool_id 显式绑定。不得暗选其中一个。

**依赖**：D04–D07。**影响面**：tool_id/version/status、M expiry/deadline/scope、I consent/constraints 引用。**兼容性**：mandate 有效、服务可用、某动作获准是三件事；严格策略也会破坏旧 workflow，不自动证明其获批。**安全**：紧急阻止、恢复与旧权限放宽必须显式审议；不能发明 deprecation 的秘密撤销例外。

**验收**：对旧 entry→新 entry、变分类、增加确认、仅变 URI、变 operator/辖区、deprecated/安全风险逐项说明；保留旧记录与 consent 证据，不能无证据声称 grandfather 或完成迁移。

### D09 — Discovery、分类准确性与动作前检查（P3）

**C**：T lazy search/describe/check_permissions；相同 query+registry state 排序可重现。**U 选项**：部署过滤作为明确 profile 输入；基线排序加独立限制结果；带明确状态的统一搜索；不选择 API 形状。

**依赖**：D03/D04/D07。**影响面**：search filters、describe、check_permissions、boundary、alias/composition。**兼容性**：新增隐藏部署状态影响排序/可见性，会破坏旧可重现性假设。**安全**：public/可搜索不是授权；read label 不掩盖实际转账，pipeline/alias 不能逃逸逐动作约束。

**验收**：能够辨别发现、元数据声明、动作前授权判断与实际行为；说明状态输入、未知分类及复合工具限制。真实性审计与大规模离线验证仍开放，不能把文档情景当适配器测试。

### D10 — 证明消费、缺失证据与决定记录（P3）

**C**：P 要求 aggregate、版本路由、工具/身份/成功条件检查；E 保留证据与绑定缺口。**U 选项**：完整导出依赖证据的 profile；外部版本化引用并规定取证边界；版本化扩展绑定关系。供 #5 后续讨论，不制定 receipt schema。

**依赖**：D01–D09 的确切结果或明确保留限制；当前可先列证据清单。**影响面**：P intent/mandate/tool/attestation/signature，未定义的 policy/approval 引用。**兼容性**：新 verifier 要求可能令旧 proof 不足；不足证据不自动等于假证明、违规或应 slash。**安全**：提交了 hash、签名、审批 claim 不等于实际权限/付款/交付；只读草稿不验证任何这些事件。

**验收**：能关联原 signed Intent、Agent 接受、有效链、具体动作、依赖版本、确认与结果；分别标记已知、冲突、缺失和不能判断，给后续设计明确的缺证据语义；决定记录区分 proposal/review/accepted/implementation，不能从合并说明推断协议采纳。

## 优先级与验收情景矩阵（全部纸面）

**S 顺序**：第一组 D01–D03 建立对象和授权语义；第二组 D04–D07 联合比较来源、确认和版本（需要与第一组往返）；第三组 D08–D10 处理历史兼容与证据消费。首份可交付仅为三组的决定卡和差异清单，不启动设计实现。#7 继续 UNKNOWN/延期，不是联合决定清单依赖。

| 情景 | 关联项 | 后续文档验收条件 / 本次不宣称的结果 |
|---|---|---|
| T01 已签 Intent 后激活 executor | D01/D02 | 指明工件/签名/ID 绑定；本次 U，不假装原地补字段有效。 |
| T02 错根身份或有操作密钥无委托链 | D01/D06 | 区分根约束与链验证；标明当前规则及缺失凭据表示，不运行验签。 |
| T03 相同 scope 字符串覆盖更宽资源 | D03 | 保留 covering 而非 membership 要求；语法仍 U。 |
| T04 admin 与 destructive 比较 | D03/D04 | 不数值排序，列不可比及组合动作问题。 |
| T05 注册 read、部署/实际动作转账 | D04/D09 | 明确分类冲突与来源争议，元数据不充当授权证据。 |
| T06 restricted→automatic 或新加展示 | D04/D05 | 分别列候选收紧/放宽判定与旧工作流变化；不自动认定升级获批。 |
| T07 展示但未肯定同意 | D05 | 保留现行文字差别；额外 affirmative approval 标 S/U。 |
| T08 同意针对其他金额/版本/时间 | D05/D07 | 记录证据不匹配与未定义绑定，不制造审批成功。 |
| T09 子密钥过期、root 轮换/compromise | D06 | 分别列 expiry 与 key-state 原文；撤销传播 U，不全等化。 |
| T10 同 ID 新版本、旧 mandate 未到期 | D07/D08 | 说明接受/调用/验证时间依赖；不默认 latest 或静默重绑。 |
| T11 严格变体新 tool_id | D04/D08 | 不默认继承旧 token 授权，列显式映射/再同意选项。 |
| T12 deprecated 且服务不可用 | D08 | 区分 mandate 有效与服务可用，保留现行 expiry 文字。 |
| T13 URI 轮换与 operator/辖区改变 | D08 | 前者与 trust-property re-consent 分开，具体边界待定。 |
| T14 policy revision 无法获取/未知 | D07/D10 | 不声称授权可判，不冒用 proof-version error；缺证据结果需决定。 |
| T15 query/registry 相同，隐藏 deployment config 不同 | D09 | 指出复现状态边界，给后续显式状态选项，不声称排序复现测试。 |
| T16 完整 proof 但缺 policy/consent 依赖 | D10 | 不把 aggregate 签名当 prior consent；不足与欺诈区分。 |
| T17 mandate_id/plan_hash 引用无明确来源 | D02/D10 | 保留差异，不能新增 ID 或修改 prev_hash/hash preimage 来“修好”。 |
| T18 空白/冲突 constraints 与价格超预算 | D03/D05 | 缺省、deny 和 fee/budget 关系显式标 U；不补写执行默认值。 |

## 文档审阅标准、剩余门槛与治理

本文的编辑审阅标准：10 个决定项均有 C/S/U、选项、依赖、字段影响、兼容性、安全和验收条件；18 个情景均为文档审阅；没有新字段/公式/permission rule 被实际采纳，文档合并不代表设计采纳。原贡献、讨论和许可文件保留原字节。

后续若要**采纳**某项，需明确新范围，按既有 GOVERNANCE 的提案/审阅/决定记录过程处理，披露安全/隐私/兼容性和反对意见。不能把维护者文档自复审称作外部共识；当前没有请求 review、联系作者或派发任务。对于不可判的设计保留 U 是合法交付，不为了关闭 issue 伪造规则。

记录这些未决问题不解决协议门槛。协议定版仍受 D01–D10 未决项与治理裁定门槛约束；这些不是开始适配器、实验、服务验证或 MSEC 研究的授权。

## 贡献与许可

© OM World Protocol contributors，来源 https://github.com/omworldprotocol/om-world ，原 prose 适用 CC-BY-4.0；本清单新增整理文字同样按 CC-BY-4.0 提供，完整许可见 [LICENSE-DOCS](../LICENSE-DOCS)。变更性质仅为 2026-10-21 的决定选项整理，不改变原来源。

保留 #4 scope/memory 讨论、#6 security/lazy-discovery 记录及 [kawacukennedy 的权限来源原提案](https://github.com/omworldprotocol/om-world/issues/6#issuecomment-4817560998)；该提案未被本清单采纳，外部 production 声明不作本轮实证。R/Q/E 原文与 CONTRIBUTORS 中的具体贡献和 citation-only 限定保持原样。没有给历史贡献者新增作者/审阅/会议角色、假定其同意或声称参与 MSEC。品牌/视觉资产权利未扩张。
