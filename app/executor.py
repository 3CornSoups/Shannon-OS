from __future__ import annotations

import asyncio
import logging
import os
import platform
import shlex
from dataclasses import dataclass
from typing import Any

import asyncssh
import paramiko

from app.connection import pool

logger = logging.getLogger(__name__)


@dataclass
class TargetHost:
    host_id: int | None
    name: str
    host: str
    port: int = 22
    username: str | None = None
    password: str | None = None
    private_key: str | None = None
    use_local: bool = False


@dataclass
class ExecContext:
    cwd: str | None = None
    timeout_sec: int = 60
    on_output: Any | None = None  # async callback(line: str, is_stderr: bool) -> None


@dataclass
class ExecResult:
    command: str
    returncode: int
    stdout: str
    stderr: str
    cwd_after: str | None


class BaseExecutor:
    async def run(self, command: str, context: ExecContext) -> ExecResult:
        raise NotImplementedError

    async def probe_environment(self) -> dict[str, str | None]:
        raise NotImplementedError


class LocalExecutor(BaseExecutor):
    async def run(self, command: str, context: ExecContext) -> ExecResult:
        wrapped = _wrap_command_with_cwd(command, context.cwd)
        process = await asyncio.create_subprocess_shell(
            wrapped,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
        )
        stdout_b, stderr_b = await asyncio.wait_for(
            process.communicate(), timeout=context.timeout_sec
        )
        stdout = stdout_b.decode(errors="ignore")
        stderr = stderr_b.decode(errors="ignore")
        cwd_after = _extract_cwd_marker(stdout)
        return ExecResult(
            command=command,
            returncode=process.returncode or 0,
            stdout=_strip_cwd_marker(stdout),
            stderr=stderr,
            cwd_after=cwd_after or context.cwd,
        )

    async def probe_environment(self) -> dict[str, str | None]:
        return await _probe_with_runner(self.run)


class SSHExecutor(BaseExecutor):
    def __init__(self, target: TargetHost):
        self.target = target

    async def run(self, command: str, context: ExecContext) -> ExecResult:
        wrapped = _wrap_command_with_cwd(command, context.cwd)

        try:
            return await self._run_via_pool(wrapped, context)
        except Exception as exc:
            logger.warning(
                "SSH 命令执行失败，释放连接后重试一次: %s - %s",
                self.target.host, exc,
            )
            # 释放可能损坏的连接，再次尝试
            await pool.release_connection(
                self.target.host,
                self.target.port,
                self.target.username,
            )
            try:
                return await self._run_via_pool(wrapped, context)
            except Exception as exc2:
                return ExecResult(
                    command=command,
                    returncode=-1,
                    stdout="",
                    stderr=f"SSH 命令执行失败: {exc2}",
                    cwd_after=None,
                )

    async def _run_via_pool(self, wrapped: str, context: ExecContext) -> ExecResult:
        entry = await pool.get_connection(
            host=self.target.host,
            port=self.target.port,
            username=self.target.username,
            password=self.target.password,
            private_key=self.target.private_key,
        )

        if entry.use_paramiko:
            return await self._run_paramiko_with_client(wrapped, context)
        else:
            return await self._run_asyncssh_with_conn(entry, wrapped, context)

    async def _run_asyncssh_with_conn(
        self, entry: Any, command: str, context: ExecContext
    ) -> ExecResult:
        process = await entry.conn.create_process(command)
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        async def read_stream(reader, lines_list, is_stderr=False):
            async for line in reader:
                decoded = line.decode(errors="ignore") if isinstance(line, bytes) else line
                lines_list.append(decoded)
                if context.on_output:
                    try:
                        await context.on_output(decoded, is_stderr)
                    except Exception:
                        pass

        try:
            await asyncio.wait_for(
                asyncio.gather(
                    read_stream(process.stdout, stdout_lines),
                    read_stream(process.stderr, stderr_lines, True),
                ),
                timeout=context.timeout_sec,
            )
            completed = await asyncio.wait_for(process.wait(), timeout=5)
            exit_status = completed.exit_status
        except asyncio.TimeoutError:
            process.close()
            raise

        entry.last_used = __import__("time").time()
        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)
        cwd_after = _extract_cwd_marker(stdout)
        return ExecResult(
            command=command,
            returncode=exit_status,
            stdout=_strip_cwd_marker(stdout),
            stderr=stderr,
            cwd_after=cwd_after or context.cwd,
        )

    async def _run_paramiko_with_client(self, command: str, context: ExecContext) -> ExecResult:
        return await asyncio.to_thread(
            self._run_paramiko_sync, command, context
        )

    def _run_paramiko_sync(self, command: str, context: ExecContext) -> ExecResult:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs: dict[str, Any] = {
            "hostname": self.target.host,
            "port": self.target.port,
            "username": self.target.username,
            "timeout": context.timeout_sec,
        }
        if self.target.private_key:
            connect_kwargs["key_filename"] = self.target.private_key
        if self.target.password:
            connect_kwargs["password"] = self.target.password
        client.connect(**connect_kwargs)
        try:
            stdin, stdout_f, stderr_f = client.exec_command(
                command, timeout=context.timeout_sec
            )
            stdin.close()
            stdout = stdout_f.read().decode(errors="ignore")
            stderr = stderr_f.read().decode(errors="ignore")
            return_code = stdout_f.channel.recv_exit_status()
            cwd_after = _extract_cwd_marker(stdout)
            return ExecResult(
                command=command,
                returncode=return_code,
                stdout=_strip_cwd_marker(stdout),
                stderr=stderr,
                cwd_after=cwd_after or context.cwd,
            )
        finally:
            client.close()

    async def probe_environment(self) -> dict[str, str | None]:
        return await _probe_with_runner(self.run)


class ExecutorRouter:
    @staticmethod
    def create_executor(target: TargetHost) -> BaseExecutor:
        system_name = platform.system().lower()
        local_allowed = system_name == "linux"
        if target.use_local and local_allowed:
            return LocalExecutor()
        if target.host in {"127.0.0.1", "localhost"} and local_allowed:
            return LocalExecutor()
        return SSHExecutor(target)


async def _probe_with_runner(runner: Any) -> dict[str, str | None]:
    context = ExecContext(cwd=None, timeout_sec=30)
    shell = await runner("echo $SHELL", context)
    py = await runner("python3 --version || python --version", context)
    docker = await runner("docker --version", context)
    systemctl = await runner("systemctl --version", context)
    uname = await runner("uname -a", context)
    os_release = await runner("cat /etc/os-release", context)
    mem = await runner("free -h", context)
    disk = await runner("df -h", context)
    return {
        "shell": _one_line(shell.stdout),
        "python_version": _one_line(py.stdout or py.stderr),
        "docker_version": _one_line(docker.stdout or docker.stderr),
        "systemctl_version": _one_line(systemctl.stdout or systemctl.stderr),
        "uname": _one_line(uname.stdout),
        "os_release": _short_block(os_release.stdout),
        "memory_summary": _short_block(mem.stdout),
        "disk_summary": _short_block(disk.stdout),
    }


def _wrap_command_with_cwd(command: str, cwd: str | None) -> str:
    if cwd:
        safe_cwd = shlex.quote(cwd)
        cmd = f"cd {safe_cwd} && {command}"
    else:
        cmd = command
    # 在 pwd 标记前添加换行，确保 pwd 标记始终在单独一行
    return f"{cmd}; echo; echo '__SHANNON_PWD__:'$(pwd)"


def _extract_cwd_marker(output: str) -> str | None:
    for line in output.splitlines():
        if line.startswith("__SHANNON_PWD__:"):
            return line.replace("__SHANNON_PWD__:", "", 1).strip()
    return None


def _strip_cwd_marker(output: str) -> str:
    lines = [
        line for line in output.splitlines()
        if not line.startswith("__SHANNON_PWD__:")
    ]
    return "\n".join(lines).strip()


def _one_line(text: str | None) -> str | None:
    if not text:
        return None
    return text.strip().splitlines()[0] if text.strip() else None


def _short_block(text: str | None, max_lines: int = 8) -> str | None:
    if not text:
        return None
    lines = [line for line in text.strip().splitlines() if line.strip()]
    if not lines:
        return None
    return "\n".join(lines[:max_lines])
