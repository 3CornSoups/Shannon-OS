from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.executor import ExecutorRouter, ExecContext, ExecResult, TargetHost

logger = logging.getLogger(__name__)


class BatchExecutor:
    """在所有目标服务器上并行执行命令的批量执行器"""

    def __init__(self, targets: list[TargetHost]):
        self.targets = targets
        self.results: dict[int, list[ExecResult]] = {}

    async def run_command(self, cmd: str, context: ExecContext) -> dict[int, ExecResult]:
        """在所有目标上并行执行同一条命令，返回 host_id -> result 映射"""
        results: dict[int, ExecResult] = {}

        async def _run_one(host: TargetHost) -> tuple[int, ExecResult]:
            executor = ExecutorRouter.create_executor(host)
            return host.host_id, await executor.run(cmd, context)

        tasks = [_run_one(h) for h in self.targets]
        for coro in asyncio.as_completed(tasks):
            try:
                host_id, result = await coro
                results[host_id] = result
            except Exception as e:
                logger.warning(f"批量执行异常: {e}")

        for host in self.targets:
            hid = host.host_id
            if hid not in results:
                results[hid] = ExecResult(command="", returncode=-1, stdout="", stderr="执行异常", cwd_after=None)

        return results

    def accumulate_result(self, host_id: int, result: ExecResult) -> None:
        if host_id not in self.results:
            self.results[host_id] = []
        self.results[host_id].append(result)

    def get_summary(self) -> dict[str, Any]:
        summary = {}
        for host_id, cmd_results in self.results.items():
            total = len(cmd_results)
            success = sum(1 for r in cmd_results if r.returncode == 0)
            summary[str(host_id)] = {"total": total, "success": success, "failed": total - success}
        return summary
