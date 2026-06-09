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


@router.get("/monitor/history/{host_id}")
async def api_get_monitor_history(
    host_id: int,
    from_time: str = "",
    to_time: str = "",
) -> dict:
    from app.database import get_metrics_history

    try:
        data = await get_metrics_history(host_id, from_time, to_time)
        return {"ok": True, "data": data}
    except Exception as exc:
        logger.error(f"查询历史监控数据失败: {exc}")
        return {"ok": False, "message": f"查询失败: {str(exc)}"}


@router.get("/monitor/overview")
async def api_get_monitor_overview() -> dict:
    from app.database import list_hosts, get_latest_metrics_for_all_hosts
    from app.database import get_alert_events as db_get_alert_events

    try:
        hosts = await list_hosts(decrypt_pwd=False)
        latest_metrics = await get_latest_metrics_for_all_hosts()
        metrics_by_host = {m["host_id"]: m for m in latest_metrics}

        result = []
        for h in hosts:
            host_id = h["id"]
            m = metrics_by_host.get(host_id)
            alerts, _ = await db_get_alert_events(host_id=host_id, status="alerting", page=1, page_size=100)
            active_alert_count = len(alerts)

            cpu_usage = m["cpu_usage"] if m else None
            memory_usage = m["memory_usage"] if m else None
            disk_usage = m["disk_max_usage"] if m else None

            if any(a.get("severity") == "critical" for a in alerts):
                status = "critical"
            elif any(a.get("severity") == "warning" for a in alerts):
                status = "warning"
            else:
                status = "healthy"

            result.append({
                "host_id": host_id,
                "host_name": h.get("name", h["host"]),
                "host_ip": h["host"],
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "disk_usage": disk_usage,
                "status": status,
                "active_alerts": active_alert_count,
                "last_collected_at": m["collected_at"] if m else None,
            })

        return {"ok": True, "data": result}
    except Exception as exc:
        logger.error(f"获取监控概览失败: {exc}")
        return {"ok": False, "message": f"获取失败: {str(exc)}"}
