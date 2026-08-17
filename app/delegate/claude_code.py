"""Claude Code 子智能体实现 — 非交互模式"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Awaitable
from typing import TYPE_CHECKING

from app.delegate.base import DelegationContext, DelegateResult, SubAgent

if TYPE_CHECKING:
    from app.executor import BaseExecutor

logger = logging.getLogger(__name__)


class ClaudeCodeSubAgent(SubAgent):
    name = "claude_code"
    display_name = "Claude Code"
    description = "Anthropic 的 CLI 编程智能体，擅长代码重构、多文件编辑、架构分析"
    capability_tags = ["code", "refactor", "multi-file", "architecture", "git"]

    TIMEOUT_SEC = 900

    def __init__(self):
        self._cancel_event = asyncio.Event()

    @staticmethod
    async def detect(executor: "BaseExecutor") -> bool:
        try:
            from app.executor import ExecContext
            result = await executor.run(
                "which claude && claude --version 2>&1",
                ExecContext(timeout_sec=10),
            )
            return result.returncode == 0 and "claude" in (result.stdout or "").lower()
        except Exception:
            return False

    async def execute(
        self,
        task: str,
        context: DelegationContext,
        executor: "BaseExecutor",
        on_output: "Callable[[str, bool], Awaitable[None]] | None" = None,
    ) -> DelegateResult:
        from app.executor import ExecContext

        self._cancel_event.clear()
        start = time.monotonic()

        command = "{ echo y; cat; } | claude --print"

        try:
            result = await executor.run_with_stdin(
                command, task,
                ExecContext(timeout_sec=self.TIMEOUT_SEC, on_output=on_output, cancel_event=self._cancel_event),
            )
        except asyncio.TimeoutError:
            elapsed = time.monotonic() - start
            return DelegateResult(
                agent_name=self.name, exit_code=-1, stdout="",
                stderr=f"委托执行超时（{self.TIMEOUT_SEC}秒）",
                execution_time_sec=elapsed, timed_out=True,
            )
        except NotImplementedError:
            return DelegateResult(
                agent_name=self.name, exit_code=-1, stdout="",
                stderr="当前执行器不支持 stdin 管道", execution_time_sec=0,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            return DelegateResult(
                agent_name=self.name, exit_code=-1, stdout="",
                stderr=f"Claude Code 执行异常: {exc}", execution_time_sec=elapsed,
            )

        elapsed = time.monotonic() - start
        if self._cancel_event.is_set():
            return DelegateResult(
                agent_name=self.name, exit_code=-1,
                stdout=result.stdout or "", stderr="",
                execution_time_sec=elapsed, cancelled=True,
            )
        return DelegateResult(
            agent_name=self.name, exit_code=result.returncode,
            stdout=result.stdout or "", stderr=result.stderr or "",
            execution_time_sec=elapsed,
        )

    async def cancel(self) -> None:
        self._cancel_event.set()
