"""远程服务器 CLI 工具探测 — 自动发现可用命令行工具并注入 LLM 上下文"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.executor import BaseExecutor

logger = logging.getLogger(__name__)

# 值得探测的 CLI 工具（含分类标签供 LLM 理解用途）
TOOL_CATALOG: dict[str, str] = {
    # 容器/编排
    "docker": "容器管理",
    "kubectl": "Kubernetes 集群管理",
    "podman": "容器管理（无守护进程）",
    # 版本控制
    "git": "版本控制",
    # 语言运行时
    "python3": "Python 3 运行时",
    "python": "Python 运行时",
    "node": "Node.js 运行时",
    "go": "Go 编译器/运行时",
    "java": "Java 运行时",
    "ruby": "Ruby 运行时",
    "perl": "Perl 运行时",
    # 包管理
    "npm": "Node.js 包管理",
    "yarn": "Node.js 包管理",
    "pip3": "Python 包管理",
    "pip": "Python 包管理",
    "mvn": "Maven (Java) 构建工具",
    "gradle": "Gradle 构建工具",
    "cargo": "Rust 包管理/构建",
    # 数据库
    "psql": "PostgreSQL 客户端",
    "mysql": "MySQL 客户端",
    "redis-cli": "Redis 客户端",
    "sqlite3": "SQLite 客户端",
    "mongo": "MongoDB 客户端",
    # 构建/编译
    "make": "Make 构建工具",
    "cmake": "CMake 构建系统",
    "gcc": "GCC C 编译器",
    "g++": "G++ C++ 编译器",
    # 系统服务
    "systemctl": "systemd 服务管理",
    "journalctl": "systemd 日志查看",
    "nginx": "Nginx Web 服务器",
    "apache2": "Apache Web 服务器",
    "sshd": "SSH 守护进程",
    # 网络
    "curl": "HTTP/文件传输",
    "wget": "文件下载",
    "netstat": "网络连接查看",
    "ss": "Socket 统计",
    "nmap": "网络扫描",
    "tcpdump": "网络抓包",
    # 监控
    "htop": "交互式进程监控",
    "iotop": "磁盘 I/O 监控",
    "vmstat": "虚拟内存统计",
    "iostat": "磁盘 I/O 统计",
    # 文本处理
    "jq": "JSON 处理",
    "yq": "YAML 处理",
    "awk": "文本处理",
    "sed": "流编辑器",
    # 压缩
    "tar": "归档工具",
    "zip": "压缩工具",
    "unzip": "解压工具",
    # 其他
    "openssl": "SSL/TLS 工具",
    "crontab": "定时任务管理",
    "rsync": "文件同步",
    "ssh": "SSH 客户端",
    "scp": "安全文件复制",
}

# 探测命令模板：批量检查所有工具
PROBE_SCRIPT = (
    "for cmd in "
    + " ".join(TOOL_CATALOG.keys())
    + "; do p=$(command -v $cmd 2>/dev/null) && echo \"FOUND:$cmd:$p\"; done"
)


async def detect_available_tools(
    executor: "BaseExecutor",
) -> dict[str, dict]:
    """探测远程服务器上可用的 CLI 工具列表

    Returns:
        {tool_name: {"path": "/usr/bin/docker", "label": "容器管理"}, ...}
    """
    from app.executor import ExecContext

    available: dict[str, dict] = {}
    try:
        result = await executor.run(PROBE_SCRIPT, ExecContext(timeout_sec=15))
        for line in (result.stdout or "").splitlines():
            line = line.strip()
            if line.startswith("FOUND:"):
                parts = line.split(":", 2)  # FOUND:tool_name:path
                if len(parts) >= 3:
                    name = parts[1]
                    path = parts[2]
                    label = TOOL_CATALOG.get(name, "未知")
                    available[name] = {"path": path, "label": label}
                    logger.info(f"探测到工具: {name} ({label}) -> {path}")
    except Exception as exc:
        logger.warning(f"远程工具探测失败: {exc}")

    return available


def format_tools_for_prompt(available_tools: dict[str, dict]) -> str:
    """将可用工具列表格式化为 system prompt 片段"""
    if not available_tools:
        return ""

    lines = [
        "\n\n=== 远程服务器可用工具 ===\n",
        "以下命令行工具已在目标服务器上检测到，你可以通过 execute_command 调用：\n",
    ]
    # 按分类分组
    by_label: dict[str, list[str]] = {}
    for name, info in available_tools.items():
        label = info["label"]
        by_label.setdefault(label, []).append(name)

    for label, names in sorted(by_label.items()):
        tools_str = ", ".join(f"`{n}`" for n in sorted(names))
        lines.append(f"- {label}: {tools_str}")

    lines.append(
        "\n优先使用以上已安装的工具完成任务。如果需要的工具不在列表中，请告知用户。"
    )
    return "\n".join(lines)
