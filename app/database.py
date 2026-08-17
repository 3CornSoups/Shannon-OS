from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import aiosqlite

from app.security import PasswordManager

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "shannon.db"


async def get_connection() -> aiosqlite.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(DB_PATH.as_posix())
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db() -> None:
    conn = await get_connection()
    try:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS hosts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                host TEXT NOT NULL,
                port INTEGER NOT NULL DEFAULT 22,
                username TEXT,
                os_name TEXT,
                distro TEXT,
                last_pwd TEXT,
                pwd_encrypted INTEGER NOT NULL DEFAULT 0,
                last_seen TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_hosts_unique
            ON hosts(host, port, COALESCE(username, ''));

            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host_id INTEGER,
                mode TEXT NOT NULL,
                intent TEXT,
                commands_plan TEXT,
                risk_level TEXT,
                status TEXT NOT NULL,
                stdout TEXT,
                stderr TEXT,
                exit_code INTEGER,
                task_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(host_id) REFERENCES hosts(id)
            );

            CREATE TABLE IF NOT EXISTS audit_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host_id INTEGER,
                task_id TEXT NOT NULL,
                reason TEXT,
                risk_level TEXT NOT NULL,
                approved INTEGER NOT NULL DEFAULT 0,
                operator_name TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(host_id) REFERENCES hosts(id)
            );

            CREATE TABLE IF NOT EXISTS env_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host_id INTEGER NOT NULL,
                shell TEXT,
                python_version TEXT,
                docker_version TEXT,
                systemctl_version TEXT,
                uname TEXT,
                os_release TEXT,
                memory_summary TEXT,
                disk_summary TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(host_id) REFERENCES hosts(id)
            );

            CREATE TABLE IF NOT EXISTS user_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host_id INTEGER,
                task_id TEXT,
                mode TEXT NOT NULL,
                user_prompt TEXT NOT NULL,
                parsed_commands TEXT,
                executed INTEGER NOT NULL DEFAULT 0,
                result_summary TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(host_id) REFERENCES hosts(id)
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT '新对话',
                status TEXT NOT NULL DEFAULT 'active',
                task_summary TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(host_id) REFERENCES hosts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                meta TEXT,
                conversation_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(host_id) REFERENCES hosts(id),
                FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS metrics_snapshots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                host_id         INTEGER NOT NULL,
                cpu_usage       REAL,
                cpu_load_1      REAL,
                cpu_load_5      REAL,
                cpu_load_15     REAL,
                memory_usage    REAL,
                memory_used_kb  INTEGER,
                memory_total_kb INTEGER,
                disk_partitions TEXT,
                disk_max_usage  REAL,
                network_rx      INTEGER,
                network_tx      INTEGER,
                process_count   INTEGER,
                raw_data        TEXT,
                collected_at    TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(host_id) REFERENCES hosts(id)
            );
            CREATE INDEX IF NOT EXISTS idx_metrics_host_time ON metrics_snapshots(host_id, collected_at);

            CREATE TABLE IF NOT EXISTS alert_rules (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                metric_type     TEXT NOT NULL,
                operator        TEXT NOT NULL,
                threshold       REAL NOT NULL,
                duration        INTEGER DEFAULT 0,
                severity        TEXT DEFAULT 'warning',
                enabled         INTEGER DEFAULT 1,
                channels        TEXT DEFAULT '[]',
                host_ids        TEXT DEFAULT '[]',
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS alert_events (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id         INTEGER NOT NULL,
                host_id         INTEGER NOT NULL,
                severity        TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'alerting',
                current_value   REAL,
                threshold       REAL,
                message         TEXT,
                triggered_at    TEXT NOT NULL DEFAULT (datetime('now')),
                recovered_at    TEXT,
                acknowledged_at TEXT,
                acknowledged_by TEXT,
                notify_count    INTEGER DEFAULT 1,
                FOREIGN KEY(rule_id) REFERENCES alert_rules(id),
                FOREIGN KEY(host_id) REFERENCES hosts(id)
            );
            CREATE INDEX IF NOT EXISTS idx_alerts_status ON alert_events(status, host_id);
            CREATE INDEX IF NOT EXISTS idx_alerts_time ON alert_events(triggered_at);

            CREATE TABLE IF NOT EXISTS memory_entries (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                type            TEXT NOT NULL,
                key             TEXT NOT NULL,
                content         TEXT NOT NULL,
                importance      INTEGER DEFAULT 3,
                vector          TEXT,
                source_conv_id  INTEGER,
                host_id         INTEGER,
                created_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_entries(type);
            CREATE INDEX IF NOT EXISTS idx_memory_importance ON memory_entries(importance);
            """
        )

        # 迁移：为旧表添加 pwd_encrypted 列（如果不存在）
        try:
            await conn.execute("ALTER TABLE hosts ADD COLUMN pwd_encrypted INTEGER NOT NULL DEFAULT 0")
            await conn.commit()
            logger.info("数据库迁移：添加 pwd_encrypted 列")
        except Exception:
            pass  # 列已存在

        # 迁移：为旧表添加 conversation_id 列（如果不存在）
        try:
            await conn.execute("ALTER TABLE chat_messages ADD COLUMN conversation_id INTEGER REFERENCES conversations(id)")
            await conn.commit()
            logger.info("数据库迁移：添加 conversation_id 列")
        except Exception:
            pass  # 列已存在

        # 迁移：为 conversations 添加 status 列
        try:
            await conn.execute("ALTER TABLE conversations ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
            await conn.commit()
            logger.info("数据库迁移：添加 conversations.status 列")
        except Exception:
            pass  # 列已存在

        # 迁移：为 conversations 添加 task_summary 列
        try:
            await conn.execute("ALTER TABLE conversations ADD COLUMN task_summary TEXT")
            await conn.commit()
            logger.info("数据库迁移：添加 conversations.task_summary 列")
        except Exception:
            pass  # 列已存在

        # 预置默认告警规则（仅首次）
        cursor = await conn.execute("SELECT COUNT(*) FROM alert_rules")
        row = await cursor.fetchone()
        await cursor.close()
        if row and row[0] == 0:
            preset_rules = [
                ("CPU使用率过高(严重)", "cpu", ">", 95.0, 60, "critical", 1, "[]", "[]"),
                ("CPU使用率过高(警告)", "cpu", ">", 85.0, 300, "warning", 1, "[]", "[]"),
                ("内存使用率过高(严重)", "memory", ">", 90.0, 60, "critical", 1, "[]", "[]"),
                ("内存使用率过高(警告)", "memory", ">", 80.0, 300, "warning", 1, "[]", "[]"),
                ("磁盘使用率过高(严重)", "disk", ">", 90.0, 0, "critical", 1, "[]", "[]"),
                ("磁盘使用率过高(警告)", "disk", ">", 80.0, 0, "warning", 1, "[]", "[]"),
                ("系统负载过高", "load", ">", 2.0, 300, "warning", 1, "[]", "[]"),
            ]
            for rule in preset_rules:
                await conn.execute(
                    "INSERT INTO alert_rules(name, metric_type, operator, threshold, duration, severity, enabled, channels, host_ids) VALUES(?,?,?,?,?,?,?,?,?)",
                    rule,
                )
            logger.info("预置 7 条默认告警规则")

        await conn.commit()
    finally:
        await conn.close()


async def upsert_host_context(
    name: str,
    host: str,
    port: int = 22,
    username: str | None = None,
    os_name: str | None = None,
    distro: str | None = None,
    last_pwd: str | None = None,
    encrypt_pwd: bool = True,
) -> int:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT id FROM hosts WHERE host = ? AND port = ? AND COALESCE(username, '') = COALESCE(?, '')
            """,
            (host, port, username),
        )
        row = await cursor.fetchone()
        await cursor.close()

        # 处理密码加密
        pwd_value = None
        pwd_encrypted = 0
        if last_pwd:
            if encrypt_pwd:
                pwd_value = PasswordManager.encrypt(last_pwd)
                pwd_encrypted = 1
            else:
                pwd_value = last_pwd
                pwd_encrypted = 0

        if row:
            host_id = int(row["id"])
            await conn.execute(
                """
                UPDATE hosts
                SET name = ?, os_name = COALESCE(?, os_name), distro = COALESCE(?, distro),
                    last_pwd = COALESCE(?, last_pwd),
                    pwd_encrypted = CASE WHEN ? IS NOT NULL THEN ? ELSE pwd_encrypted END,
                    last_seen = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (name, os_name, distro, pwd_value, pwd_value, pwd_encrypted, host_id),
            )
        else:
            cursor = await conn.execute(
                """
                INSERT INTO hosts(name, host, port, username, os_name, distro, last_pwd, pwd_encrypted, last_seen)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (name, host, port, username, os_name, distro, pwd_value, pwd_encrypted),
            )
            host_id = int(cursor.lastrowid)
            await cursor.close()
        await conn.commit()
        return host_id
    finally:
        await conn.close()


async def get_host_context(host_id: int, decrypt_pwd: bool = True) -> dict[str, Any] | None:
    conn = await get_connection()
    try:
        cursor = await conn.execute("SELECT * FROM hosts WHERE id = ?", (host_id,))
        row = await cursor.fetchone()
        await cursor.close()
        if not row:
            return None
        data = dict(row)

        # 密码解密（兼顾旧版明文密码）
        last_pwd = data.get("last_pwd")
        pwd_encrypted = data.get("pwd_encrypted", 0)
        if last_pwd and pwd_encrypted == 1 and decrypt_pwd:
            decrypted = PasswordManager.decrypt(last_pwd)
            if decrypted:
                data["last_pwd"] = decrypted
            # 解密失败则保留加密字符串
        elif last_pwd and pwd_encrypted == 0:
            pass  # 旧版明文密码，原样返回

        return data
    finally:
        await conn.close()


async def list_hosts(decrypt_pwd: bool = False) -> list[dict[str, Any]]:
    conn = await get_connection()
    try:
        cursor = await conn.execute("SELECT * FROM hosts ORDER BY updated_at DESC")
        rows = await cursor.fetchall()
        await cursor.close()
        result = []
        for row in rows:
            data = dict(row)
            last_pwd = data.get("last_pwd")
            pwd_encrypted = data.get("pwd_encrypted", 0)
            if last_pwd and pwd_encrypted == 1 and decrypt_pwd:
                decrypted = PasswordManager.decrypt(last_pwd)
                if decrypted:
                    data["last_pwd"] = decrypted
            # list 时默认不返回密码（安全）
            if not decrypt_pwd:
                data["last_pwd"] = "***" if data.get("last_pwd") else None
            result.append(data)
        return result
    finally:
        await conn.close()


async def delete_host(host_id: int) -> bool:
    conn = await get_connection()
    try:
        cursor = await conn.execute("DELETE FROM hosts WHERE id = ?", (host_id,))
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


async def update_host(
    host_id: int,
    name: str,
    host: str,
    port: int,
    username: str | None = None,
    last_pwd: str | None = None,
    encrypt_pwd: bool = True,
) -> bool:
    conn = await get_connection()
    try:
        # 处理密码
        if last_pwd:
            if encrypt_pwd:
                pwd_value = PasswordManager.encrypt(last_pwd)
                pwd_encrypted = 1
            else:
                pwd_value = last_pwd
                pwd_encrypted = 0
            cursor = await conn.execute(
                """
                UPDATE hosts
                SET name = ?, host = ?, port = ?, username = ?,
                    last_pwd = ?, pwd_encrypted = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (name, host, port, username, pwd_value, pwd_encrypted, host_id),
            )
        else:
            cursor = await conn.execute(
                """
                UPDATE hosts
                SET name = ?, host = ?, port = ?, username = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (name, host, port, username, host_id),
            )
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


# ---- 会话管理 ----

async def create_conversation(host_id: int, title: str = "新对话") -> int:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "INSERT INTO conversations(host_id, title) VALUES(?, ?)",
            (host_id, title),
        )
        await conn.commit()
        return int(cursor.lastrowid)
    finally:
        await conn.close()


async def list_conversations(host_id: int) -> list[dict[str, Any]]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT c.*, COUNT(m.id) AS message_count
            FROM conversations c
            LEFT JOIN chat_messages m ON m.conversation_id = c.id
            WHERE c.host_id = ?
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            """,
            (host_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_conversation(conv_id: int) -> dict[str, Any] | None:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        )
        row = await cursor.fetchone()
        await cursor.close()
        return dict(row) if row else None
    finally:
        await conn.close()


async def update_conversation_title(conv_id: int, title: str) -> bool:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, conv_id),
        )
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


async def delete_conversation(conv_id: int) -> bool:
    conn = await get_connection()
    try:
        # 先删除会话内的消息
        await conn.execute("DELETE FROM chat_messages WHERE conversation_id = ?", (conv_id,))
        # 再删除会话
        cursor = await conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


async def list_conversation_messages(
    conv_id: int, include_meta: bool = True
) -> list[dict[str, Any]]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM chat_messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conv_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        result = []
        for row in rows:
            item = dict(row)
            if include_meta and item.get("meta"):
                try:
                    item["meta"] = json.loads(item["meta"])
                except Exception:
                    item["meta"] = None
            elif not include_meta:
                item.pop("meta", None)
            result.append(item)
        return result
    finally:
        await conn.close()


# ---- 以下函数保持不变 ----


async def append_operation_log(
    host_id: int | None,
    mode: str,
    intent: str | None,
    commands_plan: list[dict[str, Any]] | list[str] | None,
    risk_level: str | None,
    status: str,
    stdout: str | None = None,
    stderr: str | None = None,
    exit_code: int | None = None,
    task_id: str | None = None,
) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT INTO operation_logs(host_id, mode, intent, commands_plan, risk_level, status, stdout, stderr, exit_code, task_id)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                host_id,
                mode,
                intent,
                json.dumps(commands_plan, ensure_ascii=False) if commands_plan is not None else None,
                risk_level,
                status,
                stdout,
                stderr,
                exit_code,
                task_id,
            ),
        )
        await conn.commit()
    finally:
        await conn.close()


async def append_delegate_log(
    host_id: int | None,
    task_id: str,
    agent: str,
    task: str,
    reason: str,
    risk_level: str,
    exit_code: int | None,
    goal_achieved: str | None,
    execution_time_sec: float | None,
    files_changed: list[str] | None,
    cancelled: bool = False,
    timed_out: bool = False,
) -> None:
    """记录委托操作日志"""
    return await append_operation_log(
        host_id=host_id,
        mode="delegate",
        intent="delegation",
        commands_plan=[{
            "agent": agent,
            "task": task,
            "reason": reason,
            "risk_level": risk_level,
            "exit_code": exit_code,
            "goal_achieved": goal_achieved,
            "execution_time_sec": execution_time_sec,
            "files_changed": files_changed or [],
            "cancelled": cancelled,
            "timed_out": timed_out,
        }],
        risk_level=risk_level,
        status="completed" if not cancelled else "cancelled",
        exit_code=exit_code,
        task_id=task_id,
    )


async def append_audit_record(
    host_id: int | None,
    task_id: str,
    reason: str | None,
    risk_level: str,
    approved: bool,
    operator_name: str | None = None,
) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT INTO audit_records(host_id, task_id, reason, risk_level, approved, operator_name)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (host_id, task_id, reason, risk_level, int(approved), operator_name),
        )
        await conn.commit()
    finally:
        await conn.close()


async def append_env_snapshot(
    host_id: int,
    shell: str | None = None,
    python_version: str | None = None,
    docker_version: str | None = None,
    systemctl_version: str | None = None,
    uname: str | None = None,
    os_release: str | None = None,
    memory_summary: str | None = None,
    disk_summary: str | None = None,
) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT INTO env_snapshots(
                host_id, shell, python_version, docker_version, systemctl_version,
                uname, os_release, memory_summary, disk_summary
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                host_id,
                shell,
                python_version,
                docker_version,
                systemctl_version,
                uname,
                os_release,
                memory_summary,
                disk_summary,
            ),
        )
        await conn.commit()
    finally:
        await conn.close()


async def list_env_snapshots(host_id: int, limit: int = 20) -> list[dict[str, Any]]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM env_snapshots WHERE host_id = ? ORDER BY created_at DESC LIMIT ?",
            (host_id, limit),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def append_user_action(
    host_id: int | None,
    task_id: str | None,
    mode: str,
    user_prompt: str,
    parsed_commands: list[str] | list[dict[str, Any]] | None = None,
    executed: bool = False,
    result_summary: str | None = None,
) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT INTO user_actions(host_id, task_id, mode, user_prompt, parsed_commands, executed, result_summary)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                host_id,
                task_id,
                mode,
                user_prompt,
                json.dumps(parsed_commands, ensure_ascii=False) if parsed_commands is not None else None,
                int(executed),
                result_summary,
            ),
        )
        await conn.commit()
    finally:
        await conn.close()


async def list_user_actions(host_id: int, limit: int = 100) -> list[dict[str, Any]]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM user_actions WHERE host_id = ? ORDER BY created_at DESC LIMIT ?",
            (host_id, limit),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def set_app_setting(key: str, value: str) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT INTO app_settings(key, value, updated_at)
            VALUES(?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_app_setting(key: str) -> str | None:
    conn = await get_connection()
    try:
        cursor = await conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        await cursor.close()
        return row["value"] if row else None
    finally:
        await conn.close()


async def get_app_settings(keys: list[str]) -> dict[str, str]:
    if not keys:
        return {}
    conn = await get_connection()
    try:
        placeholders = ",".join(["?"] * len(keys))
        cursor = await conn.execute(
            f"SELECT key, value FROM app_settings WHERE key IN ({placeholders})",
            tuple(keys),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return {str(row["key"]): str(row["value"]) for row in rows}
    finally:
        await conn.close()


async def append_chat_message(
    host_id: int,
    role: str,
    content: str,
    meta: dict[str, Any] | None = None,
    conversation_id: int | None = None,
) -> int:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO chat_messages(host_id, role, content, meta, conversation_id)
            VALUES(?, ?, ?, ?, ?)
            """,
            (host_id, role, content, json.dumps(meta) if meta else None, conversation_id),
        )
        # 更新会话的 updated_at
        if conversation_id:
            await conn.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conversation_id,),
            )
        await conn.commit()
        return cursor.lastrowid
    finally:
        await conn.close()


async def list_chat_messages(
    host_id: int, limit: int = 100, include_meta: bool = True
) -> list[dict[str, Any]]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM chat_messages WHERE host_id = ? ORDER BY created_at ASC LIMIT ?",
            (host_id, limit),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        result = []
        for row in rows:
            item = dict(row)
            if include_meta and item.get("meta"):
                try:
                    item["meta"] = json.loads(item["meta"])
                except Exception:
                    item["meta"] = None
            elif not include_meta:
                item.pop("meta", None)
            result.append(item)
        return result
    finally:
        await conn.close()


async def clear_chat_messages(host_id: int) -> None:
    conn = await get_connection()
    try:
        await conn.execute("DELETE FROM chat_messages WHERE host_id = ?", (host_id,))
        await conn.commit()
    finally:
        await conn.close()


# ---- 指标快照 (metrics_snapshots) ----

async def insert_metrics_snapshot(host_id: int, data: dict[str, Any]) -> int:
    cpu = data.get("cpu", {})
    memory = data.get("memory", {})
    disk = data.get("disk", {})
    network = data.get("network", {})
    processes = data.get("processes", {})

    partitions = disk.get("partitions", [])
    disk_max = max((p.get("usage_percent", 0) for p in partitions), default=0)

    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO metrics_snapshots(
                host_id, cpu_usage, cpu_load_1, cpu_load_5, cpu_load_15,
                memory_usage, memory_used_kb, memory_total_kb,
                disk_partitions, disk_max_usage,
                network_rx, network_tx, process_count, raw_data, collected_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                host_id,
                cpu.get("usage_percent"),
                cpu.get("load_avg_1"),
                cpu.get("load_avg_5"),
                cpu.get("load_avg_15"),
                memory.get("usage_percent"),
                memory.get("used_kb"),
                memory.get("total_kb"),
                json.dumps(partitions, ensure_ascii=False),
                disk_max,
                network.get("total_rx"),
                network.get("total_tx"),
                processes.get("total_count"),
                json.dumps(data, ensure_ascii=False),
                now,
            ),
        )
        await conn.commit()
        return int(cursor.lastrowid)
    finally:
        await conn.close()


async def get_metrics_history(
    host_id: int, from_time: str, to_time: str
) -> dict[str, Any]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT cpu_usage, memory_usage, collected_at
            FROM metrics_snapshots
            WHERE host_id = ? AND collected_at >= ? AND collected_at <= ?
            ORDER BY collected_at ASC
            """,
            (host_id, from_time, to_time),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        timestamps = []
        cpu_usage = []
        memory_usage = []
        for row in rows:
            timestamps.append(row["collected_at"])
            cpu_usage.append(row["cpu_usage"] or 0)
            memory_usage.append(row["memory_usage"] or 0)
        return {
            "timestamps": timestamps,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
        }
    finally:
        await conn.close()


async def get_latest_metrics_for_all_hosts() -> list[dict[str, Any]]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT m.* FROM metrics_snapshots m
            INNER JOIN (
                SELECT host_id, MAX(collected_at) AS max_time
                FROM metrics_snapshots
                GROUP BY host_id
            ) latest ON m.host_id = latest.host_id AND m.collected_at = latest.max_time
            """
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_latest_metrics_for_host(host_id: int) -> dict[str, Any] | None:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT * FROM metrics_snapshots
            WHERE host_id = ?
            ORDER BY collected_at DESC
            LIMIT 1
            """,
            (host_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return dict(row) if row else None
    finally:
        await conn.close()


# ---- 告警规则 (alert_rules) ----

async def get_alert_rules() -> list[dict[str, Any]]:
    conn = await get_connection()
    try:
        cursor = await conn.execute("SELECT * FROM alert_rules ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_alert_rule_by_id(rule_id: int) -> dict[str, Any] | None:
    conn = await get_connection()
    try:
        cursor = await conn.execute("SELECT * FROM alert_rules WHERE id = ?", (rule_id,))
        row = await cursor.fetchone()
        await cursor.close()
        return dict(row) if row else None
    finally:
        await conn.close()


async def create_alert_rule(data: dict[str, Any]) -> int:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO alert_rules(name, metric_type, operator, threshold, duration, severity, enabled, channels, host_ids)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["name"],
                data["metric_type"],
                data["operator"],
                data["threshold"],
                data.get("duration", 0),
                data.get("severity", "warning"),
                data.get("enabled", 1),
                json.dumps(data.get("channels", []), ensure_ascii=False),
                json.dumps(data.get("host_ids", []), ensure_ascii=False),
            ),
        )
        await conn.commit()
        return int(cursor.lastrowid)
    finally:
        await conn.close()


async def update_alert_rule(rule_id: int, data: dict[str, Any]) -> bool:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            UPDATE alert_rules
            SET name = ?, metric_type = ?, operator = ?, threshold = ?, duration = ?,
                severity = ?, enabled = ?, channels = ?, host_ids = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                data["name"],
                data["metric_type"],
                data["operator"],
                data["threshold"],
                data.get("duration", 0),
                data.get("severity", "warning"),
                data.get("enabled", 1),
                json.dumps(data.get("channels", []), ensure_ascii=False),
                json.dumps(data.get("host_ids", []), ensure_ascii=False),
                rule_id,
            ),
        )
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


async def delete_alert_rule(rule_id: int) -> bool:
    conn = await get_connection()
    try:
        cursor = await conn.execute("DELETE FROM alert_rules WHERE id = ?", (rule_id,))
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


async def toggle_alert_rule(rule_id: int) -> bool:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            UPDATE alert_rules
            SET enabled = CASE WHEN enabled = 1 THEN 0 ELSE 1 END,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (rule_id,),
        )
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


async def get_active_rules_for_host(host_id: int) -> list[dict[str, Any]]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM alert_rules WHERE enabled = 1 ORDER BY created_at"
        )
        rows = await cursor.fetchall()
        await cursor.close()
        result = []
        for row in rows:
            rule = dict(row)
            host_ids_str = rule.get("host_ids", "[]")
            try:
                host_ids = json.loads(host_ids_str) if host_ids_str else []
            except Exception:
                host_ids = []
            if not host_ids or host_id in host_ids:
                result.append(rule)
        return result
    finally:
        await conn.close()


async def seed_preset_rules() -> int:
    conn = await get_connection()
    try:
        cursor = await conn.execute("SELECT COUNT(*) FROM alert_rules")
        row = await cursor.fetchone()
        await cursor.close()
        if row and row[0] > 0:
            return 0
        preset_rules = [
            ("CPU使用率过高(严重)", "cpu", ">", 95.0, 60, "critical", 1, "[]", "[]"),
            ("CPU使用率过高(警告)", "cpu", ">", 85.0, 300, "warning", 1, "[]", "[]"),
            ("内存使用率过高(严重)", "memory", ">", 90.0, 60, "critical", 1, "[]", "[]"),
            ("内存使用率过高(警告)", "memory", ">", 80.0, 300, "warning", 1, "[]", "[]"),
            ("磁盘使用率过高(严重)", "disk", ">", 90.0, 0, "critical", 1, "[]", "[]"),
            ("磁盘使用率过高(警告)", "disk", ">", 80.0, 0, "warning", 1, "[]", "[]"),
            ("系统负载过高", "load", ">", 2.0, 300, "warning", 1, "[]", "[]"),
        ]
        for rule in preset_rules:
            await conn.execute(
                "INSERT INTO alert_rules(name, metric_type, operator, threshold, duration, severity, enabled, channels, host_ids) VALUES(?,?,?,?,?,?,?,?,?)",
                rule,
            )
        await conn.commit()
        logger.info(f"预置 {len(preset_rules)} 条默认告警规则")
        return len(preset_rules)
    finally:
        await conn.close()


# ---- 告警事件 (alert_events) ----

async def create_alert_event(
    rule_id: int,
    host_id: int,
    severity: str,
    current_value: float,
    threshold: float,
    message: str,
) -> int:
    from datetime import datetime
    conn = await get_connection()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = await conn.execute(
            """
            INSERT INTO alert_events(rule_id, host_id, severity, status, current_value, threshold, message, triggered_at)
            VALUES(?, ?, ?, 'alerting', ?, ?, ?, ?)
            """,
            (rule_id, host_id, severity, current_value, threshold, message, now),
        )
        await conn.commit()
        return int(cursor.lastrowid)
    finally:
        await conn.close()


async def get_alert_events(
    host_id: int | None = None,
    severity: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    conn = await get_connection()
    try:
        conditions = []
        params: list[Any] = []

        if host_id is not None:
            conditions.append("e.host_id = ?")
            params.append(host_id)
        if severity:
            conditions.append("e.severity = ?")
            params.append(severity)
        if status:
            conditions.append("e.status = ?")
            params.append(status)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        count_cursor = await conn.execute(
            f"SELECT COUNT(*) FROM alert_events e {where_clause}", tuple(params)
        )
        count_row = await count_cursor.fetchone()
        await count_cursor.close()
        total = count_row[0] if count_row else 0

        offset = (page - 1) * page_size
        cursor = await conn.execute(
            f"""
            SELECT e.*, r.name AS rule_name, h.name AS host_name, h.host AS host_ip
            FROM alert_events e
            LEFT JOIN alert_rules r ON e.rule_id = r.id
            LEFT JOIN hosts h ON e.host_id = h.id
            {where_clause}
            ORDER BY e.triggered_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params + [page_size, offset]),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows], total
    finally:
        await conn.close()


async def get_alert_event_by_id(event_id: int) -> dict[str, Any] | None:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT e.*, r.name AS rule_name, h.name AS host_name, h.host AS host_ip
            FROM alert_events e
            LEFT JOIN alert_rules r ON e.rule_id = r.id
            LEFT JOIN hosts h ON e.host_id = h.id
            WHERE e.id = ?
            """,
            (event_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return dict(row) if row else None
    finally:
        await conn.close()


async def acknowledge_alert_event(event_id: int, operator: str = "admin") -> bool:
    from datetime import datetime
    conn = await get_connection()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = await conn.execute(
            """
            UPDATE alert_events
            SET status = 'acknowledged', acknowledged_at = ?, acknowledged_by = ?
            WHERE id = ? AND status = 'alerting'
            """,
            (now, operator, event_id),
        )
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


async def archive_alert_event(event_id: int) -> bool:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "UPDATE alert_events SET status = 'archived' WHERE id = ?",
            (event_id,),
        )
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


async def find_active_alert(rule_id: int, host_id: int) -> dict[str, Any] | None:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT * FROM alert_events
            WHERE rule_id = ? AND host_id = ? AND status = 'alerting'
            ORDER BY triggered_at DESC LIMIT 1
            """,
            (rule_id, host_id),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return dict(row) if row else None
    finally:
        await conn.close()


async def mark_alert_recovered(rule_id: int, host_id: int) -> bool:
    from datetime import datetime
    conn = await get_connection()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = await conn.execute(
            """
            UPDATE alert_events
            SET status = 'recovered', recovered_at = ?
            WHERE rule_id = ? AND host_id = ? AND status = 'alerting'
            """,
            (now, rule_id, host_id),
        )
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


async def get_alert_stats() -> dict[str, int]:
    conn = await get_connection()
    try:
        today = "datetime('now', 'start of day')"
        cursor = await conn.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) AS critical,
                SUM(CASE WHEN severity = 'warning' THEN 1 ELSE 0 END) AS warning,
                SUM(CASE WHEN severity = 'info' THEN 1 ELSE 0 END) AS info,
                SUM(CASE WHEN status = 'recovered' THEN 1 ELSE 0 END) AS recovered
            FROM alert_events
            WHERE triggered_at >= {today}
            """
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row:
            return {
                "total": row["total"] or 0,
                "critical": row["critical"] or 0,
                "warning": row["warning"] or 0,
                "info": row["info"] or 0,
                "recovered": row["recovered"] or 0,
            }
        return {"total": 0, "critical": 0, "warning": 0, "info": 0, "recovered": 0}
    finally:
        await conn.close()


# ---- 通知渠道设置 keys ----
NOTIFICATION_SETTING_KEYS = [
    "dingtalk_webhook_url",
    "dingtalk_secret",
    "smtp_host",
    "smtp_port",
    "smtp_username",
    "smtp_password",
    "smtp_recipients",
    "webhook_url",
    "webhook_headers",
    "monitor_interval",
]


# ---- 多服务器环境信息查询 ----

async def get_hosts_env_info(host_ids: list[int]) -> list[dict[str, Any]]:
    """查询多台服务器的环境信息（OS/发行版/主机名/IP）"""
    if not host_ids:
        return []
    conn = await get_connection()
    try:
        placeholders = ",".join(["?"] * len(host_ids))
        cursor = await conn.execute(
            f"SELECT id, name, host, os_name, distro FROM hosts WHERE id IN ({placeholders})",
            tuple(host_ids),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        results = []
        for row in rows:
            d = dict(row)
            results.append({
                "host_id": d["id"],
                "name": d.get("name", d.get("host", "")),
                "host": d.get("host", ""),
                "os": d.get("os_name") or "未知",
                "distro": d.get("distro") or "未知",
            })
        return results
    finally:
        await conn.close()


# ── Memory Entries CRUD ──

async def insert_memory_entry(
    entry_type: str,
    key: str,
    content: str,
    importance: int = 3,
    vector: str | None = None,
    source_conv_id: int | None = None,
    host_id: int | None = None,
) -> int:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "INSERT INTO memory_entries(type, key, content, importance, vector, source_conv_id, host_id) "
            "VALUES(?, ?, ?, ?, ?, ?, ?)",
            (entry_type, key, content, importance, vector, source_conv_id, host_id),
        )
        await conn.commit()
        return cursor.lastrowid
    finally:
        await conn.close()


async def list_memory_entries(limit: int = 500) -> list[dict]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM memory_entries ORDER BY importance DESC, created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_memory_always() -> list[dict]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM memory_entries WHERE importance >= 5 ORDER BY created_at DESC",
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def update_memory_entry(
    entry_id: int,
    content: str | None = None,
    importance: int | None = None,
    vector: str | None = None,
) -> bool:
    conn = await get_connection()
    try:
        updates = []
        params = []
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if importance is not None:
            updates.append("importance = ?")
            params.append(importance)
        if vector is not None:
            updates.append("vector = ?")
            params.append(vector)
        if not updates:
            return False
        params.append(entry_id)
        await conn.execute(
            f"UPDATE memory_entries SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        await conn.commit()
        return True
    finally:
        await conn.close()


async def delete_memory_entry(entry_id: int) -> bool:
    conn = await get_connection()
    try:
        cursor = await conn.execute("DELETE FROM memory_entries WHERE id = ?", (entry_id,))
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


# ── Conversation Status CRUD ──

async def pause_conversation(conv_id: int, task_summary: str = "") -> bool:
    """Mark a conversation as paused with a task summary."""
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE conversations SET status = 'paused', task_summary = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (task_summary, conv_id),
        )
        await conn.commit()
        return True
    finally:
        await conn.close()


async def resume_conversation(conv_id: int) -> dict | None:
    """Resume a paused conversation. Returns the conversation dict with task_summary."""
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE conversations SET status = 'active', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conv_id,),
        )
        await conn.commit()
        cursor = await conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
        row = await cursor.fetchone()
        await cursor.close()
        return dict(row) if row else None
    finally:
        await conn.close()


async def archive_conversation(conv_id: int) -> bool:
    """Archive a completed conversation."""
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE conversations SET status = 'archived', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conv_id,),
        )
        await conn.commit()
        return True
    finally:
        await conn.close()


async def list_paused_conversations(host_id: int) -> list[dict]:
    """List all paused conversations for a host."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM conversations WHERE host_id = ? AND status = 'paused' ORDER BY updated_at DESC",
            (host_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(r) for r in rows]
    finally:
        await conn.close()
