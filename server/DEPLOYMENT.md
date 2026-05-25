# OMW Server · Deployment Guide

## 三种部署形态(选 1)

### 形态 A · 本地 dev(单用户 / 本机测试)

```bash
cd /Users/feiyang/all_bots/om-world
pip3 install fastapi 'uvicorn[standard]'

# 启动(默认 127.0.0.1:8765, only localhost)
python3 -m server.server

# 客户端切到 Stage 3
export OMW_BACKEND=server
export OMW_SERVER_URL=http://127.0.0.1:8765
export OMW_API_TOKEN=devtoken
```

**用途**:Stage 3 设计验证;founder 跨多个 process / 多个项目共享中心 invocation log。

### 形态 B · 小团队私网(Genesis Builders 阶段)

```bash
# 在团队 VPS / Hetzner / 内网 server 上:
# 1. 拉 OMW 仓库(public + private,private 仍走 SSH 协议私库)
git clone git@github.com:flyoung588/om-world.git
# 私库本地 sync,绝不公开
rsync -avz om-world-private/ user@vps:/srv/om-world-private/

# 2. 装依赖 + 配 systemd
ssh user@vps
cd /srv/om-world
pip3 install fastapi 'uvicorn[standard]'

# 3. 配多 token(每人一个)
export OMW_SERVER_TOKENS="alice:tok_a1b2c3,bob:tok_d4e5f6,founder:tok_xyz"
export HOST=0.0.0.0  # 监听全网卡(内网)
export PORT=8765

# 4. systemd unit(见下 systemd 模板)
sudo systemctl start omw-server
```

**Caddy/nginx 反向代理 + TLS**:

```caddyfile
# /etc/caddy/Caddyfile
omw-server.example.com {
    reverse_proxy 127.0.0.1:8765
    # 可选:basic auth 二层
    # basicauth { ... }
}
```

### 形态 C · 公开 OMW Cloud(Stage 3 末期 / 转 Stage 4)

走 Linux Foundation / 第三方托管:
- 公开仓库挂 Cloudflare Pages / Vercel / Fly.io
- 多用户 OAuth(GitHub OAuth App)
- visibility=private 走"作者 token allowlist"严格执行
- 持久层换 PostgreSQL(invocations 量大)
- 加 Prometheus / Grafana metrics dashboard

→ 实际转 Stage 4(IPFS + 链上 registry)更优,Stage 3 cloud 是过渡。

## Systemd unit 模板(形态 B)

```ini
# /etc/systemd/system/omw-server.service
[Unit]
Description=OMW Server (Stage 3)
After=network.target

[Service]
Type=simple
User=omw
WorkingDirectory=/srv/om-world
Environment="HOST=0.0.0.0"
Environment="PORT=8765"
Environment="OMW_SERVER_TOKENS=alice:tok_a1b2,bob:tok_c3d4,founder:tok_root"
Environment="OMW_PATTERN_PATH=/srv/om-world/patterns:/srv/om-world-private/patterns"
Environment="OMW_SERVER_DB=/srv/omw_data/server.db"
ExecStart=/usr/bin/python3 -m server.server
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用:
```bash
sudo systemctl daemon-reload
sudo systemctl enable omw-server
sudo systemctl start omw-server
sudo journalctl -u omw-server -f
```

## 安全 checklist

- [ ] **绝不**把 server bind 到 `0.0.0.0` 且无 TLS + auth(必须 nginx/Caddy TLS + 强 token)
- [ ] OMW_SERVER_TOKENS env 走 systemd EnvironmentFile,不 commit
- [ ] **绝不**把 om-world-private 仓库 push 任何 remote(本地 rsync only)
- [ ] SQLite db 文件 mode 600(`chmod 600 server.db`)
- [ ] 每周备份 server.db 到独立 server / S3
- [ ] systemd Restart=on-failure 自动恢复
- [ ] Caddy / nginx 加 rate-limit(防爬虫 / abuse)

## 客户端集成(形态 B/C)

任何接入 OMW SDK 的项目无需改代码,只改 env:

```bash
# 本地 → Stage 3 切换
export OMW_BACKEND=server
export OMW_SERVER_URL=https://omw-server.example.com
export OMW_API_TOKEN=tok_xxx
```

defi-auto-audit / AVA-trend 等已有的 shim **自动支持**(LocalBackend 自动让位 ServerBackend)。

## 监控

```bash
# health check
curl https://omw-server.example.com/health

# query metrics for any pattern
curl -H "Authorization: Bearer tok_xxx" \
  https://omw-server.example.com/patterns/<pattern-id>/metrics

# search
curl -H "Authorization: Bearer tok_xxx" -H "Content-Type: application/json" \
  -d '{"domain":"ai-traffic-x"}' \
  https://omw-server.example.com/search
```

## SQLite 数据 schema

```sql
CREATE TABLE invocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    agent_id TEXT,
    pattern_id TEXT,
    invocation_id TEXT,
    phase TEXT,
    success INTEGER,
    duration_s INTEGER,
    context TEXT,        -- JSON
    metrics TEXT,        -- JSON
    notes TEXT,
    user TEXT,           -- 来自 token allowlist
    recv_at INTEGER NOT NULL
);
CREATE INDEX idx_pattern_id ON invocations(pattern_id);
CREATE INDEX idx_invocation_id ON invocations(invocation_id);
```

Backup / dump:
```bash
sqlite3 /srv/omw_data/server.db .dump > backup_$(date +%Y%m%d).sql
```

## 演化到 Stage 4

当 Stage 3 server 长期跑通,演化触发:
- visibility=public Pattern → 内容寻址(IPFS hash)
- invocation events → 链上 attestation(EAS-like)
- 客户端 env 切 `OMW_BACKEND=protocol`,server 退化为 cache + indexer

→ 真正的 self-running protocol(类比 BTC 不依赖任何一台服务器)。详见 ARCHITECTURE.md §二 Stage 4。
