"""Pydantic 数据模型集中管理"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field
from typing import Literal


class CommandItem(BaseModel):
    command: str
    purpose: str = ""


class AgentOutput(BaseModel):
    intent: str
    commands_plan: list[CommandItem] = Field(default_factory=list)
    risk_level: str = "LOW"
    reasoning: str = ""
    reply_message: str = ""


class ReActCommand(BaseModel):
    action: Literal["run"] = "run"
    command: str
    purpose: str = ""
    reasoning: str = ""
    risk_level: str = "LOW"  # LLM 标注：LOW / HIGH


class ReActDone(BaseModel):
    action: Literal["done"] = "done"
    message: str


class ReActAsk(BaseModel):
    action: Literal["ask"] = "ask"
    message: str
    reasoning: str = ""


class ReActDelegate(BaseModel):
    action: Literal["delegate"] = "delegate"
    target_agent: str
    reason: str
    risk_level: str = "LOW"  # LOW / HIGH
    context_for_delegate: str
    work_dir: str | None = None


@dataclass
class AgentConfig:
    api_base: str
    api_key: str
    model: str = "deepseek-chat"
    timeout_sec: int = 90
    max_context_messages: int = 20


ReActAction = ReActCommand | ReActDone | ReActAsk | ReActDelegate


# ---- 批量多服务器管理 ----

class MultiHostPayload(BaseModel):
    """单个主机信息（批量模式下使用，复用现有字段）"""
    id: int | None = None
    name: str = "Target Host"
    host: str = "localhost"
    port: int | None = None
    username: str | None = None
    password: str | None = None
    private_key: str | None = None
    use_local: bool = False


class HostPlanItem(BaseModel):
    """单台服务器的命令计划（independent 模式）"""
    host_id: int
    host_name: str = ""
    commands_plan: list[CommandItem] = Field(default_factory=list)


class BatchAgentOutput(BaseModel):
    """LLM 输出的批量执行计划（支持两种模式）"""
    execution_mode: str = "unified"
    reasoning: str = ""
    commands_plan: list[CommandItem] = Field(default_factory=list)
    host_plans: list[HostPlanItem] = Field(default_factory=list)
