#!/usr/bin/env python3
"""OMW Server — Stage 3 reference implementation.

单文件 FastAPI server. 复用 sdk.LocalBackend 读 Pattern 文件;invocations 写 SQLite。

启动:
    python3 -m server.server                          # default port 8765
    PORT=9000 python3 -m server.server                # 自定 port
    OMW_SERVER_TOKENS='alice:tok1,bob:tok2' python3 -m server.server  # 多 token

env:
    PORT                       默认 8765
    HOST                       默认 127.0.0.1(不外开)
    OMW_PATTERN_PATH           覆盖 Pattern 库路径(支持 overlay)
    OMW_SERVER_DB              SQLite 路径,默认 ./server/omw_server.db
    OMW_SERVER_TOKENS          逗号分隔 "user:token,user:token"(v0 简单 auth)
                               或单 token "devtoken"(无 user)
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

# Bootstrap SDK path
_OMW_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_OMW_ROOT))

# v0.2.1: server 启动时自动 detect om-world-private overlay(与客户端 shim 同款逻辑),
# 这样跑 server 就能服务 private Pattern 给授权 client。
if "OMW_PATTERN_PATH" not in os.environ:
    _private = _OMW_ROOT.parent / "om-world-private" / "patterns"
    if _private.is_dir():
        os.environ["OMW_PATTERN_PATH"] = f"{_OMW_ROOT}/patterns:{_private}"
    else:
        os.environ["OMW_PATTERN_PATH"] = f"{_OMW_ROOT}/patterns"

from sdk.backends.local import LocalBackend             # noqa: E402

try:
    from fastapi import FastAPI, HTTPException, Header, Request
    from fastapi.responses import JSONResponse
    import uvicorn
except ImportError:
    print("ERROR: pip3 install fastapi 'uvicorn[standard]'", file=sys.stderr)
    sys.exit(1)


# ─── auth (v0 simple bearer) ──────────────────────────────────────────────

def _parse_tokens(env_val: str) -> dict[str, str]:
    """Parse OMW_SERVER_TOKENS env into {token: user} mapping."""
    out: dict[str, str] = {}
    if not env_val:
        out["devtoken"] = "dev"
        return out
    for pair in env_val.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if ":" in pair:
            user, tok = pair.split(":", 1)
            out[tok.strip()] = user.strip()
        else:
            out[pair] = "anon"
    return out


_TOKENS = _parse_tokens(os.environ.get("OMW_SERVER_TOKENS", ""))


def _require_auth(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    tok = authorization[len("Bearer "):].strip()
    user = _TOKENS.get(tok)
    if not user:
        raise HTTPException(403, "invalid token")
    return user


def _check_visibility(pattern_visibility: str, user: str) -> None:
    """v0 简化:public 任意 user OK;private 仅当 user 在 author allowlist
    (后续实施)。当前所有 authenticated user 可读 private(本地开发友好)。"""
    if pattern_visibility == "public":
        return
    # TODO: implement author allowlist for private patterns
    return


# ─── SQLite invocations log ───────────────────────────────────────────────

_DB_PATH = Path(os.environ.get(
    "OMW_SERVER_DB",
    str(_OMW_ROOT / "server" / "omw_server.db"),
))


def _init_db() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS invocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            agent_id TEXT,
            pattern_id TEXT,
            invocation_id TEXT,
            phase TEXT,
            success INTEGER,
            duration_s INTEGER,
            context TEXT,
            metrics TEXT,
            notes TEXT,
            user TEXT,
            recv_at INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_pattern_id
            ON invocations(pattern_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_invocation_id
            ON invocations(invocation_id)
    """)
    # v0.3.0 migration: add step-level columns. ALTER ... ADD COLUMN is idempotent-safe via try/except.
    for col, ddl in [
        ("parent_invocation_id", "TEXT"),
        ("step_id",              "TEXT"),
        ("step_kind",            "TEXT"),
        ("guards_triggered",     "TEXT"),  # JSON
        ("judgment_score",       "REAL"),
        ("gap_signal",           "TEXT"),  # JSON
    ]:
        try:
            conn.execute(f"ALTER TABLE invocations ADD COLUMN {col} {ddl}")
        except sqlite3.OperationalError:
            pass  # column exists
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_parent_invocation
            ON invocations(parent_invocation_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_pattern_step
            ON invocations(pattern_id, step_id)
    """)
    conn.commit()
    conn.close()


def _log_invocation(event: dict, user: str) -> int:
    conn = sqlite3.connect(_DB_PATH)
    cur = conn.execute("""
        INSERT INTO invocations
        (ts, agent_id, pattern_id, invocation_id, phase, success, duration_s,
         context, metrics, notes, user, recv_at,
         parent_invocation_id, step_id, step_kind, guards_triggered,
         judgment_score, gap_signal)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        event.get("ts", int(time.time())),
        event.get("agent_id", "?"),
        event.get("pattern_id", "?"),
        event.get("invocation_id", "?"),
        event.get("phase", "?"),
        1 if event.get("success") else (0 if event.get("success") is False else None),
        event.get("duration_s"),
        json.dumps(event.get("context") or {}, ensure_ascii=False),
        json.dumps(event.get("metrics") or {}, ensure_ascii=False),
        event.get("notes", ""),
        user,
        int(time.time()),
        # v0.3.0 step-level columns
        event.get("parent_invocation_id"),
        event.get("step_id"),
        event.get("step_kind"),
        json.dumps(event.get("guards_triggered"),
                   ensure_ascii=False) if event.get("guards_triggered") else None,
        event.get("judgment_score"),
        json.dumps(event.get("gap_signal"),
                   ensure_ascii=False) if event.get("gap_signal") else None,
    ))
    rid = cur.lastrowid
    conn.commit()
    conn.close()
    return rid


def _aggregate_metrics(pattern_id: str) -> dict[str, Any]:
    """Aggregate invocation events for one Pattern → metrics dict.

    v0.3.0: rolls up step-level data (per step_id success / judgment_score /
    guards_triggered / gap_signal) alongside the legacy pack/pattern totals."""
    conn = sqlite3.connect(_DB_PATH)
    rows = conn.execute("""
        SELECT phase, success, ts, metrics, step_id, step_kind,
               guards_triggered, judgment_score, gap_signal,
               parent_invocation_id
        FROM invocations
        WHERE pattern_id = ?
    """, (pattern_id,)).fetchall()
    conn.close()
    invoked = sum(1 for r in rows if r[0] == "loaded")
    completed_rows = [r for r in rows if r[1] is not None]
    successes = sum(1 for r in completed_rows if r[1] == 1)
    success_rate = (round(successes / len(completed_rows), 3)
                    if completed_rows else None)
    last_ts = max((r[2] for r in rows), default=0)
    import datetime as dt
    last_validated = (dt.datetime.fromtimestamp(last_ts, tz=dt.timezone.utc)
                      .date().isoformat() if last_ts else None)
    # Step-level rollup (v0.3.0)
    steps: dict[str, dict[str, Any]] = {}
    guard_violations = 0
    guard_warnings = 0
    judgment_sum = 0.0
    judgment_n = 0
    gap_signal_count = 0
    for r in rows:
        sid = r[4]
        if sid and r[0] == "completed":
            entry = steps.setdefault(sid, {"completed": 0, "ok": 0,
                                          "step_kind": r[5]})
            entry["completed"] += 1
            if r[1] == 1:
                entry["ok"] += 1
        if r[6]:
            try:
                for g in json.loads(r[6]) or []:
                    if g.get("result") == "violation":
                        guard_violations += 1
                    elif g.get("result") == "warn":
                        guard_warnings += 1
            except (json.JSONDecodeError, TypeError):
                pass
        if r[7] is not None:
            judgment_sum += float(r[7])
            judgment_n += 1
        if r[8]:
            gap_signal_count += 1
    # Per-step success-rate breakdown
    step_metrics = {
        sid: {
            "step_kind": e["step_kind"],
            "completed": e["completed"],
            "success_rate": (round(e["ok"] / e["completed"], 3)
                             if e["completed"] else None),
        }
        for sid, e in steps.items()
    }
    return {
        "invoked": invoked,
        "measured-success-rate": success_rate,
        "last-validated": last_validated,
        "total-events": len(rows),
        # v0.3.0 step-level rollup
        "steps": step_metrics,
        "guard-violations": guard_violations,
        "guard-warnings": guard_warnings,
        "judgment-score-avg": (round(judgment_sum / judgment_n, 3)
                               if judgment_n else None),
        "gap-signal-count": gap_signal_count,
    }


# ─── FastAPI app ─────────────────────────────────────────────────────────

app = FastAPI(title="OMW Server (Stage 3)", version="0.3.0")
_backend = LocalBackend()                              # reuses LocalBackend for file IO


def _pattern_to_dict(p) -> dict:
    return {
        "id": p.id,
        "description": p.description,
        "description-en": p.description_en,
        "schema-version": p.schema_version,
        "trigger": p.trigger,
        "trigger-en": p.trigger_en,
        "anti-trigger": p.anti_trigger,
        "domain": p.domain,
        "applicable-project-types": p.applicable_project_types,
        "status": p.status,
        "version": p.version,
        "visibility": p.visibility,
        "depends-on": p.depends_on,
        "extends": p.extends,
        "composes-with": p.composes_with,
        "provenance": p.provenance,
        "metrics": p.metrics,
        "body": p.body,
        "body_sections": p.body_sections,
        "workflow": p.workflow,
    }


@app.get("/health")
def health():
    return {"ok": True, "version": app.version,
            "patterns_dirs": [str(d) for d in _backend.patterns_dirs]}


@app.get("/patterns/{pattern_id}")
def get_pattern(pattern_id: str, authorization: str | None = Header(None)):
    user = _require_auth(authorization)
    try:
        p = _backend.load_pattern(pattern_id)
    except FileNotFoundError:
        raise HTTPException(404, f"Pattern {pattern_id!r} not found")
    _check_visibility(p.visibility, user)
    return _pattern_to_dict(p)


@app.get("/packs/{pack_id}")
def get_pack(pack_id: str, authorization: str | None = Header(None)):
    user = _require_auth(authorization)
    try:
        pk = _backend.load_pack(pack_id)
    except FileNotFoundError:
        raise HTTPException(404, f"Pack {pack_id!r} not found")
    _check_visibility(pk.visibility, user)
    return {
        "id": pk.id,
        "description": pk.description,
        "domain": pk.domain,
        "applicable-project-types": pk.applicable_project_types,
        "status": pk.status,
        "version": pk.version,
        "visibility": pk.visibility,
        "includes": [{"id": i.pattern_id, "when": i.when, "order": i.order}
                     for i in pk.includes],
        "includes-pack": pk.includes_pack,
        "workflow": pk.workflow,
        "patterns": [_pattern_to_dict(p) for p in pk.patterns],
    }


@app.post("/search")
async def search(req: Request, authorization: str | None = Header(None)):
    _require_auth(authorization)
    body = await req.json()
    results = _backend.search(
        trigger_keywords=body.get("trigger_keywords"),
        domain=body.get("domain"),
        project_type=body.get("project_type"),
        visibility=body.get("visibility"),
    )
    return [{"id": p.id, "description": p.description,
             "domain": p.domain, "visibility": p.visibility,
             "version": p.version, "schema-version": p.schema_version}
            for p in results]


@app.post("/invocations")
async def post_invocation(req: Request, authorization: str | None = Header(None)):
    user = _require_auth(authorization)
    event = await req.json()
    rid = _log_invocation(event, user)
    return {"ok": True, "id": rid}


@app.get("/patterns/{pattern_id}/metrics")
def get_metrics(pattern_id: str, authorization: str | None = Header(None)):
    _require_auth(authorization)
    return _aggregate_metrics(pattern_id)


@app.get("/patterns/{pattern_id}/deps")
def get_deps(pattern_id: str, authorization: str | None = Header(None)):
    user = _require_auth(authorization)
    try:
        p = _backend.load_pattern(pattern_id)
    except FileNotFoundError:
        raise HTTPException(404, f"Pattern {pattern_id!r} not found")
    _check_visibility(p.visibility, user)
    return {
        "depends-on": p.depends_on,
        "extends": p.extends,
        "composes-with": p.composes_with,
    }


def main() -> int:
    _init_db()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8765"))
    print(f"OMW Server starting on http://{host}:{port}")
    print(f"  Patterns dirs:  {[str(d) for d in _backend.patterns_dirs]}")
    print(f"  SQLite db:      {_DB_PATH}")
    print(f"  Tokens loaded:  {len(_TOKENS)} ({list(_TOKENS.values())})")
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
