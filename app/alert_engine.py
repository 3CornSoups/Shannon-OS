from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.database import (
    get_active_rules_for_host,
    create_alert_event,
    find_active_alert,
    mark_alert_recovered,
)

logger = logging.getLogger(__name__)

# 记录每个 (host_id, rule_id) 的条件持续满足次数
_condition_duration: dict[tuple[int, int], int] = {}
# 记录最近一次通知时间（用于合并窗口）
_last_notification_time: dict[int, float] = {}
# 5 分钟内触发的待合并告警
_pending_merged_alerts: dict[int, list[dict[str, Any]]] = {}

MERGE_WINDOW = 300


class AlertEngine:

    async def evaluate(self, host_id: int, metrics: dict[str, Any]) -> None:
        rules = await get_active_rules_for_host(host_id)
        if not rules:
            return

        cpu = metrics.get("cpu", {})
        memory = metrics.get("memory", {})
        disk = metrics.get("disk", {})
        cpu_count = cpu.get("cpu_count", 1)

        newly_fired: list[dict[str, Any]] = []

        for rule in rules:
            rule_id = int(rule["id"])
            metric_type = rule["metric_type"]
            operator = rule["operator"]
            threshold = float(rule["threshold"])
            duration = int(rule.get("duration", 0))
            severity = rule.get("severity", "warning")

            # 提取当前值
            current_value = self._extract_value(
                metrics, metric_type, threshold, cpu_count
            )

            # 条件检查
            condition_met = self._check_condition(current_value, operator, threshold)
            key = (host_id, rule_id)

            if condition_met:
                count = _condition_duration.get(key, 0) + 1
                _condition_duration[key] = count

                if duration == 0 or count * 60 >= duration:
                    active = await find_active_alert(rule_id, host_id)
                    if not active:
                        message = self._build_message(rule, current_value)
                        event_id = await create_alert_event(
                            rule_id=rule_id,
                            host_id=host_id,
                            severity=severity,
                            current_value=current_value,
                            threshold=threshold,
                            message=message,
                        )
                        newly_fired.append({
                            "event_id": event_id,
                            "rule": rule,
                            "current_value": current_value,
                            "threshold": threshold,
                            "message": message,
                        })
                        logger.info(f"告警触发: host_id={host_id}, rule={rule['name']}, value={current_value}")
            else:
                _condition_duration.pop(key, None)
                active = await find_active_alert(rule_id, host_id)
                if active:
                    await mark_alert_recovered(rule_id, host_id)
                    await self._send_recovery(active)
                    logger.info(f"告警恢复: host_id={host_id}, rule={rule['name']}")

        # 发送新告警通知
        if newly_fired:
            await self._dispatch_notifications(host_id, newly_fired)

    def _extract_value(
        self, metrics: dict, metric_type: str, threshold: float, cpu_count: int
    ) -> float:
        cpu = metrics.get("cpu", {})
        memory = metrics.get("memory", {})
        disk = metrics.get("disk", {})

        if metric_type == "cpu":
            return float(cpu.get("usage_percent", 0))
        elif metric_type == "memory":
            return float(memory.get("usage_percent", 0))
        elif metric_type == "disk":
            partitions = disk.get("partitions", [])
            return max((p.get("usage_percent", 0) for p in partitions), default=0)
        elif metric_type == "load":
            load_1 = float(cpu.get("load_avg_1", 0))
            return load_1 / max(cpu_count, 1)
        return 0.0

    def _check_condition(self, value: float, operator: str, threshold: float) -> bool:
        if operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return value == threshold
        return False

    def _build_message(self, rule: dict, value: float) -> str:
        name = rule.get("name", "")
        metric = rule.get("metric_type", "")
        operator = rule.get("operator", ">")
        threshold = rule.get("threshold", 0)
        metric_names = {"cpu": "CPU使用率", "memory": "内存使用率", "disk": "磁盘使用率", "load": "系统负载"}
        unit = "%"
        if metric == "load":
            unit = " (负载/核心)"
        return f"{metric_names.get(metric, metric)} {operator} {threshold}{unit}，当前 {value}{unit}"

    async def _dispatch_notifications(self, host_id: int, alerts: list[dict]) -> None:
        now = time.time()
        last = _last_notification_time.get(host_id, 0)

        if now - last < MERGE_WINDOW:
            if host_id not in _pending_merged_alerts:
                _pending_merged_alerts[host_id] = []
            _pending_merged_alerts[host_id].extend(alerts)
            return

        # 如果有待合并告警，先发送合并通知
        if host_id in _pending_merged_alerts:
            merged = _pending_merged_alerts.pop(host_id)
            alerts = merged + alerts

        _last_notification_time[host_id] = now

        # 延迟导入避免循环依赖
        from app.notification import NotificationManager
        nm = NotificationManager()

        if len(alerts) == 1:
            a = alerts[0]
            channels_raw = a["rule"].get("channels", "[]")
            try:
                channels = json.loads(channels_raw) if isinstance(channels_raw, str) else channels_raw
            except Exception:
                channels = []
            await nm.send_alert(a, channels)
        else:
            await nm.send_merged_alert(host_id, alerts)

    async def _send_recovery(self, alert_record: dict) -> None:
        from app.notification import NotificationManager
        nm = NotificationManager()
        await nm.send_recovery(alert_record)
