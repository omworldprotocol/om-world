"""ServerBackend — Stage 3 implementation: REST API client.

通过 HTTP 调 OMW Server(`om-world/server/server.py`)。客户端代码不变,只改
`OMW_BACKEND=server` + `OMW_SERVER_URL` + `OMW_API_TOKEN`。

依赖:Python 标准库 `urllib.request`(避免 requests 依赖)。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from ..pack import Pack, PackInclude
from ..pattern import Pattern
from .base import OMWBackend


class ServerBackend(OMWBackend):
    """Stage 3: REST API client.

    env:
        OMW_SERVER_URL    必填, e.g. http://127.0.0.1:8765
        OMW_API_TOKEN     必填, bearer token (server's OMW_SERVER_TOKENS)
        OMW_REQUEST_TIMEOUT  optional, seconds (default 15)
    """

    def __init__(self):
        self.server_url = os.environ.get("OMW_SERVER_URL", "").rstrip("/")
        if not self.server_url:
            raise RuntimeError(
                "OMW_SERVER_URL not set. Set to e.g. http://127.0.0.1:8765")
        self.api_token = os.environ.get("OMW_API_TOKEN", "")
        if not self.api_token:
            raise RuntimeError("OMW_API_TOKEN not set")
        self.timeout = float(os.environ.get("OMW_REQUEST_TIMEOUT", "15"))

    # ─── HTTP 封装 ───────────────────────────────────────────────────

    def _request(self, method: str, path: str,
                 body: dict | None = None) -> Any:
        url = self.server_url + path
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.api_token}")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload) if payload else None
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            if e.code == 404:
                raise FileNotFoundError(f"{path}: {err_body}")
            raise RuntimeError(f"HTTP {e.code} {path}: {err_body}")

    # ─── Pattern / Pack 加载 ─────────────────────────────────────────

    @staticmethod
    def _pattern_from_dict(d: dict) -> Pattern:
        return Pattern(
            id=d.get("id", ""),
            description=d.get("description", ""),
            description_en=d.get("description-en", ""),
            schema_version=str(d.get("schema-version", "0.1")),
            trigger=d.get("trigger", ""),
            trigger_en=d.get("trigger-en", ""),
            anti_trigger=d.get("anti-trigger", ""),
            domain=d.get("domain", ""),
            applicable_project_types=d.get("applicable-project-types", []) or [],
            status=d.get("status", "active"),
            version=str(d.get("version", "0.1.0")),
            visibility=d.get("visibility", "private"),
            depends_on=d.get("depends-on", []) or [],
            extends=d.get("extends", []) or [],
            composes_with=d.get("composes-with", []) or [],
            provenance=d.get("provenance", {}) or {},
            metrics=d.get("metrics", {}) or {},
            body=d.get("body", ""),
            body_sections=d.get("body_sections", {}) or {},
            workflow=d.get("workflow", []) or [],  # v0.3.0
        )

    def load_pattern(self, pattern_id: str) -> Pattern:
        d = self._request("GET", f"/patterns/{pattern_id}")
        return self._pattern_from_dict(d)

    def load_pack(self, pack_id: str) -> Pack:
        d = self._request("GET", f"/packs/{pack_id}")
        pack = Pack(
            id=d.get("id", ""),
            description=d.get("description", ""),
            schema_version="0.2.1",
            domain=d.get("domain", ""),
            applicable_project_types=d.get("applicable-project-types", []) or [],
            status=d.get("status", "active"),
            version=str(d.get("version", "0.1.0")),
            visibility=d.get("visibility", "private"),
            includes=[PackInclude(
                pattern_id=inc.get("id", ""),
                when=inc.get("when", "always"),
                order=int(inc.get("order", 100)),
            ) for inc in d.get("includes", []) or []],
            includes_pack=d.get("includes-pack", []) or [],
            workflow=d.get("workflow", []) or [],  # v0.3.0
        )
        pack.patterns = [self._pattern_from_dict(pd)
                         for pd in d.get("patterns", []) or []]
        return pack

    # ─── 调用 log + 查询 ─────────────────────────────────────────────

    def log_invocation_event(self, event: dict[str, Any]) -> None:
        self._request("POST", "/invocations", body=event)

    def search(
        self,
        trigger_keywords: list[str] | None = None,
        domain: str | None = None,
        project_type: str | None = None,
        visibility: str | None = None,
    ) -> list[Pattern]:
        body = {
            "trigger_keywords": trigger_keywords,
            "domain": domain,
            "project_type": project_type,
            "visibility": visibility,
        }
        results = self._request("POST", "/search", body=body) or []
        # search 返回 summary list, 不含 body — 需要 load_pattern 拿完整版,
        # 但 search 通常只看 summary, 节省带宽。
        out: list[Pattern] = []
        for d in results:
            out.append(Pattern(
                id=d.get("id", ""),
                description=d.get("description", ""),
                schema_version=str(d.get("schema-version", "0.1")),
                trigger="",
                anti_trigger="",
                domain=d.get("domain", ""),
                version=str(d.get("version", "0.1.0")),
                visibility=d.get("visibility", "private"),
            ))
        return out

    def query_metrics(self, pattern_id: str) -> dict[str, Any]:
        return self._request("GET", f"/patterns/{pattern_id}/metrics") or {}

    def resolve_deps(self, pattern_id: str) -> dict[str, list[str]]:
        return self._request("GET", f"/patterns/{pattern_id}/deps") or {}


__all__ = ["ServerBackend"]
