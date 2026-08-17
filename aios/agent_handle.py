"""AgentHandle — unified interface for AIOS to manage any Agent.

All Agents (Python-native or external) must present this interface to AIOS.
Python-native agents extend BaseAgent which implements AgentHandle.
External agents are wrapped by an AgentAdapter that implements AgentHandle.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    """Unified lifecycle states for all Agents."""
    IDLE = "idle"        # Ready, waiting for a task
    BUSY = "busy"        # Executing a task
    ERROR = "error"      # Terminal error state
    OFFLINE = "offline"  # Shut down / unavailable


@dataclass
class AgentCapability:
    """Advertised capability of an Agent (used by Dispatcher for routing)."""
    name: str
    description: str
    tags: list[str] = field(default_factory=list)


class AgentHandle(ABC):
    """Unified interface for AIOS to manage, query, and dispatch to any Agent.

    Every Agent (local Python class or external subprocess) must expose
    this set of operations.  AIOS core code only talks to AgentHandle,
    never to concrete Agent classes.
    """

    # ── Identity ──

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Unique identifier for this agent instance."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for UI / logs."""
        ...

    @property
    @abstractmethod
    def status(self) -> AgentStatus:
        """Current lifecycle status."""
        ...

    # ── Capability discovery ──

    @abstractmethod
    async def get_capabilities(self) -> list[AgentCapability]:
        """Return the capabilities this agent advertises (for Dispatcher routing)."""
        ...

    @abstractmethod
    async def get_tools(self) -> list[dict[str, Any]]:
        """Return tool definitions (OpenAI function-calling format)."""
        ...

    # ── Execution ──

    @abstractmethod
    async def execute(self, task: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Dispatch a task to the agent. Returns a structured result dict."""
        ...

    @abstractmethod
    async def stream_execute(
        self, task: str, context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Dispatch a task and stream textual progress/results."""
        ...

    # ── Lifecycle ──

    @abstractmethod
    async def cancel(self) -> None:
        """Cancel the current execution (best-effort)."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Gracefully release resources."""
        ...
