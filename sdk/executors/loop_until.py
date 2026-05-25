"""loop_until executor — iterate body steps until predicate true or max hit.

Body steps see `state.loop_index` (0-based). `until` is a Python-eval'd
boolean expression after substitution. Safe-eval limited to literal expressions
+ a small whitelist (==, !=, <, >, <=, >=, and, or, not, in).
"""
from __future__ import annotations

import ast
import operator
from typing import Any

from .base import Executor

# Whitelist of AST nodes allowed in `until` expressions — keeps eval safe.
_ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.UnaryOp, ast.BinOp, ast.Compare,
    ast.Name, ast.Load, ast.Constant, ast.Str, ast.Num,  # legacy aliases
    ast.And, ast.Or, ast.Not, ast.Eq, ast.NotEq, ast.Lt, ast.Gt, ast.LtE,
    ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
    ast.List, ast.Tuple, ast.Set,
)


def _safe_eval(expr: str, scope: dict[str, Any]) -> bool:
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise RuntimeError(f"loop_until: disallowed expression element {type(node).__name__}")
    code = compile(tree, "<until>", "eval")
    return bool(eval(code, {"__builtins__": {}}, scope))


class LoopUntilExecutor(Executor):
    def execute(self, step: dict[str, Any], ctx) -> dict[str, Any] | None:
        until_expr = step.get("until", "False")
        max_iter = int(step.get("max_iterations", 20))
        body = step.get("body") or []
        if not body:
            raise RuntimeError("loop_until: missing `body`")

        iter_count = 0
        last_state = dict(ctx.state)
        while iter_count < max_iter:
            ctx.state["loop_index"] = iter_count
            # Substitute against current state.
            scope = {**ctx.intent, **ctx.produces, **ctx.state}
            substituted = ctx.substitute(until_expr)
            # The substitution above already replaced {state.X} occurrences;
            # if the user wrote plain identifiers (e.g. status == 'done'),
            # we provide them via scope.
            try:
                if _safe_eval(substituted, scope):
                    break
            except Exception as exc:  # noqa: BLE001
                # Substitution may have left a string literal not yet a Python expr;
                # treat eval errors as "predicate false, keep looping".
                pass

            # Execute body steps under the same parent invocation chain.
            # We need to inject a synthetic parent_invocation_id; the cleanest
            # way is to recurse into runtime._execute_steps with the loop's
            # invocation id as parent. To do so we need access to the current
            # sub_inv_id, which Runtime passes through ctx.state.
            # Strategy: piggy-back on ctx.state to know the parent.
            parent_inv = ctx.state.get("_loop_parent_inv", ctx.state.get("root_invocation_id"))
            root_pattern = ctx.state.get("root_pattern_id") or ctx.pattern_bodies and next(iter(ctx.pattern_bodies))
            agent = ctx.state.get("agent_id", "omw-runtime")

            try:
                self.runtime._execute_steps(  # noqa: SLF001
                    body, ctx,
                    parent_invocation_id=parent_inv,
                    root_pattern_id=root_pattern,
                    agent_id=agent,
                )
            except Exception as exc:  # noqa: BLE001
                # Loop body errored — record and break.
                return {
                    "metrics": {"iterations": iter_count + 1, "broke_on_error": True},
                    "produces": {"error": str(exc)},
                }

            iter_count += 1

        if iter_count >= max_iter:
            return {
                "metrics": {"iterations": iter_count, "hit_max": True},
                "gap_signal": {
                    "kind": "loop_max_iterations",
                    "detail": f"loop_until reached max_iterations={max_iter} without satisfying `until`",
                    "until": until_expr,
                },
            }
        return {"metrics": {"iterations": iter_count}}
