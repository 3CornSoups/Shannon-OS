"""Echo API 路由 — 会话 / 聊天 / 报告。

聊天走 SSE：POST /api/echo/chat 返回 task_id，前端连 /api/stream/{task_id} 收流。
事件格式复用现有（raw_content / done / error）。
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.database import (
    delete_memory_entry,
    get_memory_entry,
    list_memory_entries,
    update_memory_entry,
)
from app.events import event_store

from aios.echo.agent import echo_agent
from aios.echo.consolidator import consolidate_memories
from aios.echo.db import (
    add_message,
    create_conversation,
    delete_conversation,
    delete_report,
    get_conversation,
    get_messages,
    get_report,
    list_conversations,
    list_reports,
    rename_conversation,
)
from aios.echo.memory import get_user_profile, log_question, update_user_profile
from aios.echo.report import ensure_daily_digest, generate_daily_digest, generate_topic_report
from aios.embedding import EmbeddingClient
from aios.memory import MemoryEntry, MemoryManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["echo"])

# 会话级"待提取"计数：每 _EXTRACT_INTERVAL 轮触发一次实时记忆沉淀（内存态，重启归零）
_EXTRACT_INTERVAL = 5
_pending_extract_counts: dict[int, int] = {}


# ── 请求模型 ──

class EchoChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    message: str


class TopicRequest(BaseModel):
    topic: str


class RenameRequest(BaseModel):
    title: str


class MemoryCreateRequest(BaseModel):
    type: str
    content: str
    importance: int = 3


class MemoryUpdateRequest(BaseModel):
    content: str | None = None
    importance: int | None = None
    type: str | None = None


# ── 会话 ──

@router.post("/echo/conversations")
async def api_echo_create_conversation() -> dict:
    conv_id = await create_conversation()
    return {"ok": True, "conversation_id": conv_id, "title": "新对话"}


@router.get("/echo/conversations")
async def api_echo_list_conversations() -> dict:
    return {"conversations": await list_conversations()}


@router.get("/echo/conversations/{conv_id}/messages")
async def api_echo_get_messages(conv_id: int) -> dict:
    conv = await get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"conversation": conv, "messages": await get_messages(conv_id, limit=200)}


@router.post("/echo/conversations/{conv_id}/rename")
async def api_echo_rename_conversation(conv_id: int, payload: RenameRequest) -> dict:
    ok = await rename_conversation(conv_id, payload.title.strip() or "新对话")
    return {"ok": ok}


@router.post("/echo/conversations/{conv_id}/close")
async def api_echo_close_conversation(conv_id: int) -> dict:
    """对话关闭：异步更新用户画像 + 补当日小结。"""
    messages = await get_messages(conv_id, limit=200)
    asyncio.create_task(_finalize_conversation(conv_id, messages))
    return {"ok": True, "message": "已安排记忆整理"}


@router.delete("/echo/conversations/{conv_id}")
async def api_echo_delete_conversation(conv_id: int) -> dict:
    ok = await delete_conversation(conv_id)
    return {"ok": ok}


# ── 聊天 ──

@router.post("/echo/chat")
async def api_echo_chat(payload: EchoChatRequest) -> dict:
    message = (payload.message or "").strip()
    if not message:
        return {"ok": False, "message": "消息不能为空"}

    conv_id = payload.conversation_id
    if conv_id is None:
        conv_id = await create_conversation()
    else:
        conv = await get_conversation(conv_id)
        if not conv:
            raise HTTPException(status_code=404, detail="会话不存在")

    # 先落库用户消息 + 记提问档案，再后台生成回复
    await add_message(conv_id, "user", message)
    await log_question(conv_id, message)

    task_id = str(uuid.uuid4())
    asyncio.create_task(_run_echo_chat(task_id, conv_id, message))
    return {"ok": True, "task_id": task_id, "conversation_id": conv_id}


async def _run_echo_chat(task_id: str, conv_id: int, message: str) -> None:
    """后台：检索增强生成回复 → 流式推 SSE → 落库 → done。"""
    try:
        await event_store.emit(task_id, {"type": "status", "message": "正在回忆与思考..."})
        full = ""
        async for chunk in echo_agent.stream_chat(conv_id, message):
            full += chunk
            await event_store.emit(task_id, {"type": "raw_content", "content": chunk})

        full = full.strip()
        await add_message(conv_id, "assistant", full or "（未生成回复）")
        await _maybe_auto_title(conv_id, message)
        # 实时记忆沉淀：每 _EXTRACT_INTERVAL 轮触发一次（异步执行，不阻塞 SSE）
        count = _pending_extract_counts.get(conv_id, 0) + 1
        _pending_extract_counts[conv_id] = count
        if count % _EXTRACT_INTERVAL == 0:
            from aios.echo.extractor import extract_and_store_memories
            recent = await get_messages(conv_id, limit=20)
            asyncio.create_task(extract_and_store_memories(conv_id, recent))
        await event_store.emit(task_id, {
            "type": "done", "message": full, "conversation_id": conv_id,
        })
    except Exception as exc:
        logger.exception("Echo 聊天失败 conv_id=%s", conv_id)
        await event_store.emit(task_id, {"type": "error", "message": f"出错了: {exc}"})


async def _maybe_auto_title(conv_id: int, first_message: str) -> None:
    """新会话首次对话后，用首条消息生成标题。"""
    try:
        conv = await get_conversation(conv_id)
        if conv and conv.get("title", "新对话") == "新对话":
            title = first_message.strip().replace("\n", " ")[:20]
            await rename_conversation(conv_id, title or "新对话")
    except Exception as exc:
        logger.debug("自动标题失败: %s", exc)


async def _finalize_conversation(conv_id: int, messages: list[dict]) -> None:
    """对话关闭收尾：更新画像 + 补当日小结。"""
    try:
        await update_user_profile(conv_id, messages)
        await ensure_daily_digest()
    except Exception as exc:
        logger.warning("对话收尾失败 conv_id=%s: %s", conv_id, exc)


# ── 报告 ──

@router.post("/echo/reports/generate")
async def api_echo_generate_topic_report(payload: TopicRequest) -> dict:
    report = await generate_topic_report(payload.topic.strip())
    return report


@router.post("/echo/reports/daily")
async def api_echo_generate_daily() -> dict:
    report = await generate_daily_digest()
    return report


@router.get("/echo/reports")
async def api_echo_list_reports() -> dict:
    return {"reports": await list_reports()}


@router.get("/echo/reports/{report_id}")
async def api_echo_get_report(report_id: int) -> dict:
    report = await get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return report


@router.delete("/echo/reports/{report_id}")
async def api_echo_delete_report(report_id: int) -> dict:
    ok = await delete_report(report_id)
    return {"ok": ok}


# ── 记忆库 API ──

_MEMORY_TYPES = ("preference", "fact", "decision", "server_info")


@router.get("/echo/memory")
async def api_echo_list_memory(
    type: str | None = None,
    importance: int | None = None,
    consolidated: int | None = None,
    limit: int = Query(default=200, le=500),
) -> dict:
    entries = await list_memory_entries(
        limit=limit, entry_type=type, importance=importance, consolidated=consolidated
    )
    return {"memories": entries, "total": len(entries)}


@router.get("/echo/memory/search")
async def api_echo_search_memory(q: str = Query(default="", min_length=1)) -> dict:
    if not q.strip():
        return {"memories": []}
    manager = MemoryManager()
    hits = await manager.search(q, top_k=10)
    return {"memories": hits}


@router.post("/echo/memory")
async def api_echo_create_memory(payload: MemoryCreateRequest) -> dict:
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="内容不能为空")
    if payload.type not in _MEMORY_TYPES:
        raise HTTPException(status_code=400, detail="type 不合法")
    entry_id = await MemoryManager().add(
        MemoryEntry(
            type=payload.type,
            key=content[:40],
            content=content,
            importance=max(1, min(5, payload.importance)),
        )
    )
    return {"ok": True, "id": entry_id}


@router.put("/echo/memory/{memory_id}")
async def api_echo_update_memory(memory_id: int, payload: MemoryUpdateRequest) -> dict:
    entry = await get_memory_entry(memory_id)
    if not entry:
        raise HTTPException(status_code=404, detail="记忆不存在")
    new_content = (payload.content or entry.get("content", "")).strip()
    new_imp = entry.get("importance", 3)
    if payload.importance is not None:
        new_imp = max(1, min(5, payload.importance))
    vector_str = None
    try:
        emb = EmbeddingClient()
        vec = emb.encode_vector(await emb.embed(new_content))
        vector_str = json.dumps(vec)
    except Exception as exc:
        logger.warning("记忆更新 embedding 失败: %s", exc)
    await update_memory_entry(
        memory_id,
        content=new_content,
        importance=new_imp,
        vector=vector_str,
    )
    return {"ok": True}


@router.delete("/echo/memory/{memory_id}")
async def api_echo_delete_memory(memory_id: int) -> dict:
    ok = await delete_memory_entry(memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {"ok": True}


@router.post("/echo/memory/consolidate")
async def api_echo_consolidate_memory() -> dict:
    result = await consolidate_memories()
    return {"ok": True, **result}


@router.get("/echo/memory/profile")
async def api_echo_memory_profile() -> dict:
    profile = await get_user_profile()
    return {"profile": profile}
