"""Echo 记忆 — 提问档案记录 + 用户画像维护。

- 提问档案：每条用户消息实时记录（原文 + bigram 关键词），是报告的数据源
- 用户画像：对话关闭时，LLM 增量更新 `memory_entries` 中 type=user_profile 的画像条目
"""

from __future__ import annotations

import logging
import re
from typing import Any

from aios.embedding import EmbeddingClient
from aios.llm import request_text_from_messages
from aios.memory import MemoryEntry, MemoryManager
from app.database import (
    list_memory_entries,
    update_memory_entry,
)
from app.settings import load_runtime_settings

from aios.echo.db import add_question_log

logger = logging.getLogger(__name__)

_CJK = r"一-鿿"

memory_manager = MemoryManager()


def extract_keywords(text: str) -> str:
    """中英文混合关键词：英文按词、中文按字符 bigram，空格分隔。"""
    kws: set[str] = set()
    for token in re.split(r"\s+", text.lower()):
        token = token.strip()
        if not token:
            continue
        if re.fullmatch(rf"[{_CJK}]+", token):
            chars = list(token)
            if len(chars) == 1:
                kws.add(chars[0])
            else:
                for i in range(len(chars) - 1):
                    kws.add(chars[i] + chars[i + 1])
        else:
            kws.add(token)
    return " ".join(sorted(kws))[:200]


async def log_question(conv_id: int | None, question: str) -> None:
    """实时记录用户提问（供报告与"了解用户提问"使用）。"""
    try:
        kw = extract_keywords(question)
        await add_question_log(question[:500], kw, conv_id)
    except Exception as exc:
        logger.warning("记录提问失败: %s", exc)


async def get_user_profile() -> str:
    """返回最新用户画像内容（无则空串）。"""
    try:
        entries = await list_memory_entries(limit=500)
        profiles = [e for e in entries if e.get("type") == "user_profile"]
        if profiles:
            return profiles[0].get("content", "")
    except Exception as exc:
        logger.warning("读取用户画像失败: %s", exc)
    return ""


async def update_user_profile(conv_id: int, messages: list[dict]) -> None:
    """对话关闭时，LLM 结合现有画像 + 本次对话，增量更新用户画像。"""
    if not messages:
        return
    current = await get_user_profile()
    conv_text = "\n".join(
        f"[{m['role']}]: {m['content'][:300]}" for m in messages[-30:]
    )
    settings = await load_runtime_settings()
    prompt = (
        "你是用户画像维护者。下面是用户当前画像与最近一段对话，"
        "请产出**更新后**的用户画像（一段 100-200 字的中文文字），"
        "提炼用户背景、偏好、习惯、关注点。不要复述对话细节，只保留稳定的画像特征。"
        "只输出画像正文，不要任何前缀/后缀/标题。\n\n"
        f"【当前画像】\n{current or '（暂无）'}\n\n"
        f"【最近对话】\n{conv_text}"
    )
    try:
        raw = await request_text_from_messages(
            settings.get("api_base", "https://api.deepseek.com"),
            settings.get("api_key", ""),
            settings.get("aux_model", "deepseek-chat"),
            [
                {"role": "system", "content": "你是一个严谨的用户画像维护助手。"},
                {"role": "user", "content": prompt},
            ],
            timeout_sec=60,
        )
        new_profile = raw.strip()[:1000]
        if not new_profile:
            return

        # 计算新画像向量
        vector = None
        try:
            emb = await _build_emb(settings)
            vec = await emb.embed(new_profile)
            vector = EmbeddingClient.encode_vector(vec)
        except Exception as exc:
            logger.warning("画像向量计算失败: %s", exc)

        # upsert：有则更新，无则新增
        entries = await list_memory_entries(limit=500)
        existing = [e for e in entries if e.get("type") == "user_profile"]
        if existing:
            await update_memory_entry(
                existing[0]["id"], content=new_profile, vector=vector,
            )
        else:
            await memory_manager.add(MemoryEntry(
                type="user_profile", key="用户画像", content=new_profile,
                importance=5,
            ))
        logger.info("用户画像已更新（conv_id=%s）", conv_id)
    except Exception as exc:
        logger.warning("更新用户画像失败: %s", exc)


async def _build_emb(settings: dict) -> EmbeddingClient:
    return EmbeddingClient(
        api_base="https://dashscope.aliyuncs.com/compatible-mode",
        api_key=settings.get("dashscope_api_key", ""),
        model=settings.get("dashscope_embed_model", "qwen3.7-text-embedding"),
    )


async def recent_questions(limit: int = 5) -> list[dict[str, Any]]:
    """最近的提问列表，注入 system prompt。"""
    from aios.echo.db import list_question_log

    try:
        return await list_question_log(limit=limit)
    except Exception as exc:
        logger.warning("读取提问档案失败: %s", exc)
        return []
