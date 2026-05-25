"""Executor base — each workflow step kind has one implementation."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..runtime import Runtime, StepContext


class Executor(ABC):
    """Abstract executor. Implementations:
      - tool_call.ToolCallExecutor
      - llm_action.LLMActionExecutor
      - loop_until.LoopUntilExecutor
      - pattern_apply.PatternApplyExecutor
      - guard_check.GuardCheckExecutor
      - judgment.JudgmentExecutor
    """

    def __init__(self, runtime: "Runtime"):
        self.runtime = runtime

    @abstractmethod
    def execute(
        self,
        step: dict[str, Any],
        ctx: "StepContext",
    ) -> dict[str, Any] | None:
        """Execute one workflow step.

        Returns a dict that may carry the following recognized keys (all optional):
          - produces: value to register under step['produces'] key
          - metrics: dict to merge into the step's completion event metrics
          - judgment_score: float 0.0-1.0
          - gap_signal: {kind, detail} when LLM lacked Pattern guidance
          - guards_triggered: list of {pattern, rule, result, ...}

        Raise RuntimeError_ (or any Exception) to signal step failure;
        Runtime will record the error and apply `on_fail` policy.
        """
