---
name: playbook-openclaw-x-bypass
description: 用 OpenClaw + Chrome CDP(用户已登录 session)绕过 X API —— 不需 X API credentials,绕 Free Tier search 不可用限制。
schema-version: 0.2
visibility: public

trigger: OpenClaw / X API bypass / Chrome CDP / Playwright / x-twitter-poster skill / web-search / agent-browser-cli / 无 API key 发推
trigger-en: OpenClaw / X API bypass / Chrome CDP / no-credentials X posting
anti-trigger: 用 X API Premium 付费的场景

domain: ai-traffic-x
applicable-project-types:
  - SOVEREIGN-X
  - OM-WORLD-X

status: active
version: 0.1.0

composes-with:
  - meta-x-free-tier-budget
  - scope-x-platform-constraints

provenance:
  source-project: SOVEREIGN-X
  source-file: AGENTS.md §OpenClaw Integration
  approved-by: founder
  created: 2026-05-24

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
  domain-specific:
    skills-used: ["x-twitter-poster", "web-search", "agent-browser-cli"]
    bypass-targets: ["X Search API (not available in Free Tier)", "X API daily write quota (use browser supplement)"]
---

## Rules

OpenClaw 三 skill 覆盖 X API 限制:

| Skill | 用途 | 替代什么 |
|---|---|---|
| `x-twitter-poster` | Playwright + 用户已登录 Chrome CDP 发推 | `POST /2/tweets`(配额限制 / 无 API key 时) |
| `web-search` | DuckDuckGo search | SerpAPI 配额 |
| `agent-browser-cli` | headless browser 抓页面 | content extraction(无 X Search API) |

**Chrome CDP 前置**:Chrome 启动加 `--remote-debugging-port=28800`,OpenClaw connect 该端口。

## Heuristics

- x-twitter-poster 用真实浏览器 session = X 视为正常用户行为(不触 rate limit)
- 但仍受**账号级别**的反 spam 风控约束(每天发 100 推会被人工 flag)
- web-search DuckDuckGo 免费但 rate limit 中等,大量搜索仍建议 SerpAPI 配额
- OpenClaw daemon 本地 `ws://127.0.0.1:18789`,失联时 fallback 走 [[meta-three-tier-connector]]

## Anti-Pattern

- ❌ Chrome 没起 `--remote-debugging-port` → OpenClaw 连不上
- ❌ 同 Chrome session 同时被用户用 + OpenClaw 用 → 互相打架
- ❌ 把 `CMDOP_API_KEY` 当 OpenClaw 必需(它是 remote 管理用,与 X 发推无关)

## Hard-Forbidden

- ❌ 用 OpenClaw bypass 大批量自动发推(>X 账号正常使用上限)→ 账号封禁
- ❌ OpenClaw skill 输出未经 M8 governance 直接 publish(违反 [[flow-governance-gate]])

## Soft-Avoid

- ⚠ OpenClaw + X API 混用同账号(数据 dedup 难)
- ⚠ x-twitter-poster 发完不抓 platform_id(下游 monitor 找不到)

## Judgment

OpenClaw daemon health:`ws://127.0.0.1:18789` ping 通过 + auth token 有效。
post 后:Playwright 抓 X 返回的 tweet_id → 存 DB。

## Workflow

```
publisher.post_tweet(text):
  if X API quota OK:
    use X API
  else:
    if openclaw daemon up:
      openclaw_client.post_tweet_via_browser(text)
      → 抓 tweet_id 存 DB
    else:
      skip + Hermes notify
```

## References

- 原文:`SOVEREIGN-X/AGENTS.md` §OpenClaw Integration
- 实现:`SOVEREIGN-X/connectors/openclaw_client.py`
- OpenClaw skills:`/Users/feiyang/.openclaw/workspace/skills/{x-twitter-poster,web-search,agent-browser-cli}/`
