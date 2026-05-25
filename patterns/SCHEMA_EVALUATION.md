# Pattern Schema Evaluation (public)

> 详细 dogfood findings 含具体 business pattern 内容,已移至私有 overlay。
> 本文件只保留 schema **设计哲学 + 演化结论**(public 部分)。

## Schema 演化简史

- **v0.1** — 初版 schema:frontmatter + 5 段 body(Rules / Heuristics / Negative / Judgment / Workflow)
- **v0.2** — 重大重构:
  - frontmatter 加 `domain` / `applicable-project-types` / `depends-on` / `extends` / `composes-with`
  - body Negative 段拆为 `Anti-Pattern` / `Hard-Forbidden` / `Soft-Avoid` 三段
  - metrics 加 `domain-specific` + `auto-tracked`
  - i18n:`description-en` / `trigger-en` / `anti-trigger-en` 可选
  - 新增 Pack 机制(`packs/<id>/PACK.md`)
- **v0.2.1** — 加 `visibility: public | private | restricted` 字段(默认 private)+ SDK `OMW_PATTERN_PATH` 多目录 overlay
- **v1.0**(待)— freeze 后接受外部 PR

## 跨领域成立性结论(基于多领域 dogfood)

Schema 已在以下大类领域跑通:
- 智能合约审计类(代码安全 / 攻击边枚举 / fork fuzz)
- AI 流量内容创造类(短视频 + X 自动账号)
- AI 意图实现产品类(wedge validation pipeline)

**6 层结构在所有领域都自然成立**:meta / flow / playbook / tech / scope / compound。
**5 段 body 在所有领域都不被空置**(填充率 100%)。

## 关键设计决策

1. **i18n 双语字段** — frontmatter keys 强制英文(跨厂商兼容);values 可中英双语
2. **visibility 默认 private** — 协议设计偏保守,作者主动 opt-in 才公开
3. **Pack 任一 private → 整 Pack private** — 防泄露
4. **SDK overlay 加载** — `OMW_PATTERN_PATH=<public>:<private>` 让客户端代码无感切换

## 已知 v0.3 候选改进(未实施)

- metrics `domain-specific` 字段类型校验(自由 schema 失约束)
- `Negative` 三分段在某些 Pattern 重叠(部分作者反馈过细)
- `applicable-project-types` 跨多项目时手工维护成本(可加 glob 模式)
- Pack `when:` 条件 DSL 仍局限(`==/!=/in`),复杂条件难表达
- Pattern 间 `[[name]]` wiki link 未被 SDK 解析为结构化引用

参考实施详情见 PATTERN_SCHEMA.md。
