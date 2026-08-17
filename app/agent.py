"""Backward-compatibility shim.

Phase 1 of AIOS extraction: delegates to aios/ and agents/ modules.
All existing import paths continue to work:

    from app.agent import ShannonAgent    → ServerAgent alias
    from app.agent import is_blocked      → aios.security
    from app.agent import assess_risk     → aios.security

The original implementation has moved to:
  - agents/server_agent.py  (ServerAgent class)
  - aios/security.py        (is_blocked, assess_risk)
  - aios/base_agent.py      (BaseAgent abstract class)
"""

from __future__ import annotations

from agents.server_agent import ServerAgent as ShannonAgent  # noqa: F401
from aios.security import is_blocked, assess_risk            # noqa: F401
