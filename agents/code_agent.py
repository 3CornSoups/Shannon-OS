"""Code Agent — remote code operations via SSH.

Extends BaseAgent.  All operations execute on the remote server through
an SSH executor (same as ServerAgent).  Focused on code analysis, search,
refactoring, and script writing on the remote server.

Use cases:
  - Code search and analysis on remote servers
  - Reading and modifying remote files
  - Script writing and refactoring
  - Project structure exploration on remote servers

NOT for:
  - System operations (use ServerAgent for deployment, package mgmt, etc.)
  - Complex multi-file refactors (use Claude Code delegation)
"""

from __future__ import annotations

import asyncio
import json
import logging
import shlex
from typing import Any, Callable
from uuid import uuid4

from app.executor import ExecContext

from aios.base_agent import BaseAgent
from aios.models import BaseAgentConfig
from aios.security import is_blocked
from aios.tools import get_tool_registry
from app.models import AgentConfig

logger = logging.getLogger(__name__)

# ── Code Agent system prompt ──

CODE_AGENT_SYSTEM_PROMPT = """你是 Shannon OS Code Agent，一个远程代码助手。

你通过 SSH 在远程服务器上操作，专注于代码相关任务。你有以下工具：

  1. read_file: 读取远程服务器上的文件内容
  2. write_file: 写入内容到远程服务器上的文件
  3. list_directory: 列出远程服务器上的目录内容
  4. search_code: 在远程服务器上搜索代码 (grep)
  5. run_shell: 在远程服务器上执行 shell 命令（用于代码构建、测试等）
  6. task_done: 任务完成
  7. ask_user: 需要用户介入
  8. delegate_to_agent: 委托子任务给其他 Agent（如 Server Agent 做系统操作）

规则：
- 所有操作在远程服务器上执行，请使用正确的远程路径
- 每次执行一个操作，观察结果再决定下一步
- 读取文件后再修改，不要猜测内容
- 写入文件前确认路径正确，文件存在则先备份
- 搜索代码时使用合适的 grep 模式
- 如果任务涉及系统管理操作（安装包、启停服务等），使用 delegate_to_agent 委托给 Server Agent
- 最多 20 轮迭代
"""


class CodeAgent(BaseAgent):
    """Remote code operations agent (via SSH).

    Tools (from ToolRegistry, scope "agent:code"):
      read_file, write_file, list_directory, search_code, run_shell
    Base tools (shared):
      task_done, ask_user, delegate_to_agent
    """

    def __init__(self, config: AgentConfig):
        aios_cfg = BaseAgentConfig(
            agent_id=f"code_{id(self)}",
            display_name="Shannon Code Agent",
            api_base=config.api_base,
            api_key=config.api_key,
            model=config.model,
            timeout_sec=config.timeout_sec,
            max_context_messages=config.max_context_messages,
        )
        super().__init__(aios_cfg)
        self._legacy_config = config
        self._capability_tags = ["code", "files", "analysis", "remote"]

    # ── AgentHandle identity ──

    @property
    def agent_id(self) -> str:
        return self.config.agent_id

    @property
    def display_name(self) -> str:
        return "Shannon Code Agent"

    # ── Abstract method implementations ──

    def _build_system_prompt(self, *args: Any, **kwargs: Any) -> str:
        return CODE_AGENT_SYSTEM_PROMPT

    def _get_tools(self) -> list[dict[str, Any]]:
        return get_tool_registry().get_for_agent("code")

    def _tool_call_to_action(self, name: str, args: dict[str, Any]) -> Any:
        if name in ("read_file", "write_file", "list_directory",
                     "search_code", "run_shell"):
            return CodeAction(
                tool=name,
                params=args,
                reasoning=args.get("reasoning", ""),
            )
        elif name == "task_done":
            return CodeDone(message=args.get("message", ""))
        elif name == "ask_user":
            return CodeAsk(
                message=args.get("message", ""),
                reasoning=args.get("reasoning", ""),
            )
        elif name == "delegate_to_agent":
            return CodeDelegate(
                target_agent_id=args.get("agent_id", ""),
                task=args.get("task", ""),
                reason=args.get("reason", ""),
            )
        return None

    def _dict_to_action(self, data: dict[str, Any]) -> Any:
        tool = data.get("tool") or data.get("action")
        if tool in ("read_file", "write_file", "list_directory",
                     "search_code", "run_shell"):
            return CodeAction(tool=tool, params=data, reasoning=data.get("reasoning", ""))
        elif tool in ("done", "task_done"):
            return CodeDone(message=data.get("message", ""))
        elif tool in ("ask", "ask_user"):
            return CodeAsk(message=data.get("message", ""), reasoning=data.get("reasoning", ""))
        elif tool in ("delegate", "delegate_to_agent"):
            return CodeDelegate(
                target_agent_id=data.get("agent_id", ""),
                task=data.get("task", ""),
                reason=data.get("reason", ""),
            )
        raise ValueError(f"Unknown code action: {tool}")

    def _validate_action(self, action: Any) -> Any:
        return action

    def _build_fallback_done_action(self, raw: str) -> Any:
        return CodeDone(message=raw.strip() or "任务已完成")

    # ── Tool implementations (all via SSH executor) ──

    async def execute_tool(self, action: CodeAction, executor) -> str:
        """Execute a single tool action on the remote server via SSH.

        Args:
            action: The CodeAction to execute.
            executor: An SSH executor (from ExecutorRouter.create_executor).
        """
        tool = action.tool
        params = action.params

        if tool == "read_file":
            return await self._read_remote_file(params.get("path", ""), executor)
        elif tool == "write_file":
            return await self._write_remote_file(
                params.get("path", ""), params.get("content", ""), executor,
            )
        elif tool == "list_directory":
            return await self._list_remote_dir(params.get("path", "."), executor)
        elif tool == "search_code":
            return await self._search_remote_code(
                params.get("pattern", ""),
                params.get("path", "."),
                params.get("file_pattern", "*"),
                executor,
            )
        elif tool == "run_shell":
            return await self._run_remote_shell(params.get("command", ""), executor)
        return f"[CodeAgent] Unknown tool: {tool}"

    async def _run_ssh(self, command: str, executor, timeout: int = 30) -> tuple[str, int]:
        """Run a command via SSH and return (output, exit_code)."""
        try:
            result = await executor.run(command, ExecContext(timeout_sec=timeout))
            out = (result.stdout or "") + (result.stderr or "")
            return out, result.returncode
        except Exception as e:
            return str(e), -1

    async def _read_remote_file(self, path: str, executor) -> str:
        """Read a file on the remote server."""
        if not path:
            return "Error: 未指定文件路径"
        # Use head to limit output to 200 lines; shlex.quote 防注入
        q = shlex.quote(path)
        cmd = f"test -f {q} && (wc -l < {q} | xargs -I{{}} echo 'Lines: {{}}'; head -200 {q}) || echo 'Error: file not found or not a regular file: {path}'"
        out, rc = await self._run_ssh(cmd, executor)
        return f"Remote file: {path}\n{out}"

    async def _write_remote_file(self, path: str, content: str, executor) -> str:
        """Write content to a file on the remote server."""
        if not path:
            return "Error: 未指定文件路径"
        # 随机 heredoc 分隔符 + shlex.quote 防注入/提前终止
        escaped = content.replace("\\", "\\\\").replace("'", "'\\''")
        q = shlex.quote(path)
        delim = f"SHANNON_EOF_{uuid4().hex[:8]}"
        cmd = f"cat > {q} << '{delim}'\n{escaped}\n{delim}\necho 'Written successfully: {path} ('$(wc -c < {q})' bytes)'"
        out, rc = await self._run_ssh(cmd, executor, timeout=30)
        return f"Write result:\n{out}" if rc == 0 else f"Error writing file:\n{out}"

    async def _list_remote_dir(self, path: str, executor) -> str:
        """List directory on the remote server."""
        cmd = f"ls -lah {shlex.quote(path)} 2>&1 | head -100"
        out, rc = await self._run_ssh(cmd, executor)
        return f"Remote directory: {path}\n{out}"

    async def _search_remote_code(self, pattern: str, path: str, file_pattern: str, executor) -> str:
        """Search code on the remote server using grep."""
        if not pattern:
            return "Error: 未指定搜索模式"
        # Build grep command with optional file filter; shlex.quote 防注入
        glob = ""
        if file_pattern and file_pattern != "*":
            glob = f" --include={shlex.quote(file_pattern)}"
        cmd = f"grep -rn{glob} --color=never {shlex.quote(pattern)} {shlex.quote(path)} 2>/dev/null | head -50"
        out, rc = await self._run_ssh(cmd, executor, timeout=30)
        if not out.strip():
            return f"Search '{pattern}' in {path}: no matches found"
        return f"Search '{pattern}' in {path}:\n{out}"

    async def _run_remote_shell(self, command: str, executor) -> str:
        """Execute an arbitrary shell command on the remote server."""
        if not command:
            return "Error: 未指定命令"
        # 硬阻断清单兜底（与 ServerAgent 一致）
        blocked, reason = is_blocked(command)
        if blocked:
            return f"Error: 命令被安全策略拦截: {reason}"
        out, rc = await self._run_ssh(command, executor, timeout=60)
        return f"Command: {command}\nExit: {rc}\n{out[:4000]}"

    # ── ReAct loop ──

    async def run_task(
        self,
        user_prompt: str,
        executor,  # SSH executor from ExecutorRouter
        emit: Callable[[dict[str, Any]], Any] | None = None,
        max_iterations: int = 20,
    ) -> str:
        """Run a full ReAct loop for this CodeAgent on the remote server.

        Args:
            user_prompt: The task to execute.
            executor: SSH executor (from ExecutorRouter.create_executor).
            emit: Optional SSE event callback.
            max_iterations: Max ReAct iterations.
        """
        system_prompt = self._build_system_prompt()
        self.conversation.set_system_prompt(system_prompt)

        async def _emit(event: dict) -> None:
            if emit:
                try:
                    await emit(event) if asyncio.iscoroutinefunction(emit) else emit(event)
                except Exception:
                    pass

        await _emit({"type": "status", "message": "Code Agent 正在分析任务..."})

        # First action via tool calling
        first_action = await self._request_first_action(user_prompt)
        if first_action is None:
            chunks: list[str] = []
            async for chunk in self.stream_reply(user_prompt):
                chunks.append(chunk)
                await _emit({"type": "raw_content", "stage": "plan", "content": chunk})
            raw = "".join(chunks)
            from aios.llm import extract_json
            parsed = extract_json(raw)
            if parsed:
                try:
                    first_action = self._dict_to_action(parsed)
                except Exception:
                    first_action = CodeDone(message=raw.strip() or "任务已完成")
            else:
                first_action = CodeDone(message=raw.strip() or "任务已完成")

        iteration = 0
        final_reply = ""

        while iteration < max_iterations:
            iteration += 1
            await _emit({"type": "iteration_start", "iteration": iteration, "max_iterations": max_iterations})

            if isinstance(first_action, CodeAction):
                tool_name = first_action.tool
                await _emit({
                    "type": "command_start",
                    "command": f"[{tool_name}] {json.dumps(first_action.params, ensure_ascii=False)[:200]}",
                    "purpose": first_action.reasoning,
                })

                result_text = await self.execute_tool(first_action, executor)

                await _emit({
                    "type": "command_result",
                    "command": tool_name,
                    "stdout": result_text,
                    "returncode": 0,
                })

                self.conversation.add_tool_result(
                    f"[{tool_name}] {json.dumps(first_action.params, ensure_ascii=False)[:100]}",
                    0, result_text, "",
                )

                try:
                    first_action = await self._request_react_action()
                except Exception as exc:
                    final_reply = f"Code Agent LLM 调用失败: {exc}"
                    await _emit({"type": "error", "message": final_reply})
                    break

            elif isinstance(first_action, CodeDelegate):
                target_id = first_action.target_agent_id
                await _emit({"type": "status", "message": f"Code Agent 委托任务给 {target_id}..."})
                from aios.ipc import call_agent
                ipc_result = await call_agent(target_id, first_action.task)
                result_text = json.dumps(ipc_result, ensure_ascii=False)
                self.conversation.add_tool_result(
                    f"delegate_to:{target_id}", 0, result_text, "",
                )
                try:
                    first_action = await self._request_react_action()
                except Exception as exc:
                    final_reply = f"委托后 LLM 调用失败: {exc}"
                    await _emit({"type": "error", "message": final_reply})
                    break

            elif isinstance(first_action, CodeDone):
                final_reply = first_action.message
                await _emit({"type": "react_done", "message": final_reply})
                break

            elif isinstance(first_action, CodeAsk):
                final_reply = first_action.message
                await _emit({"type": "react_ask", "message": final_reply, "reasoning": first_action.reasoning})
                break

            else:
                final_reply = f"未知的 action 类型: {type(first_action).__name__}"
                await _emit({"type": "error", "message": final_reply})
                break

        else:
            final_reply = f"已达到最大迭代次数 ({max_iterations})，执行终止。"
            await _emit({"type": "done", "message": final_reply})

        if not final_reply:
            final_reply = "Code Agent 执行完成。"

        await _emit({"type": "done", "message": final_reply})
        return final_reply


# ── Code Agent action types ──

from dataclasses import dataclass, field


@dataclass
class CodeAction:
    """A tool execution action."""
    tool: str
    params: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


@dataclass
class CodeDone:
    """Task completed."""
    message: str


@dataclass
class CodeAsk:
    """Need user input."""
    message: str
    reasoning: str = ""


@dataclass
class CodeDelegate:
    """Delegate to another agent."""
    target_agent_id: str
    task: str
    reason: str = ""
