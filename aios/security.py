"""Shared security primitives for AIOS.

Phase 1: extracted from app/agent.py (is_blocked, assess_risk).
These are generic — they apply to ANY agent that can execute shell commands.
"""

from __future__ import annotations

import re

# ── Hard-block patterns: operations that must NEVER auto-execute ──
_HARD_BLOCK_PATTERNS: list[re.Pattern] = [
    # Raw disk writes / formatting
    re.compile(r'\bdd\s+.*of=/dev/'),
    re.compile(r'\bmkfs\b'),
    re.compile(r'\bmkswap\b'),
    re.compile(r'\bshred\b'),
    # Fork bombs / high-risk shell
    re.compile(r':\(\)\s*\{'),
    re.compile(r'curl.*\|.*(?:sh|bash|dash)'),
    re.compile(r'wget.*\|.*(?:sh|bash|dash)'),
    # Root-level destruction
    re.compile(r'\brm\s+-rf\s+/\b'),
    re.compile(r'\brm\s+-rf\s+/etc\b'),
    re.compile(r'\bchmod\s+-R\s+777\s+/'),
    # System-level dangerous writes
    re.compile(r'>\s*/etc/'),
    re.compile(r'>>\s*/etc/(?:passwd|shadow|sudoers)\b'),
]


def is_blocked(command: str) -> tuple[bool, str]:
    """Check if a command matches any hard-block pattern.
    Returns (blocked, reason).
    """
    for pat in _HARD_BLOCK_PATTERNS:
        if pat.search(command):
            return True, f"命中硬阻断规则: {pat.pattern}"
    return False, ""


def assess_risk(command: str) -> tuple[str, str]:
    """Compatibility wrapper: blocked -> HIGH, else LOW.
    (Actual risk assessment is done by the LLM; this is the hard-block floor.)
    """
    blocked, reason = is_blocked(command)
    if blocked:
        return "HIGH", reason
    return "LOW", ""
