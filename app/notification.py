from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP_SSL, SMTP
from typing import Any

import httpx

from app.database import get_app_settings, NOTIFICATION_SETTING_KEYS

logger = logging.getLogger(__name__)


class NotificationManager:

    async def _get_config(self) -> dict[str, str]:
        return await get_app_settings(list(NOTIFICATION_SETTING_KEYS))

    async def send_alert(self, alert_record: dict, channels: list[str]) -> None:
        if not channels:
            return
        tasks = []
        if "dingtalk" in channels:
            tasks.append(self._send_dingtalk(alert_record, "alert"))
        if "email" in channels:
            tasks.append(self._send_email(alert_record, "alert"))
        if "webhook" in channels:
            tasks.append(self._send_webhook(alert_record, "alert"))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def send_merged_alert(self, host_id: int, alerts: list[dict]) -> None:
        if not alerts:
            return

        rules_text = "\n".join([
            f"- {a['rule'].get('name', '')}: {a['message']}"
            for a in alerts
        ])

        all_channels = set()
        for a in alerts:
            channels_raw = a["rule"].get("channels", "[]")
            try:
                ch = json.loads(channels_raw) if isinstance(channels_raw, str) else channels_raw
            except Exception:
                ch = []
            all_channels.update(ch)

        merged_record = {
            "event_id": None,
            "rule": {"name": f"多告警汇总 ({len(alerts)}条)"},
            "current_value": 0,
            "threshold": 0,
            "message": f"服务器触发 {len(alerts)} 条告警：\n{rules_text}",
        }

        tasks = []
        if "dingtalk" in all_channels:
            tasks.append(self._send_dingtalk(merged_record, "merged", rules_text))
        if "email" in all_channels:
            tasks.append(self._send_email(merged_record, "merged", rules_text))
        if "webhook" in all_channels:
            tasks.append(self._send_webhook(merged_record, "merged", rules_text))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def send_recovery(self, alert_record: dict) -> None:
        msg = f"已恢复: {alert_record.get('message', '')}"
        alert_record["message"] = msg
        channels_raw = "[]"
        try:
            from app.database import get_alert_rule_by_id
            rule_id = alert_record.get("rule_id", 0)
            rule = await get_alert_rule_by_id(rule_id)
            if rule:
                channels_raw = rule.get("channels", "[]")
        except Exception:
            pass

        try:
            channels = json.loads(channels_raw) if isinstance(channels_raw, str) else channels_raw
        except Exception:
            channels = []

        if not channels:
            return
        tasks = []
        if "dingtalk" in channels:
            tasks.append(self._send_dingtalk(alert_record, "recovery"))
        if "email" in channels:
            tasks.append(self._send_email(alert_record, "recovery"))
        if "webhook" in channels:
            tasks.append(self._send_webhook(alert_record, "recovery"))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_dingtalk(self, record: dict, event_type: str, extra_text: str = "") -> None:
        config = await self._get_config()
        webhook_url = config.get("dingtalk_webhook_url", "")
        secret = config.get("dingtalk_secret", "")

        if not webhook_url:
            logger.debug("钉钉 Webhook URL 未配置，跳过")
            return

        title_prefix = {"alert": "🚨 告警通知", "recovery": "✅ 恢复通知", "merged": "🚨 多告警汇总"}
        title = title_prefix.get(event_type, "告警通知")

        rule_name = record.get("rule", {}).get("name", "") if isinstance(record.get("rule"), dict) else record.get("rule_name", "")
        message = record.get("message", "")
        current_value = record.get("current_value", "")
        threshold = record.get("threshold", "")

        text = f"## {title}\n\n**规则：** {rule_name}\n**详情：** {message}\n"
        if current_value and threshold:
            text += f"**当前值：** {current_value}\n**阈值：** {threshold}\n"
        if extra_text:
            text += f"\n{extra_text}\n"

        payload = {"msgtype": "markdown", "markdown": {"title": title, "text": text}}

        try:
            timestamp = str(round(time.time() * 1000))
            url = webhook_url
            if secret:
                sign = self._dingtalk_sign(timestamp, secret)
                url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, timeout=10)
                logger.info(f"钉钉通知发送: status={resp.status_code}")
        except Exception as e:
            logger.error(f"钉钉通知发送失败: {e}")

    def _dingtalk_sign(self, timestamp: str, secret: str) -> str:
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        )
        return hmac_code.hexdigest()

    async def _send_email(self, record: dict, event_type: str, extra_text: str = "") -> None:
        config = await self._get_config()
        smtp_host = config.get("smtp_host", "")
        smtp_port = config.get("smtp_port", "465")
        smtp_username = config.get("smtp_username", "")
        smtp_password = config.get("smtp_password", "")
        recipients_raw = config.get("smtp_recipients", "")

        if not smtp_host or not smtp_username or not recipients_raw:
            logger.debug("SMTP 配置不完整，跳过邮件通知")
            return

        recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
        if not recipients:
            return

        rule_name = record.get("rule", {}).get("name", "") if isinstance(record.get("rule"), dict) else record.get("rule_name", "")
        message = record.get("message", "")

        title_prefix = {"alert": "告警", "recovery": "恢复", "merged": "多告警汇总"}
        title_label = title_prefix.get(event_type, "通知")

        subject = f"[Shannon OS {title_label}] {rule_name}"

        html = f"""
        <html><body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #ef4444;">{title_label}</h2>
        <p><strong>规则：</strong> {rule_name}</p>
        <p><strong>详情：</strong> {message}</p>
        {f"<pre>{extra_text}</pre>" if extra_text else ""}
        <hr><p style="color: #64748b; font-size: 12px;">Shannon OS 监控告警系统</p>
        </body></html>
        """

        def _smtp_send():
            port = int(smtp_port)
            if port == 465:
                server = SMTP_SSL(smtp_host, port, timeout=10)
            else:
                server = SMTP(smtp_host, port, timeout=10)
                server.starttls()

            server.login(smtp_username, smtp_password)

            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = smtp_username
            msg["To"] = ", ".join(recipients)
            msg.attach(MIMEText(html, "html", "utf-8"))

            server.sendmail(smtp_username, recipients, msg.as_string())
            server.quit()

        try:
            await asyncio.to_thread(_smtp_send)
            logger.info(f"邮件通知发送成功: recipients={len(recipients)}")
        except Exception as e:
            logger.error(f"邮件通知发送失败: {e}")

    async def _send_webhook(self, record: dict, event_type: str, extra_text: str = "") -> None:
        config = await self._get_config()
        url = config.get("webhook_url", "")
        headers_raw = config.get("webhook_headers", "{}")

        if not url:
            logger.debug("Webhook URL 未配置，跳过")
            return

        try:
            headers = json.loads(headers_raw) if headers_raw else {}
        except Exception:
            headers = {}

        rule_name = record.get("rule", {}).get("name", "") if isinstance(record.get("rule"), dict) else record.get("rule_name", "")

        payload = {
            "event": event_type,
            "rule_name": rule_name,
            "message": record.get("message", ""),
            "severity": record.get("severity", ""),
            "current_value": record.get("current_value"),
            "threshold": record.get("threshold"),
            "triggered_at": record.get("triggered_at", ""),
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=10)
                logger.info(f"Webhook 通知发送: status={resp.status_code}")
        except Exception as e:
            logger.error(f"Webhook 通知发送失败: {e}")

    async def send_test(
        self, channel: str, config_override: dict[str, str] | None = None
    ) -> dict[str, Any]:
        test_record = {
            "rule": {"name": "测试通知"},
            "message": "这是一条来自 Shannon OS 监控告警系统的测试消息",
            "severity": "info",
            "current_value": 0,
            "threshold": 0,
            "triggered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        try:
            if channel == "dingtalk":
                await self._send_dingtalk(test_record, "alert")
            elif channel == "email":
                await self._send_email(test_record, "alert")
            elif channel == "webhook":
                await self._send_webhook(test_record, "alert")
            else:
                return {"ok": False, "message": f"未知渠道: {channel}"}
            return {"ok": True, "message": f"测试通知已发送到 {channel}"}
        except Exception as e:
            return {"ok": False, "message": f"发送失败: {str(e)}"}
