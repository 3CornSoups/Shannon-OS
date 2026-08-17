"""委托上下文构建器 — 生成结构化的委托 prompt 和对话摘要"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.executor import BaseExecutor


async def build_conversation_summary(
    api_base: str,
    api_key: str,
    model: str,
    messages: list[dict],
    timeout_sec: int = 30,
) -> str:
    """使用 LLM 生成对话历史摘要"""
    from app.llm_client import request_text

    if not messages:
        return "无历史对话"

    history_text = "\n".join(
        f"[{m['role']}]: {str(m.get('content', ''))[:500]}" for m in messages[-10:]
    )

    system_prompt = "你是对话摘要助手。请用 2-3 句话概括以下对话的核心内容，聚焦于用户的需求和任务进展。"
    try:
        summary = await request_text(
            api_base, api_key, model, system_prompt, history_text, timeout_sec
        )
        return summary.strip() or "对话历史摘要生成失败"
    except Exception:
        # 降级：取最近 3 轮对话原文
        recent = messages[-6:] if len(messages) > 6 else messages
        return "\n".join(
            f"[{m['role']}]: {str(m.get('content', ''))[:300]}" for m in recent
        )


async def probe_remote_environment(executor: "BaseExecutor") -> dict[str, str | None]:
    """探测远程服务器环境信息"""
    try:
        return await executor.probe_environment()
    except Exception:
        return {}


def build_delegation_context(
    user_input: str,
    host_info: dict[str, str | None],
    work_dir: str | None,
    conversation_summary: str,
    task_id: str,
    risk_level: str,
) -> dict:
    """构建委托上下文字典"""
    return {
        "user_input": user_input,
        "host_info": host_info,
        "work_dir": work_dir,
        "conversation_summary": conversation_summary,
        "task_id": task_id,
        "risk_level": risk_level,
    }
