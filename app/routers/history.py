from __future__ import annotations

from fastapi import APIRouter, Query

from app.database import list_env_snapshots, list_user_actions

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history/actions/{host_id}")
async def api_list_actions(host_id: int, limit: int = Query(default=100, le=500)):
    return await list_user_actions(host_id, limit)


@router.get("/history/env-snapshots/{host_id}")
async def api_list_env(host_id: int, limit: int = Query(default=20, le=100)):
    return await list_env_snapshots(host_id, limit)
