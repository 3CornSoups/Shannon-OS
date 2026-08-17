"""EchoAgent — 检索增强的日常聊天 Agent。

运行时模式：每轮 1 次 LLM 调用。检索层（用户画像 + memory_entries + FTS5 原文
+ 近期提问）注入 system prompt，无 ReAct / 工具循环。模型用 aux_model。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from aios.agent_handle import AgentCapability, AgentHandle, AgentStatus
from aios.llm import request_text_stream
from aios.memory import MemoryManager
from app.settings import load_runtime_settings

from aios.echo.db import create_conversation, add_message, get_messages
from aios.echo import fts
from aios.echo.memory import get_user_profile, recent_questions
from aios.echo.prompts import build_system_prompt

logger = logging.getLogger(__name__)

memory_manager = MemoryManager()


class EchoAgent(AgentHandle):
    """面向日常聊天的门面 Agent。"""

    agent_id = "echo"
    display_name = "回声"

    def __init__(self) -> None:
        self._status = AgentStatus.IDLE
        self._capability_tags = ["interaction", "chat", "memory"]

    @property
    def status(self) -> AgentStatus:
        return self._status

    # ── 检索增强纯聊天 ──

    async def stream_chat(self, conv_id: int, user_message: str) -> AsyncGenerator[str, None]:
        """流式生成回复（不含工具循环）。调用前须已保存用户消息。"""
        context = await self._retrieve_context(user_message, exclude_conv_id=conv_id)
        messages = await self._build_messages(conv_id, user_message, context)
        settings = await load_runtime_settings()
        async for chunk in request_text_stream(
            settings.get("api_base", "https://api.deepseek.com"),
            settings.get("api_key", ""),
            settings.get("aux_model", "deepseek-chat"),
            messages,
            timeout_sec=90,
        ):
            yield chunk

    async def _retrieve_context(self, query: str, exclude_conv_id: int | None) -> dict[str, Any]:
        """并行检索记忆上下文。"""
        profile = await get_user_profile()
        try:
            memory_hits = await memory_manager.search(query, top_k=5)
            # 画像已单独注入，避免重复
            memory_hits = [h for h in memory_hits if h.get("type") != "user_profile"]
        except Exception as exc:
            logger.warning("记忆检索失败: %s", exc)
            memory_hits = []
        try:
            recall = await fts.search(query, top_k=5, exclude_conv_id=exclude_conv_id)
        except Exception as exc:
            logger.warning("对话全文检索失败: %s", exc)
            recall = []
        questions = await recent_questions(limit=5)
        return {
            "profile": profile,
            "memory_hits": memory_hits,
            "conversation_recall": recall,
            "recent_questions": questions,
        }

    async def _build_messages(
        self, conv_id: int, user_message: str, context: dict[str, Any],
    ) -> list[dict[str, str]]:
        system = build_system_prompt(context)
        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        history = await get_messages(conv_id, limit=20)
        for m in history:
            messages.append({"role": m["role"], "content": m["content"]})
        # 防御：若历史最后一条不是本次用户消息，补上（避免遗漏）
        if not history or history[-1].get("content") != user_message or history[-1].get("role") != "user":
            messages.append({"role": "user", "content": user_message})
        return messages

    # ── AgentHandle ──

    async def get_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(name="日常聊天", description="陪聊、答疑、跨会话记忆回找", tags=self._capability_tags),
        ]

    async def get_tools(self) -> list[dict[str, Any]]:
        return []

    async def execute(
        self, task: str, context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """非流式单轮回复（供未来 Dispatcher 调度）。"""
        conv_id = context.get("conversation_id") if context else None
        if conv_id is None:
            conv_id = await create_conversation()
        await add_message(conv_id, "user", task)
        chunks = [c async for c in self.stream_chat(conv_id, task)]
        reply = "".join(chunks)
        await add_message(conv_id, "assistant", reply)
        return {"reply": reply, "conversation_id": conv_id}

    async def stream_execute(
        self, task: str, context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str, None]:
        conv_id = context.get("conversation_id") if context else None
        if conv_id is None:
            conv_id = await create_conversation()
        await add_message(conv_id, "user", task)
        async for chunk in self.stream_chat(conv_id, task):
            yield chunk

    async def cancel(self) -> None:
        self._status = AgentStatus.IDLE

    async def shutdown(self) -> None:
        self._status = AgentStatus.OFFLINE


echo_agent = EchoAgent()
