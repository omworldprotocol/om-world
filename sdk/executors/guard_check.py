"""guard_check executor — LLM checks a subject against Pattern rules / anti-patterns.

Subject may be:
  - inline string
  - {file: <path>} → read file contents
  - {data: <obj>}  → JSON-serialize obj

Output: list of guards_triggered entries, each
  {pattern, section, rule, result: pass|warn|violation, severity: soft|hard, detail}

Hard-forbidden violations cause Runtime to break workflow.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from ..llm import default_client
from .base import Executor

DEFAULT_SECTIONS = ["Rules", "Anti-Pattern", "Hard-Forbidden", "Soft-Avoid",
                    "Negative"]  # Negative = v0.1 legacy (treated as soft)
HARD_SECTIONS = {"Hard-Forbidden", "Anti-Pattern"}  # severity=hard


class GuardCheckExecutor(Executor):
    def execute(self, step: dict[str, Any], ctx) -> dict[str, Any] | None:
        src_id = step.get("source_pattern")
        if not src_id:
            raise RuntimeError("guard_check: missing `source_pattern`")
        pattern = ctx.pattern_bodies.get(src_id)
        if not pattern:
            try:
                pattern = self.runtime.omw.load_pattern(src_id)
                ctx.pattern_bodies[src_id] = pattern
            except FileNotFoundError as exc:
                raise RuntimeError(f"guard_check: pattern '{src_id}' not found") from exc

        sections = step.get("sections") or DEFAULT_SECTIONS
        subject_raw = step.get("subject", "")
        subject = self._resolve_subject(ctx.substitute(subject_raw))

        # Build prompt.
        rule_blocks = []
        for sec in sections:
            content = pattern.body_sections.get(sec, "").strip()
            if content:
                rule_blocks.append(f"## {sec}\n{content}")

        if not rule_blocks:
            # Nothing to check — no-op pass.
            return {"guards_triggered": [{
                "pattern": src_id,
                "result": "pass",
                "detail": "no rule sections present in pattern",
            }]}

        pass_criteria = step.get("pass_criteria", "All rules satisfied; no anti-pattern or hard-forbidden violations.")
        # v0.3.3 (P2 fix 2026-05-27): tell LLM to use EXACT section names from
        # the Pattern body — otherwise it paraphrases (e.g. "persona drift" instead
        # of "Hard-Forbidden") and severity defaults to soft, breaking the hard-
        # block contract. Sections list passed verbatim into the system prompt.
        allowed_sections_list = ", ".join(f'"{s}"' for s in sections)
        system = (
            "You are an OMW guard. You enforce Pattern rules against a subject. "
            "Output STRICT JSON only, no prose. Schema: "
            '{"verdict": "pass"|"warn"|"violation", '
            '"violations": [{"section": "...", "rule": "...", "evidence": "..."}], '
            '"warnings":   [{"section": "...", "rule": "...", "evidence": "..."}]}'
            f". IMPORTANT: the `section` field MUST be one of these EXACT strings: "
            f"[{allowed_sections_list}]. Do not paraphrase or invent new section names — "
            f"the section name determines violation severity (Hard-Forbidden / Anti-Pattern "
            f"= hard-block; others = soft warn). Pick the section that contains the rule "
            f"you are citing."
        )
        user = (
            f"Pattern: {src_id}\n\nRules:\n\n" + "\n\n".join(rule_blocks) +
            f"\n\nPass criteria: {pass_criteria}\n\n"
            f"Subject:\n{subject}\n\n"
            "Return JSON only."
        )

        client = default_client()
        raw = client.complete(system, user, max_tokens=1024)
        verdict = self._parse_verdict(raw)

        # v0.3.3: severity decision — prefer LLM-reported section if it matches
        # an allowed section name, else fall back to the "primary intent" of this
        # check call:if any of `sections` contains a hard-classified name,
        # treat all violations as hard (caller asked us to enforce Hard-Forbidden).
        called_with_hard = any(s in HARD_SECTIONS for s in sections)
        triggered: list[dict[str, Any]] = []
        for v in verdict.get("violations", []) or []:
            llm_sec = v.get("section") or ""
            if llm_sec in HARD_SECTIONS:
                sev = "hard"
            elif called_with_hard and llm_sec not in sections:
                # LLM paraphrased section but we asked for Hard-Forbidden → trust caller's intent
                sev = "hard"
            elif llm_sec in sections:
                # explicit non-hard section name → soft
                sev = "soft"
            else:
                sev = "soft"
            triggered.append({
                "pattern": src_id,
                "section": llm_sec or "(unknown)",
                "rule": v.get("rule"),
                "result": "violation",
                "severity": sev,
                "evidence": (v.get("evidence") or "")[:300],
            })
        for w in verdict.get("warnings", []) or []:
            triggered.append({
                "pattern": src_id,
                "section": w.get("section"),
                "rule": w.get("rule"),
                "result": "warn",
                "severity": "soft",
                "evidence": (w.get("evidence") or "")[:300],
            })
        if not triggered:
            triggered.append({"pattern": src_id, "result": "pass",
                              "detail": "no violations or warnings"})
        return {"guards_triggered": triggered,
                "metrics": {"violations": sum(1 for t in triggered if t["result"] == "violation"),
                            "warnings": sum(1 for t in triggered if t["result"] == "warn")}}

    @staticmethod
    def _resolve_subject(subject: Any) -> str:
        if isinstance(subject, str):
            # Heuristic: if it looks like a path that exists, read it.
            if len(subject) < 1024 and os.path.isfile(subject):
                try:
                    return open(subject, encoding="utf-8", errors="replace").read()[:20_000]
                except OSError:
                    pass
            return subject
        if isinstance(subject, dict):
            if "file" in subject:
                path = subject["file"]
                if os.path.isfile(path):
                    return open(path, encoding="utf-8", errors="replace").read()[:20_000]
                return f"[file not found: {path}]"
            if "data" in subject:
                return json.dumps(subject["data"], ensure_ascii=False, indent=2)[:20_000]
        return str(subject)

    @staticmethod
    def _parse_verdict(raw: str) -> dict[str, Any]:
        raw = raw.strip()
        # Try direct parse.
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # Try to extract a JSON object from prose.
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        # Fall back to pass with raw as evidence (so we don't false-positive block).
        return {"verdict": "pass", "violations": [], "warnings": [
            {"section": "_parse_error", "rule": "LLM returned non-JSON",
             "evidence": raw[:300]}
        ]}
