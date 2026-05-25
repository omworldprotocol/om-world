"""tool_call executor — dispatch shell / python_module / python_callable / http.

This is the bridge from OMW Runtime back to existing business code.
Example mappings:
  shell           → subprocess.run(...)
  python_module   → import module, run as __main__ via runpy
  python_callable → import module.callable(*args, **kwargs)
  http            → urllib request (rarely used directly; usually shell + curl)
"""
from __future__ import annotations

import importlib
import os
import runpy
import shlex
import subprocess
import sys
import time
import urllib.request
from typing import Any

from .base import Executor


class ToolCallExecutor(Executor):
    def execute(self, step: dict[str, Any], ctx) -> dict[str, Any] | None:
        tool = step.get("tool", "shell")
        if tool == "shell":
            return self._shell(step, ctx)
        if tool == "python_module":
            return self._python_module(step, ctx)
        if tool == "python_callable":
            return self._python_callable(step, ctx)
        if tool == "http":
            return self._http(step, ctx)
        raise RuntimeError(f"tool_call: unknown tool '{tool}'")

    # ── shell ──

    def _shell(self, step: dict[str, Any], ctx) -> dict[str, Any]:
        cmd = ctx.substitute(step.get("cmd", ""))
        if not cmd:
            raise RuntimeError("tool_call shell: missing `cmd`")
        cwd = ctx.substitute(step.get("cwd")) if step.get("cwd") else None
        timeout = float(step.get("timeout_s", 60))
        expect = step.get("expect_exit_code", 0)
        if isinstance(expect, int):
            expect = [expect]

        t0 = time.time()
        r = subprocess.run(
            cmd if isinstance(cmd, list) else shlex.split(cmd),
            cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False,
        )
        duration = time.time() - t0
        rc = r.returncode
        if rc not in expect:
            raise RuntimeError(
                f"shell `{cmd}` exited {rc} (expected {expect}). "
                f"stderr: {r.stderr.strip()[:400]}")
        # Truncate big outputs to keep events lean.
        out = (r.stdout or "")[-4000:]
        err = (r.stderr or "")[-1000:]
        return {
            "produces": {"exit_code": rc, "stdout": out, "stderr": err,
                         "duration_s": round(duration, 2)},
            "metrics": {"exit_code": rc, "duration_s": round(duration, 2)},
        }

    # ── python_module (run module __main__) ──

    def _python_module(self, step: dict[str, Any], ctx) -> dict[str, Any]:
        mod = ctx.substitute(step.get("module", ""))
        if not mod:
            raise RuntimeError("tool_call python_module: missing `module`")
        argv = [ctx.substitute(a) for a in (step.get("argv") or [])]
        cwd = ctx.substitute(step.get("cwd")) if step.get("cwd") else None

        # runpy.run_module replaces sys.argv temporarily.
        old_argv, old_cwd = sys.argv, os.getcwd()
        try:
            sys.argv = [mod] + argv
            if cwd:
                os.chdir(cwd)
            t0 = time.time()
            runpy.run_module(mod, run_name="__main__", alter_sys=True)
            return {"metrics": {"duration_s": round(time.time() - t0, 2)}}
        except SystemExit as exc:
            rc = exc.code if isinstance(exc.code, int) else 1
            expect = step.get("expect_exit_code", 0)
            if isinstance(expect, int):
                expect = [expect]
            if rc not in expect:
                raise RuntimeError(f"python_module `{mod}` SystemExit {rc} (expected {expect})")
            return {"metrics": {"exit_code": rc}}
        finally:
            sys.argv = old_argv
            if cwd:
                os.chdir(old_cwd)

    # ── python_callable ──

    def _python_callable(self, step: dict[str, Any], ctx) -> dict[str, Any]:
        spec = ctx.substitute(step.get("callable", ""))
        if not spec:
            raise RuntimeError("tool_call python_callable: missing `callable` (e.g. mymod.func)")
        if ":" in spec:
            mod_name, attr = spec.split(":", 1)
        else:
            mod_name, _, attr = spec.rpartition(".")
        if not (mod_name and attr):
            raise RuntimeError(f"python_callable: malformed `callable` {spec!r}")
        mod = importlib.import_module(mod_name)
        fn = getattr(mod, attr)
        args = [ctx.substitute(a) for a in (step.get("args") or [])]
        kwargs = {k: ctx.substitute(v) for k, v in (step.get("kwargs") or {}).items()}
        t0 = time.time()
        result = fn(*args, **kwargs)
        return {"produces": result,
                "metrics": {"duration_s": round(time.time() - t0, 2)}}

    # ── http ──

    def _http(self, step: dict[str, Any], ctx) -> dict[str, Any]:
        url = ctx.substitute(step.get("url", ""))
        if not url:
            raise RuntimeError("tool_call http: missing `url`")
        method = step.get("method", "GET").upper()
        body = ctx.substitute(step.get("body")) if step.get("body") else None
        headers = {k: ctx.substitute(v) for k, v in (step.get("headers") or {}).items()}
        data = body.encode("utf-8") if isinstance(body, str) else (body if body else None)
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=float(step.get("timeout_s", 30))) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
            return {
                "produces": {"status": resp.status, "body": payload[:8000]},
                "metrics": {"status": resp.status,
                            "duration_s": round(time.time() - t0, 2)},
            }
