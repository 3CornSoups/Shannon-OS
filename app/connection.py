from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import asyncssh
import paramiko

logger = logging.getLogger(__name__)


@dataclass
class PoolKey:
    host: str
    port: int
    username: str | None

    def __hash__(self) -> int:
        return hash((self.host, self.port, self.username or ""))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PoolKey):
            return NotImplemented
        return (
            self.host == other.host
            and self.port == other.port
            and self.username == other.username
        )


@dataclass
class ConnectionEntry:
    """包装 asyncssh 连接 + 元数据"""
    conn: asyncssh.SSHClientConnection | None
    last_used: float = 0.0
    fail_count: int = 0
    use_paramiko: bool = False
    closed: bool = False


class SSHConnectionPool:
    """SSH 连接池

    管理到各主机的复用连接：
    - 按 (host, port, username) 为键缓存连接
    - 空闲超过 idle_timeout 秒的连接自动关闭
    - 连接失败计数超过 max_failures 后切换到 paramiko
    - 健康检查：使用前验证连接是否存活
    """

    def __init__(
        self,
        idle_timeout: int = 300,
        max_failures: int = 2,
        keepalive_interval: int = 30,
    ):
        self._pool: dict[PoolKey, ConnectionEntry] = {}
        self._lock = asyncio.Lock()
        self._idle_timeout = idle_timeout
        self._max_failures = max_failures
        self._keepalive_interval = keepalive_interval
        self._cleanup_task: asyncio.Task | None = None

    async def start(self):
        """启动后台清理任务"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("SSH连接池清理任务已启动")

    async def stop(self):
        """关闭所有连接并停止清理任务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        async with self._lock:
            for key, entry in list(self._pool.items()):
                await self._close_entry(entry)
            self._pool.clear()
        logger.info("SSH连接池已关闭")

    async def _cleanup_loop(self):
        """定期清理空闲连接"""
        while True:
            try:
                await asyncio.sleep(60)
                await self._evict_idle()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("连接池清理异常")

    async def _evict_idle(self):
        """关闭并移除空闲超时的连接"""
        now = time.time()
        async with self._lock:
            for key, entry in list(self._pool.items()):
                if entry.closed:
                    del self._pool[key]
                    continue
                if entry.conn and (now - entry.last_used) > self._idle_timeout:
                    logger.info(f"关闭空闲连接: {key}")
                    await self._close_entry(entry)
                    del self._pool[key]

    async def _close_entry(self, entry: ConnectionEntry):
        if entry.conn and not entry.closed:
            try:
                entry.conn.close()
            except Exception:
                pass
            entry.closed = True
            entry.conn = None

    def _build_connect_kwargs(self, password: str | None, private_key: str | None) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"known_hosts": None}
        if password:
            kwargs["password"] = password
        if private_key:
            kwargs["client_keys"] = [private_key]
        return kwargs

    def _build_paramiko_kwargs(self, password: str | None, private_key: str | None) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "timeout": 30,
        }
        if password:
            kwargs["password"] = password
        if private_key:
            kwargs["key_filename"] = private_key
        return kwargs

    async def _check_alive(self, entry: ConnectionEntry) -> bool:
        """检查 asyncssh 连接是否存活"""
        if not entry.conn or entry.closed:
            return False
        try:
            result = await asyncio.wait_for(
                entry.conn.run("echo alive", check=False),
                timeout=5,
            )
            return result.exit_status == 0
        except Exception:
            return False

    async def get_connection(
        self,
        host: str,
        port: int,
        username: str | None,
        password: str | None = None,
        private_key: str | None = None,
    ) -> ConnectionEntry:
        """获取一个 SSH 连接（可能复用已有连接）"""
        key = PoolKey(host=host, port=port, username=username)
        async with self._lock:
            entry = self._pool.get(key)

            # 如果有缓存连接，检查是否存活
            if entry and not entry.closed:
                if entry.use_paramiko:
                    # paramiko 模式不复用，每次都新建
                    # 但继续保留 entry 作为 fallback 状态标记
                    pass
                elif entry.conn:
                    alive = await self._check_alive(entry)
                    if alive:
                        entry.last_used = time.time()
                        return entry
                    else:
                        # 连接已断开，清理
                        logger.warning(f"连接已断开，将重建: {key}")
                        await self._close_entry(entry)
                        del self._pool[key]
                        entry = None
                else:
                    # conn 为 None 但未 closed（异常状态）
                    del self._pool[key]
                    entry = None

            # 需要新建连接
            if not entry:
                entry = ConnectionEntry(conn=None)
                self._pool[key] = entry

            try:
                kwargs = self._build_connect_kwargs(password, private_key)
                conn = await asyncio.wait_for(
                    asyncssh.connect(host, port=port, username=username, **kwargs),
                    timeout=15,
                )
                entry.conn = conn
                entry.fail_count = 0
                entry.use_paramiko = False
                entry.closed = False
                entry.last_used = time.time()
                logger.info(f"新建 SSH 连接: {key}")
                return entry
            except Exception as e:
                entry.fail_count += 1
                logger.warning(f"asyncssh 连接失败 ({entry.fail_count}/{self._max_failures}): {key} - {e}")

                # 达到最大失败次数，切换到 paramiko
                if entry.fail_count >= self._max_failures and (password or private_key):
                    entry.use_paramiko = True
                    entry.closed = False
                    entry.fail_count = 0  # 重置以便 paramiko 模式下重新计数
                    logger.info(f"切换至 paramiko 模式: {key}")
                    return entry

                # 还未达到阈值，保留 entry 让 fail_count 能累积（否则下次重试又从 0 开始）
                raise

    async def get_paramiko_client(
        self,
        host: str,
        port: int,
        username: str | None,
        password: str | None = None,
        private_key: str | None = None,
    ) -> paramiko.SSHClient:
        """创建 paramiko 客户端（用于连接池标记为 paramiko 模式时）"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs = self._build_paramiko_kwargs(password, private_key)
        client.connect(hostname=host, port=port, username=username, **kwargs)
        return client

    async def release_connection(self, host: str, port: int, username: str | None):
        """主动释放一个连接（出错时调用）"""
        key = PoolKey(host=host, port=port, username=username)
        async with self._lock:
            entry = self._pool.get(key)
            if entry:
                await self._close_entry(entry)
                del self._pool[key]


# 全局单例
pool = SSHConnectionPool()
