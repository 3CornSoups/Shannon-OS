"""REPL 会话管理器 — 持久化交互式 SSH 进程管理

绕过 executor 层直接使用 asyncssh，保持 stdin 开放以支持双向通信。
"""

from __future__ import annotations

import asyncio
import logging
import re
import shlex
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import asyncssh

from app.connection import pool, ConnectionEntry
from app.events import event_store

logger = logging.getLogger(__name__)

# ── ANSI / 控制字符清洗 ──
_ANSI_CSI_RE = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]')
_ANSI_OSC_RE = re.compile(r'\x1b\][^\x07]*\x07')
_ANSI_OTHER_RE = re.compile(r'\x1b[PX^_][^\x1b]*\x1b\\\\')
_CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1a\x1c-\x1f]')


def _clean_line(line: str) -> str:
    """移除 ANSI 转义序列、spinner 覆写（\\r）、控制字符"""
    line = _ANSI_CSI_RE.sub('', line)
    line = _ANSI_OSC_RE.sub('', line)
    line = _ANSI_OTHER_RE.sub('', line)
    if '\r' in line:
        parts = [p for p in line.split('\r') if p.strip()]
        line = parts[-1] if parts else ''
    line = _CONTROL_CHARS_RE.sub('', line)
    return line


def _clean_for_display(line: str) -> str:
    """保留 ANSI 颜色，仅处理 \\r 覆写和控制字符（用于终端展示）"""
    if '\r' in line:
        parts = [p for p in line.split('\r') if p.strip()]
        line = parts[-1] if parts else ''
    line = _CONTROL_CHARS_RE.sub('', line)
    return line


# 空闲超时（秒）— 会话无输入/输出则自动关闭
IDLE_TIMEOUT_SEC = 600
# 心跳间隔（秒）— 防止连接池逐出空闲连接
HEARTBEAT_INTERVAL_SEC = 30
# 输出缓冲区最大行数
MAX_OUTPUT_BUFFER = 1000

async def _extract_answer(raw_output: str, session_id: str) -> str | None:
    """调用 LLM 从 Claude Code TUI 输出中提取有效回复"""
    if not raw_output.strip():
        return None
    try:
        from app.settings import load_runtime_settings
        from app.llm_client import request_text

        settings = await load_runtime_settings()
        system_prompt = (
            "你是输出提取助手。从 Claude Code 的终端输出中提取实际回复内容。"
            "忽略：ANSI 转义序列、进度动画、spinner、状态栏、分隔线、光标控制。"
            "只提取：Claude Code 对用户的实际回复文本。"
            "保留原始语言，不要改写。如果没有有效回复，回复空字符串。"
        )
        user_prompt = f"## Claude Code 原始终端输出\n{raw_output[:4000]}\n\n请提取实际回复："

        result = await request_text(
            settings.get("api_base", "https://api.deepseek.com"),
            settings.get("api_key", ""),
            settings.get("api_model", "deepseek-chat"),
            system_prompt,
            user_prompt,
            timeout_sec=15,
        )
        answer = result.strip()
        return answer if answer else None
    except Exception as exc:
        logger.warning(f"LLM 提取答案失败: {exc}")
        return None

# 全局会话注册表
_active_sessions: dict[str, "ReplSession"] = {}

# 支持的工具命令映射
BIG_TOOL_COMMANDS: dict[str, str] = {
    "claude_code": "claude",
    # === REMOVABLE_START ===
    "openclaw": "openclaw",
    "codex": "codex",
    "manus": "manus",
    "hermes": "hermes",
    # === REMOVABLE_END ===
}


@dataclass
class ReplSession:
    session_id: str
    tool_name: str
    host: str
    process: asyncssh.SSHClientProcess
    conn_entry: ConnectionEntry
    output_queues: list[asyncio.Queue] = field(default_factory=list)
    _queues_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    ws_clients: list = field(default_factory=list)
    _ws_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    reader_task: asyncio.Task | None = None
    heartbeat_task: asyncio.Task | None = None
    created_at: float = 0.0
    last_activity: float = 0.0
    closed: bool = False
    turn_buffer: list[str] = field(default_factory=list)
    extract_task: asyncio.Task | None = None


def _format_output_event(line: str, is_stderr: bool = False) -> dict:
    return {"type": "tool_output", "line": line, "is_stderr": is_stderr}


async def create_session(
    tool_name: str,
    conn_entry: ConnectionEntry,
    work_dir: str | None = None,
) -> str:
    """创建持久化 REPL 会话，返回 session_id"""
    if tool_name not in BIG_TOOL_COMMANDS:
        raise ValueError(f"未知工具: {tool_name}")

    command = BIG_TOOL_COMMANDS[tool_name]
    if work_dir:
        command = f"cd {work_dir} && {command}"
    # 直接运行，不加 PTY：异步读取 stdout + 通过 stdin 写入输入

    session_id = str(uuid.uuid4())
    now = time.time()

    # PTY 模式
    process = await conn_entry.conn.create_process(
        command,
        term_type="xterm-256color",
        encoding="utf-8",
    )
    # 不调用 write_eof()——stdin 保持开放

    session = ReplSession(
        session_id=session_id,
        tool_name=tool_name,
        host=f"{conn_entry.conn.get_extra_info('host', 'unknown')}",
        process=process,
        conn_entry=conn_entry,
        created_at=now,
        last_activity=now,
    )

    # 启动后台读取任务
    session.reader_task = asyncio.create_task(
        _read_output(session, process), name=f"repl-read-{session_id[:8]}"
    )
    # 启动心跳任务
    session.heartbeat_task = asyncio.create_task(
        _heartbeat(session), name=f"repl-beat-{session_id[:8]}"
    )

    _active_sessions[session_id] = session
    logger.info(f"REPL 会话已创建: {tool_name} -> {session_id[:8]}")

    # 向所有订阅者发送会话开始事件
    await _broadcast(session,{"type": "session_started", "tool": tool_name})

    return session_id


# 特殊按键映射
SPECIAL_KEYS: dict[str, str] = {
    "up": "\x1b[A",
    "down": "\x1b[B",
    "left": "\x1b[D",
    "right": "\x1b[C",
    "enter": "\r",
    "escape": "\x1b",
    "tab": "\t",
}


async def _write_stdin(session: ReplSession, data: str | bytes) -> None:
    """写入 stdin（适配 binary/text 模式）"""
    if session.closed:
        raise ValueError("会话已关闭")
    try:
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        session.process.stdin.write(data)
    except OSError as exc:
        session.closed = True
        logger.warning(f"写入 REPL stdin 失败: {exc}")
        raise ValueError(f"进程已断开: {exc}")


async def send_key(session_id: str, key: str) -> None:
    """发送特殊按键（方向键、Enter、Esc 等）"""
    session = _active_sessions.get(session_id)
    if not session:
        raise ValueError(f"会话不存在: {session_id}")

    sequence = SPECIAL_KEYS.get(key)
    if not sequence:
        raise ValueError(f"未知按键: {key}，支持: {', '.join(SPECIAL_KEYS)}")

    session.last_activity = time.time()
    logger.info(f"REPL 发送按键: {key} -> {sequence!r}")
    await _write_stdin(session, sequence)


async def send_input(session_id: str, text: str) -> None:
    """向 REPL 进程发送输入"""
    session = _active_sessions.get(session_id)
    if not session:
        raise ValueError(f"会话不存在: {session_id}")

    session.last_activity = time.time()
    await _write_stdin(session, text + "\r")

    # 推送用户消息到事件流（前端回显）
    await _broadcast(session,{"type": "user_message", "content": text})


async def subscribe_output(session_id: str, queue: asyncio.Queue) -> int:
    """订阅会话输出流，返回已缓冲的事件数"""
    session = _active_sessions.get(session_id)
    if not session:
        return -1
    async with session._queues_lock:
        session.output_queues.append(queue)
    return 0


async def unsubscribe_output(session_id: str, queue: asyncio.Queue) -> None:
    """取消订阅"""
    session = _active_sessions.get(session_id)
    if session:
        async with session._queues_lock:
            if queue in session.output_queues:
                session.output_queues.remove(queue)


async def close_session(session_id: str) -> bool:
    """关闭 REPL 会话并清理资源"""
    session = _active_sessions.get(session_id)
    if not session or session.closed:
        return False

    session.closed = True
    logger.info(f"关闭 REPL 会话: {session_id[:8]}")

    # 关闭所有 WebSocket 连接
    async with session._ws_lock:
        for ws in session.ws_clients:
            try:
                await ws.close(code=1000)
            except Exception:
                pass
        session.ws_clients.clear()

    # 发送 EOF 给进程
    try:
        session.process.stdin.write_eof()
    except Exception:
        pass

    # 等待进程退出（最多 5s）
    try:
        await asyncio.wait_for(session.process.wait(), timeout=5)
    except asyncio.TimeoutError:
        session.process.close()

    # 取消后台任务
    for task in (session.reader_task, session.heartbeat_task):
        if task and not task.done():
            task.cancel()

    # 通知订阅者
    exit_code = session.process.exit_status if session.process.exit_status is not None else -1
    await _broadcast(session,{"type": "session_closed", "exit_code": exit_code})

    # 清理队列
    session.output_queues.clear()
    del _active_sessions[session_id]

    return True


async def get_session_status(session_id: str) -> dict | None:
    """查询会话状态"""
    session = _active_sessions.get(session_id)
    if not session:
        return None
    return {
        "session_id": session.session_id,
        "tool_name": session.tool_name,
        "host": session.host,
        "status": "closed" if session.closed else "active",
        "created_at": session.created_at,
        "last_activity": session.last_activity,
    }


async def close_all_sessions() -> None:
    """关闭所有活跃会话（服务关闭时调用）"""
    for sid in list(_active_sessions.keys()):
        try:
            await close_session(sid)
        except Exception as exc:
            logger.warning(f"关闭会话 {sid[:8]} 失败: {exc}")


# ── 内部函数 ──


async def _broadcast(session: ReplSession, event: dict) -> None:
    """向所有订阅队列广播事件（异步锁保护）"""
    dead_queues = []
    async with session._queues_lock:
        for q in session.output_queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass
            except Exception:
                dead_queues.append(q)
        for q in dead_queues:
            try:
                session.output_queues.remove(q)
            except ValueError:
                pass


async def _maybe_extract(session: ReplSession):
    """检测到 ❯ 提示符时，用 LLM 从累积输出中提取有效回复"""
    if not session.turn_buffer:
        return
    # 限制缓冲区大小防止无限增长
    if len(session.turn_buffer) > 500:
        session.turn_buffer = session.turn_buffer[-300:]
    raw = "\n".join(session.turn_buffer)
    parts = raw.split("❯")
    if len(parts) >= 2:
        latest = parts[-2].strip()
    else:
        latest = raw.strip()
    if len(latest) < 3:
        return

    extracted = await _extract_answer(latest, session.session_id)
    if extracted:
        await _broadcast(session, {"type": "tool_answer", "content": extracted})
    session.turn_buffer.clear()


async def _read_output(session: ReplSession, process: asyncssh.SSHClientProcess) -> None:
    """持续读取 stdout/stderr：原始行 → WebSocket 二进制帧 + SSE 广播 + ❯ 检测"""

    async def _read_stream(reader, tag):
        stopped = False
        try:
            async for line in reader:
                if session.closed:
                    break

                # 解码（文本模式 asyncssh 已做，兜底处理 bytes）
                if isinstance(line, bytes):
                    line = line.decode("utf-8", errors="replace")

                # ── 直通 WebSocket（二进制帧，保留 ESC）──
                raw_bytes = line.encode("utf-8", errors="replace")
                async with session._ws_lock:
                    dead = []
                    for ws in session.ws_clients:
                        try:
                            await ws.send_bytes(raw_bytes)
                        except Exception:
                            dead.append(ws)
                    for ws in dead:
                        session.ws_clients.remove(ws)

                # ── SSE / LLM 提取 ──
                decoded = line.rstrip("\n\r")
                if not decoded:
                    continue
                session.last_activity = time.time()

                clean = _clean_line(decoded)
                session.turn_buffer.append(clean)

                await _broadcast(session, _format_output_event(decoded, is_stderr=(tag == "stderr")))

                if "❯" in clean and tag == "stdout":
                    if session.extract_task and not session.extract_task.done():
                        session.extract_task.cancel()
                    session.extract_task = asyncio.create_task(_maybe_extract(session))

        except asyncio.CancelledError:
            pass
        except asyncssh.ProcessError as exc:
            stopped = True
            logger.warning(f"REPL 进程异常 ({tag}): {exc}")
            await _broadcast(session,{"type": "session_error", "message": f"进程错误: {exc}"})
        except Exception as exc:
            stopped = True
            logger.exception(f"读取 {tag} 流异常: {exc}")
            await _broadcast(session,{"type": "session_error", "message": f"读取异常: {exc}"})
        else:
            stopped = True
        finally:
            if stopped and not session.closed:
                exit_code = process.exit_status if process.exit_status is not None else -1
                await _broadcast(session,{"type": "session_closed", "exit_code": exit_code})
                session.closed = True

    try:
        await asyncio.gather(
            _read_stream(process.stdout, "stdout"),
            _read_stream(process.stderr, "stderr"),
        )
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("_read_output 致命异常")


async def _heartbeat(session: ReplSession) -> None:
    """定期更新连接池时间戳，防止空闲连接被逐出；检测空闲超时"""
    while not session.closed:
        try:
            await asyncio.sleep(HEARTBEAT_INTERVAL_SEC)
            if session.closed:
                break

            # 防止连接池逐出
            session.conn_entry.last_used = time.time()

            # 空闲超时检测
            idle = time.time() - session.last_activity
            if idle > IDLE_TIMEOUT_SEC:
                logger.info(f"REPL 会话 {session.session_id[:8]} 空闲超时 ({idle:.0f}s)")
                await close_session(session.session_id)
                break

        except asyncio.CancelledError:
            break
