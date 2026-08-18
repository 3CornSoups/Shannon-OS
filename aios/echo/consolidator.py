"""Echo 记忆提炼器 — 把零散记忆整理为长期事实。

取 consolidated=0 的新增记忆，按类型分组交给 LLM 去重、合并、提炼，
生成精炼后的长期事实；merge_ids 对应的原条目更新为提炼结果并标记已提炼，
重复条目删除。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.database import delete_memory_entry, list_memory_entries, update_memory_entry
from app.llm_client import request_text_from_messages
from app.settings import load_runtime_settings

logger = logging.getLogger(__name__)

_MAX_ITEMS_PER_GROUP = 30

_CONSOLIDATE_SYSTEM_PROMPT = """你是 Shannon 的记忆整理员。把一组零散记忆提炼为长期事实。

输入是 JSON 数组，每项形如 {"id": 123, "type": "fact", "content": "..."}。
输出严格为 JSON 数组，每项形如：
{"type": "fact", "content": "提炼后的精炼陈述", "importance": 3, "merge_ids": [123, 124]}

规则：
1. 内容重复/同义的记忆合并为一条（merge_ids 列出被合并的原 id）
2. 同类事实合并后写成简洁、自包含的中文陈述
3. 独立不重复的记忆保持原样，merge_ids 只含自身 id
4. importance 1-5，取该类记忆中最高重要性
5. 输出数组顺序任意，不要输出其他文字
"""


def _parse_consolidation(raw: str) -> list[dict[str, Any]]:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip(), flags=re.MULTILINE)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if not isinstance(item, dict) or not item.get("content"):
            continue
        ids = item.get("merge_ids") or []
        if not isinstance(ids, list):
            ids = [ids]
        result.append({
            "type": str(item.get("type", "fact")),
            "content": str(item["content"]).strip(),
            "importance": item.get("importance", 3),
            "merge_ids": [int(i) for i in ids if isinstance(i, int) or str(i).isdigit()],
        })
    return result


async def consolidate_memories() -> dict[str, int]:
    """提炼 consolidated=0 的记忆。按类型分批交给 LLM，合并去重后写回。"""
    result = {"processed": 0, "merged": 0, "deleted": 0}
    try:
        settings = await load_runtime_settings()
        if not settings.get("api_key"):
            return result
        pending = await list_memory_entries(limit=500, consolidated=0)
        if not pending:
            return result

        # 按类型分组
        groups: dict[str, list[dict]] = {}
        for e in pending:
            groups.setdefault(e.get("type", "fact"), []).append(e)

        for etype, entries in groups.items():
            for start in range(0, len(entries), _MAX_ITEMS_PER_GROUP):
                chunk = entries[start:start + _MAX_ITEMS_PER_GROUP]
                payload = json.dumps(
                    [{"id": e["id"], "type": e.get("type"), "content": e.get("content", "")}
                     for e in chunk],
                    ensure_ascii=False,
                )
                raw = await request_text_from_messages(
                    settings.get("api_base", "https://api.deepseek.com"),
                    settings.get("api_key", ""),
                    settings.get("aux_model", "deepseek-chat"),
                    [
                        {"role": "system", "content": _CONSOLIDATE_SYSTEM_PROMPT},
                        {"role": "user", "content": payload},
                    ],
                    timeout_sec=90,
                )
                consolidated_items = _parse_consolidation(raw)
                chunk_ids = {e["id"] for e in chunk}
                handled: set[int] = set()
                for item in consolidated_items:
                    content = item["content"]
                    try:
                        imp = max(1, min(5, int(item.get("importance", 3))))
                    except (TypeError, ValueError):
                        imp = 3
                    merge_ids = [i for i in item["merge_ids"] if i in chunk_ids]
                    if not merge_ids:
                        continue
                    primary = merge_ids[0]
                    await update_memory_entry(
                        primary, content=content, importance=imp, consolidated=1
                    )
                    result["merged"] += 1
                    handled.add(primary)
                    for extra in merge_ids[1:]:
                        await delete_memory_entry(extra)
                        result["deleted"] += 1
                        handled.add(extra)
                # 未被 LLM 提到的条目直接标记已提炼（保留原内容）
                for e in chunk:
                    if e["id"] not in handled:
                        await update_memory_entry(e["id"], consolidated=1)
                result["processed"] += len(chunk)
        return result
    except Exception as exc:
        logger.warning("记忆提炼失败: %s", exc)
        return result
