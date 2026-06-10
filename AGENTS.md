# AGENTS — om-world

> Hermes 中枢统一项目协议(UPP)清单。详见 hermes-cursor-tools/docs/UNIFIED_PROJECT_PROTOCOL.md

<!-- hermes-manifest:start -->
```yaml
schema: 1
id: om-world
display_name: OM-WORLD
classification: worldview        # worldview | content | decision | other | infra
mission: 自增长意图实现网络/意图经济协议,也是 OMW 飞轮基础设施(SDK+Pattern库+invocations事件流)
intent: 顶层世界观;所有项目作意图实现项目通过 OMW SDK 接入,omw_server.db 聚合跨项目活动
host: both
status: active
status_note: Phase 3.0-internal,27 Pattern,app.omworld.one live,验收 Gate G1-G5 未全过
capabilities:
  - 意图→mandate→执行→outcome→Pattern演化
  - OMW SDK 多 backend
  - Pattern 库+propose_evolutions 飞轮
interop:
  cli: []
  api: []
  read_signals:
    - om-world/runtime/invocations.jsonl
    - omw_server.db(hetzner-ash:8765)
    - runtime/pattern_evolution/<date>.proposals.json
daily_report: "python scripts/hermes_report.py"
relations:
  - 所有项目的 Pattern 上游与事件汇聚点
owner: feiyang
updated: 2026-06-10
```
<!-- hermes-manifest:end -->
