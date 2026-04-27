"""LLM API 调用层"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, AsyncGenerator

import httpx

from app.errors import LLMAPIError, retry_async
from app.logger import save_llm_log, save_stream_log

logger = logging.getLogger(__name__)


async def request_text(
    api_base: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout_sec: int = 90,
) -> str:
    """非流式调用 LLM，传入 system + user 两条消息"""
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    headers = _headers(api_key)
    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        response = await client.post(
            _url(api_base), headers=headers, json=payload
        )
        response.raise_for_status()
        data = response.json()
        result = data["choices"][0]["message"]["content"]
        save_llm_log(system_prompt, user_prompt, model, api_base, payload, data, api_key=api_key)
        return result


async def request_text_from_messages(
    api_base: str,
    api_key: str,
    model: str,
    messages: list[dict],
    timeout_sec: int = 90,
) -> str:
    """非流式调用 LLM，传入预构建的 messages 列表"""
    payload = {"model": model, "stream": False, "messages": messages}
    headers = _headers(api_key)
    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        response = await client.post(
            _url(api_base), headers=headers, json=payload
        )
        response.raise_for_status()
        data = response.json()
        result = data["choices"][0]["message"]["content"]
        save_llm_log(
            system_prompt=messages[0]["content"] if messages and messages[0]["role"] == "system" else "",
            user_prompt=messages[-1]["content"] if messages else "",
            model=model, api_base=api_base, request_data=payload, response_data=data,
            api_key=api_key,
        )
        return result


async def stream_reply(
    api_base: str,
    api_key: str,
    model: str,
    messages: list[dict],
    timeout_sec: int = 90,
) -> AsyncGenerator[str, None]:
    """流式调用 LLM，逐 chunk 产出文本"""
    payload = {"model": model, "stream": True, "messages": messages}
    headers = _headers(api_key)
    full_content: list[str] = []

    async def _do_stream():
        nonlocal full_content
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            async with client.stream(
                "POST", _url(api_base), headers=headers, json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line.replace("data:", "", 1).strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = (
                            obj.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if delta:
                            full_content.append(delta)
                            yield delta
                    except Exception:
                        continue

    try:
        async for chunk in _do_stream():
            yield chunk
    except Exception as exc:
        logger.error(f"流式调用 LLM 失败: {exc}")
        raise LLMAPIError(f"LLM API 调用失败: {exc}")

    full_text = "".join(full_content)
    save_stream_log(
        system_prompt=messages[0]["content"] if messages and messages[0]["role"] == "system" else "",
        user_prompt=messages[-1]["content"] if messages else "",
        model=model, api_base=api_base,
        thinking_chunks=[], final_response=full_text, api_key=api_key,
    )


REACT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "在服务器上执行一条 shell 命令并观察输出",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的 shell 命令"},
                    "purpose": {"type": "string", "description": "这条命令的目的"},
                    "reasoning": {"type": "string", "description": "为什么执行这条命令"},
                },
                "required": ["command", "purpose", "reasoning"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_done",
            "description": "任务已完成，向用户报告最终结果",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "给用户的最终总结"},
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": "需要用户输入或确认时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "向用户提出的问题或需要确认的内容"},
                    "reasoning": {"type": "string", "description": "为什么需要用户介入"},
                },
                "required": ["message", "reasoning"],
            },
        },
    },
]


async def try_tool_call(
    api_base: str,
    api_key: str,
    model: str,
    messages: list[dict],
    timeout_sec: int = 90,
) -> dict | None:
    """尝试用 tool calling 获取结构化输出，返回首个 tool call 的 {name, arguments}"""
    headers = _headers(api_key)
    payload = {
        "model": model,
        "stream": False,
        "messages": messages,
        "tools": REACT_TOOLS,
        "tool_choice": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            response = await client.post(
                _url(api_base), headers=headers, json=payload
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


def extract_json(raw: str) -> dict[str, Any] | None:
    """从 LLM 响应中提取 JSON 对象（支持 markdown 代码块和嵌套花括号）"""
    clean = _strip_think(raw).strip()
    # 1) Try markdown code block first: ```json ... ```
    md_match = re.search(
        r"```(?:json)?\s*\n?(.*?)```", clean, re.DOTALL | re.IGNORECASE
    )
    if md_match:
        candidate = md_match.group(1).strip()
        try:
            return json.loads(candidate)
        except Exception:
            pass
    # 2) Try direct parse
    try:
        return json.loads(clean)
    except Exception:
        pass
    # 3) Balanced brace matching
    brace_stack = []
    start = -1
    for i, ch in enumerate(clean):
        if ch == "{":
            if not brace_stack:
                start = i
            brace_stack.append(i)
        elif ch == "}":
            if brace_stack:
                brace_stack.pop()
                if not brace_stack and start >= 0:
                    candidate = clean[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        start = -1
    return None


def extract_think(text: str) -> str:
    blocks = re.findall(r"<think>(.*?)</think>", text, flags=re.DOTALL | re.IGNORECASE)
    return "\n\n".join(b.strip() for b in blocks if b.strip())


def _strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _url(api_base: str) -> str:
    return f"{api_base.rstrip('/')}/v1/chat/completions"
