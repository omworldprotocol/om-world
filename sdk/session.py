"""Session — agent-led OMW orchestration (P1.5 / 形态 A).

When an agent (Claude Code, GPT, etc) drives a long-running task (defi audit
session, content creation session, etc), it wants:

  1. Open ONE session at task start (gets root_invocation_id).
  2. Many subsequent omw.check / omw.judge / omw.invoke calls, ALL linked to
     that root via parent_invocation_id.
  3. Close the session at task end (records aggregate outcome).

This complements `omw.run()` (CLI orchestrator) — same `parent_invocation_id`
event chain, but the orchestrator is the *agent* not the Runtime.

Usage:

    omw = OMW()
    with omw.session(pack_id="pack-defi-audit-cdp",
                     intent={"protocol_slug": "alto"}) as sess:
        # ... agent does work ...
        verdict = sess.check("meta-honest-0-discipline",
                             subject={"file": "docs/alto/finding.md"})
        if verdict.violations:
            ...
        score = sess.judge("pack-defi-audit-cdp",
                           subject={"file": "docs/alto/audit-report.md"})
        # All these events share parent_invocation_id = sess.root_invocation_id.
        sess.record_outcome(success=True, metrics={"findings": 5})
"""
from __future__ import annotations

import os
import time
import uuid
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .omw import OMW


class GuardResult:
    """Lightweight verdict object returned by Session.check()."""

    def __init__(self, raw: dict[str, Any]):
        self._raw = raw

    @property
    def passed(self) -> bool:
        return not self.violations

    @property
    def violations(self) -> list[dict[str, Any]]:
        return [g for g in self._raw.get("guards_triggered", [])
                if g.get("result") == "violation"]

    @property
    def warnings(self) -> list[dict[str, Any]]:
        return [g for g in self._raw.get("guards_triggered", [])
                if g.get("result") == "warn"]

    @property
    def hard_violations(self) -> list[dict[str, Any]]:
        return [v for v in self.violations if v.get("severity") == "hard"]

    @property
    def raw(self) -> dict[str, Any]:
        return self._raw

    def __bool__(self) -> bool:
        return self.passed

    def __repr__(self) -> str:
        return (f"GuardResult(passed={self.passed}, "
                f"violations={len(self.violations)}, "
                f"warnings={len(self.warnings)})")


class JudgmentResult:
    """Lightweight rubric-score object returned by Session.judge()."""

    def __init__(self, raw: dict[str, Any]):
        self._raw = raw

    @property
    def score(self) -> float | None:
        return self._raw.get("judgment_score")

    @property
    def rubric_hits(self) -> list[str]:
        produces = self._raw.get("produces") or {}
        return produces.get("rubric_hits", []) or []

    @property
    def improvements(self) -> list[str]:
        produces = self._raw.get("produces") or {}
        return produces.get("improvements", []) or []

    @property
    def raw(self) -> dict[str, Any]:
        return self._raw

    def __repr__(self) -> str:
        return (f"JudgmentResult(score={self.score}, "
                f"improvements={len(self.improvements)})")


class Session(AbstractContextManager["Session"]):
    """Agent-led OMW session — all events under one root_invocation_id.

    Use as a context manager. On __enter__ emits a root `loaded` event;
    on __exit__ emits a root `completed` (or `errored`) event with rolled-up
    metrics from all sub-invocations.
    """

    def __init__(
        self,
        omw: "OMW",
        pack_id: str | None = None,
        pattern_id: str | None = None,
        intent: dict[str, Any] | None = None,
        agent_id: str | None = None,
    ):
        self.omw = omw
        if not (pack_id or pattern_id):
            raise ValueError("Session: must specify pack_id or pattern_id")
        self.pack_id = pack_id
        self.pattern_id = pattern_id
        self.root_pattern_id = pack_id or pattern_id
        self.intent = dict(intent or {})
        self.agent_id = agent_id or os.environ.get(
            "OMW_AGENT_ID", "agent-session")
        self.root_invocation_id = f"inv_{uuid.uuid4().hex[:12]}"
        self._started_at: float | None = None
        self._closed = False
        # Roll-up counters.
        self._sub_count = 0
        self._guard_violations = 0
        self._guard_warnings = 0
        self._judgment_scores: list[float] = []
        self._gap_signals = 0
        # Eager-load the pack so the bodies are cached for guard/judge calls.
        self._pack = None
        self._pack_as_pattern = None  # pack itself, wrapped as a synthetic Pattern
        if pack_id:
            try:
                self._pack = self.omw.load_pack(pack_id)
                self._pack_as_pattern = self._wrap_pack_as_pattern(self._pack)
            except FileNotFoundError:
                pass  # Pattern-only sessions skip pack load.

    @staticmethod
    def _wrap_pack_as_pattern(pack):
        """Wrap a Pack as a Pattern so guard_check / judgment can target the
        pack's own body sections (mirrors runtime._pack_as_synthetic_pattern).
        """
        from .pattern import Pattern
        return Pattern(
            id=pack.id, description=pack.description,
            schema_version=pack.schema_version, trigger=pack.trigger,
            anti_trigger=pack.anti_trigger, domain=pack.domain,
            applicable_project_types=pack.applicable_project_types,
            status=pack.status, version=pack.version,
            provenance=pack.provenance, body=pack.body,
            body_sections=pack.body_sections, workflow=pack.workflow,
            visibility=pack.visibility,
        )

    # ── context manager ──

    def __enter__(self) -> "Session":
        self._started_at = time.time()
        self.omw.backend.log_invocation_event({
            "ts": int(self._started_at),
            "agent_id": self.agent_id,
            "pattern_id": self.root_pattern_id,
            "invocation_id": self.root_invocation_id,
            "phase": "loaded",
            "context": {"intent": self.intent,
                        "kind": "Pack" if self.pack_id else "Pattern",
                        "session_mode": "agent-led"},
            "step_kind": "root",
        })
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        if self._closed:
            return None
        self._emit_completion(success=False if exc_type else None,
                              error=repr(exc_val) if exc_val else None)
        return None

    def _emit_completion(self, success: bool | None,
                         metrics: dict[str, Any] | None = None,
                         notes: str = "",
                         error: str | None = None) -> None:
        if self._closed:
            return
        ev = {
            "ts": int(time.time()),
            "agent_id": self.agent_id,
            "pattern_id": self.root_pattern_id,
            "invocation_id": self.root_invocation_id,
            "phase": "errored" if error else "completed",
            "success": success,
            "duration_s": int(time.time() - (self._started_at or time.time())),
            "step_kind": "root",
            "metrics": {
                "sub_invocation_count": self._sub_count,
                "guard_violations": self._guard_violations,
                "guard_warnings": self._guard_warnings,
                "gap_signals": self._gap_signals,
                "judgment_score_avg": (round(
                    sum(self._judgment_scores) / len(self._judgment_scores), 3)
                    if self._judgment_scores else None),
                **(metrics or {}),
            },
        }
        if notes:
            ev["notes"] = notes
        if error:
            ev["error"] = error
        self.omw.backend.log_invocation_event(ev)
        self._closed = True

    def record_outcome(self, success: bool,
                       metrics: dict[str, Any] | None = None,
                       notes: str = "") -> None:
        """Close the session explicitly with an outcome. Agent should call this
        when the task succeeds/fails meaningfully (rather than relying on __exit__)."""
        self._emit_completion(success=success, metrics=metrics, notes=notes)

    # ── public ops (agent calls these inside `with`) ──

    def check(
        self,
        pattern_id: str,
        subject: Any,
        sections: list[str] | None = None,
        pass_criteria: str = "",
    ) -> GuardResult:
        """LLM checks `subject` against the given Pattern's rules / anti-patterns.

        Emits a guard_check invocation event linked to this session's root.
        """
        from .runtime import Runtime, StepContext
        rt = Runtime(self.omw)
        # Build a minimal StepContext that mimics what Runtime would.
        ctx = StepContext(intent=self.intent)
        if self._pack:
            for sub in self._pack.patterns:
                ctx.pattern_bodies[sub.id] = sub
            # Pack itself addressable by its own id for pack-as-rubric judgments
            if self._pack_as_pattern:
                ctx.pattern_bodies[self._pack.id] = self._pack_as_pattern
        sub_inv_id = self._sub_invoke_start(
            pattern_id=pattern_id, step_id=f"check_{uuid.uuid4().hex[:8]}",
            step_kind="guard_check",
            ctx_payload={"subject_preview": str(subject)[:200],
                         "sections": sections, "pass_criteria": pass_criteria})
        ok = True
        guards_triggered: list[dict[str, Any]] = []
        metrics: dict[str, Any] = {}
        err: str | None = None
        try:
            result = rt._executors["guard_check"].execute(  # noqa: SLF001
                {"source_pattern": pattern_id, "sections": sections,
                 "subject": subject, "pass_criteria": pass_criteria},
                ctx)
            guards_triggered = (result or {}).get("guards_triggered", []) or []
            metrics = (result or {}).get("metrics", {}) or {}
            for g in guards_triggered:
                r = g.get("result")
                if r == "violation":
                    self._guard_violations += 1
                elif r == "warn":
                    self._guard_warnings += 1
        except Exception as exc:  # noqa: BLE001
            ok = False
            err = f"{type(exc).__name__}: {exc}"
        self._sub_invoke_end(sub_inv_id, pattern_id=pattern_id,
                             step_id=None, step_kind="guard_check",
                             success=ok, metrics=metrics,
                             guards_triggered=guards_triggered, error=err)
        return GuardResult({"guards_triggered": guards_triggered,
                            "metrics": metrics, "error": err})

    def judge(
        self,
        pattern_id: str,
        subject: Any,
        rubric_section: str = "Judgment",
    ) -> JudgmentResult:
        """LLM scores `subject` against the given Pattern's rubric_section.

        Emits a judgment invocation event linked to this session's root.
        """
        from .runtime import Runtime, StepContext
        rt = Runtime(self.omw)
        ctx = StepContext(intent=self.intent)
        if self._pack:
            for sub in self._pack.patterns:
                ctx.pattern_bodies[sub.id] = sub
            # Pack itself addressable by its own id for pack-as-rubric judgments
            if self._pack_as_pattern:
                ctx.pattern_bodies[self._pack.id] = self._pack_as_pattern
        sub_inv_id = self._sub_invoke_start(
            pattern_id=pattern_id, step_id=f"judge_{uuid.uuid4().hex[:8]}",
            step_kind="judgment",
            ctx_payload={"subject_preview": str(subject)[:200],
                         "rubric_section": rubric_section})
        ok = True
        judgment_score: float | None = None
        metrics: dict[str, Any] = {}
        produces: dict[str, Any] = {}
        err: str | None = None
        try:
            result = rt._executors["judgment"].execute(  # noqa: SLF001
                {"source_pattern": pattern_id, "subject": subject,
                 "rubric_section": rubric_section}, ctx)
            judgment_score = (result or {}).get("judgment_score")
            metrics = (result or {}).get("metrics", {}) or {}
            produces = (result or {}).get("produces", {}) or {}
            if judgment_score is not None:
                self._judgment_scores.append(float(judgment_score))
        except Exception as exc:  # noqa: BLE001
            ok = False
            err = f"{type(exc).__name__}: {exc}"
        self._sub_invoke_end(sub_inv_id, pattern_id=pattern_id,
                             step_id=None, step_kind="judgment",
                             success=ok, metrics=metrics,
                             judgment_score=judgment_score, error=err)
        return JudgmentResult({"judgment_score": judgment_score,
                               "metrics": metrics, "produces": produces})

    def invoke(self, pattern_id: str, context: dict[str, Any] | None = None,
               step_id: str | None = None, step_kind: str | None = None):
        """Open a child Invocation under this session — context manager.

        Use for ad-hoc decisions agent wants tracked, e.g.:

            with sess.invoke("playbook-cdp",
                             context={"edge_id": "L-3"},
                             step_kind="manual_edge_eval") as inv:
                ... agent work ...
                inv.record_outcome(success=True, metrics={"covered": 1})
        """
        from .invocation import Invocation
        self._sub_count += 1
        return Invocation(
            self.omw.backend, pattern_id, context or {},
            agent_id=self.agent_id,
            parent_invocation_id=self.root_invocation_id,
            step_id=step_id,
            step_kind=step_kind,
        )

    # ── internal helpers ──

    def _sub_invoke_start(self, pattern_id: str, step_id: str, step_kind: str,
                          ctx_payload: dict[str, Any]) -> str:
        sub_inv_id = f"inv_{uuid.uuid4().hex[:12]}"
        self._sub_count += 1
        self.omw.backend.log_invocation_event({
            "ts": int(time.time()),
            "agent_id": self.agent_id,
            "pattern_id": pattern_id,
            "invocation_id": sub_inv_id,
            "parent_invocation_id": self.root_invocation_id,
            "step_id": step_id,
            "step_kind": step_kind,
            "phase": "loaded",
            "context": ctx_payload,
        })
        return sub_inv_id

    def _sub_invoke_end(self, sub_inv_id: str, pattern_id: str,
                        step_id: str | None, step_kind: str,
                        success: bool, metrics: dict[str, Any],
                        guards_triggered: list[dict[str, Any]] | None = None,
                        judgment_score: float | None = None,
                        error: str | None = None) -> None:
        ev = {
            "ts": int(time.time()),
            "agent_id": self.agent_id,
            "pattern_id": pattern_id,
            "invocation_id": sub_inv_id,
            "parent_invocation_id": self.root_invocation_id,
            "step_kind": step_kind,
            "phase": "errored" if error else "completed",
            "success": success,
        }
        if step_id:
            ev["step_id"] = step_id
        if metrics:
            ev["metrics"] = metrics
        if guards_triggered:
            ev["guards_triggered"] = guards_triggered
        if judgment_score is not None:
            ev["judgment_score"] = judgment_score
        if error:
            ev["error"] = error
        self.omw.backend.log_invocation_event(ev)


__all__ = ["Session", "GuardResult", "JudgmentResult"]
