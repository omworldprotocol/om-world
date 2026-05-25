---
name: tech-no-hardcoded-secrets
description: 所有 secrets 必须走 env(python-dotenv),代码 / 配置 / repo 内绝不出现真实 API key / token / RPC URL。
schema-version: 0.2
visibility: public

trigger: secrets / API key / .env / python-dotenv / no hardcoded secrets / gitleaks
trigger-en: secrets / API key / .env / no hardcoded
anti-trigger: 公开测试 key / 文档示例 placeholder

domain: ai-traffic-x
applicable-project-types:
  - SOVEREIGN-X
  - AVA-trend
  - OM-WORLD-X
  - AVA-MI
  - ACVA
  - defi-auto-audit

status: active
version: 0.1.0

provenance:
  source-project: SOVEREIGN-X
  source-file: AGENTS.md §Security Rules + .gitleaksignore
  approved-by: founder
  created: 2026-05-24

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
---

## Rules

- `.env` 在 `.gitignore`,**绝不 commit**
- `.env.example` 列所有需要的 key 名,值留空
- 代码读 env 走 `python-dotenv`:`load_dotenv()` 一次 + `os.getenv(KEY)` 使用
- repo 内绝不出现真实 RPC URL / API key / private key
- pre-commit hook(gitleaks)拦截

## Heuristics

- 跨设备协作:`.env` 用 1Password / 私有 vault 同步,不走 git
- CI / 服务器:env 走系统 env 或 GitHub Actions Secrets
- 测试 mock key:可在代码内 hardcode("test-key-001")

## Anti-Pattern

- ❌ `.env` 不在 `.gitignore`(commit 灾难)
- ❌ key 写进配置文件 commit(yaml / json)
- ❌ `os.environ.get(KEY, "real_default_key")`(默认值含真 key)

## Hard-Forbidden

- ❌ 真生产 key commit 到 repo(无论 public/private)—— 立即 rotate
- ❌ key 写进代码注释 / docstring

## Soft-Avoid

- ⚠ env 名写成 SECRET_KEY 容易混(应明确 OPENAI_API_KEY / DEEPSEEK_API_KEY)
- ⚠ 多 env 不分隔(production / staging / dev 混 .env)

## Judgment

- `gitleaks` pre-commit 扫描
- `.gitleaksignore` 列已知 false positive
- code review:任何 commit 含 `sk-` / `eyJ...` 等 pattern → 拦截

## Workflow

```bash
# 一次性 setup
cp .env.example .env
# 编辑 .env 填入真 key

# 代码
from dotenv import load_dotenv
load_dotenv()
import os
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise RuntimeError("DEEPSEEK_API_KEY missing")
```

## References

- 原文:`SOVEREIGN-X/AGENTS.md` §Security Rules
- gitleaks:`.gitleaksignore`(每个项目根)
- .env.example:每个项目必有
