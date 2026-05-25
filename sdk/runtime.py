"""Runtime — v0.3.0 OMW pack-driven orchestrator.

Reads `pack.workflow` (or `pattern.workflow`) and dispatches each step through
the executor registry, emitting fine-grained invocation events linked by
`parent_invocation_id` to the root run.

This is what makes Patterns *executable* rather than just documentary:
the Pack defines the step graph, sub-Patterns provide rules/heuristics/
anti-patterns/judgment that guard each step, and business code is reduced
to sub-tools dispatched by `tool_call` steps.

See patterns/PATTERN_SCHEMA.md §四 + §五 for the schema spec and execution
semantics.
"""
from __future__ import annotations

import os
import time
import uuid
from typing import TYPE_CHECKING, Any

from .pack import Pack
from .pattern import Pattern

if TYPE_CHECKING:
    from .omw import OMW
    from .executors.base import Executor


class RuntimeError_(RuntimeError):
    """Runtime-level error during workflow execution."""


class StepContext:
    """Mutable state passed through workflow execution. Holds intent payload,
    produced artifacts (per-step), and runtime state ({state.X} substitutions).

    Substitution syntax (see PATTERN_SCHEMA.md §4.3):
      {intent.X}    → intent payload field
      {produces.Y}  → output of a prior step
      {state.Z}     → runtime internal state (e.g. loop_index)
    """

    def __init__(self, intent: dict[str, Any] | None = None):
        self.intent: dict[str, Any] = dict(intent or {})
        self.produces: dict[str, Any] = {}
        self.state: dict[str, Any] = {}
        # All sub-pattern bodies available to guard_check / llm_action / pattern_apply.
        # Keyed by pattern_id; populated by Runtime.run from pack.patterns.
        self.pattern_bodies: dict[str, Pattern] = {}
        # Patterns whose body was injected via pattern_apply (LLM-context bag).
        self.applied_patterns: list[tuple[str, list[str]]] = []  # (pattern_id, sections)
        # Step-by-step event log (in-memory mirror of what backend persisted).
        self.events: list[dict[str, Any]] = []

    def substitute(self, value: Any) -> Any:
        """Recursively substitute placeholders in strings; pass-through for other types."""
        if isinstance(value, str):
            return self._sub_str(value)
        if isinstance(value, list):
            return [self.substitute(v) for v in value]
        if isinstance(value, dict):
            return {k: self.substitute(v) for k, v in value.items()}
        return value

    def _sub_str(self, s: str) -> str:
        # Cheap placeholder pass — replace {intent.X} / {produces.Y} / {state.Z}.
        # Pattern: {(intent|produces|state)\.(\w+)}
        import re
        def repl(m: re.Match[str]) -> str:
            kind, key = m.group(1), m.group(2)
            src = {"intent": self.intent, "produces": self.produces,
                   "state": self.state}[kind]
            return str(src.get(key, m.group(0)))  # leave unresolved as-is
        return re.sub(r"\{(intent|produces|state)\.(\w+)\}", repl, s)


class Runtime:
    """Pack-driven execution runtime.

    Pluggable executors registered by `step.kind`. See executors/ for the
    six built-in kinds (tool_call / llm_action / loop_until / pattern_apply
    / guard_check / judgment).
    """

    def __init__(self, omw: "OMW"):
        self.omw = omw
        self._executors: dict[str, "Executor"] = {}
        self._register_default_executors()

    # ── executor registry ──

    def _register_default_executors(self) -> None:
        from .executors.tool_call import ToolCallExecutor
        from .executors.llm_action import LLMActionExecutor
        from .executors.loop_until import LoopUntilExecutor
        from .executors.pattern_apply import PatternApplyExecutor
        from .executors.guard_check import GuardCheckExecutor
        from .executors.judgment import JudgmentExecutor

        self._executors["tool_call"] = ToolCallExecutor(self)
        self._executors["llm_action"] = LLMActionExecutor(self)
        self._executors["loop_until"] = LoopUntilExecutor(self)
        self._executors["pattern_apply"] = PatternApplyExecutor(self)
        self._executors["guard_check"] = GuardCheckExecutor(self)
        self._executors["judgment"] = JudgmentExecutor(self)

    def register_executor(self, kind: str, executor: "Executor") -> None:
        self._executors[kind] = executor

    # ── main entry ──

    def run(
        self,
        target_id: str,
        intent: dict[str, Any] | None = None,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        # 1. Load target (Pack first, then Pattern fallback).
        target, target_kind = self._load_target(target_id)
        workflow = target.workflow
        if not workflow:
            raise RuntimeError_(
                f"{target_kind} '{target_id}' has no `workflow:` frontmatter. "
                f"Cannot run; only Patterns/Packs with workflow are executable. "
                f"See PATTERN_SCHEMA.md §四.")

        # 2. Build StepContext (load sub-pattern bodies if target is a Pack).
        ctx = StepContext(intent=intent)
        if isinstance(target, Pack):
            for sub in target.patterns:
                ctx.pattern_bodies[sub.id] = sub
        ctx.pattern_bodies[target.id] = target if isinstance(target, Pattern) else self._pack_as_synthetic_pattern(target)

        # 3. Open root Invocation.
        root_agent = agent_id or os.environ.get("OMW_AGENT_ID", "omw-runtime")
        root_inv_id = f"inv_{uuid.uuid4().hex[:12]}"
        root_event_base = {
            "ts": int(time.time()),
            "agent_id": root_agent,
            "pattern_id": target.id,
            "invocation_id": root_inv_id,
            "phase": "loaded",
            "context": {"intent": ctx.intent, "kind": target_kind},
            "step_kind": "root",
        }
        self.omw.backend.log_invocation_event(root_event_base)
        ctx.events.append(root_event_base)
        ctx.state["root_invocation_id"] = root_inv_id

        # 4. Execute workflow steps in order, threading parent_invocation_id.
        start = time.time()
        success = True
        try:
            self._execute_steps(workflow, ctx, parent_invocation_id=root_inv_id,
                                root_pattern_id=target.id, agent_id=root_agent)
        except RuntimeError_ as exc:
            success = False
            # let the completion event capture the error string
            ctx.state["root_error"] = str(exc)
        finally:
            done_event = {
                "ts": int(time.time()),
                "agent_id": root_agent,
                "pattern_id": target.id,
                "invocation_id": root_inv_id,
                "phase": "completed",
                "success": success,
                "duration_s": int(time.time() - start),
                "metrics": {
                    "step_count": sum(1 for e in ctx.events if e.get("step_id")),
                    "guard_violations": sum(
                        len([g for g in (e.get("guards_triggered") or [])
                             if g.get("result") == "violation"])
                        for e in ctx.events),
                    "gap_signals": sum(1 for e in ctx.events if e.get("gap_signal")),
                },
                "step_kind": "root",
            }
            if ctx.state.get("root_error"):
                done_event["error"] = ctx.state["root_error"]
            self.omw.backend.log_invocation_event(done_event)
            ctx.events.append(done_event)

        return {
            "ok": success,
            "root_invocation_id": root_inv_id,
            "target_id": target.id,
            "produces": dict(ctx.produces),
            "events": ctx.events,
        }

    # ── helpers ──

    def _load_target(self, target_id: str) -> tuple[Any, str]:
        # Try Pack first (since Pack ids typically prefix `pack-`), then Pattern.
        if target_id.startswith("pack-"):
            return self.omw.load_pack(target_id), "Pack"
        # Fallback: try Pattern.
        try:
            return self.omw.load_pattern(target_id), "Pattern"
        except FileNotFoundError:
            return self.omw.load_pack(target_id), "Pack"

    @staticmethod
    def _pack_as_synthetic_pattern(pack: Pack) -> Pattern:
        """Adapt a Pack as a Pattern so its body sections are queryable
        identically (judgment / rules / anti-pattern guards can target the Pack)."""
        return Pattern(
            id=pack.id,
            description=pack.description,
            schema_version=pack.schema_version,
            trigger=pack.trigger,
            anti_trigger=pack.anti_trigger,
            domain=pack.domain,
            applicable_project_types=pack.applicable_project_types,
            status=pack.status,
            version=pack.version,
            provenance=pack.provenance,
            body=pack.body,
            body_sections=pack.body_sections,
            workflow=pack.workflow,
            visibility=pack.visibility,
        )

    def _execute_steps(
        self,
        steps: list[dict[str, Any]],
        ctx: StepContext,
        parent_invocation_id: str,
        root_pattern_id: str,
        agent_id: str,
    ) -> None:
        # Sequential execution honoring `requires` (simple: assume input order
        # already topologically sorted; `requires` is checked but does not
        # reorder — fail-fast if missing).
        produced: set[str] = set()
        for step in steps:
            step_id = step.get("step_id") or f"anon_{uuid.uuid4().hex[:6]}"
            requires = step.get("requires", []) or []
            for r in requires:
                if r not in produced:
                    raise RuntimeError_(
                        f"Step '{step_id}' requires '{r}' which was not produced yet.")
            kind = step.get("kind")
            if kind not in self._executors:
                raise RuntimeError_(
                    f"Step '{step_id}': unknown kind '{kind}'. "
                    f"Known: {sorted(self._executors)}.")

            executor = self._executors[kind]
            # Sub-invocation event keyed to the step's *primary* pattern.
            # For tool_call/loop_until — no pattern; use the root pattern id.
            primary_pattern = self._step_pattern_id(step, root_pattern_id)
            sub_inv_id = f"inv_{uuid.uuid4().hex[:12]}"
            t0 = time.time()
            self.omw.backend.log_invocation_event({
                "ts": int(t0),
                "agent_id": agent_id,
                "pattern_id": primary_pattern,
                "invocation_id": sub_inv_id,
                "parent_invocation_id": parent_invocation_id,
                "step_id": step_id,
                "step_kind": kind,
                "phase": "loaded",
                "context": {"step_definition": step},
            })

            on_fail = step.get("on_fail", "break")
            result_ok = True
            guards_triggered: list[dict[str, Any]] = []
            judgment_score: float | None = None
            gap_signal: dict[str, Any] | None = None
            step_error: str | None = None
            step_metrics: dict[str, Any] = {}

            try:
                # Pre-guards.
                pre_g = self._run_guards(step.get("guards", []) or [], "pre",
                                         ctx, parent_invocation_id=sub_inv_id,
                                         root_pattern_id=root_pattern_id,
                                         agent_id=agent_id)
                guards_triggered.extend(pre_g)
                if any(g.get("result") == "violation" and g.get("severity") == "hard"
                       for g in pre_g):
                    raise RuntimeError_(f"Step '{step_id}' blocked by pre-guard hard-forbidden violation")

                # Dispatch.
                exec_result = executor.execute(step, ctx)
                # exec_result may carry: {produces?, metrics?, judgment_score?, gap_signal?, guards_triggered?}
                if exec_result:
                    if "produces" in exec_result and step.get("produces"):
                        ctx.produces[step["produces"]] = exec_result["produces"]
                        produced.add(step["produces"])
                    if "metrics" in exec_result:
                        step_metrics.update(exec_result["metrics"])
                    if exec_result.get("judgment_score") is not None:
                        judgment_score = float(exec_result["judgment_score"])
                    if exec_result.get("gap_signal"):
                        gap_signal = exec_result["gap_signal"]
                    if exec_result.get("guards_triggered"):
                        guards_triggered.extend(exec_result["guards_triggered"])
                elif step.get("produces"):
                    # mark produced even with no explicit value (some steps just side-effect)
                    produced.add(step["produces"])

                # Post-guards.
                post_g = self._run_guards(step.get("guards", []) or [], "post",
                                          ctx, parent_invocation_id=sub_inv_id,
                                          root_pattern_id=root_pattern_id,
                                          agent_id=agent_id)
                guards_triggered.extend(post_g)
                if any(g.get("result") == "violation" and g.get("severity") == "hard"
                       for g in post_g):
                    raise RuntimeError_(f"Step '{step_id}' failed post-guard hard-forbidden violation")

            except RuntimeError_ as exc:
                result_ok = False
                step_error = str(exc)
            except Exception as exc:  # noqa: BLE001
                result_ok = False
                step_error = f"{type(exc).__name__}: {exc}"

            # Emit completed event for this step.
            done_ev: dict[str, Any] = {
                "ts": int(time.time()),
                "agent_id": agent_id,
                "pattern_id": primary_pattern,
                "invocation_id": sub_inv_id,
                "parent_invocation_id": parent_invocation_id,
                "step_id": step_id,
                "step_kind": kind,
                "phase": "completed" if result_ok else "errored",
                "success": result_ok,
                "duration_s": int(time.time() - t0),
            }
            if step_metrics:
                done_ev["metrics"] = step_metrics
            if guards_triggered:
                done_ev["guards_triggered"] = guards_triggered
            if judgment_score is not None:
                done_ev["judgment_score"] = judgment_score
            if gap_signal:
                done_ev["gap_signal"] = gap_signal
            if step_error:
                done_ev["error"] = step_error
            self.omw.backend.log_invocation_event(done_ev)
            ctx.events.append(done_ev)

            if not result_ok:
                if on_fail == "continue":
                    continue
                elif on_fail == "escalate":
                    raise RuntimeError_(f"Step '{step_id}' escalated: {step_error}")
                else:  # break
                    raise RuntimeError_(f"Step '{step_id}' broke workflow: {step_error}")

    def _step_pattern_id(self, step: dict[str, Any], fallback: str) -> str:
        # Best-effort: each step may pin its "primary" pattern (the source of
        # rules/judgment etc); else fall back to the root.
        for key in ("source_pattern", "prompt_pattern", "pattern"):
            if step.get(key):
                return step[key]
        return fallback

    def _run_guards(
        self,
        guards: list[dict[str, Any]],
        phase: str,
        ctx: StepContext,
        parent_invocation_id: str,
        root_pattern_id: str,
        agent_id: str,
    ) -> list[dict[str, Any]]:
        """Run all guards declared for a step at the given phase (pre/post).
        Delegates to GuardCheckExecutor; returns list of {pattern, check, result, ...}.
        """
        out: list[dict[str, Any]] = []
        guard_exec = self._executors.get("guard_check")
        if not guard_exec:
            return out
        for g in guards:
            check = g.get("check", "both")
            if check not in ("both", phase):
                continue
            try:
                step_def = {
                    "kind": "guard_check",
                    "source_pattern": g.get("source_pattern"),
                    "sections": g.get("sections"),
                    "subject": g.get("subject", ""),
                    "pass_criteria": g.get("pass_criteria", ""),
                }
                result = guard_exec.execute(step_def, ctx)
                if result and result.get("guards_triggered"):
                    out.extend(result["guards_triggered"])
            except Exception as exc:  # noqa: BLE001
                out.append({
                    "pattern": g.get("source_pattern"),
                    "phase": phase,
                    "result": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                })
        return out


__all__ = ["Runtime", "StepContext", "RuntimeError_"]
