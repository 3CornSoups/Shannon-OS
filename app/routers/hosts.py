from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import (
    delete_host,
    get_host_context,
    list_hosts,
    update_host,
    upsert_host_context,
)
from app.executor import ExecContext, ExecutorRouter, TargetHost
from app.connection import pool as ssh_pool
from app.settings import get_default_settings, load_runtime_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["hosts"])


class HostPayload(BaseModel):
    id: int | None = None
    name: str = "Target Host"
    host: str = "localhost"
    port: int | None = None
    username: str | None = None
    password: str | None = None
    private_key: str | None = None
    use_local: bool = False


class HostTestRequest(BaseModel):
    host: HostPayload


async def _build_target(payload: HostPayload) -> TargetHost:
    runtime_cfg = await load_runtime_settings()
    host_data = payload.model_dump()
    host_data.pop("id", None)
    if not host_data.get("port"):
        host_data["port"] = runtime_cfg["default_ssh_port"]
    return TargetHost(host_id=None, **host_data)


@router.get("/hosts")
async def api_list_hosts() -> List[Dict[str, Any]]:
    return await list_hosts()


@router.post("/hosts")
async def api_create_host(payload: HostPayload) -> dict[str, Any]:
    if not payload.name or not payload.name.strip():
        return {"ok": False, "message": "请填写服务器名称"}
    if not payload.host or not payload.host.strip():
        return {"ok": False, "message": "请填写服务器地址"}
    if not payload.username or not payload.username.strip():
        return {"ok": False, "message": "请填写用户名"}

    host_id = await upsert_host_context(
        name=payload.name.strip(),
        host=payload.host.strip(),
        port=payload.port or 22,
        username=payload.username.strip() if payload.username else None,
        last_pwd=payload.password.strip() if payload.password else None,
    )
    return {"ok": True, "id": host_id, "message": "服务器保存成功"}


@router.put("/hosts/{host_id}")
async def api_update_host(host_id: int, payload: HostPayload) -> dict[str, Any]:
    if not payload.name or not payload.name.strip():
        return {"ok": False, "message": "请填写服务器名称"}
    if not payload.host or not payload.host.strip():
        return {"ok": False, "message": "请填写服务器地址"}
    if not payload.username or not payload.username.strip():
        return {"ok": False, "message": "请填写用户名"}

    success = await update_host(
        host_id=host_id,
        name=payload.name.strip(),
        host=payload.host.strip(),
        port=payload.port or 22,
        username=payload.username.strip() if payload.username else None,
        last_pwd=payload.password.strip() if payload.password else None,
    )
    return {"ok": True, "message": "服务器更新成功"} if success else {"ok": False, "message": "服务器不存在"}


@router.delete("/hosts/{host_id}")
async def api_delete_host(host_id: int) -> dict[str, Any]:
    success = await delete_host(host_id)
    return {"ok": True, "message": "服务器删除成功"} if success else {"ok": False, "message": "服务器不存在或删除失败"}


@router.post("/host/test")
async def api_host_test(payload: HostTestRequest) -> dict[str, Any]:
    target = await _build_target(payload.host)

    if not target.host or not target.host.strip():
        return {"ok": False, "message": "请填写服务器地址"}
    if not target.username or not target.username.strip():
        return {"ok": False, "message": "请填写SSH用户名"}

    # 如果密码为空或掩码 ***，从 DB 加载真实密码
    if not target.password or target.password.strip() in ("", "***"):
        host_id = payload.host.id
        if host_id and host_id > 0:
            stored = await get_host_context(host_id)
            if stored:
                real_pwd = stored.get("last_pwd")
                if real_pwd and real_pwd != "***":
                    target.password = real_pwd

    has_password = bool(target.password and target.password.strip())
    has_key = bool(target.private_key and target.private_key.strip())
    if not has_password and not has_key:
        return {"ok": False, "message": "请填写SSH密码或私钥"}

    if target.use_local:
        return {"ok": True, "message": "本地连接模式"}

    # 释放连接池中该主机的旧连接，确保用最新密码测试
    await ssh_pool.release_connection(target.host, target.port, target.username)

    try:
        executor = ExecutorRouter.create_executor(target)
        result = await executor.run("echo shannon_connected", ExecContext(timeout_sec=12))
        ok = "shannon_connected" in (result.stdout or "")
        return {
            "ok": ok,
            "message": "服务器连接成功。" if ok else f"服务器连接失败: {result.stderr or result.stdout}",
        }
    except Exception as exc:
        error_msg = str(exc)
        if "Connection refused" in error_msg:
            return {"ok": False, "message": "连接被拒绝，请检查服务器地址和端口是否正确，以及SSH服务是否正在运行"}
        elif "Authentication failed" in error_msg:
            return {"ok": False, "message": "认证失败，请检查用户名和密码/私钥是否正确"}
        elif "timeout" in error_msg.lower():
            return {"ok": False, "message": "连接超时，请检查服务器地址是否正确，以及网络是否通畅"}
        else:
            return {"ok": False, "message": f"服务器连接失败: {error_msg}"}


@router.get("/context/{host_id}")
async def api_get_context(host_id: int) -> Dict[str, Any]:
    # 不返回解密凭据（前端无消费者依赖密码字段；后端连接走内部解密路径）
    host_context = await get_host_context(host_id, decrypt_pwd=False)
    if not host_context:
        raise HTTPException(status_code=404, detail="host not found")
    host_context.pop("last_pwd", None)
    host_context.pop("pwd_encrypted", None)
    return host_context
