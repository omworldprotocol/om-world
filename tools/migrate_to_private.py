#!/usr/bin/env python3
"""migrate_to_private.py — VISIBILITY_AUDIT v0.3 物理迁移脚本。

把 39 个 PRIVATE Pattern + 11 个 PRIVATE Pack 从 om-world/patterns/ 物理移动到
om-world-private/patterns/,并:
  - 给 SKILL.md / PACK.md frontmatter 加 `visibility: private`(若没)
  - 留在 om-world/patterns/ 的 19 个 PUBLIC Pattern 加 `visibility: public`(显式)

幂等 + dry-run 支持。

用法:
  python tools/migrate_to_private.py --dry-run     # 预览不做
  python tools/migrate_to_private.py               # 真跑
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

OMW = Path("/Users/feiyang/all_bots/om-world")
PRIVATE = Path("/Users/feiyang/all_bots/om-world-private")

# === VISIBILITY_AUDIT v0.3 ====================================================

# 39 个 PRIVATE Pattern(defi 22 + ava 14 + sovx 3)
PRIVATE_PATTERNS: list[str] = [
    # defi-auto-audit 22 个(整项目内部积累,不展示)
    "meta-core-target-5dim", "meta-vuln-db-3-layer", "meta-honest-0-discipline",
    "flow-6-stage-state-machine", "flow-edge-driven-audit", "flow-red-team-pivot-v11",
    "flow-adversarial-verifier", "flow-mermaid-3grep",
    "playbook-cross-cutting", "playbook-cdp", "playbook-lending",
    "playbook-yield-vault", "playbook-dexs-amm", "playbook-algo-stable",
    "scope-A-B-classify", "scope-three-streams", "scope-bespoke-priority",
    "compound-process-lesson", "compound-scope-sanity-check",
    "tech-fork-fuzz-anvil-rpc", "tech-fork-fuzz-warp-oracle",
    "tech-fork-fuzz-no-mint-then-try",
    # ava-trend 14 个
    "meta-eight-traffic-principles",
    "flow-director-pipeline-v3", "flow-snapshot-v3-collect", "flow-hook-gate-3sec",
    "playbook-hook-matrix-21", "playbook-hook-4-levers",
    "playbook-trend-3-waveforms", "playbook-narrative-frameworks",
    "tech-hard-checks-script", "tech-guardrails-banned-words",
    "tech-cross-domain-analogy", "tech-meta-word-deletion",
    "scope-topic-type-fit", "scope-tone-chigua-channel",
    # sovereign-x 3 个
    "meta-sovereign-x-thesis", "flow-9-stage-pipeline", "flow-governance-gate",
]

# 11 个 PRIVATE Pack(任一含 private pattern 即整 pack private)
PRIVATE_PACKS: list[str] = [
    # defi 6
    "pack-defi-audit-base", "pack-defi-audit-cdp", "pack-defi-audit-lending",
    "pack-defi-audit-yield-vault", "pack-defi-audit-dexs-amm",
    "pack-defi-audit-algo-stable",
    # ava 3
    "pack-ava-trend-base", "pack-ava-trend-content-creation",
    "pack-ava-trend-trend-detection",
    # sovx 2
    "pack-sovereign-x-base", "pack-sovereign-x-full",
]

# 19 个 PUBLIC Pattern(留在 om-world/patterns/,仅加显式 visibility: public)
PUBLIC_PATTERNS: list[str] = [
    # ava-trend 8 个
    "meta-ava-create-traffic", "meta-trend-single-responsibility",
    "flow-experience-backfeed", "flow-strategy-real-data-feedback",
    "scope-13-collect-channels",
    "compound-winning-failure-loop", "compound-architecture-evolution-ab",
    "compound-judge-vs-reality-pearson",
    # sovereign-x 11 个
    "meta-x-free-tier-budget", "meta-three-tier-connector",
    "flow-m7-strategy-bridge",
    "playbook-openclaw-x-bypass", "playbook-rate-limit-window",
    "tech-fire-and-forget-hermes", "tech-mock-mode-pattern",
    "tech-no-hardcoded-secrets",
    "scope-x-platform-constraints", "scope-characterfile-persona",
    "compound-strategy-bridge-loop",
]


# === frontmatter visibility 注入 ===============================================

_FM_RE = re.compile(
    r"^(?P<head>---\s*\n)(?P<fm>.*?)(?P<sep>\n---\s*\n)(?P<body>.*)$",
    re.DOTALL,
)
_VIS_LINE_RE = re.compile(r"^visibility:\s*\S+\s*$", re.MULTILINE)


def set_visibility(md_path: Path, visibility: str, dry_run: bool) -> bool:
    """In-place set visibility in frontmatter. Returns True if changed."""
    if not md_path.is_file():
        return False
    text = md_path.read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        print(f"  [warn] {md_path}: no frontmatter, skip")
        return False
    fm = m.group("fm")
    if _VIS_LINE_RE.search(fm):
        # 已有 visibility 字段 → replace
        new_fm = _VIS_LINE_RE.sub(f"visibility: {visibility}", fm)
    else:
        # 没有 → 插入 schema-version 行后(若有)否则在 frontmatter 开头
        # 优先在 description-en / description 之后,schema-version 后
        if re.search(r"^schema-version:", fm, re.MULTILINE):
            new_fm = re.sub(r"(^schema-version:.*?$)",
                             rf"\1\nvisibility: {visibility}",
                             fm, count=1, flags=re.MULTILINE)
        else:
            new_fm = f"visibility: {visibility}\n{fm}"
    if new_fm == fm:
        return False
    if dry_run:
        print(f"  [dry] {md_path.relative_to(md_path.parents[2])}: visibility → {visibility}")
        return True
    new_text = (m.group("head") + new_fm + m.group("sep") + m.group("body"))
    md_path.write_text(new_text, encoding="utf-8")
    return True


def move_pattern(pattern_id: str, dry_run: bool) -> bool:
    src = OMW / "patterns" / pattern_id
    dst = PRIVATE / "patterns" / pattern_id
    if not src.is_dir():
        if dst.is_dir():
            print(f"  [skip] {pattern_id}: already at private")
            return False
        print(f"  [miss] {pattern_id}: not in om-world/patterns/")
        return False
    if dst.exists():
        print(f"  [warn] {pattern_id}: dst already exists, skip move (manual reconcile)")
        return False
    set_visibility(src / "SKILL.md", "private", dry_run)
    if dry_run:
        print(f"  [dry] mv {src} → {dst}")
        return True
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    print(f"  [done] {pattern_id} → private")
    return True


def move_pack(pack_id: str, dry_run: bool) -> bool:
    src = OMW / "patterns" / "packs" / pack_id
    dst = PRIVATE / "patterns" / "packs" / pack_id
    if not src.is_dir():
        if dst.is_dir():
            print(f"  [skip] {pack_id}: already at private")
            return False
        print(f"  [miss] {pack_id}: not in om-world/patterns/packs/")
        return False
    if dst.exists():
        print(f"  [warn] {pack_id}: dst already exists, skip move")
        return False
    set_visibility(src / "PACK.md", "private", dry_run)
    if dry_run:
        print(f"  [dry] mv {src} → {dst}")
        return True
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    print(f"  [done] pack {pack_id} → private")
    return True


def mark_public(pattern_id: str, dry_run: bool) -> bool:
    src = OMW / "patterns" / pattern_id
    if not src.is_dir():
        print(f"  [miss-pub] {pattern_id}: not at om-world/patterns/")
        return False
    return set_visibility(src / "SKILL.md", "public", dry_run)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print(f"=== migrate_to_private.py (dry_run={args.dry_run}) ===\n")

    print(f"--- Move {len(PRIVATE_PATTERNS)} PRIVATE patterns → om-world-private/ ---")
    moved = 0
    for pid in PRIVATE_PATTERNS:
        if move_pattern(pid, args.dry_run):
            moved += 1
    print(f"  Moved/changed: {moved}/{len(PRIVATE_PATTERNS)}\n")

    print(f"--- Move {len(PRIVATE_PACKS)} PRIVATE packs → om-world-private/patterns/packs/ ---")
    pmoved = 0
    for pkid in PRIVATE_PACKS:
        if move_pack(pkid, args.dry_run):
            pmoved += 1
    print(f"  Moved/changed: {pmoved}/{len(PRIVATE_PACKS)}\n")

    print(f"--- Mark {len(PUBLIC_PATTERNS)} PUBLIC patterns (in om-world/) ---")
    pubed = 0
    for pid in PUBLIC_PATTERNS:
        if mark_public(pid, args.dry_run):
            pubed += 1
    print(f"  Marked: {pubed}/{len(PUBLIC_PATTERNS)}\n")

    if args.dry_run:
        print("=== DRY RUN — no changes written ===")
    else:
        print("=== migration complete ===")
        print(f"  Now: om-world/patterns/ = {len(PUBLIC_PATTERNS)} pattern + 0 pack")
        print(f"       om-world-private/patterns/ = +{len(PRIVATE_PATTERNS)} pattern + {len(PRIVATE_PACKS)} pack (+ 16 wedgetest)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
