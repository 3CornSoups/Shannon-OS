"""委托执行编排器 — 探测、执行、取消、冲突处理"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from app.delegate.base import DelegationContext, DelegateResult, SubAgent
from app.delegate.claude_code import ClaudeCodeSubAgent
from app.executor import BaseExecutor, ExecContext

if TYPE_CHECKING:
    from app.events import EventStore

logger = logging.getLogger(__name__)

class _GenericCLISubAgent(SubAgent):
    """通用 CLI 子智能体——通过构造参数区分不同工具"""

    def __init__(self, name, display_name, description, capability_tags, detect_cmd):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.capability_tags = capability_tags
        self._detect_cmd = detect_cmd

    @staticmethod
    async def detect(executor):
        return False  # 由工厂实例处理

    async def _detect(self, executor):
        try:
            result = await executor.run(self._detect_cmd, ExecContext(timeout_sec=10))
            return result.returncode == 0
        except Exception:
            return False

    async def execute(self, task, context, executor, on_output=None):
        raise NotImplementedError("通用 CLI 子智能体通过 REPL 会话使用，不走委托流程")

    async def cancel(self):
        pass


def _make_agent_factory(name, display_name, description, tags, detect_cmd):
    """工厂函数：创建检测指定 CLI 的 SubAgent 类"""
    class _Agent(SubAgent):
        _name = name
        _display_name = display_name
        _description = description
        _capability_tags = tags
        _detect_cmd = detect_cmd

        def __init__(self):
            self.name = self._name
            self.display_name = self._display_name
            self.description = self._description
            self.capability_tags = self._capability_tags

        @staticmethod
        async def detect(executor):
            try:
                result = await executor.run(detect_cmd, ExecContext(timeout_sec=10))
                return result.returncode == 0
            except Exception:
                return False

        async def execute(self, task, context, executor, on_output=None):
            raise NotImplementedError("通过 REPL 会话使用")

        async def cancel(self):
            pass

    _Agent.name = name
    _Agent.display_name = display_name
    _Agent.description = description
    _Agent.capability_tags = tags
    return _Agent


# 所有已知的子智能体类型（新增子智能体只需在此注册类或工厂产物）
_KNOWN_SUBAGENT_CLASSES: list[type[SubAgent]] = [
    ClaudeCodeSubAgent,
    # === REMOVABLE_START ===
    _make_agent_factory("openclaw", "OpenClaw", "开源的 Claude Code 替代 CLI 编程智能体", ["code", "refactor", "multi-file"], "which openclaw && openclaw --version 2>&1"),
    _make_agent_factory("codex", "OpenAI Codex", "OpenAI Codex CLI——终端 AI 编程助手", ["code", "refactor", "openai"], "which codex && codex --version 2>&1"),
    _make_agent_factory("manus", "Manus", "Manus Agent CLI——自主任务执行智能体", ["code", "agent", "autonomous"], "which manus && manus --version 2>&1"),
    _make_agent_factory("hermes", "Hermes", "Hermes CLI——AI 助手命令行工具", ["code", "assistant"], "which hermes && hermes --version 2>&1"),
    # === REMOVABLE_END ===
]

# 委托状态追踪：{(host_id, conversation_id): DelegateSession}
_active_delegations: dict[str, DelegateSession] = {}


@dataclass
class DelegateSession:
    task_id: str
    agent: SubAgent
    executor: BaseExecutor
    cancel_event: asyncio.Event
    queued_messages: list[dict] = field(default_factory=list)


def _session_key(host_id: int | None, conversation_id: int | None) -> str:
    return f"{host_id}:{conversation_id}"


def get_active_delegation(
    host_id: int | None, conversation_id: int | None
) -> DelegateSession | None:
    return _active_delegations.get(_session_key(host_id, conversation_id))


async def detect_available_agents(executor: BaseExecutor) -> list[SubAgent]:
    """探测远程服务器上可用的子智能体，返回可用实例列表"""
    available: list[SubAgent] = []
    for cls in _KNOWN_SUBAGENT_CLASSES:
        try:
            if await cls.detect(executor):
                available.append(cls())
                logger.info(f"探测到子智能体: {cls.name}")
        except Exception as exc:
            logger.warning(f"探测子智能体 {cls.name} 失败: {exc}")
    return available


async def check_claude_installed(executor: BaseExecutor) -> bool:
    """检查远程服务器是否安装了 claude 命令"""
    try:
        result = await executor.run(
            "which claude && claude --version 2>&1",
            ExecContext(timeout_sec=10),
        )
        return result.returncode == 0
    except Exception:
        return False


async def check_node_installed(executor: BaseExecutor) -> bool:
    """检查远程服务器是否安装了 Node.js"""
    try:
        result = await executor.run(
            "which node && node --version 2>&1",
            ExecContext(timeout_sec=10),
        )
        return result.returncode == 0
    except Exception:
        return False


async def install_claude_code(executor: BaseExecutor) -> tuple[bool, str]:
    """在远程服务器上安装 Claude Code CLI（含 Node.js 检查）"""
    has_node = await check_node_installed(executor)
    if not has_node:
        try:
            result = await executor.run(
                "curl -fsSL https://deb.nodesource.com/setup_20.x | bash - "
                "&& apt-get install -y nodejs 2>&1 || "
                "curl -fsSL https://rpm.nodesource.com/setup_20.x | bash - "
                "&& yum install -y nodejs 2>&1",
                ExecContext(timeout_sec=120),
            )
            if result.returncode != 0:
                return False, f"Node.js 安装失败: {result.stderr}"
        except Exception as exc:
            return False, f"Node.js 安装异常: {exc}"

    try:
        result = await executor.run(
            "npm install -g @anthropic-ai/claude-code 2>&1 && claude --version 2>&1",
            ExecContext(timeout_sec=120),
        )
        if result.returncode == 0:
            return True, "Claude Code CLI 安装成功"
        return False, f"Claude Code 安装失败: {result.stderr}"
    except Exception as exc:
        return False, f"Claude Code 安装异常: {exc}"


async def run_delegation(
    agent: SubAgent,
    task: str,
    context: DelegationContext,
    executor: BaseExecutor,
    event_store: "EventStore",
    host_id: int | None = None,
    conversation_id: int | None = None,
) -> DelegateResult:
    """执行委托任务，流式推送进度到前端"""
    key = _session_key(host_id, conversation_id)
    session = DelegateSession(
        task_id=context.task_id,
        agent=agent,
        executor=executor,
        cancel_event=asyncio.Event(),
    )
    _active_delegations[key] = session

    try:
        await event_store.emit(context.task_id, {
            "type": "delegate_started",
            "agent": agent.display_name,
            "task": task,
        })

        # 构建流式输出回调（去除 ANSI 码再推前端）
        import re as _re
        _ansi_re = _re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07')

        async def _stream_output(line: str, is_stderr: bool):
            clean = _ansi_re.sub('', line).rstrip("\n")
            if clean.strip():
                await event_store.emit(context.task_id, {
                    "type": "delegate_progress",
                    "line": clean,
                    "is_stderr": is_stderr,
                })

        result = await agent.execute(task, context, executor, on_output=_stream_output)

        # 检查是否被取消
        if session.cancel_event.is_set():
            result.cancelled = True
            await event_store.emit(context.task_id, {
                "type": "delegate_cancelled",
                "message": "用户取消了委托执行",
            })
        else:
            await event_store.emit(context.task_id, {
                "type": "delegate_completed",
                "exit_code": result.exit_code,
                "execution_time_sec": result.execution_time_sec,
            })

        return result

    except asyncio.TimeoutError:
        await event_store.emit(context.task_id, {
            "type": "delegate_timeout",
            "message": f"委托执行超时（{agent.DELEGATE_TIMEOUT_SEC}秒）",
        })
        return DelegateResult(
            agent_name=agent.name,
            exit_code=-1,
            stdout="",
            stderr="委托超时",
            execution_time_sec=0,
            timed_out=True,
        )
    finally:
        _active_delegations.pop(key, None)


async def cancel_delegation(
    host_id: int | None, conversation_id: int | None
) -> bool:
    """取消正在执行的委托"""
    key = _session_key(host_id, conversation_id)
    session = _active_delegations.get(key)
    if not session:
        return False
    session.cancel_event.set()
    try:
        await session.agent.cancel()
    except Exception as exc:
        logger.warning(f"取消委托失败: {exc}")
    return True
