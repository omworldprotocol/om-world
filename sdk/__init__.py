"""OM World SDK — protocol-ready Pattern Library client.

Stage 1 (Local) 实现完整;Stage 2-4 stub。所有客户端代码用同一套 API:

    from omw import OMW
    omw = OMW()                           # auto-pick backend from OMW_BACKEND env
    pattern = omw.load_pattern("playbook-cdp")
    pack = omw.load_pack("pack-defi-audit-cdp")
    with omw.invoke("playbook-cdp", context={"audit_id": "A0003"}) as inv:
        ...
        inv.record_outcome(success=True, metrics={"edges-covered-b": 9})

Backend 切换只需改 env,不改代码 — 见 ARCHITECTURE.md §3。
"""

from .omw import OMW
from .pattern import Pattern
from .pack import Pack
from .invocation import Invocation
from .session import Session, GuardResult, JudgmentResult

__all__ = ["OMW", "Pattern", "Pack", "Invocation",
           "Session", "GuardResult", "JudgmentResult"]
__version__ = "0.3.1"  # P1.5 — adds Session for agent-led (形态 A)
