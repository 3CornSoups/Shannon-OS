"""AIOS Dispatcher — LLM-driven task router.

The Dispatcher is the entry point for all user requests in AIOS.
It analyzes the user's intent, consults the Agent Registry, and
routes the task to the most suitable Agent.

Phase 2: single-target routing (always picks one Agent).
Phase 3+: multi-agent orchestration (parallel dispatch to multiple Agents).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from aios.agent_registry import agent_registry
from aios.llm import extract_json, request_text_from_messages

logger = logging.getLogger(__name__)

# ── Dispatcher system prompt ──

DISPATCHER_SYSTEM_PROMPT = """你是 AIOS 任务路由器（Dispatcher）。

你的职责：
1. 分析用户输入，理解用户意图
2. 从可用 Agent 列表中选择最合适的 Agent
3. 将用户请求重新表述为适合该 Agent 执行的任务描述

输出必须是严格的 JSON 对象（不要 markdown 代码块）：
{
  "agent_id": "选择的 Agent ID（从可用列表中选择）",
  "task": "重新表述后的任务描述（传递给 Agent）",
  "plan": "1-2 句话简述执行计划",
  "reasoning": "为什么选择这个 Agent",
  "needs_multi_agent": false
}

规则：
- 如果只有一个 Agent 可用，直接选择它
- 如果有多个 Agent，根据能力标签匹配：
  * 服务器运维/部署/监控/SSH/系统管理 → Server Agent（能力: ssh, shell, server）
  * 代码分析/重构/文件操作/脚本编写/代码搜索 → Code Agent（能力: code, files, analysis, local）
  * 如果用户只是闲聊或问一般性问题，路由到 Server Agent
- Code Agent 用于本地文件操作，Server Agent 用于远程服务器操作
- needs_multi_agent 在 Phase 3 始终为 false
"""


@dataclass
class DispatchResult:
    """Result of the Dispatcher's routing decision."""
    agent_id: str
    task: str
    plan: str = ""
    reasoning: str = ""
    needs_multi_agent: bool = False
    raw_response: str = ""


class Dispatcher:
    """LLM-driven task router.

    Usage:
        dispatcher = Dispatcher(api_base, api_key, model, timeout_sec)
        result = await dispatcher.dispatch("帮我检查服务器磁盘使用情况")
        agent = agent_registry.get(result.agent_id)
        output = await agent.execute(result.task)
    """

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model: str = "deepseek-chat",
        timeout_sec: int = 60,
    ):
        self.api_base = api_base
        self.api_key = api_key
        self.model = model
        self.timeout_sec = timeout_sec

    async def dispatch(self, user_prompt: str) -> DispatchResult:
        """Analyze user intent and route to the best Agent.

        Args:
            user_prompt: Raw user input.

        Returns:
            DispatchResult with agent_id and rephrased task.

        If the LLM call fails, falls back to routing to the first
        available Agent (or raises if none are registered).
        """
        agents_summary = agent_registry.get_capabilities_summary()

        # Build the full prompt
        user_message = (
            f"=== 用户请求 ===\n{user_prompt}\n\n"
            f"=== 可用 Agent ===\n{agents_summary}\n\n"
            "请分析意图并选择最合适的 Agent。只输出 JSON。"
        )

        try:
            raw = await request_text_from_messages(
                self.api_base,
                self.api_key,
                self.model,
                [
                    {"role": "system", "content": DISPATCHER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                self.timeout_sec,
            )
        except Exception as exc:
            logger.warning("Dispatcher LLM call failed: %s", exc)
            return self._fallback_dispatch(user_prompt)

        data = extract_json(raw)
        if not data:
            logger.warning("Dispatcher: failed to parse LLM response as JSON: %.200s", raw)
            return self._fallback_dispatch(user_prompt)

        result = DispatchResult(
            agent_id=data.get("agent_id", ""),
            task=data.get("task", user_prompt),
            plan=data.get("plan", ""),
            reasoning=data.get("reasoning", ""),
            needs_multi_agent=data.get("needs_multi_agent", False),
            raw_response=raw,
        )

        # Validate: agent must exist
        if not result.agent_id or result.agent_id not in agent_registry:
            logger.warning(
                "Dispatcher: LLM chose unknown agent '%s', falling back",
                result.agent_id,
            )
            return self._fallback_dispatch(user_prompt)

        logger.info(
            "Dispatcher routed to '%s': plan=%s",
            result.agent_id, result.plan,
        )
        return result

    def _fallback_dispatch(self, user_prompt: str) -> DispatchResult:
        """Fallback: route to the first available Agent."""
        agents = agent_registry.list_all()
        if not agents:
            raise RuntimeError(
                "No Agents registered. Register at least one Agent "
                "before using the Dispatcher."
            )
        first = agents[0]
        logger.info("Dispatcher fallback: routing to '%s'", first.agent_id)
        return DispatchResult(
            agent_id=first.agent_id,
            task=user_prompt,
            plan="（自动回退路由）",
            reasoning="LLM 调用失败，回退到默认 Agent",
        )
