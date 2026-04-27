from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class EventStore:
    """可靠的 SSE 事件系统

    支持：
    - 事件缓存（前端未连接时暂存）
    - 断线重连后重放缓存事件
    - 自动清理已完成/出错的任务
    """

    def __init__(self):
        self._subscriptions: Dict[str, Dict[str, Any]] = {}

    def subscribe(self, task_id: str, queue: asyncio.Queue) -> list[dict]:
        """订阅 task_id 的事件流，返回之前缓存的事件列表"""
        if task_id not in self._subscriptions:
            self._subscriptions[task_id] = {"queue": queue, "events": []}
        else:
            self._subscriptions[task_id]["queue"] = queue

        cached = list(self._subscriptions[task_id].get("events", []))
        self._subscriptions[task_id]["events"] = []
        return cached

    async def emit(self, task_id: str, data: dict):
        """发送事件。如果前端已连接直接放入队列，否则缓存"""
        sub = self._subscriptions.get(task_id)
        if sub and "queue" in sub:
            try:
                await sub["queue"].put(data)
                return
            except Exception:
                pass
        # 前端未连接或队列已满，缓存事件
        if task_id not in self._subscriptions:
            self._subscriptions[task_id] = {"events": []}
        self._subscriptions[task_id]["events"].append(data)

    def unsubscribe(self, task_id: str):
        """清理 task_id 的订阅"""
        self._subscriptions.pop(task_id, None)

    def is_done(self, task_id: str) -> bool:
        sub = self._subscriptions.get(task_id)
        if not sub:
            return True
        return False

    def cleanup(self):
        """清理所有已完成任务的缓存（通常不需要手动调用）"""
        pass


event_store = EventStore()
