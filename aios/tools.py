"""AIOS tool definitions — centralized tool schema registry.

Populates the ToolRegistry (aios/tool_registry.py) with all known tools.
Separates tool SCHEMA (what the LLM sees) from tool IMPLEMENTATION
(what the Agent does when a tool is called).

Phase 2: base tools + server-agent tools.
Phase 3+: each Agent type contributes its own tool set at registration time.
"""

from __future__ import annotations

from aios.tool_registry import ToolRegistry


# ── Tool parameter schemas (OpenAI function-calling JSON Schema) ──

_EXECUTE_COMMAND_PARAMS = {
    "type": "object",
    "properties": {
        "command": {"type": "string", "description": "要执行的 shell 命令"},
        "purpose": {"type": "string", "description": "这条命令的目的"},
        "reasoning": {"type": "string", "description": "为什么执行这条命令"},
        "risk_level": {
            "type": "string",
            "enum": ["LOW", "HIGH"],
            "description": (
                "⚠️ 必须正确标注！LOW = 只读查询（cat/ls/df/ps/find/grep/id/which/echo）。"
                "HIGH = 任何会改变系统状态的操作，包括但不限于：创建/删除用户、安装软件、"
                "启停服务、修改文件、删除文件、改权限、创建目录、移动文件"
            ),
        },
    },
    "required": ["command", "purpose", "reasoning", "risk_level"],
}

_TASK_DONE_PARAMS = {
    "type": "object",
    "properties": {
        "message": {"type": "string", "description": "给用户的最终总结"},
    },
    "required": ["message"],
}

_ASK_USER_PARAMS = {
    "type": "object",
    "properties": {
        "message": {"type": "string", "description": "向用户说明需要什么帮助"},
        "reasoning": {"type": "string", "description": "为什么需要用户介入"},
    },
    "required": ["message", "reasoning"],
}

_DELEGATE_TASK_PARAMS = {
    "type": "object",
    "properties": {
        "target_agent": {
            "type": "string",
            "description": "目标智能体名称，当前支持 claude_code",
        },
        "reason": {
            "type": "string",
            "description": "为什么建议委托给子智能体",
        },
        "risk_level": {
            "type": "string",
            "enum": ["LOW", "HIGH"],
            "description": "任务风险等级",
        },
        "context_for_delegate": {
            "type": "string",
            "description": "传递给子智能体的具体任务描述",
        },
        "work_dir": {
            "type": "string",
            "description": "建议的工作目录",
        },
    },
    "required": ["target_agent", "reason", "risk_level", "context_for_delegate"],
}

# ── Tool descriptions ──

_EXECUTE_COMMAND_DESC = "在服务器上执行一条 shell 命令并观察输出"

_TASK_DONE_DESC = "任务已完成，向用户报告最终结果"

_ASK_USER_DESC = (
    "需要用户帮助时使用——当遇到不可恢复的错误、"
    "需要用户提供参数或确认时调用"
)

_DELEGATE_TASK_DESC = (
    "将代码相关任务委托给 Claude Code 执行。"
    "涉及代码理解的任务优先使用此工具，不要用 find/grep/wc 等 shell 命令拼凑分析。"
    "适合委托：代码分析与审计、代码重构、模块拆分、架构调整、多文件编辑、"
    "代码审查、依赖分析、构建脚本/Docker/CI 配置编写与优化、代码级 bug 修复。"
    "不适合委托：单条 shell 运维操作、系统状态查询、软件包安装、服务启停。"
    "即使任务要求「只分析不修改」，也必须委托给 Claude Code。"
)


# ── Code Agent tool schemas ──

_READ_FILE_PARAMS = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "要读取的文件路径"},
        "reasoning": {"type": "string", "description": "为什么需要读取这个文件"},
    },
    "required": ["path"],
}

_WRITE_FILE_PARAMS = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "要写入的文件路径"},
        "content": {"type": "string", "description": "要写入的文件内容"},
        "reasoning": {"type": "string", "description": "为什么需要写入这个文件"},
    },
    "required": ["path", "content"],
}

_LIST_DIRECTORY_PARAMS = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "目录路径，默认当前目录"},
        "reasoning": {"type": "string", "description": "为什么需要列出目录"},
    },
    "required": ["path"],
}

_SEARCH_CODE_PARAMS = {
    "type": "object",
    "properties": {
        "pattern": {"type": "string", "description": "搜索模式 (支持正则表达式)"},
        "path": {"type": "string", "description": "搜索范围路径，默认当前目录"},
        "file_pattern": {"type": "string", "description": "文件名过滤，如 *.py, *.js"},
        "reasoning": {"type": "string", "description": "为什么搜索这个模式"},
    },
    "required": ["pattern"],
}

_RUN_SHELL_PARAMS = {
    "type": "object",
    "properties": {
        "command": {"type": "string", "description": "要在远程服务器上执行的 shell 命令"},
        "purpose": {"type": "string", "description": "这条命令的目的"},
        "reasoning": {"type": "string", "description": "为什么执行这条命令"},
    },
    "required": ["command", "purpose"],
}

_DELEGATE_TO_AGENT_PARAMS = {
    "type": "object",
    "properties": {
        "agent_id": {
            "type": "string",
            "description": "目标 Agent ID（从可用 Agent 列表中选择）",
        },
        "task": {
            "type": "string",
            "description": "委托给目标 Agent 的具体任务描述",
        },
        "reason": {
            "type": "string",
            "description": "为什么需要委托给这个 Agent",
        },
    },
    "required": ["agent_id", "task", "reason"],
}

# ── Code tool descriptions ──

_READ_FILE_DESC = "读取远程服务器上的文件内容，返回文件文本"
_WRITE_FILE_DESC = "写入内容到远程服务器上的文件（会覆盖已有内容）"
_LIST_DIRECTORY_DESC = "列出远程服务器上的目录内容"
_SEARCH_CODE_DESC = "在远程服务器上搜索代码（grep），支持文件名过滤"
_RUN_SHELL_DESC = "在远程服务器上执行一条 shell 命令并返回输出（用于代码构建、测试等）"
_DELEGATE_TO_AGENT_DESC = (
    "将子任务委托给 AIOS 中的另一个 Agent 执行。"
    "例如：Code Agent 可委托 Server Agent 检查服务器状态；"
    "Server Agent 可委托 Code Agent 分析代码。"
    "从可用 Agent 列表中选择合适的 agent_id。"
)


def init_tool_registry() -> ToolRegistry:
    """Create and populate the global tool registry.

    Called once at application startup (main.py startup_event).
    Also sets the global tool_registry singleton.

    Returns:
        A populated ToolRegistry ready for use by all Agents.
    """
    global tool_registry

    registry = ToolRegistry()

    # ── Base tools (available to ALL agents) ──
    registry.register_base_tool(
        name="task_done",
        description=_TASK_DONE_DESC,
        parameters=_TASK_DONE_PARAMS,
    )
    registry.register_base_tool(
        name="ask_user",
        description=_ASK_USER_DESC,
        parameters=_ASK_USER_PARAMS,
    )
    registry.register_base_tool(
        name="delegate_task",
        description=_DELEGATE_TASK_DESC,
        parameters=_DELEGATE_TASK_PARAMS,
    )
    # delegate_to_agent — AIOS internal agent-to-agent IPC
    registry.register_base_tool(
        name="delegate_to_agent",
        description=_DELEGATE_TO_AGENT_DESC,
        parameters=_DELEGATE_TO_AGENT_PARAMS,
    )

    # ── Server Agent specific tools ──
    from aios.tool_registry import ToolDef

    registry.register(
        ToolDef(
            name="execute_command",
            description=_EXECUTE_COMMAND_DESC,
            parameters=_EXECUTE_COMMAND_PARAMS,
            risk_level="HIGH",
            tags=["ssh", "shell", "server"],
        ),
        scope="agent:server",
    )

    # ── Code Agent specific tools ──
    registry.register(
        ToolDef(
            name="read_file",
            description=_READ_FILE_DESC,
            parameters=_READ_FILE_PARAMS,
            tags=["files", "read", "local"],
        ),
        scope="agent:code",
    )
    registry.register(
        ToolDef(
            name="write_file",
            description=_WRITE_FILE_DESC,
            parameters=_WRITE_FILE_PARAMS,
            risk_level="HIGH",
            tags=["files", "write", "local"],
        ),
        scope="agent:code",
    )
    registry.register(
        ToolDef(
            name="list_directory",
            description=_LIST_DIRECTORY_DESC,
            parameters=_LIST_DIRECTORY_PARAMS,
            tags=["files", "read", "local"],
        ),
        scope="agent:code",
    )
    registry.register(
        ToolDef(
            name="search_code",
            description=_SEARCH_CODE_DESC,
            parameters=_SEARCH_CODE_PARAMS,
            tags=["code", "search", "analysis"],
        ),
        scope="agent:code",
    )
    registry.register(
        ToolDef(
            name="run_shell",
            description=_RUN_SHELL_DESC,
            parameters=_RUN_SHELL_PARAMS,
            risk_level="HIGH",
            tags=["shell", "remote", "exec"],
        ),
        scope="agent:code",
    )

    # Set global singleton
    tool_registry = registry
    return registry


# ── Global singleton (populated at startup) ──
tool_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry singleton.

    Raises RuntimeError if not initialized (should be called after startup).
    """
    if tool_registry is None:
        raise RuntimeError(
            "ToolRegistry not initialized. "
            "Call init_tool_registry() at application startup."
        )
    return tool_registry
