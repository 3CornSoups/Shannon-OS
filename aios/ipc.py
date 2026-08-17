"""AIOS Inter-Agent Communication (IPC).

Phase 3: Direct agent-to-agent calls via AgentRegistry.
Allows any Agent to delegate a subtask to another Agent.

Future: Event bus for async pub/sub between Agents.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from aios.agent_registry import agent_registry

logger = logging.getLogger(__name__)


async def call_agent(
    target_agent_id: str,
    task: str,
    context: dict[str, Any] | None = None,
    timeout_sec: int = 300,
) -> dict[str, Any]:
    """Agent A directly calls Agent B (synchronous, waits for result).

    This is the backend for the ``delegate_to_agent`` tool.
    It looks up the target Agent in the global registry and calls
    its ``execute()`` method, returning the result.

    Args:
        target_agent_id: Agent ID to call (from AgentRegistry).
        task: The task description to pass to the target Agent.
        context: Optional additional context dict.
        timeout_sec: Max wait time for the target Agent to complete.

    Returns:
        {"status": "ok"|"error"|"not_found"|"timeout",
         "result": <result dict or error message>,
         "agent_id": str,
         "agent_display": str}
    """
    target = agent_registry.get(target_agent_id)
    if target is None:
        available = [a.agent_id for a in agent_registry.list_all()]
        logger.warning(
            "IPC: agent '%s' not found. Available: %s",
            target_agent_id, available,
        )
        return {
            "status": "not_found",
            "result": f"Agent '{target_agent_id}' 未找到。可用: {', '.join(available)}",
            "agent_id": target_agent_id,
            "agent_display": target_agent_id,
        }

    logger.info(
        "IPC: %s → %s: %s",
        "caller", target.display_name, task[:100],
    )

    try:
        result = await asyncio.wait_for(
            target.execute(task, context),
            timeout=timeout_sec,
        )
        return {
            "status": "ok",
            "result": result,
            "agent_id": target_agent_id,
            "agent_display": target.display_name,
        }
    except asyncio.TimeoutError:
        logger.warning("IPC: call to '%s' timed out after %ds", target_agent_id, timeout_sec)
        return {
            "status": "timeout",
            "result": f"Agent '{target.display_name}' 执行超时 ({timeout_sec}s)",
            "agent_id": target_agent_id,
            "agent_display": target.display_name,
        }
    except Exception as exc:
        logger.error("IPC: call to '%s' failed: %s", target_agent_id, exc)
        return {
            "status": "error",
            "result": f"Agent 执行异常: {exc}",
            "agent_id": target_agent_id,
            "agent_display": target.display_name,
        }
