"""Echo 数据层 — 会话 / 消息 / 提问档案 / 报告 + FTS5 全文索引。

与主聊天（chat_messages）完全隔离：Echo 使用独立的 echo_* 表。
FTS5 用 trigram 分词器（SQLite ≥3.34），支持中文子串检索；
若运行时 SQLite 不支持则优雅降级（FTS 相关查询退回 LIKE）。
"""

from __future__ import annotations

import logging
from typing import Any

from app.database import get_connection

logger = logging.getLogger(__name__)

ECHO_BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS echo_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT DEFAULT '新对话',
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS echo_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_echo_messages_conv ON echo_messages(conversation_id, id);

CREATE TABLE IF NOT EXISTS echo_question_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    keywords TEXT DEFAULT '',
    conversation_id INTEGER,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS echo_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    period TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
"""


async def init_echo_db() -> None:
    """创建 Echo 全部表（含 FTS5，失败时降级）。"""
    conn = await get_connection()
    try:
        await conn.executescript(ECHO_BASE_SCHEMA)
        # FTS5 trigram —— 失败则退回默认分词，再失败则跳过（查询走 LIKE）
        try:
            await conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS echo_messages_fts "
                "USING fts5(content, tokenize='trigram')"
            )
        except Exception as exc:
            logger.warning("FTS5 trigram 不可用（%s），尝试默认分词器", exc)
            try:
                await conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS echo_messages_fts "
                    "USING fts5(content)"
                )
            except Exception:
                logger.warning("FTS5 不可用，Echo 全文检索将退回 LIKE 查询")
        await conn.commit()
    finally:
        await conn.close()


# ── 会话 ──

async def create_conversation(title: str = "新对话") -> int:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "INSERT INTO echo_conversations(title) VALUES (?)", (title,)
        )
        await conn.commit()
        return cur.lastrowid
    finally:
        await conn.close()


async def list_conversations() -> list[dict[str, Any]]:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   (SELECT COUNT(*) FROM echo_messages m
                    WHERE m.conversation_id = c.id) AS message_count,
                   (SELECT content FROM echo_messages m
                    WHERE m.conversation_id = c.id ORDER BY m.id DESC LIMIT 1) AS last_message
            FROM echo_conversations c
            ORDER BY c.updated_at DESC
            """
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_conversation(conv_id: int) -> dict[str, Any] | None:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "SELECT * FROM echo_conversations WHERE id = ?", (conv_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def rename_conversation(conv_id: int, title: str) -> bool:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "UPDATE echo_conversations SET title = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (title, conv_id),
        )
        await conn.commit()
        return cur.rowcount > 0
    finally:
        await conn.close()


async def delete_conversation(conv_id: int) -> bool:
    conn = await get_connection()
    try:
        # 取该会话全部消息 id，用于清理 FTS
        cur = await conn.execute(
            "SELECT id FROM echo_messages WHERE conversation_id = ?", (conv_id,)
        )
        mids = [r["id"] for r in await cur.fetchall()]
        await conn.execute("DELETE FROM echo_conversations WHERE id = ?", (conv_id,))
        await conn.execute("DELETE FROM echo_messages WHERE conversation_id = ?", (conv_id,))
        await conn.execute("DELETE FROM echo_question_log WHERE conversation_id = ?", (conv_id,))
        for mid in mids:
            await conn.execute("DELETE FROM echo_messages_fts WHERE rowid = ?", (mid,))
        await conn.commit()
        return True
    except Exception:
        await conn.rollback()
        raise
    finally:
        await conn.close()


# ── 消息 ──

async def add_message(conv_id: int, role: str, content: str) -> int:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "INSERT INTO echo_messages(conversation_id, role, content) VALUES (?, ?, ?)",
            (conv_id, role, content),
        )
        mid = cur.lastrowid
        try:
            await conn.execute(
                "INSERT INTO echo_messages_fts(rowid, content) VALUES (?, ?)",
                (mid, content),
            )
        except Exception as exc:
            logger.debug("FTS 写入失败（忽略）: %s", exc)
        await conn.execute(
            "UPDATE echo_conversations SET updated_at = datetime('now','localtime') WHERE id = ?",
            (conv_id,),
        )
        await conn.commit()
        return mid
    finally:
        await conn.close()


async def get_messages(conv_id: int, limit: int = 200) -> list[dict[str, Any]]:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "SELECT id, role, content, created_at FROM echo_messages "
            "WHERE conversation_id = ? ORDER BY id ASC LIMIT ?",
            (conv_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


# ── 提问档案 ──

async def add_question_log(question: str, keywords: str, conv_id: int | None) -> int:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "INSERT INTO echo_question_log(question, keywords, conversation_id) VALUES (?, ?, ?)",
            (question, keywords, conv_id),
        )
        await conn.commit()
        return cur.lastrowid
    finally:
        await conn.close()


async def list_question_log(limit: int = 100) -> list[dict[str, Any]]:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "SELECT * FROM echo_question_log ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_question_log_by_date(date_str: str) -> list[dict[str, Any]]:
    """按当天日期取提问（date_str 形如 '2026-08-07'，匹配 created_at 前缀）。"""
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "SELECT * FROM echo_question_log WHERE created_at LIKE ? ORDER BY id ASC",
            (date_str + "%",),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


# ── 报告 ──

async def add_report(report_type: str, title: str, content: str, period: str = "") -> int:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "INSERT INTO echo_reports(type, title, content, period) VALUES (?, ?, ?, ?)",
            (report_type, title, content, period),
        )
        await conn.commit()
        return cur.lastrowid
    finally:
        await conn.close()


async def list_reports() -> list[dict[str, Any]]:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "SELECT id, type, title, period, created_at FROM echo_reports ORDER BY id DESC"
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_report(report_id: int) -> dict[str, Any] | None:
    conn = await get_connection()
    try:
        cur = await conn.execute("SELECT * FROM echo_reports WHERE id = ?", (report_id,))
        row = await cur.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def delete_report(report_id: int) -> bool:
    conn = await get_connection()
    try:
        cur = await conn.execute("DELETE FROM echo_reports WHERE id = ?", (report_id,))
        await conn.commit()
        return cur.rowcount > 0
    finally:
        await conn.close()
