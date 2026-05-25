# OMW Pattern Schema v0.3.0

> 单源真理 (Single Source of Truth)。所有 Pattern (SKILL.md) + Pack (PACK.md) 必须遵循本规范。
> 修改本规范需经 founder approve + 同步迁移已有 Pattern。
> Schema 版本由 `schema-version` 字段标记;Pattern 之间 schema-version 可不同(支持平滑过渡)。

## v0.3.0 变更(在 v0.2.1 上)

| # | 变更 | 类型 |
|---|---|---|
| v0.3.0-1 | **frontmatter 新增 `workflow:` 字段(可选,Pack 必填)** —— 机器可执行 step list,OMW Runtime 按它编排执行 | **重大新增** |
| v0.3.0-2 | **SDK 新增 `Runtime` + `omw run` CLI** —— 业务项目从"自己跑 + 旁路 invoke logging"升级为"OMW 编排 + 业务代码沦为 sub-tool" | SDK 实现 |
| v0.3.0-3 | **Body `## Rules / ## Anti-Pattern / ## Hard-Forbidden / ## Heuristics / ## Judgment` 五段被 Runtime 解析为 LLM guard prompt** | 既有段位的新用途 |
| v0.3.0-4 | invocation event 新增 `step_id` / `step_kind` / `parent_invocation_id` / `guards_triggered` / `judgment_score` / `gap_signal` 字段 | 飞轮升级 |

详见 §四 Workflow 规范 + §五 Runtime 执行语义。

## v0.2.1 变更(在 v0.2 上)

| # | 变更 | 类型 |
|---|---|---|
| v0.2.1-1 | **新增 frontmatter `visibility: public \| private \| restricted`(默认 `private`)** —— 支持"分层公开"架构,核心 IP Pattern 物理隔离到 `om-world-private/` 仓库 | **重要新增** |
| v0.2.1-2 | SDK 支持 `OMW_PATTERN_PATH` 多目录(冒号分隔),overlay 加载顺序后者优先 | SDK 实现 |
| v0.2.1-3 | aggregator 对 visibility=private Pattern 的 metrics 不导出到公开 sync(future:Stage 3 sync 时实施) | 实施前 |

## v0.2 完整变更摘要

| # | 变更 | 类型 |
|---|---|---|
| 1 | metrics 增加 `domain-specific:` 子字段 | 新增 |
| 2 | Negative 段拆分为 `Anti-Pattern / Hard-Forbidden / Soft-Avoid` 3 段 | 重构 |
| 3 | 新增 frontmatter `domain` / `applicable-project-types` | 新增 |
| 4 | 新增 frontmatter `depends-on` / `extends` / `composes-with` 结构化依赖 | 新增 |
| 5 | metrics 增加 `auto-tracked: true` 标记 (为 runtime hook 预留) | 新增 |
| 6 | i18n:`description-en` / `trigger-en` / `anti-trigger-en` 可选字段 | 新增 |
| 7 | 新增 Pack 机制 (`packs/<pack-id>/PACK.md`) | 全新概念 |

---

## visibility 字段语义

```yaml
visibility: public | private | restricted
```

- **`public`** — 任何人可见。**只有协议层通用 Pattern 应公开**(例:`meta-*` 通用元 Pattern)。
- **`private`(默认)** — 仅作者私域可见;不进任何公开 marketplace / sync 流;invocation metrics 不汇总到公开导出。**所有业务 Pattern 默认私有**。
- **`restricted`** — 命名空间内可见(团队 / 组织内部)。Stage 3 之后启用。

**物理隔离原则(Stage 1 推荐)**:
- 公开仓库 `om-world/`:**只放 visibility=public 的 Pattern + 协议层(SDK / Schema / Architecture)**
- 私有仓库 `om-world-private/`:**所有 visibility=private 的 Pattern + invocation log**
- SDK 通过 `OMW_PATTERN_PATH=<public>:<private>` 多目录加载

→ visibility 不只是 metadata,也是物理仓库的指引。

---

## 一、文件夹结构

```
patterns/
├── PATTERN_SCHEMA.md            # 本文档,v0.2 单源真理
├── INDEX.md                     # 全库索引
├── SCHEMA_EVALUATION.md         # v0.1 → v0.2 迁移评估
├── <pattern-id>/
│   ├── SKILL.md                 # Pattern 主文件
│   ├── scripts/                 # 可执行(可选)
│   │   └── *.py / *.ts / *.sh
│   └── references/              # 大块参考(可选)
│       └── *.md
└── packs/
    └── <pack-id>/
        ├── PACK.md              # Pack 主文件
        └── references/          # Pack 级补充(可选)
```

**ID 命名规范**:
- Pattern ID:`<layer>-<topic>` kebab-case;例:`meta-core-target-5dim`、`flow-6-stage-state-machine`、`tech-fork-fuzz-anvil-rpc`
- Pack ID:`pack-<domain>-<usecase>` kebab-case;例:`pack-example-base`、`pack-ava-trend-douyin-content`
- 层级前缀(当前已用):`meta-` / `flow-` / `playbook-` / `tech-` / `scope-` / `compound-` / `pack-`(可扩展,但每个新前缀需在本文件备案)

---

## 二、SKILL.md 完整规范

### 2.1 YAML frontmatter (必填 + 可选字段)

```yaml
---
# === 基础标识 (必填,英文 keys) ===
name: <pattern-id>                            # kebab-case,与目录名一致
description: <≤200 字符,founder 母语>         # progressive disclosure 第一层关键字段
description-en: <optional ≤200 char English>  # i18n,推广阶段必填
schema-version: 0.2                           # 当前 schema 版本

# === 触发匹配 (必填) ===
trigger: <关键词列表,中文或英文>               # agent 检索匹配
trigger-en: <optional English keywords>       # 跨语种任务匹配
anti-trigger: <禁用场景>
anti-trigger-en: <optional>

# === 适用范围 (v0.2 新增) ===
domain: <domain-slug>                         # 单 string 或 list,例:ai-traffic-x / ava-trend-douyin / "*"
applicable-project-types:                     # 项目 slug 列表,或 ["*"] 通用
  - <project-slug>

# === 状态 ===
status: draft | active | deprecated
version: <semver>                             # Pattern 内容版本(语义化)

# === Pattern 间关系 (v0.2 新增,结构化依赖) ===
depends-on:                                   # 概念依赖:必须先理解
  - <pattern-id>
extends:                                      # 叠加在哪个 Pattern 之上
  - <pattern-id>
composes-with:                                # 同 use case 通常一起用
  - <pattern-id>

# === 来源追溯 ===
provenance:
  source-project: <repo slug>
  source-file: <path>                         # 提炼自哪个文件
  source-sessions: <integer or note>          # 基于多少次实战
  approved-by: <人>
  created: <YYYY-MM-DD>

# === 度量 (v0.2 增加 domain-specific + auto-tracked) ===
metrics:
  auto-tracked: true | false                  # 是否走 OMW runtime 自动维护
  invoked: <int>                              # 累计调用数
  measured-success-rate: <0..1 | null>
  last-validated: <YYYY-MM-DD>
  domain-specific:                            # 自由 schema (领域特定)
    <any-key>: <any-value>                    # 例:edges-covered-b: 9
---
```

### 2.2 Body 段 (v0.2 必填顺序)

```markdown
## Rules
确定性规则 (deterministic / "always true under these conditions")

## Heuristics
概率性规律 (probabilistic / "in ~X% of cases")
每条建议标置信度 + n(基于多少次实战)

## Anti-Pattern
立即出错的反模式 — 做了立即破坏 invariant / 立即报错 / 立即假阳性
(v0.1 Negative 段拆分而来,语义最强约束)

## Hard-Forbidden
做了会破坏整个评判体系的绝对禁忌
例:"把 4/5 包装成 success" / "用 LATENT-LOW 凑数"
(语义中等约束,关乎诚信/标准)

## Soft-Avoid
做了会降低质量但不会立即出错的建议
例:"不要 trust ChainSecurity 不验证版本" / "harvest 路径忽略 slippage"
(语义最弱约束,关乎质量)

## Judgment
主观判定 / 可引用 scripts/judge.py / 引用 references/examples.md
说明 founder 的隐性判定如何被部分代码化 + 部分文档化

## Workflow
执行流程 / DAG / 步骤
通常含闭环(执行 → 反馈 → metrics 回传)

## References
- 出处文件路径(具体到行号)
- 相关 Pattern (用文字描述,与 frontmatter.depends-on/extends/composes-with 互补)
- 工具 / 模板 / 实现
```

### 2.3 字段语义详解

**`domain`**:Pattern 所属业务领域。
- 单值时:`domain: ai-traffic-x`
- 多值时:`domain: [ai-traffic-x, smart-contract-security]`
- 通用时:`domain: "*"`(慎用,通常 meta-* 才适用)
- 当前已用 domain:`ai-traffic-x` / 计划新增:`ava-trend-douyin` / `om-world-x-internal`

**`applicable-project-types`**:具体哪些项目可加载本 Pattern。
- 项目 slug 来自 repo 名:`<example-project>` / `AVA-trend` / `AVA-MI` / `ACVA` / `SOVEREIGN-X` / `OM-WORLD-X`
- `["*"]` 表示通用
- agent 加载时:先按 `domain` 筛选,再按 `applicable-project-types` 二次筛选

**`depends-on` vs `extends` vs `composes-with`**:
- `depends-on`:**概念上必须先理解 A 才能用 B**。例:用 `flow-6-stage-state-machine` 必须先懂 `meta-core-target-5dim`
- `extends`:**B 是 A 的特化叠加**。例:`meta-x-free-tier-budget` extends `playbook-cross-cutting`(CDP 边在通用边之上叠加)
- `composes-with`:**B 和 A 在同 use case 通常并用,但无主次**。例:`tech-fork-fuzz-warp-oracle` composes-with `playbook-rate-limit-window`(任何带利率累积的 lending 审计都两个一起用)

**`metrics.auto-tracked`**:
- `true`:OMW runtime 每次加载本 Pattern 时,自动追加一行到 `patterns/<id>/metrics.jsonl`(append-only 日志)。周期性聚合回写到 SKILL.md frontmatter
- `false`:metrics 全手工维护(早期/原型可用)
- v0.2 阶段:runtime 还未实现,先全部标 `false`,但字段位置预留

**`metrics.domain-specific`**:
- 任意 key-value 结构,装领域特定 metric
- 例:playbook 类的 `edges-covered-b: 9` / `edges-covered-c: 3`
- 例:AVA-trend 类未来可能 `videos-published: 142` / `avg-view-count: 5300`
- runtime 聚合时也按 domain-specific schema 写回

---

## 三、PACK.md 完整规范

Pack = 多个 Pattern 的有序加载集合 + 加载条件。**Pattern 是单元,Pack 是配方。**

### 3.1 Why Pack — v0.1 dogfood 发现的硬需求

<example-project> dogfood 暴露:**审计一个 CDP 协议要同时加载 15 个 Pattern**(见 SCHEMA_EVALUATION §🎯)。
任何复杂任务的 Pattern 调用集合都很大,**手动逐个加载不可持续**。

Pack 解决两件事:
1. **批量加载**:一次 import,自动展开依赖
2. **加载顺序 + 条件**:某些 Pattern 仅在特定 stage / 特定条件下加载

### 3.2 PACK.md YAML frontmatter

```yaml
---
# === 基础标识 ===
name: <pack-id>
description: <≤200 字符>
description-en: <optional>
schema-version: 0.2

# === 触发匹配 ===
trigger: <什么场景下整 pack 被引用>
trigger-en: <optional>
anti-trigger: <禁用场景>

# === 适用范围 ===
domain: <domain-slug>
applicable-project-types:
  - <project-slug>

# === 状态 ===
status: draft | active | deprecated
version: <semver>

# === 来源追溯 ===
provenance:
  source-project: <repo slug>
  approved-by: <人>
  created: <YYYY-MM-DD>

# === 核心:包含的 Pattern (有序) ===
includes:
  - id: <pattern-id>
    when: always                              # always / on-stage-<X> / conditional:<expression>
    order: 1                                  # 加载/呈现顺序(int)
  - id: <pattern-id>
    when: conditional:category==CDP           # 条件加载
    order: 10
  # ... 更多

# === 嵌套 Pack (可选) ===
includes-pack:
  - <pack-id>                                 # 嵌套加载子 pack
                                              # 重复 Pattern 自动去重,按 order 合并
---
```

### 3.3 PACK.md Body 段

```markdown
## Purpose
本 pack 解决什么具体任务

## When to Use
明确加载本 pack 的场景

## Loading Order Rationale
为什么 includes 是这个顺序;依赖图说明

## Pack-Level Metrics
本 pack 整体被加载的次数 / 整体 success rate
(独立于单 Pattern 的 metrics)

## References
- 相关 Pack
- 出处文档
```

### 3.4 加载语义 (runtime contract)

agent 调用 Pack 时:
1. 解析 `includes-pack:` 递归展开嵌套子 pack
2. 合并所有 `includes:` 条目(去重按 id,保留 `order` 最小值)
3. 评估每条 `when:` 条件:
   - `always`:总加载
   - `on-stage-S0`:仅当当前在 S0 阶段
   - `conditional:<expr>`:评估表达式(简单 `==` / `!=` / `in`)
4. 按 `order` 升序加载到 LLM context (progressive disclosure)
5. 每个 Pattern 仍按 SKILL.md 第一层 metadata → 第二层 SKILL.md → 第三层 references 三段加载

---

## 四、Workflow + Runtime (v0.3.0)

> 这一节是 **v0.3.0 核心新增** —— 让 Pattern 从"档案 + 旁路 logging"升级为"业务运行时的真编排器"。
> Pack 必须有 `workflow:`,Pattern 可选有(适用于"独立可执行" Pattern,比如 flow- 或 playbook- 类)。

### 4.1 `workflow:` frontmatter 字段(机器可执行 step list)

```yaml
workflow:
  - step_id: <唯一名,本 workflow 内唯一>
    kind: <tool_call | llm_action | loop_until | pattern_apply | guard_check | judgment>
    # — kind 相关参数,下面分别说明 —
    # — 通用可选 —
    requires: [<step_id>, ...]              # 必须等这些 step 完成才跑
    produces: <artifact key 或 path 模板>    # 该 step 的输出(供后续 step 引用)
    guards:                                 # 该 step 跑前/跑后要 LLM check 哪些 Pattern 的 rules
      - source_pattern: <pattern-id>
        check: pre | post | both
        sections: [Rules, Anti-Pattern, Hard-Forbidden]   # 默认全部
    on_fail: <continue | break | escalate>  # 默认 break
```

### 4.2 五种 step kind

#### `tool_call` — 调外部工具

```yaml
- step_id: s0_init
  kind: tool_call
  tool: shell                              # 或 python_module / python_callable / http
  cmd: "python tools/new_audit.py {protocol_slug}"   # shell 时
  # 或 module: "defi_auto_audit.tools.audit_run"  / callable: "main" / args: {...}  (python_module 时)
  cwd: "/Users/feiyang/all_bots/defi-auto-audit"     # 可选
  timeout_s: 120                                     # 默认 60
  expect_exit_code: 0                                # 默认 0,允许多值: [0, 1]
```

#### `llm_action` — 把 Pattern body 注入 LLM 做编排决策

```yaml
- step_id: prepare_s1_artifacts
  kind: llm_action
  prompt_pattern: flow-6-stage-state-machine        # 注入该 Pattern 的 body
  prompt_sections: [Workflow, Heuristics]           # 注入哪几段;默认全 body
  instruction: "Produce edge-ledger.md for stage S1 of protocol {protocol_slug}"
  inject_context: [protocol_slug, audit_dir, prior_stage_output]
  produces: edge_ledger_path
```

#### `loop_until` — 循环执行子 step 直到条件满足

```yaml
- step_id: stage_loop
  kind: loop_until
  until: "{state.status} == 'completed' or {state.status} == 'escalated'"
  max_iterations: 18                                # 6 stages × 3 attempts
  body:
    - step_id: ...
    - step_id: ...
```

#### `pattern_apply` — 把 Pattern body 注入后续 LLM 上下文(no exec,just inject)

```yaml
- step_id: load_cdp_playbook_context
  kind: pattern_apply
  pattern: playbook-cdp
  sections: [Rules, Workflow]
  scope: subtree                                    # 仅本 step 之后的 sibling/children;或 invocation 全局
```

#### `guard_check` — LLM 用 Pattern rules 检验某 artifact / 决策

```yaml
- step_id: gate_s1
  kind: guard_check
  source_pattern: flow-6-stage-state-machine
  sections: [Rules, Anti-Pattern, Hard-Forbidden]
  subject: "{produces.edge_ledger_path}"            # 检验对象(文件 / 内存数据)
  pass_criteria: "all hard-forbidden absent AND all rules satisfied"
  on_violation: "block"                             # 或 warn / auto_rewrite
```

#### `judgment` — LLM 用 Pattern judgment 段当 rubric 评分

```yaml
- step_id: final_judgment
  kind: judgment
  source_pattern: pack-defi-audit-cdp
  subject: "{produces.audit_report_path}"
  rubric_section: Judgment                          # 默认 Judgment 段
  output_metric: judgment_score                     # 写入 invocation event 的字段名
```

### 4.3 占位符语法

- `{intent.X}` — 来自 `omw run --intent JSON` payload 的字段
- `{produces.Y}` — 前序 step 的输出
- `{state.Z}` — runtime 内部状态(loop counter / current_stage / etc)
- `{pattern.X.Y}` — 引用某 Pattern 的字段(rare)

### 4.4 Body 段被 Runtime 解析的语义

| Body 段 | Runtime 用途 |
|---|---|
| `## Rules` | `guard_check` / `llm_action` 的硬规则 prompt |
| `## Anti-Pattern` | `guard_check` 的禁止模式列表 |
| `## Hard-Forbidden` | `guard_check` 的硬禁止(违反 → 立即 escalate) |
| `## Soft-Avoid` | `guard_check` warn(不 block) |
| `## Heuristics` | `llm_action` 的决策启发式提示 |
| `## Judgment` | `judgment` step 的 rubric prompt |
| `## Workflow` | 仅人类参考;真编排在 frontmatter `workflow:` 字段 |

→ 写 Pattern 时,以上段名严格统一(大小写敏感),Runtime 才能正确解析。

---

## 五、Runtime 执行语义(v0.3.0)

### 5.1 入口

```bash
omw run <pack-id-or-pattern-id> --intent '<json>'
```

或 SDK 调用:

```python
from sdk import OMW
omw = OMW()
report = omw.run("pack-defi-audit-cdp", intent={"protocol_slug": "alto", "category": "CDP"})
```

### 5.2 执行流程

```
1. omw.load_pack(pack_id) → 递归 includes-pack 展开 → 收集所有 sub-pattern body
2. 读 pack frontmatter.workflow (机器可执行 step list)
3. 创建 root Invocation(invocation_id = inv_xxx, parent_invocation_id = None)
4. 顺序/拓扑跑每个 step:
   a. 检查 requires 是否满足
   b. (pre-guards) 跑前置 guards (LLM 用 source_pattern 的 sections 检验入参)
   c. dispatch 到对应 executor (tool_call / llm_action / loop_until / pattern_apply / guard_check / judgment)
   d. (post-guards) 跑后置 guards
   e. 每个 step 单独 emit invocation event (parent_invocation_id = root invocation_id)
      事件字段: {pattern_id, step_id, step_kind, parent_invocation_id,
                 guards_triggered: [...], judgment_score, gap_signal, success, ...}
5. 整体 judgment step(可选,Pack 配置)
6. 返回 InvocationReport
```

### 5.3 错误处理

- `on_fail: continue` — 记错继续
- `on_fail: break` — 终止本 workflow
- `on_fail: escalate` — 立即停 + 写 escalation event,给 founder review queue

### 5.4 与 v0.2 旁路调用的关系

v0.2 的 `with omw.invoke(pattern_id) as inv` 仍然支持,**但不再是推荐主路径**。
v0.3.0 推荐:业务项目通过 `omw run` 进入,业务工具变 sub-tool。

---

## 六、i18n 约定

### 4.1 当前阶段 (founder + 自家项目)

| 字段 | 语言 | 强制度 |
|---|---|---|
| frontmatter keys | 英文 | 强制 |
| body 段标题 | 英文 | 强制 |
| `description` | 中文 OK | 推荐 |
| `description-en` | 英文 | 可选 |
| `trigger` | 中文 OK | 推荐 |
| `trigger-en` | 英文 | 可选(强烈推荐) |
| body 内容 | 中文 OK | founder 母语 |
| 代码 / 工具名 / 函数名 / 错误信息 | 英文 | 强制(技术固定) |

### 4.2 推广阶段 (>50 Pattern / 跨团队 / 开源)

`-en` 字段全部转必填。Body 内容推荐双语(英文为主、中文段附在末尾)。

### 4.3 trigger 匹配

agent 任务描述可能是中文也可能是英文:
- 写中文 trigger:中文任务匹配率高
- 写英文 trigger-en:英文任务匹配率高
- 都写:**两边都覆盖**

→ v0.2 阶段建议每个 Pattern 至少补 `trigger-en`(单次工作量 < 30 秒)。

---

## 七、迁移指引 (v0.1 → v0.2 → v0.3)

### 必做项 (机械迁移)

1. `schema-version: 0.1` → `schema-version: 0.2`
2. 新增 `domain: ai-traffic-x`
3. 新增 `applicable-project-types: [<example-project>]`
4. metrics 块顶部新增 `auto-tracked: false`(等 runtime 实现后改 true)

### 应做项 (内容判断,case-by-case)

5. Body `## Negative` 段拆分为 `## Anti-Pattern` / `## Hard-Forbidden` / `## Soft-Avoid` 三段
   - 写 "立即出错 / 立即假阳性" 的 → Anti-Pattern
   - 写 "破坏评判体系 / 诚信问题" 的 → Hard-Forbidden
   - 写 "降低质量 / 漏掉漏洞" 的 → Soft-Avoid
6. References 段的 Pattern 引用抽出来,加进 frontmatter `depends-on` / `extends` / `composes-with`
7. 自由格式的领域 metric 抽进 `metrics.domain-specific`

### 推荐项 (i18n)

8. 补 `description-en` / `trigger-en` / `anti-trigger-en`(为推广预留)

### 工具化迁移

`tools/migrate-pattern-v01-to-v02.py`(待写)负责机械迁移项(1-4)+ 8;5-7 必须人工 review。

---

## 六、Schema 演化策略

- **patch (0.2.x)**:加新可选字段,改文档,无破坏性
- **minor (0.x.0)**:新增必填字段(需迁移工具),body 段重构
- **major (X.0.0)**:不向后兼容的破坏性变更(罕见)
- 任何 Pattern 写时声明 `schema-version`,加载方按此版本解析
- v0.x 阶段刻意保持 schema 不稳定;等 ≥50 个 Pattern 跑出来 + ≥3 个 dogfood 项目验证后,再 freeze v1.0
