from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _mask_api_key(api_key: str) -> str:
    if not api_key or len(api_key) < 8:
        return "***"
    return f"{api_key[:4]}...{api_key[-4:]}"


def _generate_filename(prefix: str, api_key: str | None) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    masked = _mask_api_key(api_key) if api_key else "unknown"
    unique_id = uuid.uuid4().hex[:8]
    return f"{timestamp}_{prefix}_{unique_id}_{masked}.json"


def save_llm_log(
    system_prompt: str,
    user_prompt: str,
    model: str,
    api_base: str,
    request_data: dict[str, Any],
    response_data: dict[str, Any] | None = None,
    thinking_content: str | None = None,
    api_key: str | None = None,
) -> Path:
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "api_base": api_base,
        "api_key_masked": _mask_api_key(api_key) if api_key else None,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "request": request_data,
        "response": response_data,
        "thinking_content": thinking_content,
    }

    filename = _generate_filename("llm", api_key)
    filepath = LOG_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(log_entry, f, ensure_ascii=False, indent=2)

    return filepath


def save_stream_log(
    system_prompt: str,
    user_prompt: str,
    model: str,
    api_base: str,
    thinking_chunks: list[str],
    final_response: str | None,
    api_key: str | None = None,
) -> Path:
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "api_base": api_base,
        "api_key_masked": _mask_api_key(api_key) if api_key else None,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "thinking_content": "".join(thinking_chunks),
        "final_response": final_response,
        "stream": True,
    }

    filename = _generate_filename("stream", api_key)
    filepath = LOG_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(log_entry, f, ensure_ascii=False, indent=2)

    return filepath