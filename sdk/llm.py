"""LLM client abstraction — used by llm_action / guard_check / judgment executors.

Provider selection via env `OMW_LLM_BACKEND`:
  - openclaw (default) — call `openclaw infer ...` (uses configured model).
  - subprocess — call arbitrary shell command from `OMW_LLM_CMD` (cmd reads
                  stdin prompt, writes stdout response).
  - mock      — deterministic stub for unit tests / local dev without LLM access.

Each provider exposes `complete(system, user, max_tokens=...)` returning str.

Why minimal: SDK should not pin a specific vendor. OpenClaw routes to OpenAI/
DeepSeek/Anthropic based on `openclaw config`. Existing projects already use
openclaw; reuse that infra.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
from typing import Any


def _coerce_text(o: Any) -> str:
    if o is None:
        return ""
    if isinstance(o, str):
        return o
    return str(o)


class LLMClient:
    """Provider-agnostic LLM completion. Stateless; safe to instantiate per-call."""

    def __init__(self, backend: str | None = None):
        self.backend = (backend or os.environ.get("OMW_LLM_BACKEND", "openclaw")).lower()
        self._openclaw_bin = os.environ.get("OMW_OPENCLAW_BIN", "openclaw")
        self._timeout = float(os.environ.get("OMW_LLM_TIMEOUT", "60"))

    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 2048,
    ) -> str:
        """Run one prompt → completion. Returns the response text (stripped)."""
        if self.backend == "mock":
            return self._mock(system, user)
        if self.backend == "subprocess":
            return self._subprocess(system, user)
        return self._openclaw(system, user, max_tokens)

    # ── providers ──

    def _openclaw(self, system: str, user: str, max_tokens: int) -> str:
        """Invoke `openclaw infer model run --prompt ...`.

        OpenClaw CLI does not separate system/user — concatenate with a marker
        and rely on the model to recognize the "## System" / "## User" split.
        Memory rule: never pass `--gateway` flag (OpenClaw ≥ 2026.5.12 default
        local path works; --gateway breaks tool use).
        """
        prompt = f"## System\n{system}\n\n## User\n{user}"
        model = os.environ.get("OMW_OPENCLAW_MODEL", "")  # optional override
        cmd = [self._openclaw_bin, "infer", "model", "run", "--prompt", prompt]
        if model:
            cmd.extend(["--model", model])
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=self._timeout, check=False)
            if r.returncode != 0:
                raise RuntimeError(
                    f"openclaw infer model run failed (rc={r.returncode}): "
                    f"{(r.stderr or r.stdout).strip()[:400]}")
            return _coerce_text(r.stdout).strip()
        except FileNotFoundError:
            raise RuntimeError(
                f"OMW_LLM_BACKEND=openclaw but `{self._openclaw_bin}` not found in PATH. "
                f"Install openclaw or set OMW_LLM_BACKEND=subprocess + OMW_LLM_CMD.")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"openclaw infer timed out after {self._timeout}s")

    def _subprocess(self, system: str, user: str) -> str:
        cmd_str = os.environ.get("OMW_LLM_CMD", "")
        if not cmd_str:
            raise RuntimeError(
                "OMW_LLM_BACKEND=subprocess but OMW_LLM_CMD not set. "
                "Set OMW_LLM_CMD to a shell command that reads stdin "
                "(combined system\\n\\nuser) and writes completion to stdout.")
        prompt = f"{system}\n\n---\n\n{user}"
        r = subprocess.run(shlex.split(cmd_str), input=prompt,
                           capture_output=True, text=True,
                           timeout=self._timeout, check=False)
        if r.returncode != 0:
            raise RuntimeError(
                f"OMW_LLM_CMD failed (rc={r.returncode}): {r.stderr.strip()[:200]}")
        return _coerce_text(r.stdout).strip()

    def _mock(self, system: str, user: str) -> str:
        """Deterministic stub. Returns a JSON blob whose shape callers expect
        (guard verdicts / judgment scores). Useful for dev / CI without LLM."""
        # Heuristic: detect what the caller wants and return plausible JSON.
        if "verdict" in user.lower() or "guard" in system.lower():
            return json.dumps({
                "verdict": "pass",
                "violations": [],
                "warnings": [],
                "reasoning": "[mock] no real LLM; returning pass.",
            })
        if "judgment" in system.lower() or "rubric" in user.lower():
            return json.dumps({
                "score": 0.7,
                "rubric_hits": ["[mock] simulated rubric pass"],
                "improvements": ["[mock] no actual review performed"],
            })
        return f"[mock LLM response @ {time.time():.0f}]\nsystem={system[:80]!r}\nuser={user[:80]!r}"


def default_client() -> LLMClient:
    """Module-level default; constructed lazily inside executors."""
    return LLMClient()


__all__ = ["LLMClient", "default_client"]
