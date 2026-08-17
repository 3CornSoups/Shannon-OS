"""BaseAgent — abstract base class for Python-native LLM-driven Agents.

Extracted from ShannonAgent.  Contains everything generic that ANY
LLM-based Agent needs: conversation management, JSON request/retry,
tool-calling dispatch, streaming reply.

Subclasses implement agent-specific behavior by overriding:
  - _build_system_prompt()
  - _get_tools()
  - _tool_call_to_action()
  - _dict_to_action()
  - _validate_action()
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel, ValidationError

from aios.agent_handle import AgentHandle, AgentCapability, AgentStatus
from aios.models import BaseAgentConfig
from aios.errors import LLMAPIError, retry_async
from aios.llm import (
    extract_json,
    extract_think,
    request_text_from_messages,
    request_text_stream,
    try_tool_call,
)
from app.conversation import ConversationManager

logger = logging.getLogger(__name__)


class BaseAgent(AgentHandle):
    """Abstract base for Python-native LLM agents.

    Provides:
      - ConversationManager (private memory per agent)
      - _request_json: generic JSON LLM call with retry + model validation
      - _request_first_action: tool-calling entry point
      - _request_react_action: in-loop tool-calling with fallback
      - stream_reply: streaming chat mode

    Subclasses MUST implement the abstract methods below.
    """

    # ── Abstract methods (subclass contract) ──

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

    @abstractmethod
    def _build_system_prompt(self, *args: Any, **kwargs: Any) -> str:
        """Build the system prompt for a given mode/stage.

        Subclasses define their own signature (e.g., ServerAgent adds
        host_context, mode, stage, metrics_text, etc.).
        """
        ...

    @abstractmethod
    def _get_tools(self) -> list[dict[str, Any]]:
        """Return the tool definitions to pass to the LLM (OpenAI format)."""
        ...

    @abstractmethod
    def _tool_call_to_action(self, name: str, args: dict[str, Any]) -> Any:
        """Convert a raw tool-call result into an agent-specific action object."""
        ...

    @abstractmethod
    def _dict_to_action(self, data: dict[str, Any]) -> Any:
        """Convert a JSON dict (non-tool-call response) into an action object."""
        ...

    @abstractmethod
    def _validate_action(self, action: Any) -> Any:
        """Validate and fix an action before execution (e.g., risk assessment)."""
        ...

    # ── Constructor ──

    def __init__(self, config: BaseAgentConfig):
        self.config = config
        self.conversation = ConversationManager(
            max_messages=config.max_context_messages,
        )
        self._status = AgentStatus.IDLE

    @property
    def status(self) -> AgentStatus:
        return self._status

    # ── Generic JSON request (extracted from ShannonAgent._request_json) ──

    async def _request_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: type[BaseModel] | None = None,
    ) -> Any:
        """Send system+user prompt, parse JSON response, retry on failure.

        Args:
            system_prompt: System-level instructions.
            user_prompt: User's request.
            model: Optional Pydantic model class for validation.
                   If provided, returns a validated instance of that model.
                   If None, returns the raw dict.

        Returns:
            Validated Pydantic model instance (if model is given) or raw dict.

        Raises:
            ValueError: if JSON extraction + repair both fail.
        """

        async def _do() -> Any:
            messages = self.conversation.get_messages()
            if not messages:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            raw = await request_text_from_messages(
                self.config.api_base,
                self.config.api_key,
                self.config.model,
                messages,
                self.config.timeout_sec,
            )
            data = extract_json(raw)
            if not data:
                # One-shot repair: ask LLM to fix its JSON
                repaired = await request_text_from_messages(
                    self.config.api_base,
                    self.config.api_key,
                    self.config.model,
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",
                         "content": (
                             "你刚才输出不符合 JSON 格式，请严格只输出 JSON 对象。"
                             f"\n原问题: {user_prompt}"
                         )},
                    ],
                    self.config.timeout_sec,
                )
                data = extract_json(repaired)
            if not data:
                raise ValueError("LLM 返回非 JSON 响应且修复失败")
            if model is not None:
                try:
                    return model.model_validate(data)
                except ValidationError as e:
                    raise ValueError(f"JSON 校验失败: {e}")
            return data

        try:
            return await retry_async(
                _do, max_retries=2, base_delay=1.0,
                retryable_exceptions=(ValueError,),
            )
        except (ValueError, ValidationError):
            if model is not None:
                return model()
            return {}

    # ── Tool-calling (generic, parameterized) ──

    async def _request_first_action(
        self,
        user_prompt: str,
        system_prompt: str | None = None,
        *,
        available_tools: list[dict[str, Any]] | None = None,
    ) -> Any | None:
        """Initial tool-calling attempt with a fresh system+user message pair.

        Args:
            user_prompt: The user's request.
            system_prompt: Optional override system prompt.
            available_tools: Optional override tool list. If None, uses _get_tools().

        Returns:
            An agent-specific action object (via _tool_call_to_action), or None
            if tool calling was not used by the LLM.
        """
        tools = available_tools or self._get_tools()
        # 包含对话历史，让 LLM 能理解上下文（如 "要" 指代前文的操作建议）
        messages = self.conversation.get_messages()
        if messages:
            # 如果调用方传了 system_prompt，更新 messages[0]（覆盖之前 set_system_prompt 的版本）
            if system_prompt and messages[0]["role"] == "system":
                messages[0] = {"role": "system", "content": system_prompt}
        else:
            messages = [
                {"role": "system", "content": system_prompt or self._build_system_prompt()},
                {"role": "user", "content": user_prompt},
            ]
        result = await try_tool_call(
            self.config.api_base,
            self.config.api_key,
            self.config.model,
            messages,
            self.config.timeout_sec,
            tools=tools,
        )
        if result:
            return self._tool_call_to_action(result["name"], result["arguments"])
        return None

    async def _request_react_action(
        self,
        *,
        available_tools: list[dict[str, Any]] | None = None,
    ) -> Any:
        """In-loop tool-calling: reads from self.conversation, handles fallback.

        If tool calling fails, falls back to text completion + JSON extraction.
        If JSON extraction also fails, returns a fallback done action.
        """
        tools = available_tools or self._get_tools()

        async def _do() -> Any:
            messages = self.conversation.get_messages()
            if not messages:
                raise ValueError("Conversation 为空")
            result = await try_tool_call(
                self.config.api_base,
                self.config.api_key,
                self.config.model,
                messages,
                self.config.timeout_sec,
                tools=tools,
            )
            if result:
                action = self._tool_call_to_action(result["name"], result["arguments"])
                if action is not None:
                    return action
            raw = await request_text_from_messages(
                self.config.api_base,
                self.config.api_key,
                self.config.model,
                messages,
                self.config.timeout_sec,
            )
            data = extract_json(raw)
            if not data:
                logger.warning(
                    "LLM 返回非 JSON 响应，回退为 done: %.200s", raw,
                )
                return self._build_fallback_done_action(raw)
            try:
                return self._dict_to_action(data)
            except (ValueError, ValidationError, TypeError) as e:
                logger.warning("Failed to parse LLM action: %s, data=%.200s", e, str(data))
                return self._build_fallback_done_action(raw)

        return await retry_async(
            _do, max_retries=2, base_delay=1.0,
            retryable_exceptions=(ValueError,),
        )

    def _build_fallback_done_action(self, raw: str) -> Any:
        """Subclasses MAY override to create a task_done action from raw text.

        Default returns None — subclasses should override to return their
        equivalent of ReActDone.
        """
        return None

    # ── Streaming ──

    async def stream_reply(self, user_prompt: str) -> AsyncGenerator[str, None]:
        """Stream a text-only reply (chat mode) from the LLM."""
        messages = self.conversation.get_messages()
        if not messages:
            messages = [{"role": "user", "content": user_prompt}]
        async for chunk in request_text_stream(
            self.config.api_base,
            self.config.api_key,
            self.config.model,
            messages,
            self.config.timeout_sec,
        ):
            yield chunk

    # ── AgentHandle implementation ──

    async def get_capabilities(self) -> list[AgentCapability]:
        """Subclasses override to advertise capabilities."""
        return []

    async def get_tools(self) -> list[dict[str, Any]]:
        return self._get_tools()

    async def execute(
        self, task: str, context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Default: single JSON call. Subclasses override for multi-stage."""
        prompt = self._build_system_prompt()
        result = await self._request_json(prompt, task)
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return result

    async def stream_execute(
        self, task: str, context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Default: stream a text reply."""
        async for chunk in self.stream_reply(task):
            yield chunk

    async def cancel(self) -> None:
        self._status = AgentStatus.IDLE

    async def shutdown(self) -> None:
        self._status = AgentStatus.OFFLINE
        self.conversation.clear()

    # ── Static utilities ──

    @staticmethod
    def extract_think(text: str) -> str:
        return extract_think(text)
