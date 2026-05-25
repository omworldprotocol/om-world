"""ProtocolBackend — Stage 4 stub (self-running protocol)。

Pattern 库去中心化存储 (IPFS/Arweave) + 链上 registry。
Metrics 走链上 attestation (EAS-like)。
仿 BTC 模型: founder 离场协议仍跑。
"""
from __future__ import annotations

from .base import OMWBackend


class ProtocolBackend(OMWBackend):
    """Stage 4: self-running protocol (IPFS + chain registry + attestations)."""

    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise NotImplementedError(
            "ProtocolBackend is stage-4 stub — final form. "
            "Set OMW_BACKEND=local for stage 1.")

    def load_pattern(self, pattern_id):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    def load_pack(self, pack_id):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    def log_invocation_event(self, event):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    def search(self, **kw):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    def query_metrics(self, pattern_id):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    def resolve_deps(self, pattern_id):  # type: ignore[no-untyped-def]
        raise NotImplementedError
