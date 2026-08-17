"""远程服务器 Claude Code + Node.js 自动安装引导"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.executor import BaseExecutor

logger = logging.getLogger(__name__)


async def ensure_claude_code_available(
    executor: "BaseExecutor",
) -> tuple[bool, str, dict]:
    """确保远程服务器上 Claude Code CLI 可用

    Returns:
        (available, message, install_report)
        - available: True 表示 Claude Code 已就绪
        - message: 描述信息
        - install_report: 安装步骤报告
    """
    report = {
        "node_installed": False,
        "node_installed_now": False,
        "claude_installed": False,
        "claude_installed_now": False,
    }

    # 1. 检查 Node.js
    node_ok, node_msg = await _check_node(executor)
    report["node_installed"] = node_ok
    if not node_ok:
        logger.info(f"远程服务器缺少 Node.js: {node_msg}")
        ok, msg = await _install_node(executor)
        if not ok:
            return False, f"Node.js 安装失败: {msg}", report
        report["node_installed_now"] = True
        report["node_installed"] = True

    # 2. 检查 Claude Code
    claude_ok, claude_msg = await _check_claude(executor)
    report["claude_installed"] = claude_ok
    if not claude_ok:
        logger.info(f"远程服务器缺少 Claude Code: {claude_msg}")
        ok, msg = await _install_claude(executor)
        if not ok:
            return False, f"Claude Code 安装失败: {msg}", report
        report["claude_installed_now"] = True
        report["claude_installed"] = True

    return True, "Claude Code CLI 就绪", report


async def _check_node(executor: "BaseExecutor") -> tuple[bool, str]:
    from app.executor import ExecContext

    try:
        result = await executor.run(
            "which node && node --version 2>&1",
            ExecContext(timeout_sec=10),
        )
        if result.returncode == 0:
            version = (result.stdout or "").strip().splitlines()[-1]
            return True, version
        return False, "node 命令未找到"
    except Exception as exc:
        return False, str(exc)


async def _check_claude(executor: "BaseExecutor") -> tuple[bool, str]:
    from app.executor import ExecContext

    try:
        result = await executor.run(
            "which claude && claude --version 2>&1",
            ExecContext(timeout_sec=10),
        )
        if result.returncode == 0:
            version = (result.stdout or "").strip().splitlines()[-1]
            return True, version
        return False, "claude 命令未找到"
    except Exception as exc:
        return False, str(exc)


async def _install_node(executor: "BaseExecutor") -> tuple[bool, str]:
    from app.executor import ExecContext

    try:
        result = await executor.run(
            # 先尝试 NodeSource 的安装脚本，兼容 apt 和 yum
            'curl -fsSL https://deb.nodesource.com/setup_20.x 2>/dev/null | bash - 2>&1 && '
            'apt-get install -y nodejs 2>&1 || '
            'curl -fsSL https://rpm.nodesource.com/setup_20.x 2>/dev/null | bash - 2>&1 && '
            'yum install -y nodejs 2>&1',
            ExecContext(timeout_sec=120),
        )
        if result.returncode != 0:
            return False, result.stderr or "安装命令失败"

        # 验证
        node_ok, msg = await _check_node(executor)
        if node_ok:
            return True, f"Node.js 安装成功 ({msg})"
        return False, "安装后验证失败"
    except Exception as exc:
        return False, str(exc)


async def _install_claude(executor: "BaseExecutor") -> tuple[bool, str]:
    from app.executor import ExecContext

    try:
        result = await executor.run(
            "npm install -g @anthropic-ai/claude-code 2>&1",
            ExecContext(timeout_sec=120),
        )
        if result.returncode != 0:
            return False, result.stderr or "npm install 失败"

        # 验证
        claude_ok, msg = await _check_claude(executor)
        if claude_ok:
            return True, f"Claude Code 安装成功 ({msg})"
        return False, "安装后验证失败"
    except Exception as exc:
        return False, str(exc)
