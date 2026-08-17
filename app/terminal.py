from pydantic import BaseModel

from app.database import get_host_context
from app.executor import SSHExecutor, ExecContext, ExecResult, TargetHost


class TerminalCommandRequest(BaseModel):
    host_id: int | None
    host: str
    port: int = 22
    username: str | None = None
    password: str | None = None
    private_key: str | None = None
    command: str


async def exec_terminal_command(payload: TerminalCommandRequest) -> dict:
    password = payload.password
    private_key = payload.private_key

    if (not password or password == "***") and payload.host_id:
        stored = await get_host_context(payload.host_id, decrypt_pwd=True)
        if stored:
            if not password or password == "***":
                password = stored.get("last_pwd") or password
            if not private_key:
                private_key = stored.get("private_key") or private_key

    target = TargetHost(
        host_id=payload.host_id,
        name="terminal-session",
        host=payload.host,
        port=payload.port,
        username=payload.username,
        password=password,
        private_key=private_key,
        use_local=False,
    )
    executor = SSHExecutor(target)
    context = ExecContext(cwd=None, timeout_sec=30)
    result: ExecResult = await executor.run(payload.command, context)
    return {
        "command": result.command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
