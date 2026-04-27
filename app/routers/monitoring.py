from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.database import get_host_context
from app.monitor import ServerInfo, SystemMonitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["monitoring"])


@router.post("/monitor/{host_id}")
async def api_get_monitor(host_id: int) -> dict:
    host_info = await get_host_context(host_id)
    if not host_info:
        raise HTTPException(status_code=404, detail="host not found")

    try:
        server = ServerInfo(
            host=host_info["host"],
            port=host_info["port"] or 22,
            username=host_info.get("username"),
            password=host_info.get("last_pwd"),
        )
        monitor = SystemMonitor(server)
        system_info = await monitor.get_system_info()
        return {"ok": True, "data": system_info}
    except Exception as exc:
        logger.error(f"监控数据采集失败: {exc}")
        return {"ok": False, "message": f"监控数据采集失败: {str(exc)}"}
