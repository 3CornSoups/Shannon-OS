"""SubAgent 抽象基类 — 动态探测 + 委托执行"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Awaitable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.executor import BaseExecutor, ExecResult


@dataclass
class DelegationContext:
    user_input: str
    host_info: dict[str, str | None]
    work_dir: str | None
    conversation_summary: str
    task_id: str
    risk_level: str  # LOW / HIGH


@dataclass
class DelegateResult:
    agent_name: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time_sec: float
    cancelled: bool = False
    timed_out: bool = False


class SubAgent(ABC):
    """动态探测 + 委托执行的子智能体抽象基类

    新增子智能体只需继承此类并实现 detect/execute/cancel，
    系统在委托前自动探测远程服务器上可用的子智能体。
    """

    name: str = ""
    display_name: str = ""
    description: str = ""
    capability_tags: list[str] = field(default_factory=list)

    @staticmethod
    @abstractmethod
    async def detect(executor: "BaseExecutor") -> bool:
        """探测目标服务器上是否可用（如 which claude && claude --version）"""
        ...

    @abstractmethod
    async def execute(
        self,
        task: str,
        context: DelegationContext,
        executor: "BaseExecutor",
        on_output: "Callable[[str, bool], Awaitable[None]] | None" = None,
    ) -> DelegateResult:
        """执行委托任务，返回 DelegateResult

        Args:
            on_output: 可选回调，用于流式输出 (line: str, is_stderr: bool)
        """
        ...

    @abstractmethod
    async def cancel(self) -> None:
        """取消当前执行"""
        ...
