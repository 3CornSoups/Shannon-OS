"""Generic LLM client for the AIOS layer.

Phase 1: delegates to app.llm_client for all actual API calls.
Key extension: try_tool_call accepts an optional `tools` parameter
to override the default tool set (app.llm_client hardcodes REACT_TOOLS).

Phase 2+: provider abstraction, caching, rate-limiting, etc.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

# Re-export existing utilities unchanged
from app.llm_client import (
    extract_json,
    extract_think,
    request_text,
    request_text_from_messages,
    stream_reply as _stream_reply,
    try_tool_call as _legacy_try_tool_call,
)


async def request_text_stream(
    api_base: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_sec: int = 90,
) -> AsyncGenerator[str, None]:
    """Streaming LLM call — thin wrapper over app.llm_client.stream_reply."""
    async for chunk in _stream_reply(api_base, api_key, model, messages, timeout_sec):
        yield chunk


async def try_tool_call(
    api_base: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_sec: int = 90,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Tool-calling with optional override tools.

    When `tools` is None, delegates to the existing app.llm_client function
    (which uses the hardcoded REACT_TOOLS).  When `tools` is provided,
    does a direct httpx call with the custom tool list.

    Returns {"name": str, "arguments": dict} or None.
    """
    if tools is None:
        return await _legacy_try_tool_call(api_base, api_key, model, messages, timeout_sec)

    # -- custom tools path --
    import json
    import httpx

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "stream": False,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            response = await client.post(
                f"{api_base.rstrip('/')}/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except Exception:
        return None

    choice = data.get("choices", [{}])[0]
    msg = choice.get("message", {})
    tool_calls = msg.get("tool_calls")
    if not tool_calls:
        return None

    tc = tool_calls[0]
    try:
        args = json.loads(tc["function"]["arguments"])
    except Exception:
        return None
    return {"name": tc["function"]["name"], "arguments": args}
