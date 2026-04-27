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
    ReActDone,
)
from app.prompts import build_system_prompt
from app.errors import LLMAPIError, retry_async

logger = logging.getLogger(__name__)

# ── 高风险关键词（子串匹配，命令中包含任一关键词即触发 HIGH） ──
HIGH_RISK_KEYWORDS = [
    # 用户管理
    "useradd", "userdel", "usermod", "groupadd", "groupdel", "passwd",
    # 权限管理
    "chown", "chgrp", "chmod", "setenforce", "chcon",
    # 系统文件修改
    "/etc/passwd", "/etc/shadow", "/etc/sudoers", "/etc/fstab",
    "/etc/profile", "/etc/profile.d", "/etc/environment",
    "/etc/hosts", "/etc/hostname", "/etc/resolv.conf",
    "/etc/ssh", "/etc/nginx", "/etc/apache", "/etc/httpd",
    "/etc/mysql", "/etc/postgresql", "/etc/redis",
    "/etc/docker", "/etc/selinux",
    # 包管理
    "yum install", "yum remove", "yum erase", "yum update",
    "apt-get install", "apt-get remove", "apt-get purge", "apt-get autoremove",
    "apt install", "apt remove", "apt purge", "apt autoremove",
    "rpm -e", "rpm -i", "rpm -U", "rpm -q", "dpkg ",
    "pip install --system", "npm install -g",
    # 服务管理
    "systemctl", "service ", "init.d",
    # 网络/防火墙
    "iptables", "firewalld", "ufw ", "nft",
    # 内核/驱动
    "modprobe", "rmmod", "insmod", "dmesg -c",
    # 磁盘/存储
    "dd ", "shred", "mkfs", "fdisk", "parted", "mkswap", "mount ", "umount ",
    # 重启/关机
    "reboot", "shutdown", "poweroff", "init 0", "init 6", "halt",
    # SSH
    "ssh-keygen", "ssh-copy-id", "ssh-keyscan",
    # 定时任务
    "crontab", "cron ",
    # 进程管理
    "kill -9", "killall", "pkill",
    # 远程下载+执行
    "curl | sh", "curl | bash", "wget | sh", "wget | bash",
    "curl | /bin/sh", "curl | /bin/bash",
]

# ── 高风险正则模式（更灵活的匹配，触发任一即 HIGH） ──
HIGH_RISK_PATTERNS: list[re.Pattern] = [
    # rm 删除（排除 rm 开头的只读查询类命令）
    re.compile(r'\brm\s+(-[rfv]+\s+)?[/~]'),
    re.compile(r'\brm\s+-rf\b'),
    re.compile(r'\brm\s+-r[fv]?\b'),
    # sed -i 原地修改系统文件
    re.compile(r'sed\s+-i\b'),
    # sudo 特权操作
    re.compile(r'\bsudo\s+'),
    # 重定向到系统路径
    re.compile(r'>>?\s+/etc/'),
    re.compile(r'>\s+/boot/'),
    # 危险组合：下载后通过管道执行
    re.compile(r'(curl|wget)\s+.*\|\s*(sh|bash)'),
    # Docker 高危操作
    re.compile(r'docker\s+(rm\s+-f|system\s+prune|volume\s+rm|network\s+rm|run\s+--privileged)'),
    # chmod 递归或 777
    re.compile(r'chmod\s+(-R\s+)?777'),
    # 写入系统路径
    re.compile(r'(>|>>)\s*/(usr|bin|sbin|lib|opt)/'),
]

# ── 安全命令白名单（仅纯只读查询，修改系统状态的操作不能在此列） ──
SAFE_COMMAND_PREFIXES = (
    "echo ", "printf ", "which ", "type ",
    "cat ", "head ", "tail ", "less ", "more ",
    "grep ", "find ", "ls ", "pwd ",
    "who ", "w ", "last ", "ps ", "top ", "htop ",
    "df ", "free ", "uptime ", "arch ", "uname ", "hostname ", "id ", "whoami ",
    "date ", "cal ", "history ",
    "ping ", "netstat ", "ss ", "ip ", "nslookup ", "dig ",
    "cd ",
)


def assess_risk(command: str) -> tuple[str, str]:
    """评估单条命令的风险等级。

    Returns:
        (risk_level, reason) — risk_level 为 "HIGH" 或 "LOW", reason 为触发原因。
    """
    stripped = command.strip()

    # 安全命令：直接跳过（但要检查是否有输出重定向到系统路径）
    if stripped.startswith(SAFE_COMMAND_PREFIXES):
        if re.search(r'>>?\s+/etc/', stripped) or re.search(r'>>?\s+/boot/', stripped):
            return "HIGH", f"高危: 重定向写入系统路径"
        return "LOW", ""

    # 正则模式匹配
    for pattern in HIGH_RISK_PATTERNS:
        if pattern.search(stripped):
            return "HIGH", f"高危模式: {pattern.pattern}"

    # 关键词匹配
    for kw in HIGH_RISK_KEYWORDS:
        if kw in stripped:
            return "HIGH", f"高危关键词: {kw}"

    # 检查 rm（通用，不匹配正则的也检查）
    if re.search(r'\brm\b', stripped):
        return "HIGH", "高危操作: rm 删除命令"

    # 检查 mv/cp 覆盖
    if re.search(r'\b(mv|cp)\s+/[^\s]+', stripped):
        return "HIGH", "高危操作: 移动/复制系统文件"

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
        self, user_prompt: str, host_context: dict, mode: str
    ) -> AgentOutput:
        system_prompt = build_system_prompt(mode, host_context, stage="plan")
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
        self, user_prompt: str, host_context: dict, mode: str
    ) -> ReActAction | None:
        system_prompt = build_system_prompt(mode, host_context, stage="react")
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

    def _build_system_prompt(self, mode: str, host_context: dict, stage: str) -> str:
        return build_system_prompt(mode, host_context, stage)

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
        )
    elif name == "task_done":
        return ReActDone(message=args.get("message", ""))
    elif name == "ask_user":
        return ReActAsk(
            message=args.get("message", ""),
            reasoning=args.get("reasoning", ""),
        )
    return None


def _dict_to_action(data: dict) -> ReActAction:
    action_type = data.get("action")
    if action_type == "run":
        return ReActCommand(**data)
    elif action_type == "done":
        return ReActDone(**data)
    elif action_type == "ask":
        return ReActAsk(**data)
    raise ValueError(f"Unknown action: {action_type}")
