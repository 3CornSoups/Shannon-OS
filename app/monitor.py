from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import asyncssh
import paramiko

from app.connection import pool

logger = logging.getLogger(__name__)


@dataclass
class ServerInfo:
    host: str
    port: int = 22
    username: str | None = None
    password: str | None = None
    private_key: str | None = None


class SystemMonitor:
    def __init__(self, server: ServerInfo):
        self.server = server

    async def collect_raw(self) -> dict[str, str]:
        commands = {
            "cpu_info": "nproc",
            "cpu_stat": "cat /proc/stat | head -1",
            "cpu_per_core": "grep '^cpu[0-9]' /proc/stat",
            "load_avg": "cat /proc/loadavg",
            "mem_info": "cat /proc/meminfo",
            "disk_info": "df -B1 | grep '^/'",
            "disk_detail": "df -h | grep '^/'",
            "net_info": "cat /proc/net/dev",
            "uptime": "cat /proc/uptime",
            "top_procs": "ps aux --sort=-%cpu | head -11 | tail -10",
        }
        try:
            return await self._run_with_asyncssh(commands)
        except Exception as e:
            logger.warning(f"asyncssh 监控采集失败，切换到 paramiko: {e}")
            return await self._run_with_paramiko(commands)

    async def _run_with_asyncssh(self, commands: dict[str, str]) -> dict[str, str]:
        entry = await pool.get_connection(
            host=self.server.host,
            port=self.server.port,
            username=self.server.username,
            password=self.server.password,
            private_key=self.server.private_key,
        )
        if entry.use_paramiko:
            return await self._run_with_paramiko(commands)

        results: dict[str, str] = {}
        for name, cmd in commands.items():
            try:
                completed = await asyncio.wait_for(
                    entry.conn.run(cmd, check=False), timeout=5
                )
                results[name] = (completed.stdout or "").strip()
            except asyncio.TimeoutError:
                results[name] = ""
            except Exception as e:
                logger.debug(f"命令 {name} 执行失败: {e}")
                results[name] = ""
        import time
        entry.last_used = time.time()
        return results

    async def _run_with_paramiko(self, commands: dict[str, str]) -> dict[str, str]:
        results: dict[str, str] = {}
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs: dict[str, Any] = {
            "hostname": self.server.host,
            "port": self.server.port,
            "username": self.server.username,
            "timeout": 10,
        }
        if self.server.password:
            connect_kwargs["password"] = self.server.password
        if self.server.private_key:
            connect_kwargs["key_filename"] = self.server.private_key
        try:
            client.connect(**connect_kwargs)
            for name, cmd in commands.items():
                try:
                    _stdin, stdout_f, _stderr = client.exec_command(cmd, timeout=10)
                    results[name] = stdout_f.read().decode().strip()
                except Exception:
                    results[name] = ""
        finally:
            client.close()
        return results

    def _parse_cpu(self, raw: dict) -> dict:
        cpu_count = int(raw.get("cpu_info", "1").strip() or "1")

        cpu_line = raw.get("cpu_stat", "")
        parts = cpu_line.split()
        cpu_values = [int(x) for x in parts[1:8]]
        cpu_total = sum(cpu_values)
        cpu_idle = cpu_values[3]
        cpu_usage = round(((cpu_total - cpu_idle) / cpu_total) * 100, 1) if cpu_total > 0 else 0.0

        per_core_usage = []
        core_lines = raw.get("cpu_per_core", "").strip().split("\n")
        for line in core_lines:
            parts = line.split()
            if len(parts) < 5:
                continue
            values = [int(x) for x in parts[1:8]]
            total = sum(values)
            idle = values[3]
            usage = round(((total - idle) / total) * 100, 1) if total > 0 else 0.0
            per_core_usage.append(usage)

        load_parts = raw.get("load_avg", "").split()
        load_1 = float(load_parts[0]) if len(load_parts) > 0 else 0.0
        load_5 = float(load_parts[1]) if len(load_parts) > 1 else 0.0
        load_15 = float(load_parts[2]) if len(load_parts) > 2 else 0.0

        return {
            "cpu_count": cpu_count,
            "usage_percent": cpu_usage,
            "per_core_usage": per_core_usage,
            "load_avg_1": load_1,
            "load_avg_5": load_5,
            "load_avg_15": load_15,
        }

    def _parse_memory(self, raw: dict) -> dict:
        mem_lines = raw.get("mem_info", "").split("\n")
        mem_data: dict[str, int] = {}
        for line in mem_lines:
            parts = line.split()
            if len(parts) >= 2:
                key = parts[0].rstrip(":")
                if parts[1].isdigit():
                    mem_data[key] = int(parts[1])

        total_kb = mem_data.get("MemTotal", 0)
        free_kb = mem_data.get("MemFree", 0)
        available_kb = mem_data.get("MemAvailable", free_kb)
        buffers_kb = mem_data.get("Buffers", 0)
        cached_kb = mem_data.get("Cached", 0)
        swap_total_kb = mem_data.get("SwapTotal", 0)
        swap_free_kb = mem_data.get("SwapFree", 0)

        used_kb = total_kb - available_kb
        swap_used_kb = swap_total_kb - swap_free_kb

        def fmt_kb(kb: int) -> str:
            if kb >= 1048576:
                return f"{kb / 1048576:.1f} GB"
            return f"{kb / 1024:.1f} MB"

        mem_pct = round((used_kb / total_kb) * 100, 1) if total_kb > 0 else 0.0
        swap_pct = round((swap_used_kb / swap_total_kb) * 100, 1) if swap_total_kb > 0 else 0.0

        return {
            "total": fmt_kb(total_kb),
            "used": fmt_kb(used_kb),
            "free": fmt_kb(available_kb),
            "buffers": fmt_kb(buffers_kb),
            "cached": fmt_kb(cached_kb),
            "usage_percent": mem_pct,
            "swap_total": fmt_kb(swap_total_kb),
            "swap_used": fmt_kb(swap_used_kb),
            "swap_free": fmt_kb(swap_free_kb),
            "swap_percent": swap_pct,
            "total_kb": total_kb,
            "used_kb": used_kb,
        }

    def _parse_disk(self, raw: dict) -> dict:
        partitions = []
        disk_lines = raw.get("disk_info", "").strip().split("\n")
        detail_lines = raw.get("disk_detail", "").strip().split("\n")
        details_map: dict[str, str] = {}
        for dl in detail_lines:
            parts = dl.split()
            if parts:
                details_map[parts[-1]] = dl

        for line in disk_lines:
            parts = line.split()
            if len(parts) >= 6:
                filesystem = parts[0]
                total_bytes = int(parts[1])
                used_bytes = int(parts[2])
                avail_bytes = int(parts[3])
                use_pct = int(parts[4].replace("%", ""))
                mount_point = parts[5]

                def fmt_bytes(b: int) -> str:
                    if b >= 1073741824:
                        return f"{b / 1073741824:.1f} GB"
                    return f"{b / 1048576:.1f} MB"

                detail = details_map.get(mount_point, "")
                partitions.append({
                    "filesystem": filesystem,
                    "mount": mount_point,
                    "total": fmt_bytes(total_bytes),
                    "used": fmt_bytes(used_bytes),
                    "available": fmt_bytes(avail_bytes),
                    "usage_percent": use_pct,
                    "detail": detail,
                })

        return {"partitions": partitions}

    def _parse_network(self, raw: dict) -> dict:
        net_lines = raw.get("net_info", "").strip().split("\n")[2:]
        total_rx = 0
        total_tx = 0
        interfaces = []

        for line in net_lines:
            parts = line.split(":")
            if len(parts) < 2:
                continue
            iface = parts[0].strip()
            stats = parts[1].split()
            if len(stats) < 10:
                continue
            rx_bytes = int(stats[0])
            tx_bytes = int(stats[8])
            total_rx += rx_bytes
            total_tx += tx_bytes

            def fmt_bytes(b: int) -> str:
                if b >= 1073741824:
                    return f"{b / 1073741824:.2f} GB"
                if b >= 1048576:
                    return f"{b / 1048576:.2f} MB"
                if b >= 1024:
                    return f"{b / 1024:.2f} KB"
                return f"{b} B"

            interfaces.append({
                "name": iface,
                "rx_bytes": rx_bytes,
                "tx_bytes": tx_bytes,
                "rx_formatted": fmt_bytes(rx_bytes),
                "tx_formatted": fmt_bytes(tx_bytes),
            })

        def fmt_total(b: int) -> str:
            if b >= 1073741824:
                return f"{b / 1073741824:.2f} GB"
            return f"{b / 1048576:.2f} MB"

        return {
            "total_rx": total_rx,
            "total_tx": total_tx,
            "total_rx_formatted": fmt_total(total_rx),
            "total_tx_formatted": fmt_total(total_tx),
            "interfaces": interfaces,
        }

    def _parse_processes(self, raw: dict) -> dict:
        proc_lines = raw.get("top_procs", "").strip().split("\n")
        processes = []
        for line in proc_lines:
            parts = line.split()
            if len(parts) >= 11:
                try:
                    processes.append({
                        "pid": int(parts[1]),
                        "user": parts[0],
                        "cpu": float(parts[2]),
                        "memory": float(parts[3]),
                        "vsz": parts[4],
                        "rss": parts[5],
                        "stat": parts[7],
                        "start": parts[8],
                        "time": parts[9],
                        "name": " ".join(parts[10:]),
                    })
                except (ValueError, IndexError):
                    continue
        return {"top_processes": processes, "total_count": len(processes)}

    async def get_system_info(self) -> dict[str, Any]:
        raw = await self.collect_raw()
        cpu_info = self._parse_cpu(raw)
        mem_info = self._parse_memory(raw)
        disk_info = self._parse_disk(raw)
        net_info = self._parse_network(raw)
        proc_info = self._parse_processes(raw)

        return {
            "cpu": cpu_info,
            "memory": mem_info,
            "disk": disk_info,
            "network": net_info,
            "processes": proc_info,
        }
