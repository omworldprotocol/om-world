# OM World 架构演化路径

> 状态:草案,2026-05-24 起稿
> 目的:**从一开始就把"以后 OMW 怎么跑"画清楚**,本地实现满足当下,接口/格式/抽象层必须为未来阶段预留。
> 单源真理(架构层):本文 + `patterns/PATTERN_SCHEMA.md`

---

## 一、核心原则

1. **协议优先于实现**:OMW 是 self-running protocol,不是某个 SaaS / app。任何决策面对"协议化未来"必须 forward-compatible。
2. **抽象层稳定 + 实现层可换**:用户/agent 永远通过 OMW SDK 调用,SDK 内部实现可在 4 阶段间无缝切换。
3. **数据格式中立 + 锚定 Skills 标准**:Pattern = Claude Skills 文件夹格式,跨 LLM 跨工具兼容(2025-12 起 12+ 工具采纳)。
4. **Founder 退出不影响系统**:仿 BTC 模型,founder 离场后协议仍可运行(规则简洁 + 数据自维护)。

---

## 二、4 阶段演化路径

### Stage 1 — Local (当前)

- **scope**:单 founder + 自家 5 个项目
- **Pattern 库存储**:`om-world/patterns/` git 工作树
- **项目引用方式**:本地相对路径 / OMW_PATTERN_PATH 环境变量
- **metrics 写回**:`patterns/<id>/metrics.jsonl` (append-only)
- **聚合**:周期性脚本 `tools/aggregate_metrics.py` 把 jsonl 聚合到 SKILL.md frontmatter
- **API 实现**:`omw.LocalBackend`
- **承诺**:所有数据可被任何文本编辑器/git 读;没有任何中心服务

**特征**:零依赖、零延迟、零信任问题、零隐私问题。

### Stage 2 — Git-Synced (跨设备)

- **scope**:founder 多设备 / 服务器协作
- **Pattern 库存储**:GitHub `om-world` 公开/私有仓库
- **项目引用方式**:git submodule / OMW_PATTERN_REMOTE 配置
- **metrics 写回**:同 Stage 1,jsonl 走 git push/pull
- **冲突处理**:metrics jsonl 用 UTC timestamp + agent_id 列分行,聚合时去重(相同 timestamp+agent 视为同一记录)
- **聚合**:定时 cron 在中心设备跑 aggregator,push 回 git
- **API 实现**:`omw.GitBackend`(继承 LocalBackend,加 git pull/push hook)

**特征**:仍无中心服务,git 是事实同步层;延迟 = pull/push 周期。

### Stage 3 — Server / Multi-User

- **scope**:Genesis Builders / 小团队协作
- **Pattern 库存储**:仍 GitHub(用于版本控制 + PR),但 metrics + invocation log 走中心 server
- **服务**:`om-world-server`(暴露 REST + GraphQL API):
  - `POST /invocations` — 记录 Pattern 加载/执行
  - `GET /patterns/<id>/metrics` — 查询聚合 metrics
  - `POST /patterns` — Pattern PR 入库(可能转 GitHub PR)
- **认证**:OAuth(GitHub) / API token
- **API 实现**:`omw.ServerBackend`
- **承诺**:metrics 数据由中心收集 + 公开 dashboard,但 Pattern 内容仍 git-tracked(可 fork)

**特征**:第一次出现"OMW 中心",承担**协调成本不承担信任成本**(Pattern 内容仍去中心化)。

### Stage 4 — Self-Running Protocol

- **scope**:任何 agent / 任何用户,匿名 / 实名均可
- **Pattern 库存储**:
  - 内容寻址(IPFS / Arweave / 类似)—— Pattern ID = `did:omw:<content-hash>` 或 `omw://<hash>`
  - 索引层:链上 registry(EAS attestation / 自定 contract)
- **invocation / metrics**:
  - 写入链上(EAS attestation 模式)或 P2P pubsub
  - 任何节点可独立聚合 + 验证(无 trusted aggregator)
- **API 实现**:`omw.ProtocolBackend`
- **承诺**:
  - founder 离场协议仍跑
  - 任何项目可独立选择只读 / 只写 / 全量参与
  - Pattern 版本演化由"内容寻址 + 引用计数"治理

**特征**:仿 BTC 模型,真正 self-running。需要解决的核心:Pattern 演化共识(类比 BTC fork)、垃圾过滤(防 spam Pattern)、incentive(谁来运行节点)。

---

## 三、跨阶段的不变接口(SDK API)

无论哪个阶段,用户代码永远只用这套 API:

```python
from omw import OMW

omw = OMW()  # 自动从 OMW_BACKEND env 选 LocalBackend / GitBackend / ServerBackend / ProtocolBackend

# === Pattern 加载 ===
pattern = omw.load_pattern("meta-x-free-tier-budget")            # 加载单 Pattern
pack = omw.load_pack("pack-example-base")           # 加载 Pack(自动展开 includes-pack + includes)

# === 运行时调用 ===
with omw.invoke(pattern_id="meta-x-free-tier-budget", context={"task_id": "T0001"}) as inv:
    # ... agent 执行 ...
    inv.record_outcome(success=True, metrics={"edges-covered-b": 9})

# === 查询 ===
metrics = omw.query_metrics("meta-x-free-tier-budget")           # 聚合查询
deps = omw.resolve_deps("meta-x-free-tier-budget")               # 解析 depends-on / extends / composes-with

# === 搜索 ===
patterns = omw.search(trigger_keywords=["X API", "rate limit"], domain="ai-traffic-x")
```

### Backend 切换

```bash
# Stage 1
export OMW_BACKEND=local
export OMW_PATTERN_PATH=/Users/feiyang/all_bots/om-world/patterns

# Stage 2
export OMW_BACKEND=git
export OMW_PATTERN_REMOTE=git@github.com:flyoung588/om-world.git

# Stage 3
export OMW_BACKEND=server
export OMW_SERVER_URL=https://api.omworld.one
export OMW_API_TOKEN=...

# Stage 4
export OMW_BACKEND=protocol
export OMW_IPFS_GATEWAY=https://ipfs.io
export OMW_REGISTRY_CHAIN=base
```

**核心承诺**:**用户代码永不变更**,只改 env 即可在 4 阶段间切换。

---

## 四、Pattern ID 在 4 阶段的演化

| 阶段 | Pattern ID 形式 | 例子 |
|---|---|---|
| 1 Local | kebab-case slug | `meta-x-free-tier-budget` |
| 2 Git-Synced | slug + git ref(可选) | `meta-x-free-tier-budget@v0.2.0` |
| 3 Server | slug + version + namespace | `ai-traffic-x/meta-x-free-tier-budget@v0.2.0` |
| 4 Protocol | content-hash | `omw://Qm.../meta-x-free-tier-budget` 或 `did:omw:<hash>` |

**向后兼容承诺**:Stage 4 实现必须能解析 Stage 1-3 的所有 ID 形式(自动 latest version 解析)。

---

## 五、Metrics 数据流

### 单次 invocation 的数据生命周期

```
[agent 加载 Pattern] 
   ↓
omw.invoke(pattern_id, context) 
   ↓
[backend 写一行到 invocation log]
   ├─ Stage 1: patterns/<id>/invocations.jsonl (append)
   ├─ Stage 2: 同上 + git push (异步,batched)
   ├─ Stage 3: POST /invocations 到中心 server
   └─ Stage 4: 链上 attestation
   ↓
[agent 执行任务]
   ↓
inv.record_outcome(success, metrics)
   ↓
[backend 更新 invocation log 末行]
   ↓
[周期性聚合]
   ├─ Stage 1: cron 跑 aggregate_metrics.py → 更新 SKILL.md frontmatter
   ├─ Stage 2: 同上,聚合后 git push
   ├─ Stage 3: server 内部聚合,查询时实时计算或 cache
   └─ Stage 4: 任意节点可独立聚合(基于内容寻址的 attestation 流)
```

### invocation.jsonl 格式(stage-invariant)

```jsonl
{"ts": 1748131200, "agent_id": "claude-opus-4-7", "pattern_id": "meta-x-free-tier-budget", "invocation_id": "inv_xyz", "context": {"task_id": "T0001"}, "phase": "loaded"}
{"ts": 1748131500, "agent_id": "claude-opus-4-7", "invocation_id": "inv_xyz", "phase": "completed", "success": true, "metrics": {"edges-covered-b": 9, "duration_min": 5}}
```

字段语义:
- `ts`:UTC unix timestamp(秒)
- `agent_id`:执行 agent 的标识(LLM model name / agent runtime id)
- `invocation_id`:本次调用 UUID,跨"loaded"/"completed"对齐
- `phase`:`loaded` / `completed` / `errored`
- `metrics`:domain-specific(对应 SKILL.md `metrics.domain-specific:` 子字段)

---

## 六、Stage 1 实现:目录结构

```
om-world/
├── ARCHITECTURE.md                 # 本文档
├── patterns/                       # Pattern 库(已建)
│   ├── PATTERN_SCHEMA.md
│   ├── INDEX.md
│   ├── <pattern-id>/SKILL.md
│   ├── packs/<pack-id>/PACK.md
│   └── tools/migrate_v01_to_v02.py
├── sdk/                            # OMW SDK (本轮新建)
│   ├── __init__.py
│   ├── omw.py                      # 主 API
│   ├── backends/
│   │   ├── __init__.py
│   │   ├── base.py                 # Backend 抽象基类
│   │   ├── local.py                # Stage 1 实现
│   │   ├── git.py                  # Stage 2 stub
│   │   ├── server.py               # Stage 3 stub
│   │   └── protocol.py             # Stage 4 stub
│   ├── pattern.py                  # Pattern dataclass
│   ├── pack.py                     # Pack dataclass
│   └── invocation.py               # Invocation context manager
├── tools/
│   ├── aggregate_metrics.py        # invocation.jsonl → SKILL.md frontmatter
│   ├── omw-cli                     # `omw search / load / invoke` CLI
│   └── ...
└── runtime/                        # 运行时数据(gitignore'd 部分)
    └── invocations.jsonl           # 中央 invocation log(也可分散到 patterns/<id>/)
```

### 关键设计点

1. **SDK 是 Python 包(`om-world/sdk/`)**:5 个自家项目都是 Python,直接 import。后续可加 TS / Go binding。
2. **Backend 抽象基类 `OMWBackend`**:定义 `load_pattern / load_pack / log_invocation / aggregate_metrics / search` 5 个方法。每阶段一个实现。
3. **invocations.jsonl 双写**:全局一份(`runtime/invocations.jsonl`)+ Pattern 一份(`patterns/<id>/invocations.jsonl`)。前者便于全局分析,后者便于聚合到 SKILL.md。Stage 1 可只写全局。
4. **aggregator 独立成 CLI 工具**:不写在 SDK 内,避免 SDK 启动慢。CLI 可被 systemd timer / cron 触发。

---

## 七、跨项目引用机制(本轮要实现)

### Stage 1 实现:env var + python package

每个自家项目(客户端项目)在 startup 时:

```python
# project's main.py
import sys, os
sys.path.insert(0, os.environ.get("OMW_SDK_PATH", "/Users/feiyang/all_bots/om-world/sdk"))

from omw import OMW
omw = OMW()  # 默认 LocalBackend,自动找 OMW_PATTERN_PATH

# 加载 Pattern
pack = omw.load_pack("pack-example-base")
for pattern in pack.patterns:
    print(pattern.skill_md_path)
```

### Stage 2-4 演化

- Stage 2:换 OMW_BACKEND=git,SDK 内部 git clone/pull
- Stage 3:换 OMW_BACKEND=server,SDK 走 REST API
- Stage 4:换 OMW_BACKEND=protocol,SDK 走 IPFS + 链上 registry

---

## 八、安全 / 信任 / 中立性的渐进强化

| 关注 | Stage 1 | Stage 2 | Stage 3 | Stage 4 |
|---|---|---|---|---|
| Pattern 真实性 | 本地信任 | git commit 签名 | server-side 签名验证 | content-addressed (hash 即身份) |
| Metrics 真实性 | 本地信任 | git history | server 审计 log | 链上 attestation |
| 谁能修改 Pattern | founder | founder + 共仓者 | PR + reviewer | content-hash 不可改 + 新版本通过引用 |
| 谁能写 Metrics | 任意本地 agent | 任意 git pushable agent | 凭 token | 凭签名 + stake |
| 防 Spam | 无需 | 无需 | rate-limit | economic incentive(类比 BTC PoW) |

---

## 九、与现有公开文档的关系

| 公开文档 | 本架构对其的影响 |
|---|---|
| `README.md` | OMW 是 protocol,本架构补齐 "protocol 怎么落地"的 4 阶段路径 |
| `SELF_GROWTH_ENGINE.md` | 本架构是 §22 三阶段路径的细化(SE §22 = Centralized → Open Registry → Distributed,本文 = Local → Git → Server → Protocol,更细粒度) |
| `ROADMAP.md` | Phase 0-5 与本文 Stage 1-4 大致对应:Phase 0-2 = Stage 1-2;Phase 3 = Stage 3;Phase 4-5 = Stage 4 |
| `LITEPAPER.md` | 协议层细节(Intent/Mandate/Proof/Settlement)在 Stage 3-4 才落地 |

---

## 十、本轮实施范围(scope-limited)

✅ 本轮实施:
- 写本架构文档(ARCHITECTURE.md)
- 写 OMW Python SDK 雏形(stage 1 LocalBackend 完整 + stage 2-4 stub)
- AVA-trend Pattern 提炼 + Pack 设计(验证 v0.2 schema)
- 把 SDK 接入 <example-project>(1-2 个示范调用点,不全部改造)

⏳ 后续轮次:
- AVA-trend 完整接入 SDK(改造 director / scheduler)
- aggregate_metrics.py 完整实现
- omw-cli 命令行工具
- Stage 2 GitBackend 实现(等 Pattern 库稳定后)
- Stage 3 / 4 在 Genesis Builders 阶段实施

---

## 十一、变更管理

本架构文档版本 v0.1。修改本文档需:
- founder approve
- 影响范围评估(是否破坏 SDK 接口承诺)
- 同步更新 SDK / README / SELF_GROWTH_ENGINE

任何"为短期方便牺牲长期协议化能力"的提议必须明确写出 trade-off,且默认拒绝(本协议长期价值 > 短期开发便利)。
