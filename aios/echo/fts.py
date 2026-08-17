"""Echo FTS5 全文检索 — 跨会话回找对话原文。

策略：优先 FTS5 trigram（对中文 ≥3 字查询效果好），
查询过短或 FTS 无结果时回退到 bigram 关键词 LIKE 打分。
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.database import get_connection

logger = logging.getLogger(__name__)

_CJK = r"一-鿿"


def _clean_query(q: str) -> str:
    """去掉 FTS 特殊字符，只留 CJK + 字母数字 + 空格。"""
    q = re.sub(rf"[^\w{_CJK}\s]", " ", q, flags=re.UNICODE)
    q = re.sub(r"\s+", " ", q).strip()
    return q


def _bigrams(text: str) -> list[str]:
    """中英文混合关键词：英文按词、中文按字符 bigram。"""
    kws: set[str] = set()
    for token in re.split(r"\s+", _clean_query(text).lower()):
        if not token:
            continue
        if re.fullmatch(rf"[{_CJK}]+", token):
            chars = list(token)
            for i in range(len(chars) - 1):
                kws.add(chars[i] + chars[i + 1])
            if len(chars) == 1:
                kws.add(chars[0])
        else:
            kws.add(token)
    return list(kws)


async def search(
    query: str,
    top_k: int = 8,
    exclude_conv_id: int | None = None,
) -> list[dict[str, Any]]:
    """搜索历史 Echo 对话原文，返回消息行（含会话 id、角色、内容）。"""
    cleaned = _clean_query(query)
    if cleaned and len(cleaned) >= 3:
        try:
            rows = await _fts_search(cleaned, top_k, exclude_conv_id)
            if rows:
                return rows
        except Exception as exc:
            logger.debug("FTS 检索失败，回退 LIKE: %s", exc)
    return await _like_search(query, top_k, exclude_conv_id)


async def _fts_search(
    cleaned: str,
    top_k: int,
    exclude_conv_id: int | None,
) -> list[dict[str, Any]]:
    conn = await get_connection()
    try:
        sql = """
            SELECT m.id, m.conversation_id, m.role, m.content, m.created_at,
                   bm25(echo_messages_fts) AS score
            FROM echo_messages m
            JOIN echo_messages_fts f ON f.rowid = m.id
            WHERE echo_messages_fts MATCH ?
        """
        params: list[Any] = [cleaned]
        if exclude_conv_id is not None:
            sql += " AND m.conversation_id != ?"
            params.append(exclude_conv_id)
        sql += " ORDER BY score ASC LIMIT ?"
        params.append(top_k)
        cur = await conn.execute(sql, params)
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def _like_search(
    query: str,
    top_k: int,
    exclude_conv_id: int | None,
) -> list[dict[str, Any]]:
    kws = _bigrams(query)
    if not kws:
        return []
    conn = await get_connection()
    try:
        conditions = " OR ".join("m.content LIKE ?" for _ in kws)
        sql = f"""
            SELECT m.id, m.conversation_id, m.role, m.content, m.created_at
            FROM echo_messages m
            WHERE ({conditions}) AND m.role = 'assistant'
        """
        params: list[Any] = [f"%{k}%" for k in kws]
        if exclude_conv_id is not None:
            sql += " AND m.conversation_id != ?"
            params.append(exclude_conv_id)
        sql += " LIMIT 500"
        cur = await conn.execute(sql, params)
        rows = await cur.fetchall()

        # 按关键词命中数打分
        scored = []
        for r in rows:
            content = (r["content"] or "").lower()
            hits = sum(1 for k in kws if k in content)
            if hits:
                scored.append((hits, dict(r)))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]
    finally:
        await conn.close()
