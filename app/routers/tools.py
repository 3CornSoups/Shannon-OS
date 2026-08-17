"""工具面板 API — 大工具检测 + REPL 会话管理"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.connection import pool
from app.database import get_host_context
from app.executor import ExecutorRouter, TargetHost
from app.delegate.executor import detect_available_agents
from app.repl_sessions import (
    create_session,
    send_input,
    send_key,
    subscribe_output,
    unsubscribe_output,
    close_session,
    get_session_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])

# 大工具展示元数据（复用 SubAgent 的 detect 机制）
BIG_TOOL_CATALOG: dict[str, dict] = {
    "claude_code": {
        "display_name": "Claude Code",
        "description": "Anthropic CLI 编程智能体，擅长代码重构、多文件编辑、架构分析与评估",
        "icon": "brain",
        "capability_tags": ["code", "refactor", "multi-file", "architecture", "git"],
    },
    # === REMOVABLE_START ===
    "openclaw": {"display_name": "OpenClaw", "description": "开源的 Claude Code 替代 CLI 编程智能体", "icon": "tool", "capability_tags": ["code", "refactor", "multi-file"]},
    "codex": {"display_name": "OpenAI Codex", "description": "OpenAI Codex CLI——终端 AI 编程助手", "icon": "tool", "capability_tags": ["code", "refactor", "openai"]},
    "manus": {"display_name": "Manus", "description": "Manus Agent CLI——自主任务执行智能体", "icon": "tool", "capability_tags": ["code", "agent", "autonomous"]},
    "hermes": {"display_name": "Hermes", "description": "Hermes CLI——AI 助手命令行工具", "icon": "tool", "capability_tags": ["code", "assistant"]},
    # === REMOVABLE_END ===
}


class ToolSessionRequest(BaseModel):
    host_id: int
    password: str | None = None
    private_key: str | None = None


class ToolSendRequest(BaseModel):
    message: str


async def _build_target_async(host_id: int, password: str | None = None, private_key: str | None = None) -> TargetHost:
    """从数据库异步构建 TargetHost"""
    ctx = await get_host_context(host_id, decrypt_pwd=True)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"主机 {host_id} 未找到")

    return TargetHost(
        host_id=host_id,
        name=ctx.get("name", "Unknown"),
        host=ctx.get("host", ""),
        port=ctx.get("port", 22),
        username=ctx.get("username", ""),
        password=password or ctx.get("last_pwd", ""),
        private_key=private_key or "",
    )


@router.get("/list")
async def api_list_tools(host_id: int) -> dict[str, Any]:
    """探测远程服务器上的可用大工具"""
    try:
        target = await _build_target_async(host_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"获取主机信息失败: {exc}")

    executor = ExecutorRouter.create_executor(target)
    agents = await detect_available_agents(executor)

    tools = []
    for agent in agents:
        meta = BIG_TOOL_CATALOG.get(agent.name, {})
        tools.append({
            "name": agent.name,
            "display_name": meta.get("display_name", agent.display_name),
            "description": meta.get("description", agent.description),
            "icon": meta.get("icon", "tool"),
            "capability_tags": meta.get("capability_tags", agent.capability_tags),
            "available": True,
        })

    # 标记已注册但未安装的工具
    for name, meta in BIG_TOOL_CATALOG.items():
        if not any(t["name"] == name for t in tools):
            tools.append({
                "name": name,
                "display_name": meta["display_name"],
                "description": meta["description"],
                "icon": meta.get("icon", "tool"),
                "capability_tags": meta.get("capability_tags", []),
                "available": False,
            })

    return {
        "tools": tools,
        "host_name": target.name,
        "host_id": host_id,
    }


@router.post("/{tool_name}/sessions")
async def api_create_session(tool_name: str, payload: ToolSessionRequest) -> dict[str, Any]:
    """启动 REPL 会话"""
    target = await _build_target_async(
        payload.host_id,
        password=payload.password,
        private_key=payload.private_key,
    )

    # 获取 SSH 连接
    try:
        conn_entry = await pool.get_connection(
            host=target.host,
            port=target.port,
            username=target.username,
            password=target.password,
            private_key=target.private_key,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"SSH 连接失败: {exc}")

    if conn_entry.use_paramiko:
        raise HTTPException(status_code=400, detail="paramiko 连接不支持交互式会话")

    try:
        # 注：hosts 表无 cwd 列（历史遗留的 DB 回退逻辑已移除），会话从当前目录开始
        session_id = await create_session(
            tool_name=tool_name,
            conn_entry=conn_entry,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"创建会话失败: {exc}")

    return {
        "session_id": session_id,
        "tool_name": tool_name,
        "status": "active",
    }


@router.post("/sessions/{session_id}/send")
async def api_send_message(session_id: str, payload: ToolSendRequest) -> dict[str, Any]:
    """向 REPL 会话发送消息"""
    try:
        await send_input(session_id, payload.message)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("发送消息失败")
        raise HTTPException(status_code=500, detail=f"发送失败: {exc}")

    return {"session_id": session_id, "status": "sent"}


class ToolKeyRequest(BaseModel):
    key: str  # up, down, left, right, enter, escape, tab


@router.post("/sessions/{session_id}/key")
async def api_send_key(session_id: str, payload: ToolKeyRequest) -> dict[str, Any]:
    """向 REPL 会话发送特殊按键（方向键、Enter 等）"""
    try:
        await send_key(session_id, payload.key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("发送按键失败")
        raise HTTPException(status_code=500, detail=f"发送失败: {exc}")

    return {"session_id": session_id, "key": payload.key, "status": "sent"}


@router.get("/sessions/{session_id}/stream")
async def api_stream_output(session_id: str) -> StreamingResponse:
    """SSE 流式输出 REPL 会话的 stdout/stderr"""
    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()
        count = await subscribe_output(session_id, queue)
        if count < 0:
            # 会话不存在——直接关闭 SSE
            yield f"data: {json.dumps({'type': 'session_error', 'message': '会话不存在或已关闭'}, ensure_ascii=False)}\n\n"
            return

        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    if data.get("type") in ("session_closed", "session_error"):
                        break
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            await unsubscribe_output(session_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.delete("/sessions/{session_id}")
async def api_close_session(session_id: str) -> dict[str, Any]:
    """关闭 REPL 会话"""
    ok = await close_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在或已关闭")
    return {"session_id": session_id, "status": "closed"}


@router.get("/sessions/{session_id}/status")
async def api_session_status(session_id: str) -> dict[str, Any]:
    """查询 REPL 会话状态"""
    status = await get_session_status(session_id)
    if not status:
        raise HTTPException(status_code=404, detail="会话不存在")
    return status


@router.websocket("/sessions/{session_id}/ws")
async def ws_terminal(websocket: WebSocket, session_id: str):
    """xterm.js 终端 WebSocket — 原始 PTY 字节直通"""
    from app.repl_sessions import _active_sessions

    session = _active_sessions.get(session_id)
    if not session or session.closed:
        await websocket.close(code=4004, reason="会话不存在或已关闭")
        return

    await websocket.accept()

    # 注册 WebSocket 客户端
    async with session._ws_lock:
        session.ws_clients.append(websocket)

    try:
        while not session.closed:
            data = await websocket.receive()
            if data["type"] == "websocket.receive":
                text = data.get("text")
                if text is not None:
                    await _write_stdin(session, text)
            elif data["type"] == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket 终端异常")
    finally:
        async with session._ws_lock:
            if websocket in session.ws_clients:
                session.ws_clients.remove(websocket)


async def _write_stdin(session, data: str | bytes) -> None:
    """写入 stdin（文本模式）"""
    if session.closed:
        return
    try:
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        session.process.stdin.write(data)
    except OSError:
        session.closed = True
