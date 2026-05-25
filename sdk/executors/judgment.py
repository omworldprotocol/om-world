"""judgment executor — LLM-as-judge using Pattern's `## Judgment` section as rubric.

Outputs a 0.0-1.0 score recorded in the event's `judgment_score` field.
Optionally writes per-criterion breakdown to metrics.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from ..llm import default_client
from .base import Executor


class JudgmentExecutor(Executor):
    def execute(self, step: dict[str, Any], ctx) -> dict[str, Any] | None:
        src_id = step.get("source_pattern")
        if not src_id:
            raise RuntimeError("judgment: missing `source_pattern`")
        pattern = ctx.pattern_bodies.get(src_id)
        if not pattern:
            try:
                pattern = self.runtime.omw.load_pattern(src_id)
                ctx.pattern_bodies[src_id] = pattern
            except FileNotFoundError as exc:
                raise RuntimeError(f"judgment: pattern '{src_id}' not found") from exc

        rubric_sec = step.get("rubric_section", "Judgment")
        rubric = pattern.body_sections.get(rubric_sec, "").strip()
        if not rubric:
            return {"judgment_score": None,
                    "metrics": {"rubric_missing": True,
                                "pattern": src_id, "section": rubric_sec}}

        subject_raw = step.get("subject", "")
        subject = self._resolve_subject(ctx.substitute(subject_raw))

        system = (
            "You are an OMW judge. Score the subject against the rubric. "
            "Output STRICT JSON only. Schema: "
            '{"score": <float 0.0-1.0>, '
            '"rubric_hits": ["matched criteria"], '
            '"improvements": ["specific actionable feedback"]}'
        )
        user = (
            f"Pattern: {src_id}\n\nRubric ({rubric_sec}):\n{rubric}\n\n"
            f"Subject:\n{subject}\n\n"
            "Return JSON only."
        )
        client = default_client()
        raw = client.complete(system, user, max_tokens=1024)
        parsed = self._parse(raw)
        score = parsed.get("score")
        try:
            score = float(score) if score is not None else None
            if score is not None:
                score = max(0.0, min(1.0, score))
        except (TypeError, ValueError):
            score = None

        return {
            "judgment_score": score,
            "metrics": {
                "rubric_hits_count": len(parsed.get("rubric_hits", []) or []),
                "improvements_count": len(parsed.get("improvements", []) or []),
                "pattern": src_id,
            },
            "produces": parsed,
        }

    @staticmethod
    def _resolve_subject(subject: Any) -> str:
        if isinstance(subject, str):
            if len(subject) < 1024 and os.path.isfile(subject):
                try:
                    return open(subject, encoding="utf-8", errors="replace").read()[:20_000]
                except OSError:
                    pass
            return subject
        if isinstance(subject, dict):
            if "file" in subject and os.path.isfile(subject["file"]):
                return open(subject["file"], encoding="utf-8", errors="replace").read()[:20_000]
            if "data" in subject:
                return json.dumps(subject["data"], ensure_ascii=False, indent=2)[:20_000]
        return str(subject)

    @staticmethod
    def _parse(raw: str) -> dict[str, Any]:
        raw = raw.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return {"score": None, "rubric_hits": [], "improvements": [
            f"_parse_error: {raw[:200]}"
        ]}
