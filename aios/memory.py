"""AIOS Memory Manager — embedding-based semantic memory.

Supports:
  - Adding memory entries (with automatic embedding)
  - Semantic search (embed query → cosine similarity → top-k)
  - Summarizing conversations into memory entries via LLM
  - Retrieving always-remember (importance=5) entries
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from aios.embedding import EmbeddingClient
from app.database import (
    delete_memory_entry,
    get_memory_always,
    insert_memory_entry,
    list_memory_entries,
    update_memory_entry,
)
from app.settings import load_runtime_settings

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single memory entry."""
    type: str            # preference | fact | decision | server_info
    key: str             # Short label
    content: str         # Full memory text
    importance: int = 3  # 1-5
    embedding: list[float] | None = None
    source_conv_id: int | None = None
    host_id: int | None = None
    id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "type": self.type, "key": self.key,
            "content": self.content, "importance": self.importance,
            "source_conv_id": self.source_conv_id,
            "host_id": self.host_id,
        }
        if self.embedding:
            d["vector"] = EmbeddingClient.encode_vector(self.embedding)
        return d


class MemoryManager:
    """Manages the embedding-based memory store.

    Usage:
        mgr = MemoryManager(embedding_client)
        await mgr.add(MemoryEntry(...))
        results = await mgr.search("nginx配置优化", top_k=5)
        always = await mgr.get_always()
    """

    SUMMARIZE_PROMPT = """你是一个信息提炼助手。从以下对话中提取值得长期记住的关键信息。

输出一个 JSON 数组，每项一个记忆条目：
[
  {
    "type": "preference|fact|decision|server_info",
    "key": "简短标签（5-15字）",
    "content": "完整的记忆内容（一句话）",
    "importance": 3
  }
]

规则：
- 用户明确说的偏好（"我喜欢用yum"）→ type=preference, importance=4
- 关键事实（服务器地址、版本号）→ type=fact, importance=4
- 重要决策（"keepalive_timeout 改成65s"）→ type=decision, importance=4
- 服务器信息（OS、配置路径）→ type=server_info, importance=3
- 不重要的闲聊、中间结果 → 不要提取
- 如果对话中没有值得记住的信息，返回空数组 []
- 每条 content 控制在 100 字以内
- key 要能用于搜索匹配

只输出 JSON 数组，不要其他文字。"""

    def __init__(self, embedding_client: EmbeddingClient | None = None):
        self._emb = embedding_client

    async def _get_emb(self) -> EmbeddingClient:
        if self._emb is not None:
            return self._emb
        settings = await load_runtime_settings()
        self._emb = EmbeddingClient(
            api_base="https://dashscope.aliyuncs.com/compatible-mode",
            api_key=settings.get("dashscope_api_key", ""),
            model=settings.get("dashscope_embed_model", "qwen3.7-text-embedding"),
        )
        return self._emb

    # ── CRUD ──

    async def add(self, entry: MemoryEntry) -> int | None:
        """Add a memory entry, computing + storing its embedding vector."""
        d = entry.to_dict()
        vector = None
        try:
            emb = await self._get_emb()
            vec = await emb.embed(d["content"])
            vector = emb.encode_vector(vec)
        except Exception as exc:
            logger.warning("Embedding compute failed, storing without vector: %s", exc)
        return await insert_memory_entry(
            entry_type=d["type"],
            key=d["key"],
            content=d["content"],
            importance=d["importance"],
            vector=vector,
            source_conv_id=d.get("source_conv_id"),
            host_id=d.get("host_id"),
        )

    async def remove(self, entry_id: int) -> bool:
        return await delete_memory_entry(entry_id)

    async def get_always(self) -> list[dict[str, Any]]:
        """Get importance=5 entries (always injected)."""
        return await get_memory_always()

    async def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Keyword-based semantic search (CrewAI-style).

        Scores each memory entry by how many query words appear in
        the key and content fields.  Simple, fast, no external deps.
        """
        # Tokenize query: whitespace-split for English, bigrams for Chinese
        import re
        keywords = set()
        query_lower = query.lower()

        # 1. Whitespace-split tokens (works for English)
        for token in re.split(r'\s+', query_lower):
            token = token.strip()
            if len(token) >= 1:
                keywords.add(token)

        # 2. Character bigrams for Chinese (no spaces between words)
        # "系统版本" → ["系统", "统版", "版本"]
        chinese_chars = re.findall(r'[一-鿿]', query)
        for i in range(len(chinese_chars) - 1):
            keywords.add(chinese_chars[i] + chinese_chars[i + 1])
        # Also add individual Chinese chars as fallback
        for c in chinese_chars[:20]:  # Limit to avoid noise
            keywords.add(c)

        if not keywords:
            return []

        all_entries = await list_memory_entries()
        scored = []
        for row in all_entries:
            key = (row.get("key") or "").lower()
            content = (row.get("content") or "").lower()
            combined = f"{key} {content}"
            # Score: count matching keywords, weighted by importance
            hits = sum(1 for kw in keywords if kw in combined)
            if hits == 0:
                continue
            importance = row.get("importance", 1)
            score = hits * (1 + importance * 0.5)  # Higher importance boosts score
            scored.append((score, dict(row)))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    # ── Summarization ──

    async def summarize_and_store(
        self,
        messages: list[dict[str, str]],
        conv_id: int | None = None,
        host_id: int | None = None,
    ) -> int:
        """LLM summarizes a conversation and stores extracted memories."""
        from aios.llm import extract_json, request_text_from_messages

        settings = await load_runtime_settings()

        # Build conversation text
        conv_text = "\n".join(
            f"[{m['role']}]: {m['content'][:500]}" for m in messages[-20:]
        )

        user_msg = f"以下是一段人机对话，请提取值得长期记住的关键信息：\n\n{conv_text}"

        try:
            raw = await request_text_from_messages(
                settings.get("api_base", "https://api.deepseek.com"),
                settings.get("api_key", ""),
                settings.get("aux_model", "deepseek-chat"),
                [
                    {"role": "system", "content": self.SUMMARIZE_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                timeout_sec=30,
            )
        except Exception as exc:
            logger.warning("Memory summarize LLM call failed: %s", exc)
            return 0

        data = extract_json(raw)
        if not data or not isinstance(data, list):
            logger.info("Memory summarize: no memories extracted")
            return 0

        count = 0
        for item in data:
            try:
                entry = MemoryEntry(
                    type=item.get("type", "fact"),
                    key=item.get("key", ""),
                    content=item.get("content", ""),
                    importance=min(5, max(1, item.get("importance", 3))),
                    source_conv_id=conv_id,
                    host_id=host_id,
                )
                await self.add(entry)
                count += 1
            except Exception as exc:
                logger.warning("Failed to store memory entry: %s", exc)

        logger.info("Memory summarize: stored %d entries", count)
        return count

    @staticmethod
    def format_for_prompt(entries: list[dict[str, Any]]) -> str:
        """Format memory entries as text for system prompt injection."""
        if not entries:
            return ""
        lines = ["## 用户记忆（从历史对话中提炼）"]
        for e in entries:
            t = e.get("type", "fact")
            tag = {"preference": "偏好", "fact": "事实", "decision": "决策", "server_info": "服务器"}.get(t, t)
            lines.append(f"- [{tag}] {e.get('content', '')}")
        return "\n".join(lines)


# ── Global singleton ──
memory_manager = MemoryManager()
