#!/usr/bin/env python3
"""push_outbox.py — drain runtime/_outbox.jsonl → POST events to OMW server.

P1.6 architecture: agents always use LocalBackend (zero-setup, never fails).
This tool runs on a schedule (launchd, 5min) to ship buffered events to the
central OMW server when network is available. Agents don't open SSH tunnels;
this script auto-detects + opens one on demand.

Behavior:
  - read _outbox.jsonl line-by-line
  - POST each event to {OMW_SERVER_URL}/invocations
  - on success: collect index, then atomically rewrite _outbox.jsonl
    keeping only un-pushed lines
  - on auth/network failure: leave outbox intact, next run retries

Env:
  OMW_SERVER_URL    — e.g. http://127.0.0.1:8765 (default; we auto-tunnel)
  OMW_API_TOKEN     — bearer token
  OMW_AUTO_TUNNEL   — "1" (default) to open SSH tunnel via OMW_SERVER_HOST/SSH_KEY
  OMW_SERVER_HOST   — root@87.99.153.204 (default)
  OMW_SERVER_SSH_KEY — ~/.ssh/hetzner_ash_key (default)

Idempotent: re-running with same outbox is safe (server INSERT may dup but
events are append-only — duplicate is harmless; aggregator pairs by
invocation_id which is unique per event).

Atomic: outbox rewrite is `tmp + rename` to avoid races with concurrent agents.
"""
from __future__ import annotations

import atexit
import json
import os
import shlex
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

OMW_ROOT = Path(os.environ.get("OMW_ROOT",
    str(Path(__file__).resolve().parent.parent)))
OUTBOX = Path(os.environ.get("OMW_OUTBOX_PATH",
    str(OMW_ROOT / "runtime" / "_outbox.jsonl")))

SERVER_URL = os.environ.get("OMW_SERVER_URL", "http://127.0.0.1:8765").rstrip("/")
API_TOKEN  = os.environ.get("OMW_API_TOKEN", "")
AUTO_TUNNEL = os.environ.get("OMW_AUTO_TUNNEL", "1") == "1"
SERVER_HOST = os.environ.get("OMW_SERVER_HOST", "root@87.99.153.204")
SSH_KEY = os.environ.get("OMW_SERVER_SSH_KEY",
                         str(Path.home() / ".ssh" / "hetzner_ash_key"))
REQUEST_TIMEOUT = float(os.environ.get("OMW_REQUEST_TIMEOUT", "10"))
BATCH_MAX = int(os.environ.get("OMW_OUTBOX_BATCH", "500"))


def _open_tunnel_if_needed() -> subprocess.Popen | None:
    """Open SSH tunnel for the duration of this run if server URL points
    at localhost and nothing is listening on the port."""
    if not AUTO_TUNNEL:
        return None
    if not SERVER_URL.startswith("http://127.0.0.1:"):
        return None  # remote URL — assume reachable
    port = int(SERVER_URL.split(":")[-1])
    # Probe: is something listening already?
    try:
        with urllib.request.urlopen(f"{SERVER_URL}/health", timeout=2):
            return None  # already reachable
    except Exception:
        pass
    cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
           "-o", "ConnectTimeout=5", "-N",
           "-L", f"{port}:127.0.0.1:{port}", SERVER_HOST]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    # Wait for tunnel to come up (~2s) before first request.
    for _ in range(20):
        time.sleep(0.1)
        try:
            with urllib.request.urlopen(f"{SERVER_URL}/health", timeout=1):
                return proc
        except Exception:
            continue
    # Tunnel didn't come up
    proc.terminate()
    return None


def _close_tunnel(proc: subprocess.Popen | None) -> None:
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def _post_event(ev: dict) -> bool:
    body = json.dumps(ev, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{SERVER_URL}/invocations", data=body, method="POST",
        headers={
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json",
        })
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print(f"  AUTH FAIL ({e.code}): check OMW_API_TOKEN", file=sys.stderr)
            return False
        # treat other HTTP errors as transient — leave in outbox
        print(f"  HTTP {e.code} (will retry next run)", file=sys.stderr)
        return False
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
        print(f"  network error ({e}); will retry next run", file=sys.stderr)
        return False


def main() -> int:
    if not OUTBOX.is_file():
        print(f"no outbox at {OUTBOX} (nothing to push)")
        return 0
    if not API_TOKEN:
        print("OMW_API_TOKEN not set — cannot push; leaving outbox intact",
              file=sys.stderr)
        return 1

    # Read all lines, decide which to ship.
    lines = OUTBOX.read_text(encoding="utf-8").splitlines()
    if not lines:
        return 0
    print(f"outbox has {len(lines)} lines")

    tunnel = _open_tunnel_if_needed()
    atexit.register(_close_tunnel, tunnel)

    # Health probe — if server unreachable, abort cleanly (outbox intact).
    try:
        with urllib.request.urlopen(f"{SERVER_URL}/health", timeout=3):
            pass
    except Exception as e:
        print(f"server unreachable at {SERVER_URL}: {e}", file=sys.stderr)
        return 1

    pushed_idx: set[int] = set()
    failed_idx: set[int] = set()
    batch = lines[:BATCH_MAX]
    for i, line in enumerate(batch):
        line = line.strip()
        if not line:
            pushed_idx.add(i)  # skip empty
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            print(f"  malformed line #{i}; dropping", file=sys.stderr)
            pushed_idx.add(i)
            continue
        if _post_event(ev):
            pushed_idx.add(i)
        else:
            failed_idx.add(i)
            # Stop early on auth failure to avoid spamming.
            if API_TOKEN and not pushed_idx:
                break

    # Rewrite outbox keeping un-pushed (failed_idx) + un-batched (i >= BATCH_MAX).
    keep: list[str] = []
    for i, line in enumerate(lines):
        if i < BATCH_MAX:
            if i not in pushed_idx:
                keep.append(line)
        else:
            keep.append(line)

    tmp = OUTBOX.with_suffix(".tmp")
    tmp.write_text(("\n".join(keep) + "\n") if keep else "",
                   encoding="utf-8")
    tmp.replace(OUTBOX)

    print(f"pushed {len(pushed_idx)} / {len(batch)} (kept {len(keep)} for next run)")
    return 0 if pushed_idx else 1


if __name__ == "__main__":
    sys.exit(main())
