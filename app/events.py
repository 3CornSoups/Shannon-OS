from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)

# 未连接事件的 TTL（秒）— 超时自动清理
EVENT_TTL_SEC = 600


class EventStore:
    """可靠的 SSE 事件系统

    支持：
    - 事件缓存（前端未连接时暂存）
    - 断线重连后重放缓存事件
    - 自动清理过期事件（防止内存增长）
    """

    def __init__(self):
        self._subscriptions: Dict[str, Dict[str, Any]] = {}

    def subscribe(self, task_id: str, queue: asyncio.Queue) -> list[dict]:
        """订阅 task_id 的事件流，返回之前缓存的事件列表"""
        if task_id not in self._subscriptions:
            self._subscriptions[task_id] = {"queue": queue, "events": [], "_created_at": time.time()}
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
                sub["queue"].put_nowait(data)
                return
            except (asyncio.QueueFull, Exception):
                pass
        # 前端未连接或队列已满，缓存事件
        if task_id not in self._subscriptions:
            self._subscriptions[task_id] = {"events": [], "_created_at": time.time()}
        self._subscriptions[task_id].setdefault("events", []).append(data)

    def unsubscribe(self, task_id: str):
        """清理 task_id 的订阅"""
        self._subscriptions.pop(task_id, None)

    def is_done(self, task_id: str) -> bool:
        """检查任务是否已完成（已取消订阅）"""
        return task_id not in self._subscriptions

    def cleanup(self):
        """清理已过期的事件缓存（超过 TTL 且无活跃订阅者）"""
        now = time.time()
        expired = [
            tid for tid, sub in self._subscriptions.items()
            if "queue" not in sub and (now - sub.get("_created_at", now)) > EVENT_TTL_SEC
        ]
        for tid in expired:
            self._subscriptions.pop(tid, None)
        if expired:
            logger.debug(f"EventStore 清理了 {len(expired)} 个过期事件")


event_store = EventStore()
