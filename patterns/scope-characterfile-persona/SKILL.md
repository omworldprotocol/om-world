---
name: scope-characterfile-persona
description: characterfile.yaml 驱动 persona —— voice / forbidden_words / 选题倾向 / 调性全部读 yaml;governance 必须用 yaml 不能 hardcode。
schema-version: 0.2
visibility: public

trigger: characterfile / persona / voice / forbidden_words / yaml 驱动 / character file 一致性
trigger-en: characterfile / persona / character.yaml
anti-trigger: 一次性 prompt persona

domain: ai-traffic-x
applicable-project-types:
  - SOVEREIGN-X
  - OM-WORLD-X

status: active
version: 0.1.0

depends-on:
  - meta-sovereign-x-thesis
composes-with:
  - flow-governance-gate

provenance:
  source-project: SOVEREIGN-X
  source-file: config/characterfile.yaml + governance/audit.py
  approved-by: founder
  created: 2026-05-24

metrics:
  auto-tracked: false
  invoked: 0
  measured-success-rate: null
  last-validated: 2026-05-24
---

## Rules

`config/characterfile.yaml` 是 persona 唯一真理:
- `voice`:语气描述(冷静观察者 / 不评判)
- `forbidden_words`:禁词清单
- `preferred_topics`:倾向选题
- `avoided_topics`:回避选题
- `taglines`:可用 tagline
- `signature_phrases`:特征短语

**governance / creator / planner 全部读 yaml**,绝不 hardcode。

## Heuristics

- yaml 变更需 review(影响整账号风格)
- forbidden_words 含同义词扩展(governance 用 fuzzy match)
- 跨账号(SOVEREIGN-X / OM-WORLD-X)用不同 yaml

## Anti-Pattern

- ❌ governance forbidden_words hardcode(违反硬规则)
- ❌ creator prompt 写死 voice(应 inject yaml 内容)

## Hard-Forbidden

- ❌ 多账号共用一个 characterfile(persona 混淆)
- ❌ characterfile 提交时含真账号密码 / token(走 secrets)

## Soft-Avoid

- ⚠ characterfile 字段命名漂移(代码读不到)
- ⚠ forbidden_words 过宽 → 真合规内容被误拒

## Judgment

`character_loader.py:load_character(path) -> CharacterProfile` 是唯一入口;
任何模块用 hardcoded persona 字符串 → review reject。

## Workflow

```python
# 任何用到 persona 的地方
from connectors.character_loader import load_character
char = load_character("config/characterfile.yaml")
prompt = f"{char.voice}\n\nForbidden: {char.forbidden_words}\n..."
```

## References

- 文件:`SOVEREIGN-X/config/characterfile.yaml`
- 加载器:`SOVEREIGN-X/connectors/character_loader.py`
- governance 用:`SOVEREIGN-X/governance/audit.py`
