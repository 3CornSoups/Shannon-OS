"""Agent 核心：编排 LLM 调用、对话管理、命令验证"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from app.conversation import ConversationManager
from app.llm_client import (
    extract_json,
    extract_think,
    request_text,
    request_text_from_messages,
    stream_reply as llm_stream_reply,
    try_tool_call,
)
from app.models import (
    AgentConfig,
    AgentOutput,
    CommandItem,
    ReActAction,
    ReActAsk,
    ReActCommand,
    ReActDelegate,
    ReActDone,
)
from app.prompts import build_system_prompt
from app.errors import LLMAPIError, retry_async

logger = logging.getLogger(__name__)

# ── 硬阻断清单 —— 以下操作禁止自动执行，必须用户手动确认 ──
_HARD_BLOCK_PATTERNS: list[re.Pattern] = [
    # 裸盘写入 / 格式化
    re.compile(r'\bdd\s+.*of=/dev/'),
    re.compile(r'\bmkfs\b'),
    re.compile(r'\bmkswap\b'),
    re.compile(r'\bshred\b'),
    # fork 炸弹 / 高危 shell
    re.compile(r':\(\)\s*\{'),
    re.compile(r'curl.*\|.*(?:sh|bash|dash)'),
    re.compile(r'wget.*\|.*(?:sh|bash|dash)'),
    # root 全覆盖
    re.compile(r'\brm\s+-rf\s+/\b'),
    re.compile(r'\brm\s+-rf\s+/etc\b'),
    re.compile(r'\bchmod\s+-R\s+777\s+/'),
    # 系统级高危写操作
    re.compile(r'>\s*/etc/'),
    re.compile(r'>>\s*/etc/(?:passwd|shadow|sudoers)\b'),
]


def is_blocked(command: str) -> tuple[bool, str]:
    """检查命令是否命中硬阻断清单。返回 (blocked, reason)。"""
    for pat in _HARD_BLOCK_PATTERNS:
        if pat.search(command):
            return True, f"命中硬阻断规则: {pat.pattern}"
    return False, ""


def assess_risk(command: str) -> tuple[str, str]:
    """兼容旧接口：硬阻断 → HIGH，否则返回 LOW（实际风险由 LLM 标注）。"""
    blocked, reason = is_blocked(command)
    if blocked:
        return "HIGH", reason
    return "LOW", ""


class ShannonAgent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.conversation = ConversationManager(
            max_messages=config.max_context_messages
        )

    # ---- 意图分析 ----

    async def stage1_intent_analyze(
        self, user_prompt: str, host_context: dict, mode: str
    ) -> AgentOutput:
        system_prompt = build_system_prompt(mode, host_context, stage="intent")
        return await self._request_json(system_prompt, user_prompt)

    # ---- 计划生成 ----

    async def stage2_plan_generate(
        self, user_prompt: str, host_context: dict, mode: str, metrics_text: str = "", hosts_context: list[dict] | None = None
    ) -> AgentOutput:
        system_prompt = build_system_prompt(mode, host_context, stage="plan", metrics_text=metrics_text, hosts_context=hosts_context)
        return await self._request_json(system_prompt, user_prompt)

    # ---- 计划验证 ----

    @staticmethod
    def stage3_plan_validate(output: AgentOutput) -> AgentOutput:
        fixed = output.model_copy()
        fixed.risk_level = "HIGH" if fixed.risk_level.upper() == "HIGH" else "LOW"
        filtered: list[CommandItem] = []
        for item in fixed.commands_plan:
            cmd = item.command.strip()
            if not cmd:
                continue
            if any(t in cmd for t in ["\n", "\r"]):
                cmd = cmd.splitlines()[0].strip()
            filtered.append(CommandItem(command=cmd, purpose=item.purpose))
        fixed.commands_plan = filtered
        # 重新评估每条命令的风险
        final_risk = "LOW"
        risk_reasons = []
        for item in fixed.commands_plan:
            stripped = item.command.strip()
            risk_level, reason = assess_risk(stripped)
            if risk_level == "HIGH":
                final_risk = "HIGH"
                risk_reasons.append(reason)
        fixed.risk_level = final_risk
        if risk_reasons:
            fixed.reasoning = fixed.reasoning or "; ".join(risk_reasons)
        if not fixed.commands_plan and "chat" not in fixed.intent.lower():
            fixed.reply_message = fixed.reply_message or "当前需求更适合人工确认。"
        return fixed

    # ---- 自我修复 ----

    async def stage5_self_heal(self, failed_command: str, stderr: str, exit_code: int,
                                host_context: dict, mode: str, attempt: int) -> AgentOutput:
        prompt = (
            "上一步命令执行失败，请返回修复后的 JSON。"
            f"\n失败命令: {failed_command}"
            f"\n退出码: {exit_code}"
            f"\nstderr: {stderr[:2000]}"
            f"\n当前重试轮次: {attempt}"
        )
        system_prompt = build_system_prompt(mode, host_context, stage="heal")
        return await self._request_json(system_prompt, prompt)

    # ---- 流式响应 ----

    async def stream_reply(self, user_prompt: str):
        messages = self.conversation.get_messages()
        if not messages:
            messages = [{"role": "user", "content": user_prompt}]
        async for chunk in llm_stream_reply(
            self.config.api_base, self.config.api_key,
            self.config.model, messages, self.config.timeout_sec,
        ):
            yield chunk

    # ---- 首条 action（tool calling 优先） ----

    async def _request_first_action(
        self, user_prompt: str, host_context: dict, mode: str, metrics_text: str = "", hosts_context: list[dict] | None = None, available_tools_text: str = ""
    ) -> ReActAction | None:
        system_prompt = build_system_prompt(mode, host_context, stage="react", metrics_text=metrics_text, hosts_context=hosts_context, available_tools_text=available_tools_text)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        result = await try_tool_call(
            self.config.api_base, self.config.api_key,
            self.config.model, messages, self.config.timeout_sec,
        )
        return _tool_result_to_action(result)

    # ---- ReAct 循环中的 action ----

    async def _request_react_action(self) -> ReActAction:
        async def _do() -> ReActAction:
            messages = self.conversation.get_messages()
            if not messages:
                raise ValueError("Conversation 为空")
            result = await try_tool_call(
                self.config.api_base, self.config.api_key,
                self.config.model, messages, self.config.timeout_sec,
            )
            if result:
                action = _tool_result_to_action(result)
                if action:
                    return action
            raw = await request_text_from_messages(
                self.config.api_base, self.config.api_key,
                self.config.model, messages, self.config.timeout_sec,
            )
            data = extract_json(raw)
            if not data:
                logger.warning("LLM 返回非 JSON 响应，回退为 ReActDone: %.200s", raw)
                return ReActDone(message=raw.strip() or "任务已完成")
            return _dict_to_action(data)

        return await retry_async(
            _do, max_retries=2, base_delay=1.0,
            retryable_exceptions=(ValueError,),
        )

    # ---- 内部 JSON 请求 ----

    async def _request_json(self, system_prompt: str, user_prompt: str) -> AgentOutput:
        async def _do() -> AgentOutput:
            raw = await request_text(
                self.config.api_base, self.config.api_key,
                self.config.model, system_prompt, user_prompt,
                self.config.timeout_sec,
            )
            data = extract_json(raw)
            if not data:
                repaired = await request_text(
                    self.config.api_base, self.config.api_key,
                    self.config.model, system_prompt,
                    "你刚才输出不符合 JSON 格式，请严格只输出 JSON 对象。"
                    f"\n原问题: {user_prompt}",
                    self.config.timeout_sec,
                )
                data = extract_json(repaired)
            if not data:
                return AgentOutput(
                    intent="chat_fallback", commands_plan=[],
                    risk_level="HIGH", reasoning="LLM 返回结构异常",
                    reply_message="模型暂时无法给出可靠执行计划。",
                )
            try:
                return ShannonAgent.stage3_plan_validate(AgentOutput.model_validate(data))
            except ValidationError:
                return AgentOutput(
                    intent="chat_fallback", commands_plan=[],
                    risk_level="HIGH", reasoning="JSON 校验失败",
                    reply_message="返回结构校验失败。",
                )
        return await retry_async(
            _do, max_retries=2, base_delay=1.0,
            retryable_exceptions=(Exception,),
        )

    def _build_system_prompt(self, mode: str, host_context: dict, stage: str, metrics_text: str = "", hosts_context: list[dict] | None = None, available_tools_text: str = "") -> str:
        return build_system_prompt(mode, host_context, stage, metrics_text, hosts_context, available_tools_text)

    @staticmethod
    def extract_think(text: str) -> str:
        return extract_think(text)


def _tool_result_to_action(result: dict | None) -> ReActAction | None:
    if not result:
        return None
    name, args = result["name"], result["arguments"]
    if name == "execute_command":
        return ReActCommand(
            command=args.get("command", ""),
            purpose=args.get("purpose", ""),
            reasoning=args.get("reasoning", ""),
            risk_level=args.get("risk_level", "LOW"),
        )
    elif name == "task_done":
        return ReActDone(message=args.get("message", ""))
    elif name == "ask_user":
        return ReActAsk(
            message=args.get("message", ""),
            reasoning=args.get("reasoning", ""),
        )
    elif name == "delegate_task":
        return ReActDelegate(
            target_agent=args.get("target_agent", "claude_code"),
            reason=args.get("reason", ""),
            risk_level=args.get("risk_level", "LOW"),
            context_for_delegate=args.get("context_for_delegate", ""),
            work_dir=args.get("work_dir"),
        )
    return None


def _dict_to_action(data: dict) -> ReActAction:
    action_type = data.get("action")
    if action_type in ("run", "execute_command"):
        return ReActCommand(**data)
    elif action_type in ("done", "task_done"):
        return ReActDone(**data)
    elif action_type in ("ask", "ask_user"):
        return ReActAsk(**data)
    elif action_type in ("delegate", "delegate_task"):
        return ReActDelegate(**data)
    raise ValueError(f"Unknown action: {action_type}")
