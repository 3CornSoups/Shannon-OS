"""Shared models for AIOS layer.

Phase 1: minimal — just BaseAgentConfig.
Phase 2+: expand with AgentDescriptor, DispatcherResult, etc.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BaseAgentConfig:
    """Minimal config needed by ANY LLM-based Agent.

    Separate from app.models.AgentConfig to avoid coupling.
    ServerAgent converts from AgentConfig -> BaseAgentConfig in __init__.
    """

    agent_id: str = "default"
    display_name: str = "Base Agent"
    api_base: str = "https://api.deepseek.com"
    api_key: str = ""
    model: str = "deepseek-chat"
    timeout_sec: int = 90
    max_context_messages: int = 20
