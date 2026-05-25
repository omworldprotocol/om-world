# OMW SDK — 客户端集成指南

> Stage 1 (Local) 已完整实现;Stage 2-4 stub。所有客户端代码用同一套 API,backend 切换不改代码。
> 见 [ARCHITECTURE.md](../ARCHITECTURE.md) §三 SDK API。

## 安装(Stage 1 本地)

无需 pip install。在客户端项目入口:

```python
import sys, os
# om-world 根目录加 sys.path(SDK 是 om-world/sdk/ package)
sys.path.insert(0, os.environ.get("OMW_ROOT", "/Users/feiyang/all_bots/om-world"))

from sdk import OMW
omw = OMW()  # 自动 LocalBackend
```

依赖:`pyyaml` (Python 系统已装)。

## 环境变量

```bash
# 必须的(Stage 1)
export OMW_ROOT=/Users/feiyang/all_bots/om-world
export OMW_PATTERN_PATH=$OMW_ROOT/patterns
export OMW_RUNTIME_PATH=$OMW_ROOT/runtime

# 可选
export OMW_AGENT_ID=claude-opus-4-7   # 自报 agent 身份(写入 invocation log)
export OMW_BACKEND=local              # 默认 local;未来切 git/server/protocol
```

## 三个核心用法

### 1. 加载 Pattern + Pack

```python
# 单 Pattern
pattern = omw.load_pattern("meta-x-free-tier-budget")
print(pattern.body_sections["Rules"])
print(pattern.depends_on)

# Pack(自动展开嵌套 + 排序)
pack = omw.load_pack("pack-example-base")
for p in pack.patterns:                # 已按 includes order 排序
    print(f"{p.id} (depends_on={p.depends_on})")
```

### 2. 调用追踪(context manager)

```python
with omw.invoke(
    "meta-x-free-tier-budget",
    context={"task_id": "T0001", "stage": "S2"},
    agent_id="claude-opus-4-7",   # optional, falls back to OMW_AGENT_ID env
) as inv:
    # ... agent 实际工作 ...

    inv.record_outcome(
        success=True,
        metrics={"<domain-metric>": <value>, "duration_min": 5},
        notes="task T0001 completed"
    )
# 自动写一行到:
#   <runtime>/invocations.jsonl     (全局 log)
#   patterns/<id>/invocations.jsonl (每 Pattern log)
```

### 3. 搜索 + 查询

```python
# 按 domain 过滤
patterns = omw.search(domain="ai-traffic-x")  # X 平台相关 Pattern

# 按 trigger 关键词
cdp_related = omw.search(trigger_keywords=["X API", "rate limit"])

# 按项目类型
ava = omw.search(project_type="AVA-trend")

# Pattern 间关系
deps = omw.resolve_deps("meta-x-free-tier-budget")
# → {'depends-on': [...], 'extends': [...], 'composes-with': [...]}

# Metrics(等 aggregator 跑后从 SKILL.md frontmatter 读)
metrics = omw.query_metrics("meta-x-free-tier-budget")
```

## 集成示例:AVA-trend

```python
# services/director/pipeline.py 顶部同样接入,然后:

def run(snapshots, snapshot_source="unknown", briefs_dir=None):
    omw = OMW()
    pack = omw.load_pack("pack-ava-trend-content-creation")
    # pack.patterns 已含:base 9 + content-creation 7 = 16 个

    brief_id = _now_id()
    with omw.invoke("pack-ava-trend-content-creation",
                    context={"brief_id": brief_id, "stage": "create"}) as inv:
        # ... 原有 director 流程 ...
        inv.record_outcome(
            success=(audit.decision == "GO"),
            metrics={
                "a12_total": audit.total,
                "decision": audit.decision,
                "tactic_used": tactic,
            }
        )
```

## SDK 文件结构

```
sdk/
├── __init__.py          # 导出 OMW / Pattern / Pack / Invocation
├── omw.py               # 主 facade(backend 自动选)
├── pattern.py           # Pattern dataclass
├── pack.py              # Pack dataclass + PackInclude
├── invocation.py        # Invocation context manager
└── backends/
    ├── __init__.py
    ├── base.py          # OMWBackend 抽象基类
    ├── local.py         # ✅ Stage 1 完整实现
    ├── git.py           # ⏳ Stage 2 stub
    ├── server.py        # ⏳ Stage 3 stub
    └── protocol.py      # ⏳ Stage 4 stub
```

## Smoke test

```bash
cd /Users/feiyang/all_bots/om-world
python3 -c "
import sys; sys.path.insert(0, '.')
from sdk import OMW
omw = OMW()
print(f'Public patterns: {len(omw.search())}')
"
```

## 未来阶段迁移

Stage 1 → Stage 2 (Git-Synced):
```bash
export OMW_BACKEND=git
export OMW_PATTERN_REMOTE=git@github.com:flyoung588/om-world.git
# 代码不改 — 同一 OMW() 调用,内部走 GitBackend
```

Stage 2 → Stage 3 (Server):
```bash
export OMW_BACKEND=server
export OMW_SERVER_URL=https://api.omworld.one
export OMW_API_TOKEN=...
```

Stage 3 → Stage 4 (Protocol):
```bash
export OMW_BACKEND=protocol
export OMW_IPFS_GATEWAY=https://ipfs.io
export OMW_REGISTRY_CHAIN=base
```
