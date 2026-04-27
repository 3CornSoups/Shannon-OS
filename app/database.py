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
