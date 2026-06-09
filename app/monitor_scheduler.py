from __future__ import annotations

import asyncio
import logging
import os
import traceback
from dataclasses import dataclass

from app.monitor import ServerInfo, SystemMonitor
from app.database import (
    list_hosts,
    get_host_context,
    insert_metrics_snapshot,
    get_latest_metrics_for_all_hosts,
)

logger = logging.getLogger(__name__)


@dataclass
class MonitorScheduler:
    _task: asyncio.Task | None = None
    _interval: int = 60

    async def start(self) -> None:
        interval = int(os.getenv("SHANNON_MONITOR_INTERVAL", "60"))
        self._interval = max(interval, 10)
        self._task = asyncio.create_task(self._loop())
        logger.info(f"监控调度器已启动，采集间隔 {self._interval} 秒")

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            try:
                hosts = await list_hosts(decrypt_pwd=True)
                if not hosts:
                    logger.debug("无已配置服务器，跳过本次监控采集")
                    continue

                logger.info(f"开始采集 {len(hosts)} 台服务器监控数据")
                tasks = [self._collect_and_evaluate(h) for h in hosts]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                success = sum(1 for r in results if r is True)
                failed = len(hosts) - success
                logger.info(f"采集完成: 成功 {success}, 失败 {failed}")
            except Exception as e:
                logger.error(f"监控采集循环异常: {e}")

    async def _collect_and_evaluate(self, host: dict) -> bool:
        host_id = host["id"]
        host_ip = host.get("host", "unknown")
        try:
            server = ServerInfo(
                host=host["host"],
                port=host.get("port", 22),
                username=host.get("username"),
                password=host.get("last_pwd"),
            )
            monitor = SystemMonitor(server)
            data = await asyncio.wait_for(monitor.get_system_info(), timeout=15)

            await insert_metrics_snapshot(host_id, data)

            # 延迟导入避免循环依赖
            from app.alert_engine import AlertEngine
            engine = AlertEngine()
            await engine.evaluate(host_id, data)

            return True
        except asyncio.TimeoutError:
            logger.warning(f"服务器 {host_ip} (id={host_id}) 采集超时")
            return False
        except Exception as e:
            logger.warning(f"服务器 {host_ip} (id={host_id}) 采集失败: {e}")
            return False

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("监控调度器已停止")
