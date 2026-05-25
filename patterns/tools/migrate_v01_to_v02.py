#!/usr/bin/env python3
"""migrate_v01_to_v02.py — 把 v0.1 Pattern 的 frontmatter 机械迁移到 v0.2。

机械迁移项(本脚本处理):
  1. schema-version: 0.1 → 0.2
  2. 新增 domain: defi-audit (defi-auto-audit 项目特化)
  3. 新增 applicable-project-types: [defi-auto-audit]
  4. metrics 块顶部插入 auto-tracked: false
  5. (基于源材料启发)添加 depends-on / extends / composes-with(已硬编码映射,见 RELATIONS)

需要人工 review 项(本脚本不处理):
  - Negative 段拆分为 Anti-Pattern / Hard-Forbidden / Soft-Avoid
  - description-en / trigger-en 翻译(可后跑专门脚本)
  - metrics.domain-specific 字段填具体值

用法:
  python tools/migrate_v01_to_v02.py [pattern-id ...]    # 指定 Pattern
  python tools/migrate_v01_to_v02.py --all                # 全部除 playbook-cdp(已手工迁完)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERNS_DIR = Path(__file__).resolve().parent.parent

# 已知 Pattern 关系图(基于 v0.1 References 段抽取)
RELATIONS = {
    # === meta ===
    "meta-core-target-5dim": {
        "depends-on": [], "extends": [], "composes-with": ["meta-honest-0-discipline"]},
    "meta-vuln-db-3-layer": {
        "depends-on": [], "extends": [],
        "composes-with": ["compound-process-lesson", "playbook-cross-cutting",
                          "playbook-cdp", "playbook-lending", "playbook-yield-vault",
                          "playbook-dexs-amm", "playbook-algo-stable"]},
    "meta-honest-0-discipline": {
        "depends-on": ["meta-core-target-5dim"], "extends": [],
        "composes-with": ["flow-adversarial-verifier"]},
    # === flow ===
    "flow-6-stage-state-machine": {
        "depends-on": ["meta-core-target-5dim"],
        "extends": [],
        "composes-with": ["flow-edge-driven-audit", "flow-adversarial-verifier",
                          "compound-process-lesson"]},
    "flow-edge-driven-audit": {
        "depends-on": ["meta-core-target-5dim"],
        "extends": [],
        "composes-with": ["flow-mermaid-3grep", "flow-red-team-pivot-v11"]},
    "flow-red-team-pivot-v11": {
        "depends-on": ["meta-core-target-5dim"],
        "extends": ["flow-edge-driven-audit"],
        "composes-with": ["tech-fork-fuzz-anvil-rpc", "flow-adversarial-verifier"]},
    "flow-adversarial-verifier": {
        "depends-on": ["meta-core-target-5dim", "meta-honest-0-discipline"],
        "extends": [],
        "composes-with": ["flow-6-stage-state-machine"]},
    "flow-mermaid-3grep": {
        "depends-on": [],
        "extends": ["flow-edge-driven-audit"],
        "composes-with": []},
    # === playbook ===
    "playbook-cross-cutting": {
        "depends-on": [], "extends": [],
        "composes-with": ["playbook-cdp", "playbook-lending", "playbook-yield-vault",
                          "playbook-dexs-amm", "playbook-algo-stable"]},
    "playbook-cdp": "SKIP",  # 已手工迁完
    "playbook-lending": {
        "depends-on": ["meta-core-target-5dim", "meta-honest-0-discipline"],
        "extends": ["playbook-cross-cutting"],
        "composes-with": ["flow-edge-driven-audit", "flow-6-stage-state-machine",
                          "tech-fork-fuzz-anvil-rpc", "tech-fork-fuzz-warp-oracle",
                          "tech-fork-fuzz-no-mint-then-try"]},
    "playbook-yield-vault": {
        "depends-on": ["meta-core-target-5dim", "meta-honest-0-discipline"],
        "extends": ["playbook-cross-cutting"],
        "composes-with": ["flow-edge-driven-audit", "tech-fork-fuzz-anvil-rpc",
                          "tech-fork-fuzz-no-mint-then-try"]},
    "playbook-dexs-amm": {
        "depends-on": ["meta-core-target-5dim", "meta-honest-0-discipline"],
        "extends": ["playbook-cross-cutting"],
        "composes-with": ["flow-edge-driven-audit", "tech-fork-fuzz-anvil-rpc",
                          "tech-fork-fuzz-no-mint-then-try"]},
    "playbook-algo-stable": {
        "depends-on": ["meta-core-target-5dim", "meta-honest-0-discipline"],
        "extends": ["playbook-cross-cutting"],
        "composes-with": ["flow-edge-driven-audit", "tech-fork-fuzz-anvil-rpc",
                          "tech-fork-fuzz-warp-oracle", "tech-fork-fuzz-no-mint-then-try"]},
    # === tech ===
    "tech-fork-fuzz-anvil-rpc": {
        "depends-on": [], "extends": [],
        "composes-with": ["tech-fork-fuzz-warp-oracle",
                          "tech-fork-fuzz-no-mint-then-try"]},
    "tech-fork-fuzz-warp-oracle": {
        "depends-on": ["tech-fork-fuzz-anvil-rpc"],
        "extends": [],
        "composes-with": ["playbook-lending", "playbook-cdp", "playbook-algo-stable"]},
    "tech-fork-fuzz-no-mint-then-try": {
        "depends-on": [],
        "extends": [],
        "composes-with": ["tech-fork-fuzz-anvil-rpc"]},
    # === scope ===
    "scope-A-B-classify": {
        "depends-on": [], "extends": [],
        "composes-with": ["scope-three-streams", "scope-bespoke-priority"]},
    "scope-three-streams": {
        "depends-on": ["scope-A-B-classify"], "extends": [],
        "composes-with": ["scope-bespoke-priority"]},
    "scope-bespoke-priority": {
        "depends-on": ["scope-three-streams"], "extends": [],
        "composes-with": []},
    # === compound ===
    "compound-process-lesson": {
        "depends-on": ["meta-vuln-db-3-layer"],
        "extends": [],
        "composes-with": ["flow-6-stage-state-machine"]},
    "compound-scope-sanity-check": {
        "depends-on": ["scope-A-B-classify"],
        "extends": [],
        "composes-with": ["flow-edge-driven-audit"]},
}


def migrate_one(skill_path: Path) -> bool:
    """返回 True 表示有改动。"""
    pid = skill_path.parent.name
    rel = RELATIONS.get(pid)
    if rel == "SKIP":
        print(f"  [skip] {pid} (already migrated manually)")
        return False
    if rel is None:
        print(f"  [warn] {pid} not in RELATIONS, skipping")
        return False

    text = skill_path.read_text(encoding="utf-8")
    original = text

    # 1. schema-version 0.1 → 0.2
    text = re.sub(r"schema-version:\s*0\.1", "schema-version: 0.2", text)

    # 2. 在 schema-version 行后插入 domain / applicable-project-types(如果还没有)
    if "domain:" not in text:
        text = re.sub(
            r"(schema-version: 0\.2\n)",
            r"\1\ndomain: defi-audit\napplicable-project-types:\n  - defi-auto-audit\n",
            text, count=1,
        )

    # 3. 在 status 行前插入 depends-on / extends / composes-with(如果还没有)
    if "depends-on:" not in text:
        rel_block = "\n"
        if rel["depends-on"]:
            rel_block += "depends-on:\n" + \
                "".join(f"  - {x}\n" for x in rel["depends-on"])
        if rel["extends"]:
            rel_block += "extends:\n" + \
                "".join(f"  - {x}\n" for x in rel["extends"])
        if rel["composes-with"]:
            rel_block += "composes-with:\n" + \
                "".join(f"  - {x}\n" for x in rel["composes-with"])
        if rel_block.strip():
            text = re.sub(
                r"(\nstatus:\s)",
                rel_block + r"\1",
                text, count=1,
            )

    # 4. 在 metrics: 之后插入 auto-tracked: false(如果还没有)
    if "auto-tracked:" not in text:
        text = re.sub(
            r"(metrics:\n)",
            r"\1  auto-tracked: false\n",
            text, count=1,
        )

    if text == original:
        print(f"  [nochg] {pid}")
        return False

    skill_path.write_text(text, encoding="utf-8")
    print(f"  [done]  {pid}")
    return True


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("用法: python tools/migrate_v01_to_v02.py [pattern-id...] | --all")
        return 1
    if args == ["--all"]:
        targets = sorted(RELATIONS.keys())
    else:
        targets = args
    n = 0
    for pid in targets:
        p = PATTERNS_DIR / pid / "SKILL.md"
        if not p.is_file():
            print(f"  [miss]  {pid} (no SKILL.md)")
            continue
        if migrate_one(p):
            n += 1
    print(f"\n✓ migrated {n}/{len(targets)} patterns")
    return 0


if __name__ == "__main__":
    sys.exit(main())
