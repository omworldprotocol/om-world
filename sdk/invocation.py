"""Invocation — context manager for tracked Pattern invocations.

Usage:
    with omw.invoke("playbook-cdp", context={"audit_id": "A0003"}) as inv:
        # ... agent code ...
        inv.record_outcome(success=True, metrics={"edges-covered-b": 9})

Backend hook:
- on __enter__: append "loaded" event to invocations.jsonl
- on record_outcome / __exit__ (with error): append "completed" / "errored" event

invocation_id 是 UUID, 跨 loaded/completed/errored 对齐, 让后续 aggregator 能配对。
"""
from __future__ import annotations

import os
import time
import uuid
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .backends.base import OMWBackend


class Invocation(AbstractContextManager["Invocation"]):
    """Context manager for one Pattern invocation.

    v0.3.0 additions:
      - parent_invocation_id: link sub-step invocations to root run
      - step_id / step_kind: identify which workflow step (for Pack-level runs)
      - record_outcome accepts guards_triggered / judgment_score / gap_signal
    """

    def __init__(
        self,
        backend: "OMWBackend",
        pattern_id: str,
        context: dict[str, Any] | None = None,
        agent_id: str | None = None,
        parent_invocation_id: str | None = None,
        step_id: str | None = None,
        step_kind: str | None = None,
    ):
        self._backend = backend
        self.pattern_id = pattern_id
        self.context = context or {}
        # agent_id: try env hint, then default to "unknown-agent"
        self.agent_id = agent_id or os.environ.get(
            "OMW_AGENT_ID", "unknown-agent")
        self.invocation_id = f"inv_{uuid.uuid4().hex[:12]}"
        self.parent_invocation_id = parent_invocation_id
        self.step_id = step_id
        self.step_kind = step_kind
        self._started_at: float | None = None
        self._completed = False

    def _base_event(self, phase: str) -> dict[str, Any]:
        ev: dict[str, Any] = {
            "ts": int(time.time()),
            "agent_id": self.agent_id,
            "pattern_id": self.pattern_id,
            "invocation_id": self.invocation_id,
            "phase": phase,
        }
        if self.parent_invocation_id:
            ev["parent_invocation_id"] = self.parent_invocation_id
        if self.step_id:
            ev["step_id"] = self.step_id
        if self.step_kind:
            ev["step_kind"] = self.step_kind
        return ev

    def __enter__(self) -> "Invocation":
        self._started_at = time.time()
        ev = self._base_event("loaded")
        ev["context"] = self.context
        self._backend.log_invocation_event(ev)
        return self

    def record_outcome(
        self,
        success: bool,
        metrics: dict[str, Any] | None = None,
        notes: str = "",
        guards_triggered: list[dict[str, Any]] | None = None,
        judgment_score: float | None = None,
        gap_signal: dict[str, Any] | None = None,
    ) -> None:
        """Mark this invocation as completed with outcome.

        v0.3.0 fields:
          guards_triggered: list of {pattern, rule, result} — which guard rules
                             fired and whether subject passed/violated/warned.
          judgment_score: 0.0-1.0 LLM rubric score (for `judgment` step).
          gap_signal: {kind, detail} when LLM lacked Pattern guidance for this step.
        """
        event = self._base_event("completed")
        # 2026-05-28 fix: 透传 context 到 completed event(原 SDK 只在 __enter__
        # 的 loaded event 加 context,record_outcome 的 completed event 没 context
        # → server 表里 SQL `json_extract(context,'$.audit_id')` 拿不到 completed
        # events → propose_evolutions / defi_audit_growth_report 漏看一半数据,
        # 把 19 guards / 22 judgment 全 miss 当 0)。
        event["context"] = self.context
        event["success"] = success
        event["duration_s"] = int(time.time() - (self._started_at or time.time()))
        if metrics:
            event["metrics"] = metrics
        if notes:
            event["notes"] = notes
        if guards_triggered:
            event["guards_triggered"] = guards_triggered
        if judgment_score is not None:
            event["judgment_score"] = judgment_score
        if gap_signal:
            event["gap_signal"] = gap_signal
        self._backend.log_invocation_event(event)
        self._completed = True

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        if self._completed:
            return None
        # Auto-record an "errored" event if user did not call record_outcome.
        event = self._base_event("errored" if exc_type else "completed")
        event["success"] = False if exc_type else None
        event["duration_s"] = int(time.time() - (self._started_at or time.time()))
        if exc_val:
            event["error"] = repr(exc_val)
        self._backend.log_invocation_event(event)
        return None
