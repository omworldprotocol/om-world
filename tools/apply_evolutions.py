#!/usr/bin/env python3
"""apply_evolutions.py — P3-E 2026-05-27 Pattern auto-evolution loop.

读最新 propose_evolutions 输出的 proposals.json,按 recipe catalog 自动改
Pattern / settings.yaml,validate,commit,push,redeploy,Hermes notify。

设计要点(配合 P3-E doc 看):
- 4 recipes: R-CONFIG / R-PROMOTE / R-ADD-AP / R-ROLLBACK
- 6 safety rails: whitelist / 每日每 Pattern 配额 / YAML lint / 结构 lint /
  semantic LLM check / 干跑测试(R-PROMOTE only)
- 修改写 om-world-private (本地 git commit,不 push,rsync 到 server) /
  OM-WORLD-X (commit + push GitHub + server pull + restart) /
  SOVEREIGN-X (同样)
- 每次 auto-apply commit 含 baseline metric → R-ROLLBACK 14d 后回看

Usage:
  python tools/apply_evolutions.py                  # daily auto-apply
  python tools/apply_evolutions.py --dry-run        # validate, no writes
  python tools/apply_evolutions.py --proposals <f>  # specific proposals.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

OMW_ROOT = Path(os.environ.get("OMW_ROOT",
    str(Path(__file__).resolve().parent.parent)))
PRIVATE_ROOT = OMW_ROOT.parent / "om-world-private"
SOVX_ROOT = OMW_ROOT.parent / "SOVEREIGN-X"
OMX_ROOT = OMW_ROOT.parent / "OM-WORLD-X"

SERVER_HOST = os.environ.get("OMW_SERVER_HOST", "root@87.99.153.204")
SSH_KEY = os.environ.get("OMW_SERVER_SSH_KEY",
                         str(Path.home() / ".ssh" / "hetzner_ash_key"))

LOG_DB = OMW_ROOT / "runtime" / "auto_apply_log.sqlite3"
LOG_DB.parent.mkdir(parents=True, exist_ok=True)

# ─── safety rail 1: whitelist ────────────────────────────────────────────────
PATTERN_WHITELIST = {
    "playbook-sovereign-x-bookmark-able",
    "playbook-sovereign-x-kol-magnet",
    "playbook-sovereign-x-conversation-trigger",
    "playbook-om-world-x-article-format",
}
CONFIG_WHITELIST_FILES = {
    "OM-WORLD-X/config/settings.yaml",
    "SOVEREIGN-X/config/settings.yaml",
}

# ─── safety rail 2: 每天每 target 配额 ─────────────────────────────────────────
MAX_AUTO_CHANGES_PER_TARGET_PER_DAY = 1


# ─── log schema ──────────────────────────────────────────────────────────────
def _ensure_log_db() -> None:
    conn = sqlite3.connect(LOG_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS auto_apply_log (
            apply_id          TEXT PRIMARY KEY,
            applied_at        TEXT NOT NULL,
            proposal_id       TEXT NOT NULL,
            recipe_id         TEXT NOT NULL,
            target_repo       TEXT NOT NULL,
            target_file       TEXT NOT NULL,
            commit_sha        TEXT,
            baseline_metric   TEXT,
            outcome           TEXT,
            reverted          INTEGER DEFAULT 0,
            revert_commit_sha TEXT,
            note              TEXT
        )
    """)
    conn.commit()
    conn.close()


def _log_apply(row: dict) -> None:
    conn = sqlite3.connect(LOG_DB)
    conn.execute(
        "INSERT INTO auto_apply_log (apply_id, applied_at, proposal_id, recipe_id, "
        "target_repo, target_file, commit_sha, baseline_metric, outcome, note) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (row["apply_id"], row["applied_at"], row["proposal_id"], row["recipe_id"],
         row["target_repo"], row["target_file"], row.get("commit_sha"),
         json.dumps(row.get("baseline_metric") or {}),
         row.get("outcome", "applied"), row.get("note", "")),
    )
    conn.commit()
    conn.close()


def _count_today_changes(target_file: str) -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = sqlite3.connect(LOG_DB)
    n = conn.execute(
        "SELECT COUNT(*) FROM auto_apply_log "
        "WHERE target_file=? AND applied_at LIKE ? AND outcome='applied'",
        (target_file, f"{today}%"),
    ).fetchone()[0]
    conn.close()
    return int(n)


# ─── git helpers ─────────────────────────────────────────────────────────────
def _run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> str:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if check and r.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(cmd)}\nstderr: {r.stderr}")
    return r.stdout


def _git_commit(repo_root: Path, target_relpath: str, message: str,
                force_add: bool = False) -> str:
    args = ["git", "add"]
    if force_add:
        args.append("--force")
    args.append(target_relpath)
    _run(args, cwd=repo_root)
    # commit
    r = subprocess.run(["git", "commit", "-m", message],
                       cwd=repo_root, capture_output=True, text=True)
    if r.returncode != 0:
        if "nothing to commit" in (r.stdout + r.stderr):
            return ""  # no-op
        raise RuntimeError(f"git commit failed: {r.stderr}")
    sha = _run(["git", "rev-parse", "HEAD"], cwd=repo_root).strip()
    return sha


def _git_push(repo_root: Path, remote_url: str, branch: str = "main") -> None:
    # HTTPS fallback (Mac → GitHub SSH 不通 见 memory)
    _run(["git", "push", remote_url, branch], cwd=repo_root)


def _rsync_to_server(local_path: Path, remote_path: str) -> None:
    _run(["rsync", "-avz", "-e", f"ssh -i {SSH_KEY}", str(local_path),
          f"{SERVER_HOST}:{remote_path}"])


def _ssh(cmd: str) -> str:
    return _run(["ssh", "-i", SSH_KEY, SERVER_HOST, cmd])


# ─── proposals reader ────────────────────────────────────────────────────────
def _load_proposals(path: Path | None = None) -> dict:
    if path is None:
        candidates = sorted((OMW_ROOT / "runtime" / "pattern_evolution").glob("*.proposals.json"))
        if not candidates:
            return {"proposals": []}
        path = candidates[-1]
    return json.loads(path.read_text())


# ─── Pattern file structural lint ────────────────────────────────────────────
_REQUIRED_SECTIONS = ["## Rules", "## Hard-Forbidden", "## Anti-Pattern"]


def _validate_pattern_file(file_path: Path) -> tuple[bool, str]:
    """Returns (ok, error_msg)."""
    if not file_path.exists():
        return False, "file does not exist"
    text = file_path.read_text(encoding="utf-8")
    # YAML frontmatter parses
    if not text.startswith("---"):
        return False, "missing frontmatter"
    try:
        import yaml
        # split on lone "---" lines (not anywhere "---" appears in description)
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return False, "missing leading ---"
        end = None
        for i, ln in enumerate(lines[1:], 1):
            if ln.strip() == "---":
                end = i
                break
        if end is None:
            return False, "missing closing ---"
        meta = yaml.safe_load("\n".join(lines[1:end]))
        if not isinstance(meta, dict) or "name" not in meta:
            return False, "frontmatter missing name"
    except Exception as e:
        return False, f"frontmatter parse: {e}"
    # required sections
    for sec in _REQUIRED_SECTIONS:
        if sec not in text:
            return False, f"missing section {sec}"
    return True, ""


# ─── recipes ─────────────────────────────────────────────────────────────────
def apply_r_config(proposal: dict, recipe: dict, dry_run: bool) -> dict:
    """R-CONFIG: 编辑 OM-WORLD-X/SOVEREIGN-X config/settings.yaml。
    目前只实现 boost_article_cadence (其他 config_action 拒)。"""
    action = recipe.get("config_action")
    if action != "boost_article_cadence":
        return {"outcome": "skipped", "reason": f"unsupported config_action: {action}"}
    target_rel = recipe["target_file"]  # config/settings.yaml
    repo_root = {"OM-WORLD-X": OMX_ROOT, "SOVEREIGN-X": SOVX_ROOT}.get(recipe["repo"])
    if not repo_root or not repo_root.exists():
        return {"outcome": "error", "reason": f"repo not found: {recipe['repo']}"}
    file_path = repo_root / target_rel
    text = file_path.read_text(encoding="utf-8")

    # idempotent: 寻找 article cron section,加一档第二班次。当前是 weekday 9am EST。
    # 加第二班次 weekday 15:30 EST (jitter 同)。已存在跳过。
    # 这块改动是结构化 YAML edit,不让 LLM 自由改 yaml(风险高)。
    if "auto_apply_article_cadence_v1" in text:
        return {"outcome": "skipped", "reason": "marker auto_apply_article_cadence_v1 already present"}

    # 找 article cron 段(OM-WORLD-X 把 machine_proof_cron 复用为 article cron, 按 AGENTS.md)
    article_key = None
    for k in ("article_cron:", "machine_proof_cron:"):
        if k in text:
            article_key = k
            break
    if article_key is None:
        return {"outcome": "skipped", "reason": "neither article_cron nor machine_proof_cron present"}

    # 在 article_cron 末尾(下一个 top-level key 前)加 second slot
    # 用 marker comment 标记,便于 R-ROLLBACK 识别
    insertion = (
        "\n  # auto_apply_article_cadence_v1 (P3-E 2026-05-27 R-CONFIG)\n"
        "  # signal: article reach " + str(recipe.get("ratio", "?")) + "× single,\n"
        "  # added second weekday slot to invest more in article cadence.\n"
        "  article_cron_secondary:\n"
        "    cron: '30 15 * * 1-5'  # weekday 15:30 EST\n"
        "    jitter_minutes: 20\n"
    )
    # 安全插入 — 找 article_cron: 这一行,在该 block 结束(空行 OR 下一个非缩进 key)前插
    lines = text.splitlines(keepends=True)
    new_lines = []
    in_article_block = False
    inserted = False
    for line in lines:
        if not inserted and in_article_block and (line.startswith(" ") is False and line.strip()):
            # 出 block 之前插
            new_lines.append(insertion)
            inserted = True
            in_article_block = False
        if line.lstrip().startswith(article_key):
            in_article_block = True
        new_lines.append(line)
    if in_article_block and not inserted:
        new_lines.append(insertion)
        inserted = True
    if not inserted:
        return {"outcome": "error", "reason": "could not locate article_cron block end"}

    new_text = "".join(new_lines)
    # YAML parse validation
    try:
        import yaml as _yaml
        _yaml.safe_load(new_text)
    except Exception as e:
        return {"outcome": "error", "reason": f"YAML parse after edit: {e}"}

    if dry_run:
        return {"outcome": "dry_run_ok", "diff_lines": len(insertion.splitlines())}

    file_path.write_text(new_text, encoding="utf-8")
    return {
        "outcome": "written",
        "repo_root": str(repo_root),
        "target_rel": target_rel,
        "commit_message": f"[auto-apply] R-CONFIG {proposal['id']}: boost article cadence "
                          f"(signal: article reach {recipe.get('ratio')}× single)",
        "needs_remote_push": True,
        "needs_server_redeploy": True,
    }


def apply_r_add_ap(proposal: dict, recipe: dict, dry_run: bool) -> dict:
    """R-ADD-AP: 把 anti_pattern_text append 到目标 Pattern 的 ## Anti-Pattern 段。"""
    target_rel = recipe["target_file"]
    pattern_id = Path(target_rel).parent.name
    if pattern_id not in PATTERN_WHITELIST:
        return {"outcome": "skipped", "reason": f"pattern {pattern_id} not in whitelist"}
    file_path = PRIVATE_ROOT / target_rel
    if not file_path.exists():
        # 也试 public om-world
        file_path = OMW_ROOT / target_rel
        if not file_path.exists():
            return {"outcome": "error", "reason": f"pattern file not found"}

    text = file_path.read_text(encoding="utf-8")
    new_line = f"- ❌ {recipe['anti_pattern_text']} _(auto-apply P3-E {proposal['id']} {datetime.now(timezone.utc).strftime('%Y-%m-%d')})_"
    # idempotent — 若同 anti_pattern_text 已存在则跳过
    if recipe["anti_pattern_text"][:60] in text:
        return {"outcome": "skipped", "reason": "anti_pattern_text already present"}

    if "## Anti-Pattern" not in text:
        return {"outcome": "error", "reason": "## Anti-Pattern section missing"}

    # 找 ## Anti-Pattern,在该 section 末尾(下一个 ## 前)插
    lines = text.splitlines(keepends=True)
    new_lines: list[str] = []
    in_ap = False
    inserted = False
    for i, line in enumerate(lines):
        if line.startswith("## Anti-Pattern"):
            in_ap = True
            new_lines.append(line)
            continue
        if in_ap and line.startswith("## ") and not inserted:
            # 出 section 前插
            new_lines.append(new_line + "\n\n")
            inserted = True
            in_ap = False
        new_lines.append(line)
    if in_ap and not inserted:
        new_lines.append("\n" + new_line + "\n")
        inserted = True
    new_text = "".join(new_lines)

    ok, err = _validate_pattern_file_text(new_text)
    if not ok:
        return {"outcome": "error", "reason": f"validation: {err}"}

    if dry_run:
        return {"outcome": "dry_run_ok", "new_line": new_line[:120]}

    file_path.write_text(new_text, encoding="utf-8")
    repo_root = PRIVATE_ROOT if str(file_path).startswith(str(PRIVATE_ROOT)) else OMW_ROOT
    return {
        "outcome": "written",
        "repo_root": str(repo_root),
        "target_rel": target_rel,
        "commit_message": (
            f"[auto-apply] R-ADD-AP {proposal['id']}: append anti-pattern to {pattern_id}\n\n"
            f"signal: {recipe['anti_pattern_text'][:200]}"
        ),
        "needs_remote_push": (repo_root != PRIVATE_ROOT),  # private repo 不 push
        "needs_private_rsync": (repo_root == PRIVATE_ROOT),
        "needs_server_redeploy": False,
    }


def _validate_pattern_file_text(text: str) -> tuple[bool, str]:
    if not text.startswith("---"):
        return False, "missing frontmatter"
    try:
        import yaml
        # split on lone "---" lines (not anywhere "---" appears in description)
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return False, "missing leading ---"
        end = None
        for i, ln in enumerate(lines[1:], 1):
            if ln.strip() == "---":
                end = i
                break
        if end is None:
            return False, "missing closing ---"
        meta = yaml.safe_load("\n".join(lines[1:end]))
        if not isinstance(meta, dict) or "name" not in meta:
            return False, "frontmatter missing name"
    except Exception as e:
        return False, f"frontmatter parse: {e}"
    for sec in _REQUIRED_SECTIONS:
        if sec not in text:
            return False, f"missing section {sec}"
    return True, ""


# R-PROMOTE — LLM 生成 + 多层 validation,见下文 r_promote.py
import importlib.util as _ilu, sys as _sys, pathlib as _pl
_spec = _ilu.spec_from_file_location("_apply_r_promote",
    _pl.Path(__file__).parent / "_apply_r_promote.py")
_mod = _ilu.module_from_spec(_spec)
_sys.modules["_apply_r_promote"] = _mod
_sys.modules["tools.apply_evolutions"] = _sys.modules[__name__]  # 让 r_promote import 回拿 WHITELIST
_spec.loader.exec_module(_mod)
apply_r_promote = _mod.apply_r_promote


# ─── Hermes notify ───────────────────────────────────────────────────────────
def _hermes_notify(title: str, body: str) -> None:
    try:
        url = os.environ.get("HERMES_INGEST_URL", "http://87.99.153.204:18790/ingest")
        token = os.environ.get("HERMES_TOKEN", "")
        import urllib.request
        payload = json.dumps({
            "kind": "auto_apply",
            "title": title,
            "body": body,
            "ts": datetime.now(timezone.utc).isoformat(),
        }).encode()
        req = urllib.request.Request(url, data=payload, method="POST",
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {token}"})
        urllib.request.urlopen(req, timeout=8)
    except Exception:
        pass  # fire-and-forget


# ─── R-ROLLBACK: 14d metric 回看 ─────────────────────────────────────────────
def check_rollbacks(dry_run: bool = False) -> list[dict]:
    """检查 14 天前的 R-PROMOTE / R-CONFIG / R-ADD-AP commit,看 baseline metric
    是否改善。若没改善或更差 → git revert + log。

    简化实现:仅看 baseline.metric_name = "bookmarks_7d" / "kol_distinct_14d" /
    "depth_ge2_14d" 这 3 种。改善定义:current > baseline。
    """
    conn = sqlite3.connect(LOG_DB)
    cutoff = (datetime.now(timezone.utc).timestamp() - 14 * 86400)
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
    rows = conn.execute(
        "SELECT apply_id, applied_at, recipe_id, target_repo, target_file, commit_sha, "
        "baseline_metric FROM auto_apply_log "
        "WHERE outcome='applied' AND reverted=0 AND applied_at < ?",
        (cutoff_iso,),
    ).fetchall()
    conn.close()

    actions: list[dict] = []
    for r in rows:
        apply_id, applied_at, recipe_id, repo, target, sha, baseline_json = r
        baseline = json.loads(baseline_json or "{}")
        metric = baseline.get("metric")
        if not metric or recipe_id != "R-PROMOTE":
            continue  # 只 R-PROMOTE 走 auto-rollback (其他保守)
        # 查 server DB 当前值
        current = _query_metric(baseline.get("project", "SOVEREIGN-X"), metric)
        baseline_val = baseline.get("value", 0)
        if current is not None and current <= baseline_val:
            # 没改善 → revert
            actions.append({
                "apply_id": apply_id, "metric": metric,
                "baseline": baseline_val, "current": current,
                "commit_sha": sha, "target_repo": repo,
                "outcome": "needs_revert" if not dry_run else "would_revert",
            })
            if not dry_run:
                _execute_revert(repo, sha, apply_id, metric, baseline_val, current)
    return actions


def _query_metric(project: str, metric: str) -> int | None:
    db_map = {
        "SOVEREIGN-X": "/root/SOVEREIGN-X/data/sovereign_x.db",
        "OM-WORLD-X":  "/root/OM-WORLD-X/data/om_world_x.db",
    }
    db = db_map.get(project)
    if not db:
        return None
    sql_map = {
        "bookmarks_7d": "SELECT SUM(COALESCE(bookmark_count,0)) FROM tweet_stats WHERE fetched_at > datetime('now','-7 days')",
        "kol_distinct_14d": "SELECT COUNT(DISTINCT kol_handle) FROM kol_engagement WHERE engaged_at > datetime('now','-14 days')",
        "depth_ge2_14d": "SELECT SUM(CASE WHEN max_reply_depth >= 2 THEN 1 ELSE 0 END) FROM tweet_stats WHERE fetched_at > datetime('now','-14 days')",
    }
    sql = sql_map.get(metric)
    if not sql:
        return None
    try:
        out = _ssh(f"sqlite3 -separator '|' {db} \"{sql}\"").strip()
        return int(out) if out else 0
    except Exception:
        return None


def _execute_revert(repo: str, sha: str, apply_id: str, metric: str,
                    baseline: int, current: int) -> None:
    repo_root = {"om-world-private": PRIVATE_ROOT,
                 "OM-WORLD-X": OMX_ROOT,
                 "SOVEREIGN-X": SOVX_ROOT}.get(repo)
    if not repo_root:
        return
    msg = (f"[auto-rollback] revert {sha[:10]} ({apply_id}): "
           f"metric {metric} {baseline}→{current} after 14d, no improvement")
    try:
        _run(["git", "revert", "--no-edit", sha], cwd=repo_root)
        revert_sha = _run(["git", "rev-parse", "HEAD"], cwd=repo_root).strip()
        conn = sqlite3.connect(LOG_DB)
        conn.execute(
            "UPDATE auto_apply_log SET reverted=1, revert_commit_sha=?, "
            "note=COALESCE(note,'')||? WHERE apply_id=?",
            (revert_sha, f"\nreverted: {msg}", apply_id),
        )
        conn.commit()
        conn.close()
        _hermes_notify(f"P3-E auto-rollback: {apply_id}", msg)
    except Exception as e:
        _hermes_notify(f"P3-E auto-rollback FAILED: {apply_id}", f"{e}")


# ─── main loop ───────────────────────────────────────────────────────────────
RECIPE_HANDLERS = {
    "R-CONFIG":   apply_r_config,
    "R-ADD-AP":   apply_r_add_ap,
    "R-PROMOTE":  apply_r_promote,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--proposals", type=str, default=None)
    parser.add_argument("--skip-rollback", action="store_true")
    parser.add_argument("--only-recipe", type=str, default=None,
                        help="apply only this recipe_id (debugging)")
    args = parser.parse_args()

    _ensure_log_db()

    # 1. R-ROLLBACK 先跑
    if not args.skip_rollback:
        rb = check_rollbacks(dry_run=args.dry_run)
        if rb:
            print(f"[rollback] {len(rb)} commits flagged for revert", file=sys.stderr)
            for x in rb:
                print(f"  {x}", file=sys.stderr)

    # 2. 读 proposals
    proposals_path = Path(args.proposals) if args.proposals else None
    data = _load_proposals(proposals_path)
    proposals = data.get("proposals", [])
    if not proposals:
        print("no proposals to apply")
        return 0

    applied: list[dict] = []
    skipped: list[dict] = []
    errors: list[dict] = []
    for p in proposals:
        for recipe in p.get("recipe_candidates", []):
            rid = recipe["recipe_id"]
            if args.only_recipe and rid != args.only_recipe:
                continue
            handler = RECIPE_HANDLERS.get(rid)
            if not handler:
                skipped.append({"proposal": p["id"], "recipe": rid, "reason": "no handler"})
                continue
            # safety rail: 每日配额
            tf = recipe["target_file"]
            if _count_today_changes(tf) >= MAX_AUTO_CHANGES_PER_TARGET_PER_DAY:
                skipped.append({"proposal": p["id"], "recipe": rid,
                                "reason": f"quota: target {tf} already changed today"})
                continue
            try:
                result = handler(p, recipe, dry_run=args.dry_run)
            except Exception as e:
                errors.append({"proposal": p["id"], "recipe": rid, "error": str(e)})
                continue
            if result["outcome"] in ("skipped", "dry_run_ok"):
                skipped.append({"proposal": p["id"], "recipe": rid, **result})
                continue
            if result["outcome"] == "error":
                errors.append({"proposal": p["id"], "recipe": rid, **result})
                continue
            if result["outcome"] != "written":
                continue

            # 3. Commit + push + deploy
            commit_sha = _git_commit(
                Path(result["repo_root"]),
                result["target_rel"],
                result["commit_message"],
                force_add=(Path(result["repo_root"]) == PRIVATE_ROOT),
            )
            if result.get("needs_remote_push") and not args.dry_run:
                try:
                    _push_for_repo(Path(result["repo_root"]))
                except Exception as e:
                    errors.append({"proposal": p["id"], "recipe": rid,
                                   "error": f"push: {e}"})
            if result.get("needs_private_rsync") and not args.dry_run:
                try:
                    _rsync_to_server(
                        Path(result["repo_root"]) / Path(result["target_rel"]).parent,
                        f"/opt/om-world-private/patterns/")
                except Exception as e:
                    errors.append({"proposal": p["id"], "recipe": rid,
                                   "error": f"rsync: {e}"})
            if result.get("needs_server_redeploy") and not args.dry_run:
                try:
                    _redeploy_target(Path(result["repo_root"]))
                except Exception as e:
                    errors.append({"proposal": p["id"], "recipe": rid,
                                   "error": f"redeploy: {e}"})

            # 4. log
            apply_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{p['id']}-{rid}"
            baseline = _build_baseline(p, recipe)
            row = {
                "apply_id": apply_id,
                "applied_at": datetime.now(timezone.utc).isoformat(),
                "proposal_id": p["id"],
                "recipe_id": rid,
                "target_repo": recipe.get("repo", "unknown"),
                "target_file": tf,
                "commit_sha": commit_sha,
                "baseline_metric": baseline,
                "outcome": "applied",
                "note": result.get("commit_message", "")[:240],
            }
            _log_apply(row)
            applied.append({"proposal": p["id"], "recipe": rid,
                            "commit": commit_sha[:10] if commit_sha else "(none)",
                            "target": tf})
            _hermes_notify(
                f"[auto-apply] {rid} {p['id']}",
                f"target: {tf}\ncommit: {commit_sha[:10] if commit_sha else 'none'}\n"
                f"signal: {p.get('detail', p.get('signal', ''))[:240]}\n"
                f"revert: cd {result['repo_root']} && git revert {commit_sha[:10]}",
            )

    # 5. summary
    print(f"applied: {len(applied)}, skipped: {len(skipped)}, errors: {len(errors)}")
    for x in applied:
        print(f"  ✓ {x['recipe']} {x['proposal']} → {x['target']} @ {x['commit']}")
    for x in skipped:
        print(f"  · skip {x['recipe']} {x['proposal']}: {x.get('reason', x.get('outcome'))}")
    for x in errors:
        print(f"  ✗ ERR {x['recipe']} {x['proposal']}: {x.get('error', x.get('reason'))}")
    return 0 if not errors else 1


def _build_baseline(proposal: dict, recipe: dict) -> dict:
    """记 baseline metric 用于 R-ROLLBACK 14d 比对。"""
    out = {"proposal_id": proposal["id"], "recipe_id": recipe["recipe_id"]}
    if proposal["kind"] == "growth_gap":
        out["project"] = proposal["project"]
        out["metric"] = proposal["metric"]
        out["value"] = proposal["current_value"]
    elif proposal["kind"] == "content_type_signal":
        out["project"] = proposal["project"]
        out["signal"] = proposal["signal"]
        out["ratio"] = proposal.get("ratio")
    return out


def _push_for_repo(repo_root: Path) -> None:
    name = repo_root.name
    if name == "OM-WORLD-X":
        _git_push(repo_root, "https://github.com/flyoung588/OM-WORLD-X.git", "main")
    elif name == "SOVEREIGN-X":
        _git_push(repo_root, "https://github.com/Family-fund1688/SOVEREIGN-X.git", "main")
    elif name == "om-world":
        _git_push(repo_root, "https://github.com/omworldprotocol/om-world.git", "main")
    # om-world-private: 不 push remote


def _redeploy_target(repo_root: Path) -> None:
    name = repo_root.name
    if name == "OM-WORLD-X":
        _ssh("cd /root/OM-WORLD-X && git fetch origin main && git reset --hard origin/main "
             "&& systemctl restart om-world-x-scheduler")
    elif name == "SOVEREIGN-X":
        _ssh("cd /root/SOVEREIGN-X && git fetch origin main && git reset --hard origin/main "
             "&& systemctl restart sovereign-x-scheduler")


if __name__ == "__main__":
    sys.exit(main())
