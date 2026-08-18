from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request

from pydantic import BaseModel

from app.database import set_app_setting, get_app_settings
from app.settings import get_default_settings, SETTINGS_KEYS, load_runtime_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings")
async def api_get_settings() -> dict:
    defaults = get_default_settings()
    keys = list(defaults.keys())
    db_settings = await get_app_settings(keys)
    runtime = defaults.copy()
    runtime.update(db_settings)
    return runtime


@router.post("/settings")
async def api_save_settings(request: Request) -> dict:
    data = await request.json()
    for key, value in data.items():
        await set_app_setting(key, str(value))
    return {"ok": True, "message": "设置保存成功"}


@router.post("/settings/test")
async def api_test_api_connection(request: Request) -> dict:
    data = await request.json()
    api_key = data.get("api_key")
    api_base = data.get("api_base", "https://api.deepseek.com")
    api_model = data.get("api_model", "deepseek-chat")

    if not api_key:
        return {"ok": False, "message": "请输入API Key"}

    # 校验 API 地址格式：仅允许 http/https，拒绝 file:// 等非网络 scheme
    from urllib.parse import urlparse
    parsed = urlparse(api_base)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return {"ok": False, "message": "API 地址格式无效（需 http/https）"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_base}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": api_model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Test connection"},
                    ],
                    "max_tokens": 10,
                },
                timeout=10.0,
            )

        if response.status_code == 200:
            return {"ok": True, "message": "API连接成功"}
        else:
            return {
                "ok": False,
                "message": f"API连接失败: {response.status_code} - {response.text}",
            }
    except Exception as exc:
        return {"ok": False, "message": f"API连接失败: {str(exc)}"}


class TemplateGenerateRequest(BaseModel):
    description: str


@router.post("/templates/generate")
async def api_generate_template(payload: TemplateGenerateRequest) -> dict:
    """根据用户描述，用 LLM 生成执行计划模板"""
    runtime = await load_runtime_settings()
    api_key = runtime.get("api_key", "")
    api_base = runtime.get("api_base", "https://api.deepseek.com")
    api_model = runtime.get("api_model", "deepseek-chat")

    if not api_key:
        return {"ok": False, "message": "API Key 未配置，请先在设置页面配置"}

    system_prompt = (
        "你是一个运维模板生成器。根据用户的描述，生成一个执行计划模板。\n"
        "输出必须是严格 JSON 对象，包含以下字段：\n"
        "- name: 模板名称（简短，不超过10个字）\n"
        "- category: 分类（如：基础管理、进程服务、Docker 容器、软件管理、用户权限、安全巡检、运维自动化）\n"
        "- prompt: 发送给运维助手的提示词（详细描述要执行的操作）\n"
        "- description: 模板描述（一句话说明用途，不超过20字）\n"
        "例：{\"name\": \"磁盘检查\", \"category\": \"基础管理\", \"prompt\": \"帮我检查磁盘使用并指出风险分区\", \"description\": \"检查磁盘使用情况\"}"
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_base}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": api_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": payload.description},
                    ],
                    "temperature": 0.7,
                },
                timeout=30.0,
            )

        if response.status_code != 200:
            return {"ok": False, "message": f"API调用失败: {response.text}"}

        data = response.json()
        raw = data["choices"][0]["message"]["content"]
        import json, re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return {"ok": False, "message": "模型返回格式异常，请重试"}
        template = json.loads(match.group(0))
        return {"ok": True, "template": template}
    except Exception as exc:
        return {"ok": False, "message": f"生成失败: {str(exc)}"}


# ---- 通知渠道配置 ----

@router.get("/settings/notifications")
async def api_get_notification_settings() -> dict:
    from app.database import NOTIFICATION_SETTING_KEYS, get_app_settings
    settings = await get_app_settings(list(NOTIFICATION_SETTING_KEYS))
    return {"ok": True, "data": settings}


@router.put("/settings/notifications")
async def api_save_notification_settings(request: Request) -> dict:
    from app.database import set_app_setting
    data = await request.json()
    for key, value in data.items():
        await set_app_setting(key, str(value))
    return {"ok": True, "message": "通知配置保存成功"}


@router.post("/settings/notifications/test")
async def api_test_notification(request: Request) -> dict:
    from app.notification import NotificationManager
    data = await request.json()
    channel = data.get("channel", "")
    if not channel:
        return {"ok": False, "message": "请指定渠道 (dingtalk/email/webhook)"}

    # 先保存临时配置
    from app.database import set_app_setting
    for key, value in data.items():
        if key != "channel":
            await set_app_setting(key, str(value))

    nm = NotificationManager()
    return await nm.send_test(channel)
