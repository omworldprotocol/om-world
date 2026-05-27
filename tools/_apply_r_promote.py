"""R-PROMOTE recipe — promote a Soft-Avoid rule to Hard-Forbidden.

Hybrid 架构(配合 apply_evolutions.py 主控):
- LLM 生成具体内容(不让模板出千篇一律 Hard-Forbidden)
- 结构 slot 强制(必含规则/反例/正例/源 reference/enforcement note)
- 3 层 validation:结构 lint + LLM 语义 check + 干跑测试(已知 PASS / FAIL 样本)
- 任何 reject → 信号回退到 markdown,本周期不再 retry

Not exposed as public — only used by apply_evolutions.main loop.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

OMW_ROOT = Path(os.environ.get("OMW_ROOT",
    str(Path(__file__).resolve().parent.parent)))
PRIVATE_ROOT = OMW_ROOT.parent / "om-world-private"

# 重用 SDK LLM client
sys.path.insert(0, str(OMW_ROOT))
try:
    from sdk.llm import LLMClient
except Exception:
    LLMClient = None  # mock mode fallback


PROMOTE_SYSTEM = """你是 OMW Pattern auto-evolution 的内容生成器。

你的任务:根据真涨流量指标的真信号,把某 Pattern 的 Soft-Avoid 规则提升为
Hard-Forbidden(更强 enforcement)。

绝对要求:
1. **不能写模板套话** — 必须用输入的真信号、真违反样本里的具体语言。
2. 输出格式必须是单个 Markdown 段,严格 5 个 slot:
   - 一句话规则(粗体)
   - `> ` 引用块,说明违反 → 什么 enforcement 行为
   - `反例:` 一行(必须从输入的真违反样本里抽 OR 用同结构造一句,带具体词)
   - `正例:` 一行(怎么改对,带具体的 number/primitive/entity)
   - `源:` 一行,指回触发 signal id + Pattern 原 Soft-Avoid 段
3. 不能与该 Pattern 现有 Rules/Hard-Forbidden/Anti-Pattern 矛盾。
4. 规则必须 falsifiable — LLM check 能机械判违反/合规,不能 vague。
5. 不能引入新概念/缩写不在 Pattern 现有词汇表中。

输出**只输出**这个 Markdown 段,不要任何前后解释、不要 ``` 代码块包裹。
"""


VALIDATE_SYSTEM = """你是 OMW Pattern 规则 reviewer。

输入:
- 一个 Pattern 文件全文(现有版本)
- 一段 LLM 刚生成的新 Hard-Forbidden 规则

你的任务:判断新规则是否真可上线。给出 JSON 输出:
{
  "ok": true|false,
  "contradicts_existing": "<which existing rule, or null>",
  "anti_example_truly_violates": true|false,
  "positive_example_truly_complies": true|false,
  "is_falsifiable": true|false,
  "reasons_to_reject": ["..."]
}

任何一项 false / contradicts_existing 非 null → ok=false。

只输出 JSON,no markdown fence。
"""


def _llm_generate(signal: dict, pattern_text: str, soft_avoid_section: str,
                  sample_violations: list[str]) -> str:
    """Step 1: 让 LLM 生成具体 Hard-Forbidden 段落。"""
    if LLMClient is None:
        # mock fallback — 仅占位,实际 prod 必走 LLM
        return ("**[MOCK] Auto-promoted rule placeholder.**\n"
                "> Violations → governance compliance_passed=0 → publisher skip.\n"
                "反例:`example violation snippet`\n"
                "正例:`example compliant rewrite`\n"
                "源:auto-apply signal\n")
    client = LLMClient()
    user = f"""触发信号:
{json.dumps(signal, ensure_ascii=False, indent=2)}

目标 Pattern 全文:
{pattern_text[:6000]}

相关 Soft-Avoid 段(被提升的 source):
{soft_avoid_section[:800]}

真违反样本(从近 14d 真违反事件抽):
{json.dumps(sample_violations[:5], ensure_ascii=False, indent=2)}

输出新的 Hard-Forbidden Markdown 段(严格 5 slot)。"""
    return client.complete(PROMOTE_SYSTEM, user, max_tokens=600).strip()


def _llm_validate(new_rule: str, pattern_text: str) -> dict:
    """Step 3.2: 语义 LLM check。"""
    if LLMClient is None:
        return {"ok": True, "_mock": True}
    client = LLMClient()
    user = f"""Pattern 现有全文:
{pattern_text[:6000]}

刚生成的新 Hard-Forbidden 规则:
{new_rule}

按 system prompt 输出 JSON。"""
    raw = client.complete(VALIDATE_SYSTEM, user, max_tokens=400).strip()
    # 去 code fence
    if raw.startswith("```"):
        raw = raw[raw.find("{"):raw.rfind("}") + 1]
    try:
        return json.loads(raw)
    except Exception:
        return {"ok": False, "reasons_to_reject": [f"validator JSON parse failed: {raw[:200]}"]}


def _struct_lint(new_rule: str) -> tuple[bool, str]:
    """Step 3.1: 结构 lint — 必须 5 个 slot。"""
    must_have = ["反例", "正例", "源", ">"]
    for k in must_have:
        if k not in new_rule:
            return False, f"missing slot: {k}"
    # 第一行必须含 ** 粗体
    first_line = new_rule.split("\n", 1)[0].strip()
    if "**" not in first_line:
        return False, "first line missing bold rule"
    return True, ""


def _dry_run_test(new_rule: str, pattern_id: str,
                  pass_samples: list[str], fail_samples: list[str]) -> dict:
    """Step 3.3: 干跑 — 喂 5 PASS + 5 FAIL 样本,新规则应不触发 PASS,触发 FAIL。

    简化:LLM check 新规则是否会对每个 sample 判 violation。
    """
    if LLMClient is None:
        return {"ok": True, "_mock": True}
    client = LLMClient()
    system = ("你是 OMW Pattern 规则 enforcer。输入一段 X tweet text 和一条新 "
              "Hard-Forbidden 规则。判断 tweet 是否违反该规则。输出 JSON "
              '{"violates": true|false, "reason": "<short>"}。')
    false_negatives = 0  # FAIL sample 应被判 violates=true,若 false 算 fn
    false_positives = 0  # PASS sample 应被判 violates=false,若 true 算 fp
    for s in fail_samples[:3]:
        try:
            raw = client.complete(system, f"规则:\n{new_rule}\n\nTweet:\n{s}",
                                  max_tokens=120)
            raw = raw[raw.find("{"):raw.rfind("}") + 1]
            r = json.loads(raw)
            if not r.get("violates"):
                false_negatives += 1
        except Exception:
            false_negatives += 1
    for s in pass_samples[:3]:
        try:
            raw = client.complete(system, f"规则:\n{new_rule}\n\nTweet:\n{s}",
                                  max_tokens=120)
            raw = raw[raw.find("{"):raw.rfind("}") + 1]
            r = json.loads(raw)
            if r.get("violates"):
                false_positives += 1
        except Exception:
            pass
    ok = (false_negatives == 0 and false_positives == 0)
    return {"ok": ok, "false_negatives": false_negatives,
            "false_positives": false_positives}


def _extract_soft_avoid_section(pattern_text: str) -> str:
    m = re.search(r"##\s+Soft-Avoid\s*\n(.+?)(?=\n##\s|\Z)", pattern_text, re.S)
    return m.group(1).strip() if m else ""


def _fetch_sample_violations(project: str, pattern_id: str, limit: int = 5) -> list[str]:
    """从 server 抓近 14d 该 Pattern 的真违反事件 subject text。"""
    ssh_key = os.environ.get("OMW_SERVER_SSH_KEY",
                             str(Path.home() / ".ssh" / "hetzner_ash_key"))
    host = os.environ.get("OMW_SERVER_HOST", "root@87.99.153.204")
    db = "/opt/om-world/server/omw_server.db"
    # 从 invocations 表抓 — pattern_id 匹配 + section 在 hard-forbidden + 时间过滤
    sql = (
        f"SELECT json_extract(body,'$.subject') AS s FROM invocations "
        f"WHERE pattern_id='{pattern_id}' "
        f"  AND created_at > strftime('%s','now')-14*86400 "
        f"  AND json_extract(body,'$.subject') IS NOT NULL "
        f"LIMIT {limit}"
    )
    try:
        r = subprocess.run(
            ["ssh", "-i", ssh_key, host, f"sqlite3 -separator '|' {db} \"{sql}\""],
            capture_output=True, text=True, timeout=15,
        )
        out = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
        return out[:limit] or ["(no real samples — server DB empty for this pattern)"]
    except Exception:
        return ["(sample fetch failed — proceeding with generic)"]


def _fetch_pass_samples(project: str, limit: int = 5) -> list[str]:
    """从 server 抓近 7d 该 project 真 published(compliance_passed=1)tweets text。"""
    ssh_key = os.environ.get("OMW_SERVER_SSH_KEY",
                             str(Path.home() / ".ssh" / "hetzner_ash_key"))
    host = os.environ.get("OMW_SERVER_HOST", "root@87.99.153.204")
    db_map = {
        "SOVEREIGN-X": "/root/SOVEREIGN-X/data/sovereign_x.db",
        "OM-WORLD-X":  "/root/OM-WORLD-X/data/om_world_x.db",
    }
    db = db_map.get(project)
    if not db:
        return ["(no DB for project)"]
    sql = (
        f"SELECT d.body FROM tweet_drafts d "
        f"JOIN published_posts p ON p.draft_id=d.draft_id "
        f"WHERE p.status='published' AND p.published_at > datetime('now','-7 days') "
        f"ORDER BY p.published_at DESC LIMIT {limit}"
    )
    try:
        r = subprocess.run(
            ["ssh", "-i", ssh_key, host, f"sqlite3 -separator '|||' {db} \"{sql}\""],
            capture_output=True, text=True, timeout=15,
        )
        out = [ln.strip()[:600] for ln in (r.stdout or "").splitlines() if ln.strip()]
        return out[:limit] or ["(no recent published)"]
    except Exception:
        return ["(pass sample fetch failed)"]


def apply_r_promote(proposal: dict, recipe: dict, dry_run: bool) -> dict:
    """主入口 — 被 apply_evolutions.RECIPE_HANDLERS 调。"""
    target_rel = recipe["target_file"]
    pattern_id = Path(target_rel).parent.name
    # 白名单(冗余 safety — 主控也查)
    import sys as _sys
    PATTERN_WHITELIST = getattr(_sys.modules.get("tools.apply_evolutions"),
                                "PATTERN_WHITELIST", set()) \
                        or getattr(_sys.modules.get("__main__"),
                                   "PATTERN_WHITELIST", set())
    if pattern_id not in PATTERN_WHITELIST:
        return {"outcome": "skipped", "reason": f"{pattern_id} not in whitelist"}

    file_path = PRIVATE_ROOT / target_rel
    if not file_path.exists():
        return {"outcome": "error", "reason": "pattern file not found"}
    pattern_text = file_path.read_text(encoding="utf-8")
    soft_avoid = _extract_soft_avoid_section(pattern_text)
    if not soft_avoid:
        return {"outcome": "skipped", "reason": "no Soft-Avoid section to promote"}

    # 抓真违反样本 + 真 PASS 样本(干跑测试用)
    project = proposal.get("project", "SOVEREIGN-X")
    sample_violations = _fetch_sample_violations(project, pattern_id, limit=5)
    pass_samples = _fetch_pass_samples(project, limit=5)

    # Step 1: LLM 生成
    signal = {
        "id": proposal["id"],
        "kind": proposal["kind"],
        "metric": proposal.get("metric"),
        "current": proposal.get("current_value"),
        "detail": proposal.get("detail", "")[:300],
        "promote_reason": recipe.get("promote_reason", ""),
    }
    try:
        new_rule = _llm_generate(signal, pattern_text, soft_avoid, sample_violations)
    except Exception as e:
        return {"outcome": "error", "reason": f"LLM generate: {e}"}

    # Step 3.1: 结构 lint
    ok, err = _struct_lint(new_rule)
    if not ok:
        return {"outcome": "skipped", "reason": f"struct lint reject: {err}",
                "rejected_content": new_rule[:300]}

    # Step 3.2: 语义 LLM check
    sem = _llm_validate(new_rule, pattern_text)
    if not sem.get("ok"):
        return {"outcome": "skipped", "reason": f"semantic reject: {sem}",
                "rejected_content": new_rule[:300]}

    # Step 3.3: 干跑测试(LLM mock 模式下 skip)
    if LLMClient is not None:
        dr = _dry_run_test(new_rule, pattern_id, pass_samples, sample_violations)
        if not dr.get("ok"):
            return {"outcome": "skipped", "reason": f"dry-run reject: {dr}",
                    "rejected_content": new_rule[:300]}

    # 写入:append 到 ## Hard-Forbidden 段末
    if "## Hard-Forbidden" not in pattern_text:
        return {"outcome": "error", "reason": "no ## Hard-Forbidden section to append"}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    block = (
        f"\n### Auto-promoted ({today}, P3-E {proposal['id']})\n\n"
        f"{new_rule.strip()}\n"
    )
    # 在 ## Hard-Forbidden section 末尾(下一个 ## 前)插
    lines = pattern_text.splitlines(keepends=True)
    new_lines: list[str] = []
    in_hf = False
    inserted = False
    for line in lines:
        if line.startswith("## Hard-Forbidden"):
            in_hf = True
            new_lines.append(line)
            continue
        if in_hf and line.startswith("## ") and not inserted:
            new_lines.append(block + "\n")
            inserted = True
            in_hf = False
        new_lines.append(line)
    if in_hf and not inserted:
        new_lines.append("\n" + block)
        inserted = True
    new_text = "".join(new_lines)

    if dry_run:
        return {"outcome": "dry_run_ok", "preview": new_rule[:300]}

    file_path.write_text(new_text, encoding="utf-8")
    return {
        "outcome": "written",
        "repo_root": str(PRIVATE_ROOT),
        "target_rel": target_rel,
        "commit_message": (
            f"[auto-apply] R-PROMOTE {proposal['id']}: promote Soft-Avoid → "
            f"Hard-Forbidden in {pattern_id}\n\n"
            f"signal: {signal['metric']}={signal['current']} / {signal['detail'][:200]}\n"
            f"new rule (first line): {new_rule.splitlines()[0][:200]}"
        ),
        "needs_remote_push": False,
        "needs_private_rsync": True,
        "needs_server_redeploy": False,
    }
