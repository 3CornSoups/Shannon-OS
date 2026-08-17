"""Tool registry for AIOS.

Tools are registered at two levels:
  - Base pool: tools all agents can use (e.g., ask_user, task_done)
  - Agent-specific: tools only certain agents register (e.g., execute_command
    for ServerAgent)

Phase 1: simple in-memory registry.
Phase 2+: persistence, discovery, dynamic registration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolDef:
    """Metadata for a registered tool."""
    name: str
    description: str
    parameters: dict[str, Any]   # JSON Schema for the parameters
    tags: list[str] = field(default_factory=list)
    risk_level: str = "LOW"      # LOW | HIGH — safety classification


class ToolRegistry:
    """Minimal in-memory tool registry.

    Usage:
        registry = ToolRegistry()

        # Register base tools (available to all agents)
        registry.register(ToolDef(name="task_done", ...), scope="base")

        # Register agent-specific tools
        registry.register(ToolDef(name="execute_command", ...), scope="agent:server")

        # Get tools for a specific agent
        tools = registry.get_for_agent("server")  # base + agent:server
    """

    def __init__(self):
        self._base: dict[str, ToolDef] = {}
        self._agent_tools: dict[str, dict[str, ToolDef]] = {}

    # ── Registration ──

    def register(self, tool: ToolDef, scope: str = "base") -> None:
        """Register a tool.

        Args:
            tool: Tool definition.
            scope: "base" for all agents, or "agent:<name>" for a specific agent.
        """
        if scope == "base":
            self._base[tool.name] = tool
        elif scope.startswith("agent:"):
            agent_name = scope.split(":", 1)[1]
            if agent_name not in self._agent_tools:
                self._agent_tools[agent_name] = {}
            self._agent_tools[agent_name][tool.name] = tool
        else:
            raise ValueError(f"Unknown scope: {scope}")

    def register_base_tool(
        self, name: str, description: str, parameters: dict[str, Any],
        risk_level: str = "LOW", tags: list[str] | None = None,
    ) -> None:
        """Convenience: register a base tool from individual fields."""
        self.register(
            ToolDef(
                name=name, description=description,
                parameters=parameters, risk_level=risk_level,
                tags=tags or [],
            ),
            scope="base",
        )

    # ── Query ──

    def get_for_agent(self, agent_name: str) -> list[dict[str, Any]]:
        """Return OpenAI-format tool definitions for a given agent
        (base tools + agent-specific tools).
        """
        tools: dict[str, ToolDef] = dict(self._base)
        if agent_name in self._agent_tools:
            tools.update(self._agent_tools[agent_name])
        return [_tool_to_openai(t) for t in tools.values()]

    def get_base_tools(self) -> list[dict[str, Any]]:
        """Return only the base (shared) tools in OpenAI format."""
        return [_tool_to_openai(t) for t in self._base.values()]

    def list_tools(self, agent_name: str | None = None) -> list[ToolDef]:
        """Return ToolDef objects (not OpenAI format).

        If agent_name is given, returns base + that agent's tools.
        Otherwise returns ALL registered tools.
        """
        if agent_name and agent_name in self._agent_tools:
            return list(self._base.values()) + list(self._agent_tools[agent_name].values())
        result = list(self._base.values())
        for tools in self._agent_tools.values():
            result.extend(tools.values())
        return result


def _tool_to_openai(tool: ToolDef) -> dict[str, Any]:
    """Convert a ToolDef to OpenAI function-calling format."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }
