from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request

from app.database import (
    get_alert_rules,
    get_alert_rule_by_id,
    create_alert_rule,
    update_alert_rule,
    delete_alert_rule,
    toggle_alert_rule,
    seed_preset_rules,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["alert-rules"])


@router.get("/alert-rules")
async def api_get_rules() -> dict:
    rules = await get_alert_rules()
    for r in rules:
        try:
            r["channels"] = json.loads(r.get("channels", "[]"))
        except Exception:
            r["channels"] = []
        try:
            r["host_ids"] = json.loads(r.get("host_ids", "[]"))
        except Exception:
            r["host_ids"] = []
    return {"ok": True, "data": rules}


@router.get("/alert-rules/{rule_id}")
async def api_get_rule(rule_id: int) -> dict:
    rule = await get_alert_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    try:
        rule["channels"] = json.loads(rule.get("channels", "[]"))
    except Exception:
        rule["channels"] = []
    try:
        rule["host_ids"] = json.loads(rule.get("host_ids", "[]"))
    except Exception:
        rule["host_ids"] = []
    return {"ok": True, "data": rule}


@router.post("/alert-rules")
async def api_create_rule(request: Request) -> dict:
    data = await request.json()
    required = ["name", "metric_type", "operator", "threshold"]
    for field in required:
        if not data.get(field):
            raise HTTPException(status_code=400, detail=f"缺少必填字段: {field}")
    rule_id = await create_alert_rule(data)
    return {"ok": True, "data": {"id": rule_id}}


@router.put("/alert-rules/{rule_id}")
async def api_update_rule(rule_id: int, request: Request) -> dict:
    data = await request.json()
    ok = await update_alert_rule(rule_id, data)
    if not ok:
        raise HTTPException(status_code=404, detail="规则不存在")
    return {"ok": True, "message": "更新成功"}


@router.delete("/alert-rules/{rule_id}")
async def api_delete_rule(rule_id: int) -> dict:
    ok = await delete_alert_rule(rule_id)
    if not ok:
        raise HTTPException(status_code=404, detail="规则不存在")
    return {"ok": True, "message": "删除成功"}


@router.put("/alert-rules/{rule_id}/toggle")
async def api_toggle_rule(rule_id: int) -> dict:
    ok = await toggle_alert_rule(rule_id)
    if not ok:
        raise HTTPException(status_code=404, detail="规则不存在")
    rule = await get_alert_rule_by_id(rule_id)
    return {"ok": True, "data": {"id": rule_id, "enabled": bool(rule["enabled"]) if rule else False}}


@router.post("/alert-rules/seed")
async def api_seed_rules() -> dict:
    count = await seed_preset_rules()
    return {"ok": True, "message": f"已导入 {count} 条预置规则" if count > 0 else "预置规则已存在，无需导入"}
