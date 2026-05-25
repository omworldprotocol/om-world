"""pattern_apply executor — inject Pattern body into LLM context for downstream
llm_action / guard_check / judgment steps. Does not call LLM itself.

Scope:
  - "subtree"  (default): visible to subsequent sibling/child steps in this run
  - "global"  : visible until run end (set ctx.applied_patterns once)
"""
from __future__ import annotations

from typing import Any

from .base import Executor

DEFAULT_SECTIONS = ["Rules", "Heuristics", "Anti-Pattern", "Hard-Forbidden",
                    "Workflow", "Judgment"]


class PatternApplyExecutor(Executor):
    def execute(self, step: dict[str, Any], ctx) -> dict[str, Any] | None:
        pattern_id = step.get("pattern")
        if not pattern_id:
            raise RuntimeError("pattern_apply: missing `pattern`")
        sections = step.get("sections") or DEFAULT_SECTIONS
        # Lazy-load if not in pack.
        if pattern_id not in ctx.pattern_bodies:
            try:
                p = self.runtime.omw.load_pattern(pattern_id)
                ctx.pattern_bodies[pattern_id] = p
            except FileNotFoundError as exc:
                raise RuntimeError(f"pattern_apply: pattern '{pattern_id}' not found") from exc
        ctx.applied_patterns.append((pattern_id, sections))
        return {"metrics": {"applied_pattern": pattern_id,
                            "sections_count": len(sections)}}
