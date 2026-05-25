"""Pack — dataclass for parsed PACK.md.

Pack = N 个 Pattern 的有序加载集合 + 加载条件。见 ARCHITECTURE.md + PATTERN_SCHEMA.md §三。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .pattern import Pattern


@dataclass
class PackInclude:
    """单条 includes 条目。"""
    pattern_id: str
    when: str = "always"                          # always / on-stage-<X> / conditional:<expr>
    order: int = 100

    def is_active(self, context: dict[str, Any]) -> bool:
        """Evaluate `when` against context.

        Stage 1 supports:
          - always
          - on-stage-<X> (matches if context.get("stage") == X)
          - conditional:<key>==<val> (simple == compare)
          - conditional:<key>!=<val>
          - conditional:<key> in <val1>,<val2>
        """
        if self.when == "always":
            return True
        if self.when.startswith("on-stage-"):
            return context.get("stage") == self.when[len("on-stage-"):]
        if self.when.startswith("conditional:"):
            expr = self.when[len("conditional:"):].strip()
            if "==" in expr:
                k, v = (s.strip() for s in expr.split("==", 1))
                return str(context.get(k)) == v
            if "!=" in expr:
                k, v = (s.strip() for s in expr.split("!=", 1))
                return str(context.get(k)) != v
            if " in " in expr:
                k, vlist = (s.strip() for s in expr.split(" in ", 1))
                return str(context.get(k)) in [v.strip() for v in vlist.split(",")]
        return False


@dataclass
class Pack:
    """Parsed Pack (PACK.md)."""

    id: str
    description: str
    schema_version: str
    trigger: str = ""
    anti_trigger: str = ""
    domain: str | list[str] = ""
    applicable_project_types: list[str] = field(default_factory=list)
    status: str = "active"
    version: str = "0.1.0"
    provenance: dict[str, Any] = field(default_factory=dict)

    # i18n optional
    description_en: str = ""
    trigger_en: str = ""

    # v0.2.1: visibility — public / private / restricted (default private)
    visibility: str = "private"

    # Pack-specific
    includes: list[PackInclude] = field(default_factory=list)
    includes_pack: list[str] = field(default_factory=list)

    # Resolved patterns (populated by backend.load_pack)
    patterns: list[Pattern] = field(default_factory=list)

    # Body
    body: str = ""
    body_sections: dict[str, str] = field(default_factory=dict)

    # v0.3.0: machine-executable workflow at the Pack level.
    # Required for any Pack that is meant to be invoked via `omw run`.
    # Step kinds: tool_call / llm_action / loop_until / pattern_apply / guard_check / judgment.
    # See PATTERN_SCHEMA.md §四 for the full spec.
    workflow: list[dict[str, Any]] = field(default_factory=list)

    pack_md_path: Path | None = None

    def __repr__(self) -> str:
        return f"Pack(id={self.id!r}, includes={len(self.includes)}, patterns={len(self.patterns)})"
