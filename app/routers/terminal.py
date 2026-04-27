from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.terminal import TerminalCommandRequest, exec_terminal_command

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["terminal"])


@router.post("/terminal/exec")
async def api_terminal_exec(payload: TerminalCommandRequest) -> dict:
    try:
        result = await exec_terminal_command(payload)
        return {"ok": True, **result}
    except Exception as exc:
        logger.error(f"终端命令执行失败: {exc}")
        return {"ok": False, "message": str(exc), "stderr": str(exc)}
