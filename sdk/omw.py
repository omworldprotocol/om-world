"""OMW — main SDK entry point.

自动从 OMW_BACKEND env 选 backend (默认 local)。所有客户端代码用同一套 API,
backend 切换不改代码 (见 ARCHITECTURE.md §三)。

Usage:
    from omw import OMW
    omw = OMW()                                  # default: LocalBackend
    pattern = omw.load_pattern("playbook-cdp")
    pack = omw.load_pack("pack-defi-audit-cdp")
    with omw.invoke("playbook-cdp", context={"audit_id": "A0003"}) as inv:
        inv.record_outcome(success=True, metrics={"edges-covered-b": 9})
"""
from __future__ import annotations

import os
from typing import Any

from .backends.base import OMWBackend
from .backends.local import LocalBackend
from .invocation import Invocation
from .pack import Pack
from .pattern import Pattern

_BACKEND_REGISTRY: dict[str, type[OMWBackend]] = {
    "local": LocalBackend,
}

# Stage 2-4 lazy import (stub 时避免触发 NotImplementedError)


def _resolve_backend(name: str) -> type[OMWBackend]:
    if name in _BACKEND_REGISTRY:
        return _BACKEND_REGISTRY[name]
    # Lazy import
    if name == "git":
        from .backends.git import GitBackend
        return GitBackend
    if name == "server":
        from .backends.server import ServerBackend
        return ServerBackend
    if name == "protocol":
        from .backends.protocol import ProtocolBackend
        return ProtocolBackend
    raise ValueError(
        f"Unknown OMW backend '{name}'. "
        f"Set OMW_BACKEND to one of: local / git / server / protocol")


class OMW:
    """Top-level OMW client. Thin facade over Backend."""

    def __init__(self, backend: OMWBackend | None = None):
        if backend is not None:
            self.backend = backend
        else:
            # P1.6: default to LocalBackend regardless of OMW_BACKEND.
            #   Rationale: agents must work with zero setup (no SSH tunnel).
            #   OMW_SERVER_URL + OMW_API_TOKEN are still consumed — by
            #   tools/push_outbox.py (background ship). Agents themselves
            #   never block on network.
            #   To force a specific non-local backend (rare — for batch/cron
            #   not on Mac), set OMW_BACKEND_STRICT=1 alongside OMW_BACKEND.
            name = os.environ.get("OMW_BACKEND", "local").lower()
            strict = os.environ.get("OMW_BACKEND_STRICT", "0") == "1"
            if name != "local" and not strict:
                # Honor user intent at metadata level (so OMW_BACKEND=server
                # config still shows up in env dumps / docs) but actual
                # write path is LocalBackend with outbox shipping.
                name = "local"
            self.backend = _resolve_backend(name)()

    # === Pattern / Pack 加载 ===

    def load_pattern(self, pattern_id: str) -> Pattern:
        return self.backend.load_pattern(pattern_id)

    def load_pack(self, pack_id: str) -> Pack:
        return self.backend.load_pack(pack_id)

    # === 调用追踪 ===

    def invoke(
        self,
        pattern_id: str,
        context: dict[str, Any] | None = None,
        agent_id: str | None = None,
        parent_invocation_id: str | None = None,
        step_id: str | None = None,
        step_kind: str | None = None,
    ) -> Invocation:
        """Context manager for tracked invocation.

        Usage:
            with omw.invoke("playbook-cdp", context={"audit_id": "A0003"}) as inv:
                # agent code
                inv.record_outcome(success=True, metrics={...})

        v0.3.0: parent_invocation_id / step_id / step_kind link sub-step events
        to the root run when used via Runtime.run(); leave None for standalone use.
        """
        return Invocation(
            self.backend, pattern_id, context, agent_id,
            parent_invocation_id=parent_invocation_id,
            step_id=step_id,
            step_kind=step_kind,
        )

    # === v0.3.0: Runtime — pack-driven orchestration (CLI / cron mode) ===

    def run(
        self,
        target_id: str,
        intent: dict[str, Any] | None = None,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Run a Pack (or Pattern with workflow) end-to-end.

        Loads target_id → reads frontmatter `workflow:` → dispatches each step
        through the configured executors → emits fine-grained invocation events
        (parent_invocation_id chained). Returns InvocationReport dict.

        Usage:
            omw.run("pack-defi-audit-cdp", intent={"protocol_slug": "alto"})
        """
        # Lazy import — keeps SDK import cheap for callers that only use load_pattern/invoke
        from .runtime import Runtime
        return Runtime(self).run(target_id, intent=intent, agent_id=agent_id)

    # === P1.5: agent-led 形态 A — Session + check + judge ===

    def session(
        self,
        pack_id: str | None = None,
        pattern_id: str | None = None,
        intent: dict[str, Any] | None = None,
        agent_id: str | None = None,
    ):
        """Open a long-running agent-led session. Use as context manager.

        All `sess.check()` / `sess.judge()` / `sess.invoke()` calls inside
        the `with` block emit events linked to the session's root_invocation_id.

        Typical agent-led usage (Claude Code, GPT, etc):

            with omw.session(pack_id="pack-defi-audit-cdp",
                             intent={"protocol_slug": "alto"}) as sess:
                # ... agent thinks / runs tools ...
                v = sess.check("meta-honest-0-discipline", subject=finding_text)
                if not v.passed:
                    rework()
                # ... more work ...
                score = sess.judge("pack-defi-audit-cdp", subject=final_report)
                sess.record_outcome(success=True, metrics={"findings": 5})
        """
        from .session import Session
        return Session(self, pack_id=pack_id, pattern_id=pattern_id,
                       intent=intent, agent_id=agent_id)

    def check(self, pattern_id: str, subject: Any,
              sections: list[str] | None = None,
              pass_criteria: str = "",
              agent_id: str | None = None):
        """One-shot guard check WITHOUT a session (less ideal — prefer Session
        so multiple checks share a parent_invocation_id). Returns GuardResult.
        """
        from .session import Session
        with Session(self, pattern_id=pattern_id, agent_id=agent_id) as sess:
            return sess.check(pattern_id, subject, sections=sections,
                              pass_criteria=pass_criteria)

    def judge(self, pattern_id: str, subject: Any,
              rubric_section: str = "Judgment",
              agent_id: str | None = None):
        """One-shot LLM-as-judge. Prefer Session for multi-step audits.
        Returns JudgmentResult.
        """
        from .session import Session
        with Session(self, pattern_id=pattern_id, agent_id=agent_id) as sess:
            return sess.judge(pattern_id, subject, rubric_section=rubric_section)

    # === 搜索 / 查询 ===

    def search(
        self,
        trigger_keywords: list[str] | None = None,
        domain: str | None = None,
        project_type: str | None = None,
        visibility: str | None = None,
    ) -> list[Pattern]:
        return self.backend.search(trigger_keywords=trigger_keywords,
                                   domain=domain, project_type=project_type,
                                   visibility=visibility)

    def query_metrics(self, pattern_id: str) -> dict[str, Any]:
        return self.backend.query_metrics(pattern_id)

    def resolve_deps(self, pattern_id: str) -> dict[str, list[str]]:
        return self.backend.resolve_deps(pattern_id)
