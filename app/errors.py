from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SSHConnectionError(Exception):
    """SSH 连接级别的错误"""
    pass


class SSHAuthenticationError(Exception):
    """SSH 认证失败"""
    pass


class SSHCommandError(Exception):
    """SSH 命令执行返回非零退出码"""
    def __init__(self, command: str, returncode: int, stdout: str, stderr: str):
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(f"Command failed (exit={returncode}): {command[:100]}")


class LLMAPIError(Exception):
    """LLM API 调用错误"""
    pass


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
) -> T:
    """通用异步重试工具

    Args:
        fn: 需要重试的协程函数
        max_retries: 最大重试次数
        base_delay: 初始延迟（秒）
        max_delay: 最大延迟（秒）
        backoff: 退避倍数
        retryable_exceptions: 可重试的异常元组

    Returns:
        函数执行结果
    """
    last_exc = None
    delay = base_delay

    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except retryable_exceptions as exc:
            last_exc = exc
            if attempt < max_retries:
                sleep_time = min(delay * (backoff ** attempt), max_delay)
                logger.warning(
                    "操作失败 (attempt %d/%d): %s, %.1fs 后重试",
                    attempt + 1, max_retries, exc, sleep_time,
                )
                await asyncio.sleep(sleep_time)
            else:
                logger.error(
                    "操作失败已达重试上限 (%d): %s", max_retries, exc
                )

    raise last_exc  # type: ignore[misc]
