"""OMWBackend — 抽象基类, 4 阶段都继承自此。

不变接口:
- load_pattern(pattern_id) -> Pattern
- load_pack(pack_id) -> Pack (with patterns populated)
- log_invocation_event(event_dict)
- search(trigger_keywords, domain, project_type) -> list[Pattern]
- query_metrics(pattern_id) -> dict

ARCHITECTURE.md §三 是单源真理。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..pack import Pack
from ..pattern import Pattern


class OMWBackend(ABC):
    """Abstract base for all OMW backends."""

    @abstractmethod
    def load_pattern(self, pattern_id: str) -> Pattern:
        """Load and parse a single Pattern by id."""

    @abstractmethod
    def load_pack(self, pack_id: str) -> Pack:
        """Load a Pack and resolve all its included Patterns (incl. nested includes-pack)."""

    @abstractmethod
    def log_invocation_event(self, event: dict[str, Any]) -> None:
        """Append an invocation event to the jsonl log (or remote equivalent)."""

    @abstractmethod
    def search(
        self,
        trigger_keywords: list[str] | None = None,
        domain: str | None = None,
        project_type: str | None = None,
        visibility: str | None = None,
    ) -> list[Pattern]:
        """Find Patterns matching all given filters.

        v0.2.1: visibility parameter — None = all; "public" / "private" / "restricted".
        """

    @abstractmethod
    def query_metrics(self, pattern_id: str) -> dict[str, Any]:
        """Return current aggregated metrics for a Pattern."""

    @abstractmethod
    def resolve_deps(self, pattern_id: str) -> dict[str, list[str]]:
        """Return {'depends-on': [...], 'extends': [...], 'composes-with': [...]}."""
