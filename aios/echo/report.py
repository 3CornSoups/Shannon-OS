"""Echo 报告生成 — 主题报告 + 每日小结。

数据源：提问档案 + memory_entries + 对话原文（FTS 检索）。
产出 Markdown，存入 echo_reports 供前端回看。
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from aios.llm import request_text_from_messages
from app.database import list_memory_entries
from app.settings import load_runtime_settings

from aios.echo.db import (
    add_report,
    get_question_log_by_date,
    list_question_log,
)
from aios.echo import fts

logger = logging.getLogger(__name__)


async def _gather_memory_by_keywords(keywords: list[str], limit: int = 20) -> list[dict]:
    """按关键词过滤 memory_entries。"""
    try:
        entries = await list_memory_entries(limit=500)
    except Exception:
        return []
    hits = []
    for e in entries:
        text = f"{e.get('key', '')} {e.get('content', '')}".lower()
        if any(k in text for k in keywords):
            hits.append(e)
        if len(hits) >= limit:
            break
    return hits


async def generate_topic_report(topic: str) -> dict[str, Any]:
    """主题报告：跨会话汇总所有相关讨论。"""
    keywords = [t for t in topic.split() if t] or [topic]
    # 收集资料
    memory_hits = await _gather_memory_by_keywords(keywords)
    recall = await fts.search(topic, top_k=15)
    try:
        qlog = await list_question_log(limit=200)
        questions = [q for q in qlog if any(k in q.get("question", "").lower() for k in keywords)]
    except Exception:
        questions = []

    memory_text = "\n".join(f"- [{e.get('type')}] {e.get('content', '')}" for e in memory_hits) or "（无）"
    recall_text = "\n".join(
        f"- {m.get('content', '')[:150]}" for m in recall
    ) or "（无）"
    questions_text = "\n".join(f"- {q.get('question', '')}" for q in questions) or "（无）"

    prompt = (
        f"请根据以下资料，撰写一份关于「{topic}」的 Markdown 报告。\n\n"
        f"【相关记忆】\n{memory_text}\n\n"
        f"【过往对话片段】\n{recall_text}\n\n"
        f"【相关提问】\n{questions_text}\n\n"
        "报告结构建议：## 概述、## 关键信息、## 时间线/讨论要点、## 结论或建议。"
        "内容要实质、有条理，中文，用 Markdown 格式。"
    )
    content = await _call_llm(prompt)
    title = f"主题报告：{topic}"
    report_id = await add_report("topic", title, content, period=topic)
    return {"id": report_id, "type": "topic", "title": title, "content": content, "period": topic}


async def generate_daily_digest() -> dict[str, Any]:
    """每日小结：当天提问 + 对话要点汇总。"""
    today = date.today().isoformat()
    questions = await get_question_log_by_date(today)
    try:
        entries = await list_memory_entries(limit=200)
    except Exception:
        entries = []

    questions_text = "\n".join(f"- {q.get('question', '')}" for q in questions) or "（当天无提问记录）"
    memory_text = "\n".join(
        f"- [{e.get('type')}] {e.get('content', '')}" for e in entries[:10]
    ) or "（无）"

    prompt = (
        f"请生成 {today} 的每日小结（Markdown）。\n\n"
        f"【当天用户提问】\n{questions_text}\n\n"
        f"【近期长期记忆】\n{memory_text}\n\n"
        "结构：## 今日概述、## 提问与讨论、## 记住的新信息、## 待办/后续建议。"
        "中文，简洁有重点。"
    )
    content = await _call_llm(prompt)
    title = f"每日小结 {today}"
    report_id = await add_report("daily", title, content, period=today)
    return {"id": report_id, "type": "daily", "title": title, "content": content, "period": today}


async def ensure_daily_digest() -> None:
    """对话关闭时顺带补当日小结（若当天还没有）。"""
    today = date.today().isoformat()
    from aios.echo.db import list_reports

    reports = await list_reports()
    if any(r.get("type") == "daily" and r.get("period", "").startswith(today) for r in reports):
        return
    try:
        await generate_daily_digest()
    except Exception as exc:
        logger.warning("生成每日小结失败: %s", exc)


async def _call_llm(prompt: str) -> str:
    settings = await load_runtime_settings()
    raw = await request_text_from_messages(
        settings.get("api_base", "https://api.deepseek.com"),
        settings.get("api_key", ""),
        settings.get("aux_model", "deepseek-chat"),
        [
            {"role": "system", "content": "你是一个专业的报告撰写助手，输出规范的 Markdown。"},
            {"role": "user", "content": prompt},
        ],
        timeout_sec=90,
    )
    return raw.strip()
