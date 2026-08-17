"""Error types and utilities for AIOS layer.

Phase 1: re-exports from app.errors for convenience.
Phase 2+: may add AIOS-specific error types.
"""

from app.errors import LLMAPIError, retry_async  # noqa: F401
