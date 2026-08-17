"""Echo — AIOS 日常聊天门面 Agent（检索增强纯聊天）。

自包含包：agent / router / memory / fts / report / prompts / db。
对外暴露 echo_agent 单例与 echo_router。
"""

from aios.echo.agent import EchoAgent, echo_agent
from aios.echo.db import init_echo_db
from aios.echo.router import router as echo_router

__all__ = ["EchoAgent", "echo_agent", "echo_router", "init_echo_db"]
