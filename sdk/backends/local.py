"""LocalBackend — Stage 1 implementation: file-system based.

Pattern 库存储在 `om-world/patterns/` 本地 git 工作树。
Invocation log 写到 `om-world/runtime/invocations.jsonl` (append-only) + 同步到
patterns/<id>/invocations.jsonl 以便聚合。

未来阶段 (GitBackend / ServerBackend / ProtocolBackend) 都可继承本类并 override
存储 / 同步 / log 的实现。
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

from ..pack import Pack, PackInclude
from ..pattern import Pattern
from .base import OMWBackend


# ─── YAML frontmatter 解析 (使用 pyyaml,系统已装 v6.x) ────────────────────────

_FRONTMATTER_RE = re.compile(
    r"^---\s*\n(?P<fm>.*?)\n---\s*\n(?P<body>.*)$", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter (--- ... ---) + return (frontmatter_dict, body)."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm_text = m.group("fm")
    body = m.group("body")
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, body


# ─── Body 段提取 ─────────────────────────────────────────────────────────────


_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def _split_body_sections(body: str) -> dict[str, str]:
    """Split markdown body into {section_name: content} dict."""
    sections: dict[str, str] = {}
    matches = list(_SECTION_RE.finditer(body))
    for idx, m in enumerate(matches):
        name = m.group(1).strip()
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        sections[name] = body[start:end].strip()
    return sections


# ─── LocalBackend ─────────────────────────────────────────────────────────────


class LocalBackend(OMWBackend):
    """Stage 1: 本地 file-system 实现。

    v0.2.1: 支持 `OMW_PATTERN_PATH` 多目录(冒号分隔),overlay 加载;
    典型用法 `<public>:<private>` —— 后者优先。新写入(invocation jsonl)
    走**首个**目录(public),private Pattern 的 invocation 走对应私有目录。
    """

    def __init__(
        self,
        patterns_dir: Path | None = None,
        runtime_dir: Path | None = None,
    ):
        default_pat = str(
            Path(__file__).resolve().parent.parent.parent / "patterns")
        env_path = os.environ.get("OMW_PATTERN_PATH", default_pat)
        path_list = [p.strip() for p in env_path.split(":") if p.strip()]
        if patterns_dir is not None:
            self.patterns_dirs: list[Path] = [Path(patterns_dir)]
        else:
            self.patterns_dirs = [Path(p) for p in path_list]
        # 向后兼容:首目录作为"主"目录(invocation log 双写时用)
        self.patterns_dir = self.patterns_dirs[0]

        self.runtime_dir = runtime_dir or Path(
            os.environ.get("OMW_RUNTIME_PATH",
                           str(Path(__file__).resolve().parent.parent.parent / "runtime"))
        )
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.global_log = self.runtime_dir / "invocations.jsonl"
        # v0.3.2 (P1.6): outbox — append-only queue of events to forward to
        # OMW server (when OMW_SERVER_URL set). A separate `tools/push_outbox.py`
        # process drains this file on its own schedule (launchd, 5min). agents
        # don't open SSH tunnel; LocalBackend always works locally + outbox
        # ships data when network is available.
        self.outbox = self.runtime_dir / "_outbox.jsonl"

    # === Pattern / Pack 加载 ===

    def _pattern_dir(self, pattern_id: str) -> Path:
        """查 pattern_id 实际位置。多目录时后写优先(overlay)。
        找不到时返回首目录(用于新建 / per-pattern invocation log)。"""
        for d in reversed(self.patterns_dirs):
            cand = d / pattern_id
            if (cand / "SKILL.md").is_file():
                return cand
        return self.patterns_dirs[0] / pattern_id

    def _pack_dir(self, pack_id: str) -> Path:
        for d in reversed(self.patterns_dirs):
            cand = d / "packs" / pack_id
            if (cand / "PACK.md").is_file():
                return cand
        return self.patterns_dirs[0] / "packs" / pack_id

    def load_pattern(self, pattern_id: str) -> Pattern:
        d = self._pattern_dir(pattern_id)
        skill = d / "SKILL.md"
        if not skill.is_file():
            raise FileNotFoundError(
                f"Pattern '{pattern_id}' not found at {skill}")
        text = skill.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(text)
        sections = _split_body_sections(body)
        scripts = d / "scripts" if (d / "scripts").is_dir() else None
        references = d / "references" if (d / "references").is_dir() else None
        return Pattern(
            id=fm.get("name", pattern_id),
            description=fm.get("description", ""),
            schema_version=str(fm.get("schema-version", "0.1")),
            trigger=fm.get("trigger", ""),
            anti_trigger=fm.get("anti-trigger", ""),
            domain=fm.get("domain", ""),
            applicable_project_types=fm.get("applicable-project-types", []) or [],
            status=fm.get("status", "active"),
            version=str(fm.get("version", "0.1.0")),
            depends_on=fm.get("depends-on", []) or [],
            extends=fm.get("extends", []) or [],
            composes_with=fm.get("composes-with", []) or [],
            provenance=fm.get("provenance", {}) or {},
            metrics=fm.get("metrics", {}) or {},
            description_en=fm.get("description-en", ""),
            trigger_en=fm.get("trigger-en", ""),
            anti_trigger_en=fm.get("anti-trigger-en", ""),
            visibility=fm.get("visibility", "private"),  # v0.2.1, 默认 private
            body=body,
            body_sections=sections,
            workflow=fm.get("workflow", []) or [],  # v0.3.0
            skill_md_path=skill,
            scripts_dir=scripts,
            references_dir=references,
        )

    def load_pack(self, pack_id: str) -> Pack:
        d = self._pack_dir(pack_id)
        pack_md = d / "PACK.md"
        if not pack_md.is_file():
            raise FileNotFoundError(f"Pack '{pack_id}' not found at {pack_md}")
        text = pack_md.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(text)
        sections = _split_body_sections(body)
        includes = []
        for raw in fm.get("includes", []) or []:
            includes.append(PackInclude(
                pattern_id=raw.get("id", ""),
                when=raw.get("when", "always"),
                order=int(raw.get("order", 100)),
            ))
        pack = Pack(
            id=fm.get("name", pack_id),
            description=fm.get("description", ""),
            schema_version=str(fm.get("schema-version", "0.1")),
            trigger=fm.get("trigger", ""),
            anti_trigger=fm.get("anti-trigger", ""),
            domain=fm.get("domain", ""),
            applicable_project_types=fm.get("applicable-project-types", []) or [],
            status=fm.get("status", "active"),
            version=str(fm.get("version", "0.1.0")),
            provenance=fm.get("provenance", {}) or {},
            description_en=fm.get("description-en", ""),
            trigger_en=fm.get("trigger-en", ""),
            visibility=fm.get("visibility", "private"),  # v0.2.1, 默认 private
            includes=includes,
            includes_pack=fm.get("includes-pack", []) or [],
            body=body,
            body_sections=sections,
            workflow=fm.get("workflow", []) or [],  # v0.3.0
            pack_md_path=pack_md,
        )
        # 递归展开 includes-pack
        all_includes: dict[str, PackInclude] = {}
        for sub_pack_id in pack.includes_pack:
            sub = self.load_pack(sub_pack_id)
            for inc in sub.includes:
                # 后者覆盖前者(让外层 pack 可重排 order)
                all_includes[inc.pattern_id] = inc
        for inc in pack.includes:
            all_includes[inc.pattern_id] = inc
        # 按 order 排序后加载 Pattern
        sorted_incs = sorted(all_includes.values(), key=lambda x: x.order)
        for inc in sorted_incs:
            try:
                pack.patterns.append(self.load_pattern(inc.pattern_id))
            except FileNotFoundError:
                # 缺 Pattern 不致命 — Pattern 库可能还在演化
                pass
        return pack

    # === 日志写入 ===

    def log_invocation_event(self, event: dict[str, Any]) -> None:
        # 三写: 全局日志 + 每 Pattern/Pack + outbox (P1.6 后台推 server)
        line = json.dumps(event, ensure_ascii=False) + "\n"
        with self.global_log.open("a", encoding="utf-8") as f:
            f.write(line)
        pid = event.get("pattern_id")
        if pid:
            # Pack id 以 'pack-' 开头 → 写到 patterns/packs/<pack-id>/;
            # 其余 → 写到 patterns/<pattern-id>/。
            target_dir = (self._pack_dir(pid) if pid.startswith("pack-")
                          else self._pattern_dir(pid))
            pat_log = target_dir / "invocations.jsonl"
            pat_log.parent.mkdir(parents=True, exist_ok=True)
            with pat_log.open("a", encoding="utf-8") as f:
                f.write(line)
        # P1.6: outbox — server push 在 tools/push_outbox.py 进程里跑,这里只 append
        with self.outbox.open("a", encoding="utf-8") as f:
            f.write(line)

    # === 搜索 / 查询 ===

    def search(
        self,
        trigger_keywords: list[str] | None = None,
        domain: str | None = None,
        project_type: str | None = None,
        visibility: str | None = None,
    ) -> list[Pattern]:
        """v0.2.1: 跨 self.patterns_dirs 全部目录搜;同 id 去重(后写优先)。
        visibility 参数:filter by visibility (None = all)."""
        seen_ids: set[str] = set()
        results: list[Pattern] = []
        # 后写优先 — reverse iterate
        for base in reversed(self.patterns_dirs):
            if not base.is_dir():
                continue
            for d in base.iterdir():
                if not d.is_dir() or d.name in (
                        "packs", "tools", "__pycache__", ".git"):
                    continue
                if not (d / "SKILL.md").is_file():
                    continue
                if d.name in seen_ids:
                    continue                          # 后写已收
                try:
                    p = self.load_pattern(d.name)
                except Exception:
                    continue
                seen_ids.add(d.name)
                if visibility and p.visibility != visibility:
                    continue
                if domain:
                    pd = p.domain
                    if not (pd == domain or
                            (isinstance(pd, list) and domain in pd)):
                        continue
                if project_type and not p.applies_to_project(project_type):
                    continue
                if trigger_keywords and not p.matches_trigger(trigger_keywords):
                    continue
                results.append(p)
        return results

    def query_metrics(self, pattern_id: str) -> dict[str, Any]:
        try:
            p = self.load_pattern(pattern_id)
        except FileNotFoundError:
            return {}
        # 当前阶段: metrics 直接从 SKILL.md frontmatter 读
        # 后续 aggregator 会刷新 frontmatter (见 tools/aggregate_metrics.py)
        return dict(p.metrics)

    def resolve_deps(self, pattern_id: str) -> dict[str, list[str]]:
        p = self.load_pattern(pattern_id)
        return {
            "depends-on": list(p.depends_on),
            "extends": list(p.extends),
            "composes-with": list(p.composes_with),
        }
