# OMW Server · Stage 3

> **状态**:reference implementation,本地可跑。Stage 3 中心化协调层。
> 单文件 FastAPI(`server.py`),SQLite(`omw_server.db`),零外部依赖(uvicorn + fastapi)。

## 这是什么

OMW 4 阶段架构(见 [ARCHITECTURE.md](../ARCHITECTURE.md))的 **Stage 3 ServerBackend** 的服务端实现。

### Stage 1 vs Stage 3 vs Stage 4 对比

| | Stage 1 Local | Stage 3 Server | Stage 4 Protocol |
|---|---|---|---|
| Pattern 存储 | 本地 git 工作树 | 中心 server git clone | IPFS / 内容寻址 |
| Invocation 写 | 本地 jsonl | POST /invocations 到中心 | 链上 attestation |
| Metrics 聚合 | launchd 定时跑本地 | server 后台聚合,客户端 GET | 任意节点独立聚合 |
| 谁负责中心 | 无中心 | 单中心(founder / org) | 无中心 |
| 适用 | 单 founder | Genesis Builders 小团队 | 任意 agent |

Stage 3 解决:**多个客户端(跨设备 / 多用户)写 invocations + 中央聚合 metrics + 跨客户端可见**。

## 快速跑(本地)

```bash
cd /Users/feiyang/all_bots/om-world

# 1. 装依赖
pip3 install fastapi 'uvicorn[standard]'

# 2. 启 server(默认 port 8765,binds 127.0.0.1 only)
python3 -m server.server

# 3. 另起 shell,客户端通过 ServerBackend 调用
export OMW_BACKEND=server
export OMW_SERVER_URL=http://127.0.0.1:8765
export OMW_API_TOKEN=devtoken
python3 -c "
from sdk import OMW
omw = OMW()
print('backend:', type(omw.backend).__name__)
p = omw.load_pattern('meta-x-free-tier-budget')
print('loaded via server:', p.id)
"
```

## API Spec

| Method | Path | 用途 | Auth |
|---|---|---|---|
| GET | `/health` | health check | 无 |
| GET | `/patterns/<id>` | 加载单 Pattern(JSON) | bearer |
| GET | `/packs/<id>` | 加载 Pack(JSON, 含展开 patterns) | bearer |
| POST | `/search` | 按 trigger/domain/project_type/visibility 过滤 | bearer |
| POST | `/invocations` | 写一个 invocation event | bearer |
| GET | `/patterns/<id>/metrics` | 查 aggregated metrics | bearer |
| GET | `/patterns/<id>/deps` | resolve depends-on / extends / composes-with | bearer |

**Auth**:bearer token,env `OMW_API_TOKEN`。当前 server 用 in-memory token set(`{"devtoken"}` for v0);未来切 OAuth/JWT。

**Visibility**:
- visibility=public Pattern 任何 token 可读
- visibility=private Pattern 仅 token 在 author allowlist 可读(v0 占位,后续实施)

## 数据来源

server 启动时从本地 `OMW_PATTERN_PATH`(overlay) 读 Pattern 文件;invocations 写 SQLite (`omw_server.db`)。

未来 Stage 3 production:server 维护一个 git clone(public + private),拿 webhook 自动 pull;客户端读走 server 而非本地。

## 部署(production)

详见 [DEPLOYMENT.md](DEPLOYMENT.md)。
