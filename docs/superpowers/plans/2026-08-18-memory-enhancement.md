# 记忆系统增强（子项目 1）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Shannon Echo Agent 增加对话中实时记忆沉淀、完整记忆库 API、定时+手动记忆提炼，以及前端记忆库页面。

**Architecture:** 新增 `aios/echo/extractor.py`（实时提取+去重）与 `aios/echo/consolidator.py`（提炼合并），扩展 `aios/echo/router.py` 提供 `/api/echo/memory/*` 端点，`app/database.py` 扩展 `memory_entries` 查询/更新能力（含 `consolidated` 列迁移），`app/main.py` 挂每日 03:17 定时提炼任务；前端新增 `/memory` 记忆库页。

**Tech Stack:** Python async (FastAPI/aiosqlite) + Vue 3 + SSE；LLM 非流式调用复用 `app/llm_client.request_text_from_messages`。

**Spec:** `docs/superpowers/specs/2026-08-18-memory-enhancement-design.md`（已批准）

## Global Constraints

- 记忆类型限定：`preference | fact | decision | server_info`；importance 1-5 整数
- 提取频率：每 5 轮（按 /echo/chat 调用次数），计数为内存态（重启归零可接受）
- 去重阈值：余弦相似度 `> 0.85` 跳过；`0.7~0.85` 合并更新（importance 取较大值）
- 新记忆立即生效：不改 `_retrieve_context` 检索逻辑
- 定时提炼：每日 03:17（asyncio 后台任务，无新依赖，失败静默次日重试）
- LLM 调用失败/JSON 解析失败：静默跳过，不阻塞对话
- 本分支实施（CLAUDE.md Git 约定）：分支 `feat/memory-system`，完成后推分支 + gh pr create
- 前端验证：`cd web && npm run build`；后端：`python -m compileall app aios`

---

### Task 1: 数据库迁移——memory_entries 增加 consolidated 列

**Files:**
- Modify: `app/database.py`（init_db 建表语句 + 兼容迁移 + 查询/更新函数扩展）

**Interfaces:**
- Produces: `list_memory_entries(limit=500, entry_type=None, importance=None, consolidated=None) -> list[dict]`；`update_memory_entry(entry_id, content=None, importance=None, vector=None, consolidated=None) -> bool`；`get_memory_entry(entry_id) -> dict | None`

- [ ] **Step 1: 修改建表语句加入 consolidated 列**

`app/database.py` 约 188 行处，将：

```sql
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
```

替换为：

```sql
CREATE TABLE IF NOT EXISTS memory_entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    type            TEXT NOT NULL,
    key             TEXT NOT NULL,
    content         TEXT NOT NULL,
    importance      INTEGER DEFAULT 3,
    vector          TEXT,
    source_conv_id  INTEGER,
    host_id         INTEGER,
    consolidated    INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

- [ ] **Step 2: 在同一建表块后添加旧库兼容迁移**

在建表语句之后（`CREATE INDEX idx_memory_importance` 附近）添加：

```python
# 旧库兼容：为 memory_entries 补 consolidated 列（已存在则忽略）
try:
    await conn.execute("ALTER TABLE memory_entries ADD COLUMN consolidated INTEGER NOT NULL DEFAULT 0")
except Exception:
    pass  # 列已存在
```

（如该处无 `conn` 可用，改用 `get_connection()` 获取；参照该函数内部现有写法。）

- [ ] **Step 3: 扩展 list_memory_entries 支持过滤**

将现有 `list_memory_entries`（约 1385 行）：

```python
async def list_memory_entries(limit: int = 500) -> list[dict]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM memory_entries ORDER BY importance DESC, created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows]
    finally:
        await conn.close()
```

替换为：

```python
async def list_memory_entries(
    limit: int = 500,
    entry_type: str | None = None,
    importance: int | None = None,
    consolidated: int | None = None,
) -> list[dict]:
    conn = await get_connection()
    try:
        sql = "SELECT * FROM memory_entries WHERE 1=1"
        params: list = []
        if entry_type:
            sql += " AND type = ?"
            params.append(entry_type)
        if importance is not None:
            sql += " AND importance = ?"
            params.append(importance)
        if consolidated is not None:
            sql += " AND consolidated = ?"
            params.append(consolidated)
        sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
        params.append(limit)
        cursor = await conn.execute(sql, params)
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows]
    finally:
        await conn.close()
```

- [ ] **Step 4: 扩展 update_memory_entry 支持 consolidated**

在 `update_memory_entry`（约 1412 行）中，`if vector is not None:` 块之后、`if not updates: return False` 之前插入：

```python
        if consolidated is not None:
            updates.append("consolidated = ?")
            params.append(int(consolidated))
```

- [ ] **Step 5: 新增 get_memory_entry**

在 `delete_memory_entry` 之后新增：

```python
async def get_memory_entry(entry_id: int) -> dict | None:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM memory_entries WHERE id = ?", (entry_id,)
        )
        row = await cursor.fetchone()
        await cursor.close()
        return dict(row) if row else None
    finally:
        await conn.close()
```

- [ ] **Step 6: 验证迁移与查询**

Run: `python -c "import asyncio; from app.database import init_db, list_memory_entries; asyncio.run(init_db()); print(len(asyncio.run(list_memory_entries())))"`
Expected: 输出 0 或现有记忆数量，无异常（旧库自动补列成功）

- [ ] **Step 7: 提交**

```bash
git add app/database.py
git commit -m "feat(db): memory_entries 增加 consolidated 列与过滤查询（兼容旧库迁移）"
```

---

### Task 2: 记忆提取器（aios/echo/extractor.py）

**Files:**
- Create: `aios/echo/extractor.py`

**Interfaces:**
- Consumes: `request_text_from_messages`（app/llm_client.py:47）、`MemoryManager`（aios/memory.py:88）、`load_runtime_settings`（app/settings.py）、`list_memory_entries` / `update_memory_entry`（Task 1）
- Produces: `extract_and_store_memories(conv_id: int, messages: list[dict]) -> dict[str, int]`，返回 `{"extracted": n, "merged": n, "skipped": n}`
- Produces: `_cosine_similarity(a: list[float], b: list[float]) -> float`（模块内使用）

- [ ] **Step 1: 编写 extractor.py 完整实现**

创建 `aios/echo/extractor.py`：

```python
"""Echo 记忆提取器 — 对话中实时沉淀记忆。

每 N 轮由 LLM 从最近对话中提取值得记忆的事实（preference/fact/decision/server_info），
写入前与现有记忆做 embedding 余弦相似度去重：
  - 相似度 > 0.85  → 跳过（同一事实已存在）
  - 0.7 ~ 0.85    → 合并（更新原条目，importance 取较大值）
  - < 0.7         → 插入新记忆
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.llm_client import request_text_from_messages
from app.settings import load_runtime_settings
from aios.embedding import EmbeddingClient
from aios.echo.memory import get_user_profile
from aios.memory import MemoryEntry, MemoryManager
from app.database import list_memory_entries, update_memory_entry

logger = logging.getLogger(__name__)

VALID_TYPES = ("preference", "fact", "decision", "server_info")

# 与现有记忆比较的相似度阈值
SKIP_THRESHOLD = 0.85
MERGE_THRESHOLD = 0.7

_EXTRACT_SYSTEM_PROMPT = """你是 Shannon 的记忆提取器。从用户与助手的对话中提取"值得长期记住"的事实。

只提取以下类型（type 字段严格使用其一）：
- preference: 用户偏好（喜欢/不喜欢/习惯/口味）
- fact: 客观事实（个人信息、日程安排、家庭/工作信息、兴趣爱好）
- decision: 决定（用户做出的重要决定或结论）
- server_info: 服务器/技术环境相关信息

规则：
1. 只记"未来还有用"的信息，日常寒暄、瞬时请求不记
2. content 用中文精炼陈述，第一人称视角写用户（如"用户下周末去杭州出差"）
3. importance 1-5：影响未来多轮对话的记 4-5，一般的记 2-3
4. 无值得记的内容时输出空数组

输出严格为 JSON 数组，不要任何其他文字：
[{"type": "fact", "content": "...", "importance": 3}]
"""


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """余弦相似度（向量长度不一致时返回 0）。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _parse_extraction(raw: str) -> list[dict[str, Any]]:
    """从 LLM 输出中解析 JSON 数组，失败返回空列表。"""
    text = raw.strip()
    # 去掉可能的 markdown 代码块围栏
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE)
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
        if not isinstance(item, dict):
            continue
        t = str(item.get("type", "")).strip()
        content = str(item.get("content", "")).strip()
        if t not in VALID_TYPES or not content:
            continue
        try:
            imp = max(1, min(5, int(item.get("importance", 3))))
        except (TypeError, ValueError):
            imp = 3
        result.append({"type": t, "content": content, "importance": imp})
    return result


async def extract_and_store_memories(conv_id: int, messages: list[dict]) -> dict[str, int]:
    """从最近对话提取记忆并去重写入。任何失败都静默返回全零，不阻塞调用方。"""
    result = {"extracted": 0, "merged": 0, "skipped": 0}
    try:
        settings = await load_runtime_settings()
        if not settings.get("api_key"):
            return result
        profile = await get_user_profile()
        user_msgs = "\n".join(
            f"{'用户' if m.get('role') == 'user' else '助手'}: {m.get('content', '')}"
            for m in messages[-10:]
        )
        user_prompt = (
            f"当前用户画像：\n{profile if profile else '（暂无）'}\n\n"
            f"最近对话：\n{user_msgs}\n\n请提取值得长期记住的记忆。"
        )
        raw = await request_text_from_messages(
            settings.get("api_base", "https://api.deepseek.com"),
            settings.get("api_key", ""),
            settings.get("aux_model", "deepseek-chat"),
            [
                {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            timeout_sec=60,
        )
        candidates = _parse_extraction(raw)
        if not candidates:
            return result

        manager = MemoryManager()
        emb = EmbeddingClient()
        existing = await list_memory_entries(limit=500)
        existing_vecs: list[tuple[int, dict, list[float] | None]] = []
        for e in existing:
            v = None
            if e.get("vector"):
                try:
                    v = json.loads(e["vector"])
                except json.JSONDecodeError:
                    v = None
            existing_vecs.append((e["id"], e, v))

        for cand in candidates:
            content = cand["content"]
            vec = None
            try:
                vec = emb.encode_vector(await emb.embed(content))
            except Exception as exc:
                logger.warning("提取记忆 embedding 失败（无向量入库）: %s", exc)

            # 去重：与现有记忆比较
            best_id, best_sim = None, 0.0
            for eid, entry, ev in existing_vecs:
                if ev and vec:
                    sim = _cosine_similarity(vec, ev)
                    if sim > best_sim:
                        best_id, best_sim = eid, sim
            if best_id is not None and best_sim > SKIP_THRESHOLD:
                result["skipped"] += 1
                continue
            if best_id is not None and best_sim >= MERGE_THRESHOLD:
                old = dict(existing_vecs[[i for i, (iid, _, _) in enumerate(existing_vecs) if iid == best_id][0]][1])
                new_imp = max(int(old.get("importance", 3)), cand["importance"])
                vector_str = json.dumps(vec) if vec else None
                await update_memory_entry(
                    best_id,
                    content=content,
                    importance=new_imp,
                    vector=vector_str,
                )
                result["merged"] += 1
                continue
            # 插入新记忆
            await manager.add(
                MemoryEntry(
                    type=cand["type"],
                    key=cand["content"][:40],
                    content=content,
                    importance=cand["importance"],
                    source_conv_id=conv_id,
                )
            )
            result["extracted"] += 1
        return result
    except Exception as exc:
        logger.warning("记忆提取失败（静默跳过）: %s", exc)
        return result
```

- [ ] **Step 2: 验证语法与导入**

Run: `python -m compileall aios/echo/extractor.py && python -c "from aios.echo.extractor import extract_and_store_memories; print('导入成功')"`
Expected: `导入成功`

- [ ] **Step 3: 提交**

```bash
git add aios/echo/extractor.py
git commit -m "feat(echo): 新增对话记忆提取器（LLM 提取 + 向量去重 + 合并/跳过/插入）"
```

---

### Task 3: 对话中实时沉淀接入（/echo/chat 每 5 轮触发）

**Files:**
- Modify: `aios/echo/router.py`（`_run_echo_chat` + 模块级计数）

**Interfaces:**
- Consumes: `extract_and_store_memories`（Task 2）、`get_messages`（aios/echo/db.py:186）
- Produces: 无（内部行为）

- [ ] **Step 1: 添加模块级提取计数与触发逻辑**

在 `aios/echo/router.py` 顶部（`import uuid` 附近）添加：

```python
import asyncio

# 会话级"待提取"计数：每 5 轮触发一次记忆提取（内存态，重启归零）
_EXTRACT_INTERVAL = 5
_pending_extract_counts: dict[int, int] = {}
```

（若 `asyncio` 已导入则跳过导入行。）

- [ ] **Step 2: 在 _run_echo_chat 完成回复落库后触发提取**

在 `_run_echo_chat` 中"落库 assistant 消息"之后、`done` 事件之前插入：

```python
        # 实时记忆沉淀：每 _EXTRACT_INTERVAL 轮触发一次（异步执行，不阻塞 SSE）
        count = _pending_extract_counts.get(conv_id, 0) + 1
        _pending_extract_counts[conv_id] = count
        if count % _EXTRACT_INTERVAL == 0:
            from aios.echo.extractor import extract_and_store_memories
            recent = await get_messages(conv_id, limit=20)
            asyncio.create_task(
                extract_and_store_memories(conv_id, recent)
            )
```

（`get_messages` 若未在 router.py 导入则从 `aios.echo.db import get_messages` 导入。）

- [ ] **Step 3: 验证语法**

Run: `python -m compileall aios/echo/router.py`
Expected: 通过

- [ ] **Step 4: 提交**

```bash
git add aios/echo/router.py
git commit -m "feat(echo): /echo/chat 每 5 轮触发实时记忆沉淀（异步不阻塞）"
```

---

### Task 4: 记忆提炼器（aios/echo/consolidator.py）

**Files:**
- Create: `aios/echo/consolidator.py`

**Interfaces:**
- Consumes: `request_text_from_messages`、`list_memory_entries(consolidated=0)` / `update_memory_entry(consolidated=...)` / `delete_memory_entry`（Task 1）、`load_runtime_settings`
- Produces: `consolidate_memories() -> dict[str, int]`，返回 `{"processed": n, "merged": n, "deleted": n}`

- [ ] **Step 1: 编写 consolidator.py 完整实现**

创建 `aios/echo/consolidator.py`：

```python
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

from app.database import (
    delete_memory_entry,
    list_memory_entries,
    update_memory_entry,
)
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
                    imp = max(1, min(5, int(item.get("importance", 3))))
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
```

- [ ] **Step 2: 验证语法与导入**

Run: `python -m compileall aios/echo/consolidator.py && python -c "from aios.echo.consolidator import consolidate_memories; print('导入成功')"`
Expected: `导入成功`

- [ ] **Step 3: 提交**

```bash
git add aios/echo/consolidator.py
git commit -m "feat(echo): 新增记忆提炼器（分组 LLM 合并去重 + 标记已提炼）"
```

---

### Task 5: 记忆库 API（router.py 扩展）

**Files:**
- Modify: `aios/echo/router.py`（新增 7 个端点）

**Interfaces:**
- Consumes: `list_memory_entries`/`get_memory_entry`/`update_memory_entry`/`delete_memory_entry`/`insert_memory_entry`（Task 1）、`MemoryManager`（aios/memory.py）、`consolidate_memories`（Task 4）、`get_user_profile`（aios/echo/memory.py:59）
- Produces: 7 个 HTTP 端点（见下）

- [ ] **Step 1: 添加 Pydantic 请求模型**

在 `aios/echo/router.py` 的模型定义区添加：

```python
from pydantic import BaseModel

class MemoryCreateRequest(BaseModel):
    type: str
    content: str
    importance: int = 3

class MemoryUpdateRequest(BaseModel):
    content: str | None = None
    importance: int | None = None
    type: str | None = None
```

- [ ] **Step 2: 添加 7 个端点（在文件末尾、现有端点之后）**

```python
# ── 记忆库 API ──

@router.get("/echo/memory")
async def api_echo_list_memory(
    type: str | None = None,
    importance: int | None = None,
    consolidated: int | None = None,
    limit: int = Query(default=200, le=500),
) -> dict:
    entries = await list_memory_entries(
        limit=limit, entry_type=type, importance=importance, consolidated=consolidated
    )
    return {"memories": entries, "total": len(entries)}


@router.get("/echo/memory/search")
async def api_echo_search_memory(q: str = Query(default="", min_length=1)) -> dict:
    if not q.strip():
        return {"memories": []}
    manager = MemoryManager()
    hits = await manager.search(q, top_k=10)
    return {"memories": hits}


@router.post("/echo/memory")
async def api_echo_create_memory(payload: MemoryCreateRequest) -> dict:
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="内容不能为空")
    if payload.type not in ("preference", "fact", "decision", "server_info"):
        raise HTTPException(status_code=400, detail="type 不合法")
    entry_id = await MemoryManager().add(
        MemoryEntry(
            type=payload.type,
            key=content[:40],
            content=content,
            importance=max(1, min(5, payload.importance)),
        )
    )
    return {"ok": True, "id": entry_id}


@router.put("/echo/memory/{memory_id}")
async def api_echo_update_memory(memory_id: int, payload: MemoryUpdateRequest) -> dict:
    entry = await get_memory_entry(memory_id)
    if not entry:
        raise HTTPException(status_code=404, detail="记忆不存在")
    new_content = payload.content.strip() if payload.content else entry.get("content")
    new_imp = payload.importance if payload.importance is not None else entry.get("importance")
    if payload.importance is not None:
        new_imp = max(1, min(5, payload.importance))
    vector_str = None
    try:
        emb = EmbeddingClient()
        vec = emb.encode_vector(await emb.embed(new_content or ""))
        vector_str = json.dumps(vec)
    except Exception as exc:
        logger.warning("记忆更新 embedding 失败: %s", exc)
    await update_memory_entry(
        memory_id,
        content=new_content,
        importance=new_imp,
        vector=vector_str,
    )
    return {"ok": True}


@router.delete("/echo/memory/{memory_id}")
async def api_echo_delete_memory(memory_id: int) -> dict:
    ok = await delete_memory_entry(memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {"ok": True}


@router.post("/echo/memory/consolidate")
async def api_echo_consolidate_memory() -> dict:
    result = await consolidate_memories()
    return {"ok": True, **result}


@router.get("/echo/memory/profile")
async def api_echo_memory_profile() -> dict:
    profile = await get_user_profile()
    return {"profile": profile}
```

**注意**：文件末尾需补充导入（按文件中现有 import 风格）：
```python
from aios.echo.consolidator import consolidate_memories
from aios.echo.memory import get_user_profile
from aios.embedding import EmbeddingClient
from aios.memory import MemoryEntry, MemoryManager
from app.database import (
    delete_memory_entry,
    get_memory_entry,
    insert_memory_entry,  # 如未使用可不加
    list_memory_entries,
    update_memory_entry,
)
from fastapi import Query
import json
import logging
```
（`json`/`logging`/`Query` 如已导入则跳过；`logger = logging.getLogger(__name__)` 如缺失则补充。）

- [ ] **Step 3: 验证语法与路由注册**

Run: `python -m compileall aios/echo/router.py`
Expected: 通过

- [ ] **Step 4: 提交**

```bash
git add aios/echo/router.py
git commit -m "feat(echo): 新增记忆库 API（列表/搜索/增/改/删/提炼/画像）"
```

---

### Task 6: 定时提炼任务（app/main.py）

**Files:**
- Modify: `app/main.py`（startup_event + shutdown_event）

**Interfaces:**
- Consumes: `consolidate_memories`（Task 4）
- Produces: 后台任务生命周期管理（app.state）

- [ ] **Step 1: 添加后台定时任务**

在 `app/main.py` 的 `startup_event` 中、`MonitorScheduler` 启动之后添加：

```python
    # -- Echo 记忆每日提炼（03:17） --
    from aios.echo.consolidator import consolidate_memories

    async def _memory_consolidation_loop():
        while True:
            now = datetime.now()
            target = now.replace(hour=3, minute=17, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            await asyncio.sleep((target - now).total_seconds())
            try:
                result = await consolidate_memories()
                logger.info("每日记忆提炼完成: %s", result)
            except Exception as exc:
                logger.warning("每日记忆提炼失败（次日重试）: %s", exc)

    app.state.memory_consolidate_task = asyncio.create_task(_memory_consolidation_loop())
```

并确保 `app/main.py` 顶部已有 `import asyncio` 与 `from datetime import datetime, timedelta`（缺失则补充）。

- [ ] **Step 2: 在 shutdown_event 中取消任务**

在 `shutdown_event` 中（`close_all_sessions` 附近）添加：

```python
    task = getattr(app.state, "memory_consolidate_task", None)
    if task:
        task.cancel()
```

- [ ] **Step 3: 验证语法**

Run: `python -m compileall app/main.py`
Expected: 通过

- [ ] **Step 4: 提交**

```bash
git add app/main.py
git commit -m "feat: 每日 03:17 自动提炼 Echo 记忆（asyncio 后台任务，随服务启停）"
```

---

### Task 7: 前端记忆库页（api.js + Memory.vue + 路由 + 入口）

**Files:**
- Modify: `web/src/services/api.js`、`web/src/router/index.js`、`web/src/components/layout/Layout.vue`
- Create: `web/src/pages/Memory.vue`

**Interfaces:**
- Consumes: 后端 `/api/echo/memory*` 端点（Task 5）
- Produces: `memoryApi` 对象 + `/memory` 路由 + 记忆库页

- [ ] **Step 1: api.js 添加 memoryApi**

在 `web/src/services/api.js` 中 `echoApi` 定义后添加：

```js
// 记忆库
export const memoryApi = {
  list: (params) => api.get('/echo/memory', { params }),
  search: (q) => api.get('/echo/memory/search', { params: { q } }),
  create: (data) => api.post('/echo/memory', data),
  update: (id, data) => api.put(`/echo/memory/${id}`, data),
  remove: (id) => api.delete(`/echo/memory/${id}`),
  consolidate: () => api.post('/echo/memory/consolidate'),
  profile: () => api.get('/echo/memory/profile'),
}
```

- [ ] **Step 2: router/index.js 添加 /memory 路由**

在 `web/src/router/index.js` 的 `/echo/reports` 路由后添加：

```js
    {
      path: '/memory',
      name: 'Memory',
      component: () => import('../pages/Memory.vue')
    },
```

- [ ] **Step 3: Layout.vue「更多」抽屉加入口**

在 `web/src/components/layout/Layout.vue` 的 `moreItems` 数组（约 246-254 行）中添加一项：

```js
  { path: '/memory', label: '记忆库', icon: '🧠' },
```

- [ ] **Step 4: 创建 Memory.vue 页面**

创建 `web/src/pages/Memory.vue`：

```vue
<template>
  <Layout>
    <div class="page-header">
      <h1 class="page-title">记忆库</h1>
      <div class="flex items-center gap-1">
        <TerminalButton v-if="isMobile" />
        <NotificationBell v-if="isMobile" />
      </div>
    </div>

    <!-- 用户画像 -->
    <div class="memory-card profile-card" v-if="profile">
      <div class="card-title">🧑‍💻 用户画像</div>
      <p class="profile-text">{{ profile }}</p>
    </div>

    <!-- 操作行 -->
    <div class="toolbar">
      <input v-model="searchQuery" class="input flex-1" placeholder="搜索记忆..." @keyup.enter="doSearch" />
      <button @click="doSearch" class="btn btn-outline">搜索</button>
      <button @click="resetSearch" class="btn btn-outline">全部</button>
      <button @click="openCreate" class="btn btn-primary">+ 添加记忆</button>
      <button @click="doConsolidate" class="btn btn-outline" :disabled="consolidating">🧹 提炼记忆</button>
    </div>

    <!-- 记忆列表 -->
    <div v-for="group in groupedMemories" :key="group.type" class="memory-card">
      <div class="card-title">{{ typeLabels[group.type] || group.type }}
        <span class="count-badge">{{ group.items.length }}</span>
      </div>
      <div class="memory-item" v-for="m in group.items" :key="m.id">
        <div class="memory-content">{{ m.content }}</div>
        <div class="memory-meta">
          <span class="stars">{{ '★'.repeat(m.importance || 0) }}<span class="stars-dim">{{ '★'.repeat(5 - (m.importance || 0)) }}</span></span>
          <span class="memory-date">{{ formatDate(m.created_at) }}</span>
          <span v-if="!m.consolidated" class="raw-tag">未提炼</span>
        </div>
        <div class="memory-actions">
          <button class="action-icon" title="编辑" @click="openEdit(m)">✏️</button>
          <button class="action-icon" title="删除" @click="removeMemory(m)">🗑️</button>
        </div>
      </div>
      <div v-if="group.items.length === 0" class="empty-state"><p>暂无{{ typeLabels[group.type] }}记忆</p></div>
    </div>
    <div v-if="!loading && allMemories.length === 0" class="memory-card empty-state">
      <p>暂无记忆。去 Echo 聊聊天，重要信息会自动沉淀在这里。</p>
    </div>

    <!-- 编辑/添加弹窗 -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3 class="modal-title">{{ editing ? '编辑记忆' : '添加记忆' }}</h3>
          <button @click="showModal = false" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="filter-label">类型</label>
            <select v-model="form.type" class="input w-full">
              <option value="preference">偏好</option>
              <option value="fact">事实</option>
              <option value="decision">决定</option>
              <option value="server_info">服务器信息</option>
            </select>
          </div>
          <div class="form-group">
            <label class="filter-label">内容</label>
            <textarea v-model="form.content" class="input w-full form-textarea" rows="4" placeholder="记忆内容..."></textarea>
          </div>
          <div class="form-group">
            <label class="filter-label">重要性 (1-5)</label>
            <input v-model.number="form.importance" type="number" min="1" max="5" class="input w-full" />
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showModal = false" class="btn btn-outline">取消</button>
          <button @click="saveMemory" class="btn btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Layout from '../components/layout/Layout.vue'
import NotificationBell from '../components/NotificationBell.vue'
import TerminalButton from '../components/TerminalButton.vue'
import { useIsMobile } from '../composables/useIsMobile'
import { memoryApi } from '../services/api'

const { isMobile } = useIsMobile()

const typeLabels = { preference: '偏好', fact: '事实', decision: '决定', server_info: '服务器信息' }
const allTypes = ['preference', 'fact', 'decision', 'server_info']

const allMemories = ref([])
const profile = ref('')
const loading = ref(false)
const saving = ref(false)
const consolidating = ref(false)
const searchQuery = ref('')
const showModal = ref(false)
const editing = ref(null)
const form = ref({ type: 'fact', content: '', importance: 3 })

const groupedMemories = computed(() =>
  allTypes.map(type => ({ type, items: allMemories.value.filter(m => m.type === type) }))
)

async function loadMemories(params = {}) {
  loading.value = true
  try {
    const res = await memoryApi.list({ limit: 200, ...params })
    allMemories.value = res.data.memories || []
  } catch (e) {
    console.error('加载记忆失败:', e)
  } finally {
    loading.value = false
  }
}

async function loadProfile() {
  try {
    const res = await memoryApi.profile()
    profile.value = res.data.profile || ''
  } catch (e) {
    console.error('加载画像失败:', e)
  }
}

function doSearch() {
  const q = searchQuery.value.trim()
  if (!q) return resetSearch()
  memoryApi.search(q).then(res => { allMemories.value = res.data.memories || [] })
    .catch(e => console.error('搜索失败:', e))
}

function resetSearch() {
  searchQuery.value = ''
  loadMemories()
}

function openCreate() {
  editing.value = null
  form.value = { type: 'fact', content: '', importance: 3 }
  showModal.value = true
}

function openEdit(m) {
  editing.value = m
  form.value = { type: m.type, content: m.content, importance: m.importance || 3 }
  showModal.value = true
}

async function saveMemory() {
  if (!form.value.content.trim()) return
  saving.value = true
  try {
    if (editing.value) {
      await memoryApi.update(editing.value.id, {
        content: form.value.content, importance: form.value.importance, type: form.value.type
      })
    } else {
      await memoryApi.create(form.value)
    }
    showModal.value = false
    loadMemories()
  } catch (e) {
    console.error('保存失败:', e)
  } finally {
    saving.value = false
  }
}

async function removeMemory(m) {
  if (!confirm(`确定删除这条记忆？\n${m.content.slice(0, 50)}`)) return
  try {
    await memoryApi.remove(m.id)
    loadMemories()
  } catch (e) {
    console.error('删除失败:', e)
  }
}

async function doConsolidate() {
  if (!confirm('将零散记忆提炼为长期事实，确定执行？')) return
  consolidating.value = true
  try {
    const res = await memoryApi.consolidate()
    alert(`提炼完成：处理 ${res.data.processed || 0} 条，合并 ${res.data.merged || 0} 条，删除重复 ${res.data.deleted || 0} 条`)
    loadMemories()
  } catch (e) {
    console.error('提炼失败:', e)
  } finally {
    consolidating.value = false
  }
}

function formatDate(s) {
  if (!s) return ''
  const d = new Date(s.replace(' ', 'T'))
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(() => { loadMemories(); loadProfile() })
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 16px; align-items: center; }
.memory-card {
  background: var(--bg-surface); border: 1px solid var(--bg-border);
  border-radius: var(--radius-lg); padding: 20px; margin-bottom: 16px;
}
.card-title { font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 12px; }
.count-badge { font-size: 11px; background: var(--bg-hover); color: var(--text-tertiary); border-radius: 10px; padding: 1px 8px; margin-left: 6px; }
.profile-text { font-size: 13px; line-height: 1.8; color: var(--text-secondary); white-space: pre-wrap; }
.memory-item {
  display: flex; align-items: flex-start; gap: 10px; padding: 10px 0;
  border-top: 1px solid var(--bg-border);
}
.memory-item:first-of-type { border-top: none; }
.memory-content { flex: 1; font-size: 13px; color: var(--text-primary); line-height: 1.6; }
.memory-meta { display: flex; gap: 8px; align-items: center; font-size: 11px; color: var(--text-tertiary); white-space: nowrap; }
.stars { color: var(--primary); }
.stars-dim { color: var(--bg-hover); }
.raw-tag { background: var(--warning-light); color: var(--warning); border-radius: 8px; padding: 1px 6px; }
.memory-actions { display: flex; gap: 4px; }
.action-icon { background: none; border: none; cursor: pointer; font-size: 14px; opacity: 0.7; }
.action-icon:hover { opacity: 1; }
.form-group { margin-bottom: 12px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.empty-state { text-align: center; color: var(--text-tertiary); font-size: 13px; padding: 20px 0; }
</style>
```

- [ ] **Step 5: 前端构建验证**

Run: `cd web && node node_modules/vite/bin/vite.js build`
Expected: `✓ built in ...`（构建成功，无未定义引用）

- [ ] **Step 6: 提交**

```bash
git add web/src
git commit -m "feat(web): 新增记忆库页面（画像/列表/搜索/增删改/提炼）+ memoryApi + 路由与入口"
```

---

### Task 8: 端到端验证与 PR

**Files:** 无（验证 + 发布）

- [ ] **Step 1: 后端全量编译**

Run: `python -m compileall app aios agents`
Expected: 全部通过

- [ ] **Step 2: 记忆库 API 冒烟测试（起服务）**

Run（后台启动服务后逐个 curl）：
```bash
python -m uvicorn app.main:app --port 8001 &
curl -s http://127.0.0.1:8001/api/echo/memory | head -c 300
curl -s -X POST http://127.0.0.1:8001/api/echo/memory -H 'Content-Type: application/json' -d '{"type":"fact","content":"用户下周末去杭州出差","importance":3}'
curl -s "http://127.0.0.1:8001/api/echo/memory/search?q=杭州" | head -c 300
curl -s -X POST http://127.0.0.1:8001/api/echo/memory/consolidate
curl -s http://127.0.0.1:8001/api/echo/memory/profile
```
Expected: 各端点返回 200/ok，添加后列表可见，搜索命中

- [ ] **Step 3: 完整验证后收尾**

确认第 2 步添加的测试记忆已删除（DELETE），服务停止。

- [ ] **Step 4: 推分支并创建 PR**

```bash
git add -A
git commit -m "docs: 记忆增强实施计划" 2>/dev/null || true
git push -u origin feat/memory-system
gh pr create --title "feat: 记忆系统增强（子项目 1）" --body "实现对话中实时记忆沉淀、记忆库 API、定时+手动提炼、前端记忆库页面。详见 spec: docs/superpowers/specs/2026-08-18-memory-enhancement-design.md"
```

（若 `gh` 不在当前会话 PATH，用 `/c/Program Files/GitHub CLI/gh.exe pr create ...`）

---

## Self-Review 记录

**Spec 覆盖：**
- ① 对话中实时沉淀（每 5 轮 LLM 提取 + 0.85/0.7 去重阈值）→ Task 2 + Task 3 ✓
- ② 记忆库 API（7 端点）→ Task 5 ✓
- ③ 提炼（定时 03:17 + 手动）→ Task 4 + Task 6 ✓
- ④ 前端记忆库页（画像/列表/搜索/编辑删除/手动添加/提炼按钮）→ Task 7 ✓
- ⑤ 验证方式 → Task 8 ✓
- 不做的事（无遗忘策略/多用户/改检索架构）→ Global Constraints ✓
- DB consolidated 列 → Task 1 ✓

**占位符检查：** 所有代码步骤含完整实现；Task 3 的插入位置以现有函数行为锚点，无 TBD。

**类型一致性：** `extract_and_store_memories(conv_id, messages) -> dict[str,int]`（Task 2 定义，Task 3 消费）；`consolidate_memories() -> dict[str,int]`（Task 4 定义，Task 5/6 消费）；`list_memory_entries(limit, entry_type, importance, consolidated)`（Task 1 定义，Task 2/4/5 消费）——前后一致。
