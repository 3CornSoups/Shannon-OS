from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.database import (
    get_alert_events,
    get_alert_event_by_id,
    acknowledge_alert_event,
    archive_alert_event,
    get_alert_stats,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["alerts"])


@router.get("/alerts")
async def api_get_alerts(
    host_id: int | None = Query(None),
    severity: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    items, total = await get_alert_events(
        host_id=host_id,
        severity=severity,
        status=status,
        page=page,
        page_size=page_size,
    )
    return {
        "ok": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/alerts/stats")
async def api_get_alert_stats() -> dict:
    stats = await get_alert_stats()
    return {"ok": True, "data": stats}


@router.get("/alerts/{event_id}")
async def api_get_alert(event_id: int) -> dict:
    event = await get_alert_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="告警不存在")
    return {"ok": True, "data": event}


@router.post("/alerts/{event_id}/acknowledge")
async def api_acknowledge_alert(event_id: int) -> dict:
    ok = await acknowledge_alert_event(event_id, operator="admin")
    if not ok:
        raise HTTPException(status_code=400, detail="告警已确认或不存在")
    return {"ok": True, "message": "已确认"}


@router.post("/alerts/{event_id}/archive")
async def api_archive_alert(event_id: int) -> dict:
    ok = await archive_alert_event(event_id)
    if not ok:
        raise HTTPException(status_code=404, detail="告警不存在")
    return {"ok": True, "message": "已归档"}
