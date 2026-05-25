"""Pattern — dataclass for parsed SKILL.md."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Pattern:
    """Parsed Pattern (SKILL.md frontmatter + body)."""

    id: str                                       # frontmatter.name
    description: str
    schema_version: str
    trigger: str
    anti_trigger: str = ""
    domain: str | list[str] = ""
    applicable_project_types: list[str] = field(default_factory=list)
    status: str = "active"
    version: str = "0.1.0"
    depends_on: list[str] = field(default_factory=list)
    extends: list[str] = field(default_factory=list)
    composes_with: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)

    # i18n optional
    description_en: str = ""
    trigger_en: str = ""
    anti_trigger_en: str = ""

    # v0.2.1: visibility — public / private / restricted (default private)
    visibility: str = "private"

    # Body content
    body: str = ""                                # raw markdown body
    body_sections: dict[str, str] = field(default_factory=dict)  # section_name -> content

    # v0.3.0: machine-executable workflow (frontmatter `workflow:` field)
    # When present, OMW Runtime can execute this Pattern as a self-contained intent.
    # Empty list = doc-only Pattern (still usable as guard/heuristic/judgment source).
    workflow: list[dict[str, Any]] = field(default_factory=list)

    # Resource paths
    skill_md_path: Path | None = None
    scripts_dir: Path | None = None
    references_dir: Path | None = None

    def has_section(self, name: str) -> bool:
        return name in self.body_sections

    def section(self, name: str) -> str:
        return self.body_sections.get(name, "")

    def matches_trigger(self, keywords: list[str]) -> bool:
        """Naive substring match over trigger / trigger-en."""
        t = (self.trigger + " " + self.trigger_en).lower()
        return any(kw.lower() in t for kw in keywords)

    def applies_to_project(self, project_slug: str) -> bool:
        if not self.applicable_project_types:
            return True
        return "*" in self.applicable_project_types or \
            project_slug in self.applicable_project_types

    def __repr__(self) -> str:
        return f"Pattern(id={self.id!r}, v{self.schema_version}, status={self.status})"
