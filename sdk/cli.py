"""omw CLI — `omw run` plus a few inspection commands.

Usage:
    python -m sdk run pack-defi-audit-cdp --intent '{"protocol_slug": "alto"}'
    python -m sdk run pack-defi-audit-cdp --intent-file intent.json
    python -m sdk show pack-defi-audit-cdp
    python -m sdk list --domain defi-audit

Once installed as `omw` script (via setup.py / pyproject), the `python -m sdk`
prefix becomes just `omw`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .omw import OMW


def cmd_run(args: argparse.Namespace) -> int:
    intent: dict = {}
    if args.intent:
        intent = json.loads(args.intent)
    elif args.intent_file:
        intent = json.loads(Path(args.intent_file).read_text(encoding="utf-8"))

    omw = OMW()
    report = omw.run(args.target_id, intent=intent, agent_id=args.agent_id)
    out = {
        "ok": report["ok"],
        "root_invocation_id": report["root_invocation_id"],
        "target_id": report["target_id"],
        "step_count": sum(1 for e in report["events"] if e.get("step_id")),
        "produces_keys": list(report["produces"].keys()),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.verbose:
        print("\n--- events ---", file=sys.stderr)
        for ev in report["events"]:
            print(json.dumps(ev, ensure_ascii=False), file=sys.stderr)
    return 0 if report["ok"] else 1


def cmd_show(args: argparse.Namespace) -> int:
    omw = OMW()
    try:
        if args.target_id.startswith("pack-"):
            obj = omw.load_pack(args.target_id)
            out = {
                "kind": "Pack",
                "id": obj.id,
                "description": obj.description,
                "version": obj.version,
                "visibility": obj.visibility,
                "includes_count": len(obj.includes),
                "patterns_count": len(obj.patterns),
                "has_workflow": bool(obj.workflow),
                "workflow_steps": len(obj.workflow),
            }
        else:
            obj = omw.load_pattern(args.target_id)
            out = {
                "kind": "Pattern",
                "id": obj.id,
                "description": obj.description,
                "version": obj.version,
                "visibility": obj.visibility,
                "body_sections": list(obj.body_sections.keys()),
                "has_workflow": bool(obj.workflow),
            }
    except FileNotFoundError as exc:
        print(f"not found: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    omw = OMW()
    results = omw.search(domain=args.domain, project_type=args.project_type,
                          visibility=args.visibility)
    for p in results:
        print(f"{p.id:<50} v{p.version:<8} domain={p.domain or '-':<15} "
              f"visibility={p.visibility}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Diagnose OMW agent setup. Used by agents at task start to confirm
    they can record events + ship to server. Always returns useful info,
    never fails the agent's work (returns 0 unless --strict)."""
    import os, urllib.request, urllib.error
    from sdk import __version__
    omw = OMW()

    issues: list[str] = []
    info: list[str] = []

    info.append(f"OMW SDK version: {__version__}")
    info.append(f"backend in use:  {type(omw.backend).__name__}")

    # 1. Pattern path
    paths = os.environ.get("OMW_PATTERN_PATH", "").split(":")
    paths = [p for p in paths if p]
    if not paths:
        # backend infers default
        paths = [str(p) for p in getattr(omw.backend, "patterns_dirs", [])]
    info.append(f"pattern dirs ({len(paths)}):")
    for p in paths:
        exists = os.path.isdir(p)
        info.append(f"  {'OK' if exists else 'MISSING':7} {p}")
        if not exists:
            issues.append(f"pattern dir missing: {p}")

    # 2. Outbox + push_outbox.py
    outbox = getattr(omw.backend, "outbox", None)
    if outbox:
        info.append(f"outbox:        {outbox}")
        if outbox.is_file():
            lines = sum(1 for _ in outbox.open(encoding="utf-8"))
            info.append(f"outbox queue:  {lines} pending events")
            if lines > 1000:
                issues.append(f"outbox backed up ({lines} events) — run push_outbox.py")
        else:
            info.append("outbox queue:  0 (file not yet created)")

    # 3. Server reachability + auth (best-effort — failure is informational, not blocking)
    url = os.environ.get("OMW_SERVER_URL", "").rstrip("/")
    token = os.environ.get("OMW_API_TOKEN", "")
    if url:
        info.append(f"server URL:    {url}")
        info.append(f"server token:  {'set (' + str(len(token)) + ' chars)' if token else 'NOT SET'}")
        if not token:
            issues.append("OMW_SERVER_URL set but OMW_API_TOKEN missing — outbox won't push")
        else:
            # Probe /health
            try:
                with urllib.request.urlopen(f"{url}/health", timeout=2) as r:
                    info.append(f"server health: HTTP {r.status} ✓")
            except urllib.error.URLError as e:
                info.append(f"server health: UNREACHABLE ({e}) — outbox will buffer, push_outbox.py will retry")
            except Exception as e:
                info.append(f"server health: ERROR ({e})")
    else:
        info.append("server URL:    (unset — local-only mode; flywheel data stays on Mac)")

    # 4. Try loading a known pack to confirm SDK works.
    try:
        pat = omw.search()
        info.append(f"loadable patterns: {len(pat)} discovered")
    except Exception as e:
        issues.append(f"SDK search failed: {e}")

    # output
    print("\n".join(info))
    if issues:
        print("\n──── ISSUES ────")
        for i in issues:
            print(f"  ⚠ {i}")
        return 1 if args.strict else 0
    print("\n✓ OMW agent setup looks healthy")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="omw")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Run a Pack or Pattern with workflow")
    run_p.add_argument("target_id")
    run_p.add_argument("--intent", help="JSON-encoded intent payload")
    run_p.add_argument("--intent-file", help="Path to JSON file with intent payload")
    run_p.add_argument("--agent-id", default=None)
    run_p.add_argument("--verbose", "-v", action="store_true",
                       help="Print all events to stderr")
    run_p.set_defaults(func=cmd_run)

    show_p = sub.add_parser("show", help="Show Pack or Pattern metadata")
    show_p.add_argument("target_id")
    show_p.set_defaults(func=cmd_show)

    list_p = sub.add_parser("list", help="List Patterns matching filters")
    list_p.add_argument("--domain")
    list_p.add_argument("--project-type")
    list_p.add_argument("--visibility")
    list_p.set_defaults(func=cmd_list)

    doc_p = sub.add_parser("doctor",
                           help="Diagnose OMW agent setup (run at task start)")
    doc_p.add_argument("--strict", action="store_true",
                       help="Exit 1 if any issues found")
    doc_p.set_defaults(func=cmd_doctor)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
