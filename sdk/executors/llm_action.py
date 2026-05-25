"""llm_action executor — inject Pattern body as system prompt, run LLM.

The Pattern's body becomes the LLM's behavior spec; the step's `instruction`
becomes the user message. Output is recorded as `produces` for downstream steps.
"""
from __future__ import annotations

from typing import Any

from ..llm import default_client
from .base import Executor

DEFAULT_SECTIONS = ["Rules", "Heuristics", "Anti-Pattern", "Hard-Forbidden",
                    "Workflow", "Judgment"]


class LLMActionExecutor(Executor):
    def execute(self, step: dict[str, Any], ctx) -> dict[str, Any] | None:
        prompt_pattern_id = step.get("prompt_pattern")
        if not prompt_pattern_id:
            raise RuntimeError("llm_action: missing `prompt_pattern`")
        pattern = ctx.pattern_bodies.get(prompt_pattern_id)
        if not pattern:
            # Lazy-load if not in pack.
            try:
                pattern = self.runtime.omw.load_pattern(prompt_pattern_id)
                ctx.pattern_bodies[prompt_pattern_id] = pattern
            except FileNotFoundError as exc:
                raise RuntimeError(f"llm_action: pattern '{prompt_pattern_id}' not found") from exc

        sections = step.get("prompt_sections") or DEFAULT_SECTIONS
        system_parts = [
            f"You are an OMW agent following Pattern '{pattern.id}' "
            f"(v{pattern.version}).",
            f"Pattern description: {pattern.description}",
            "",
            "Pattern guidance (extracted sections):",
        ]
        for sec in sections:
            content = pattern.body_sections.get(sec, "").strip()
            if content:
                system_parts.append(f"\n## {sec}\n{content}")

        # Include patterns applied earlier this run (pattern_apply scope).
        if ctx.applied_patterns:
            system_parts.append("\n\n# Additional Patterns in scope:")
            for pid, secs in ctx.applied_patterns:
                p = ctx.pattern_bodies.get(pid)
                if not p:
                    continue
                system_parts.append(f"\n## Pattern `{pid}`")
                for sec in (secs or DEFAULT_SECTIONS):
                    c = p.body_sections.get(sec, "").strip()
                    if c:
                        system_parts.append(f"### {sec}\n{c}")

        system_prompt = "\n".join(system_parts)

        # User message: instruction + context payload.
        instruction = ctx.substitute(step.get("instruction", ""))
        inject_keys = step.get("inject_context") or []
        ctx_lines = []
        for k in inject_keys:
            if k in ctx.intent:
                ctx_lines.append(f"- {k} (intent): {ctx.intent[k]}")
            elif k in ctx.produces:
                ctx_lines.append(f"- {k} (produces): {ctx.produces[k]}")
            elif k in ctx.state:
                ctx_lines.append(f"- {k} (state): {ctx.state[k]}")
        user_parts = [instruction]
        if ctx_lines:
            user_parts.append("\nContext:")
            user_parts.extend(ctx_lines)
        user_msg = "\n".join(user_parts)

        max_tokens = int(step.get("max_tokens", 2048))
        client = default_client()
        response = client.complete(system_prompt, user_msg, max_tokens=max_tokens)

        # Gap heuristic: empty / "I don't know" / "no pattern guidance" answers.
        gap_signal = None
        low = response.lower()
        if not response.strip() or any(s in low for s in
                                       ("no pattern guidance", "i don't know how",
                                        "cannot determine", "no rule covers")):
            gap_signal = {
                "kind": "llm_unguided",
                "detail": f"llm_action step '{step.get('step_id')}' produced empty/uncertain response",
                "pattern": prompt_pattern_id,
            }

        return {
            "produces": response,
            "metrics": {"response_len": len(response)},
            "gap_signal": gap_signal,
        }
