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


class ReActDone(BaseModel):
    action: Literal["done"] = "done"
    message: str


class ReActAsk(BaseModel):
    action: Literal["ask"] = "ask"
    message: str
    reasoning: str = ""


@dataclass
class AgentConfig:
    api_base: str
    api_key: str
    model: str = "deepseek-chat"
    timeout_sec: int = 90
    max_context_messages: int = 20


ReActAction = ReActCommand | ReActDone | ReActAsk
