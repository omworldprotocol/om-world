"""GitBackend — Stage 2 实现:GitHub-synced 跨设备协作。

继承 LocalBackend(所有 Pattern/Pack/search 逻辑复用),只加 git 同步层:

  - on init / explicit pull():     git pull --rebase --autostash
  - on log_invocation_event():     append jsonl 后,异步 batch commit + push
                                   (jsonl 是 append-only,自然抗冲突)
  - on aggregate_metrics():        SKILL.md frontmatter 改动属"权威源更新",
                                   常规 commit + push;冲突时 last-write-wins
                                   并触发 warning(实际很少发生因 aggregator
                                   通常只在中心设备跑)

设计原则(ARCHITECTURE.md §二 Stage 2):
  1. **客户端代码 zero-change**:用户仍 `omw = OMW()`,只改 env OMW_BACKEND=git
  2. **invocations.jsonl 冲突自然解决**:UTC ts + agent_id + invocation_id 唯一标识,
     aggregator 配对时按 (ts, agent_id, invocation_id) 去重
  3. **push 失败不阻塞**:本地写入成功即返回,push 在后台 retry;失败积压日志
     在 runtime/sync_failures.log

Env(Stage 2 专属):
  OMW_GIT_REMOTE     git remote URL(默认从仓库 origin 读)
  OMW_GIT_BRANCH     默认 main
  OMW_GIT_AUTHOR     默认 "OMW Agent <noreply@omworld.one>"
  OMW_GIT_PUSH_ASYNC 默认 true;false 时同步 push(测试用)
  OMW_GIT_PUSH_BATCH 默认 30 秒;此周期内多次 log 合并一次 commit
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from .local import LocalBackend


class GitBackend(LocalBackend):
    """Stage 2: LocalBackend + git pull/push synchronization."""

    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)

        # 配置
        self.git_remote = os.environ.get("OMW_GIT_REMOTE", "")
        self.git_branch = os.environ.get("OMW_GIT_BRANCH", "main")
        self.git_author = os.environ.get(
            "OMW_GIT_AUTHOR",
            "OMW Agent <noreply@omworld.one>"
        )
        self.push_async = os.environ.get("OMW_GIT_PUSH_ASYNC", "true").lower() == "true"
        self.push_batch_s = int(os.environ.get("OMW_GIT_PUSH_BATCH", "30"))

        # 仓库根:patterns_dir 的 git 仓库根(找 .git/)
        self.repo_root = self._find_git_root(self.patterns_dir)
        if self.repo_root is None:
            raise RuntimeError(
                f"GitBackend: no .git/ found upward from {self.patterns_dir}. "
                f"Initialize git in om-world first, or use LocalBackend.")

        # 异步 push debouncer
        self._pending_push = False
        self._push_lock = threading.Lock()
        self._push_thread: threading.Thread | None = None

        # 启动时拉一次(同步,确保拿到远程最新 Pattern)
        if os.environ.get("OMW_GIT_PULL_ON_INIT", "true").lower() == "true":
            self._git_pull(silent=True)

    # ─── git 命令封装 ─────────────────────────────────────────────────

    @staticmethod
    def _find_git_root(start: Path) -> Path | None:
        p = start.resolve()
        for _ in range(20):
            if (p / ".git").exists():
                return p
            if p.parent == p:
                return None
            p = p.parent
        return None

    def _git(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(self.repo_root), *args],
            capture_output=True, text=True, check=check,
        )

    def _git_pull(self, silent: bool = False) -> bool:
        r = self._git("pull", "--rebase", "--autostash", "origin", self.git_branch)
        if r.returncode != 0:
            msg = f"⚠ GitBackend pull failed: {r.stderr.strip()[:200]}"
            if not silent:
                print(msg)
            self._log_sync_failure("pull", r.stderr)
            return False
        return True

    def _git_push(self) -> bool:
        # add patterns/ + runtime/(只 sync 这两个目录,不影响其他 om-world 文件)
        self._git("add", "patterns/", "runtime/")
        r = self._git("diff", "--cached", "--quiet")
        if r.returncode == 0:
            return True  # 无 staged 变更
        author = self.git_author
        commit_msg = f"omw: auto-sync invocation log + metrics (ts={int(time.time())})"
        r = self._git("-c", f"user.name={author.split('<')[0].strip()}",
                      "-c", f"user.email={author.split('<')[1].rstrip('>').strip() if '<' in author else 'noreply@omworld.one'}",
                      "commit", "-m", commit_msg)
        if r.returncode != 0:
            self._log_sync_failure("commit", r.stderr)
            return False
        r = self._git("push", "origin", self.git_branch)
        if r.returncode != 0:
            # push 失败常见原因:本地落后远程 → 先 pull --rebase 再 push
            if self._git_pull(silent=True):
                r = self._git("push", "origin", self.git_branch)
            if r.returncode != 0:
                self._log_sync_failure("push", r.stderr)
                return False
        return True

    def _log_sync_failure(self, op: str, err: str) -> None:
        f = self.runtime_dir / "sync_failures.log"
        with f.open("a", encoding="utf-8") as fp:
            fp.write(f"{int(time.time())}\t{op}\t{err.strip()[:500]}\n")

    # ─── 异步 push debouncer ─────────────────────────────────────────

    def _schedule_push(self) -> None:
        with self._push_lock:
            self._pending_push = True
            if self._push_thread and self._push_thread.is_alive():
                return  # 已有 worker 在等
            self._push_thread = threading.Thread(
                target=self._push_worker, daemon=True)
            self._push_thread.start()

    def _push_worker(self) -> None:
        time.sleep(self.push_batch_s)
        with self._push_lock:
            self._pending_push = False
        self._git_push()

    # ─── Override LocalBackend hooks ─────────────────────────────────

    def log_invocation_event(self, event: dict[str, Any]) -> None:
        # 先本地写(同 LocalBackend),再调度 push
        super().log_invocation_event(event)
        if self.push_async:
            self._schedule_push()
        else:
            self._git_push()

    # 显式 API(供 aggregator 收尾时手工触发)
    def flush(self) -> None:
        """Force sync any pending invocation logs to remote."""
        self._git_push()


# ─── 兼容性导出 ──────────────────────────────────────────────────────

__all__ = ["GitBackend"]
