from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
YAML_FILE = BASE_DIR / "config" / "shannon.yaml"

load_dotenv(dotenv_path=ENV_FILE, override=False)

SETTING_API_BASE = "api_base"
SETTING_API_KEY = "api_key"
SETTING_API_MODEL = "api_model"
SETTING_DEFAULT_SSH_PORT = "default_ssh_port"
SETTING_DASHSCOPE_API_KEY = "dashscope_api_key"
SETTING_DASHSCOPE_EMBED_MODEL = "dashscope_embed_model"
SETTING_AUX_MODEL = "aux_model"

SETTINGS_KEYS = [
    SETTING_API_BASE,
    SETTING_API_KEY,
    SETTING_API_MODEL,
    SETTING_DEFAULT_SSH_PORT,
    SETTING_DASHSCOPE_API_KEY,
    SETTING_DASHSCOPE_EMBED_MODEL,
    SETTING_AUX_MODEL,
]


@dataclass
class SettingsDefaults:
    api_base: str = "https://api.deepseek.com"
    api_model: str = "deepseek-chat"
    default_ssh_port: int = 22
    dashscope_api_key: str = ""
    dashscope_embed_model: str = "qwen3.7-text-embedding"
    aux_model: str = "deepseek-chat"


def env_fallback_aux_model() -> str | None:
    return os.getenv("DEEPSEEK_AUX_MODEL")


def env_fallback_dashscope_api_key() -> str | None:
    return os.getenv("DASHSCOPE_API_KEY")


def env_fallback_dashscope_embed_model() -> str | None:
    return os.getenv("DASHSCOPE_EMBED_MODEL")


def env_fallback_api_base() -> str | None:
    return os.getenv("DEEPSEEK_API_BASE")


def env_fallback_api_key() -> str | None:
    return os.getenv("DEEPSEEK_API_KEY")


def env_fallback_api_model() -> str | None:
    return os.getenv("DEEPSEEK_MODEL")


def env_fallback_default_ssh_port() -> int | None:
    raw = os.getenv("SHANNON_DEFAULT_SSH_PORT")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def yaml_fallbacks() -> dict[str, Any]:
    if not YAML_FILE.exists():
        return {}
    try:
        data = yaml.safe_load(YAML_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    llm = data.get("llm", {}) if isinstance(data, dict) else {}
    ssh = data.get("ssh", {}) if isinstance(data, dict) else {}
    result: dict[str, Any] = {}
    if isinstance(llm, dict):
        if llm.get("api_base"):
            result["api_base"] = str(llm["api_base"])
        if llm.get("api_key"):
            result["api_key"] = str(llm["api_key"])
        if llm.get("api_model"):
            result["api_model"] = str(llm["api_model"])
    if isinstance(ssh, dict):
        port = ssh.get("default_port")
        if isinstance(port, int):
            result["default_ssh_port"] = port
        elif isinstance(port, str) and port.isdigit():
            result["default_ssh_port"] = int(port)
    return result


def get_default_settings() -> dict[str, Any]:
    """获取配置优先级：DB > env > yaml > 代码默认值"""
    defaults = SettingsDefaults()
    yaml_settings = yaml_fallbacks()
    result: dict[str, Any] = {
        "api_base": env_fallback_api_base()
        or yaml_settings.get("api_base")
        or defaults.api_base,
        "api_key": env_fallback_api_key()
        or yaml_settings.get("api_key")
        or "",
        "api_model": env_fallback_api_model()
        or yaml_settings.get("api_model")
        or defaults.api_model,
        "default_ssh_port": env_fallback_default_ssh_port()
        or yaml_settings.get("default_ssh_port")
        or defaults.default_ssh_port,
        "dashscope_api_key": env_fallback_dashscope_api_key()
        or yaml_settings.get("dashscope_api_key")
        or defaults.dashscope_api_key,
        "dashscope_embed_model": env_fallback_dashscope_embed_model()
        or yaml_settings.get("dashscope_embed_model")
        or defaults.dashscope_embed_model,
        "aux_model": env_fallback_aux_model()
        or yaml_settings.get("aux_model")
        or defaults.aux_model,
    }
    return result


async def load_runtime_settings() -> dict[str, Any]:
    """从所有源加载运行时配置（含 DB 覆盖）"""
    from app.database import get_app_settings

    defaults = get_default_settings()
    keys = list(defaults.keys())
    db_settings = await get_app_settings(keys)
    runtime_cfg = defaults.copy()
    runtime_cfg.update(db_settings)
    return runtime_cfg
