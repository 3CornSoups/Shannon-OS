"""Agent Registry — AIOS Agent discovery and lifecycle management.

Global singleton that tracks all registered Agent instances.
Used by the Dispatcher to discover available Agents and route tasks.

Phase 2: simple in-memory registry.
Phase 3+: persistence, health checks, auto-discovery.
"""

from __future__ import annotations

from typing import Any

from aios.agent_handle import AgentHandle


class AgentRegistry:
    """Central registry for all Agent instances.

    Every Agent (ServerAgent, CodeAgent, etc.) must be registered
    before the Dispatcher can route tasks to it.

    Usage:
        from aios.agent_registry import agent_registry

        agent = ServerAgent(config)
        agent_registry.register(agent)

        # Later, in Dispatcher:
        agents = agent_registry.list_all()
    """

    def __init__(self):
        self._agents: dict[str, AgentHandle] = {}

    # ── Registration ──

    def register(self, agent: AgentHandle) -> None:
        """Register an Agent.  Replaces any existing agent with the same ID."""
        self._agents[agent.agent_id] = agent

    def unregister(self, agent_id: str) -> None:
        """Remove an Agent from the registry."""
        self._agents.pop(agent_id, None)

    # ── Lookup ──

    def get(self, agent_id: str) -> AgentHandle | None:
        """Get an Agent by its ID."""
        return self._agents.get(agent_id)

    def list_all(self) -> list[AgentHandle]:
        """Return all registered Agents."""
        return list(self._agents.values())

    def find_by_capability(self, tag: str) -> list[AgentHandle]:
        """Find Agents that advertise a specific capability tag."""
        # Synchronous scan — get_capabilities is async but in Phase 2
        # we populate capabilities at registration time.
        # TODO Phase 3: async find_by_capability
        return [
            a for a in self._agents.values()
            if tag in getattr(a, '_capability_tags', [])
        ]

    def get_capabilities_summary(self) -> str:
        """Build a summary string for the Dispatcher's LLM prompt.

        Lists each Agent's name, ID, and advertised capabilities.
        """
        if not self._agents:
            return "（当前无可用 Agent）"

        lines: list[str] = []
        for agent in self._agents.values():
            caps = getattr(agent, '_capability_tags', [])
            cap_str = ", ".join(caps) if caps else "通用"
            lines.append(
                f"- {agent.display_name} (ID: {agent.agent_id})"
                f" — 能力: {cap_str}"
            )
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._agents)

    def __contains__(self, agent_id: str) -> bool:
        return agent_id in self._agents


# ── Global singleton ──
agent_registry = AgentRegistry()
