# 子项目 1：记忆系统增强 设计

> 日期：2026-08-18
> 状态：已批准（用户确认"按推荐来"）
> 所属：Shannon OS → 个人 AI 助手演进（子项目 1/3）

## 背景

用户希望把 Shannon 项目演进为"跑在 Linux 上的个人 AI 助手（Cursor 式代码 + 豆包式聊天 + 出色的记忆）"。经范围分解，子项目 1 为**记忆系统增强**（核心卖点，独立可做）。

现状：Echo Agent 已有基础记忆（用户画像 LLM 增量维护、MemoryManager 向量检索 + importance 分级、提问档案 FTS5、报告生成），但缺三块：
1. 对话中实时沉淀（现在只在对话关闭时提炼画像）
2. 记忆可视化（前端无记忆库页面）
3. 记忆提炼（零散记忆整理为长期事实）

## 已确认的决策

1. **沉淀时机**：对话中实时沉淀（每 5 轮批量 LLM 提取）
2. **记忆库页面**：完整页（列表/搜索/编辑/删除/手动添加/画像栏）
3. **提炼机制**：定时（每日 03:17 asyncio 后台任务）+ 手动按钮
4. **提取方案**：A. 批量 LLM 提取（非每轮，去重写入）

## 详细设计

### ① 对话中实时沉淀

**接入点**：`aios/echo/agent.py` 的对话处理循环（`/echo/chat` 路由调用处）。

- 维护"待提取轮次计数"（会话级）：每轮对话（user 消息）计数 +1
- 计数达到 **5** 或对话结束（close 请求 / 会话超时）时触发 `extract_and_store_memories(conv_id, recent_messages)`：
  1. 取最近 5 轮 user/assistant 消息文本 + 当前用户画像（`get_user_profile()`）
  2. 调 LLM（`aios/llm.request_text_from_messages`，非流式，用 runtime settings 的主模型或 aux_model）输出 JSON 数组：`[{"type": "preference|fact|decision|server_info", "content": "...", "importance": 1-5}]`，无值得记的内容时输出 `[]`
  3. 对每条候选记忆**去重**：用 `MemoryManager` 的 embedding 与现有记忆做余弦相似度——`> 0.85` 跳过；`0.7~0.85` 合并（更新原条目 content，importance 取较大值）；否则 `insert_memory_entry`（含 embedding + `source_conv_id`，新字段 `consolidated=0`）
  4. 失败容错：LLM 调用异常/JSON 解析失败 → 静默跳过本轮提取（不阻塞对话）
- 新记忆**立即生效**：后续轮次的 `_retrieve_context` 检索自动命中（无需改动检索逻辑）

**新文件**：`aios/echo/extractor.py`（记忆提取器，含 prompt 与去重逻辑）

### ② 记忆库 API（后端）

挂载于 `aios/echo/router.py`（前缀 `/api`）：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/echo/memory` | 列表：`?type=` `?importance=` `?consolidated=` 过滤 + `?limit/offset` 分页，按 importance 降序、created_at 倒序 |
| GET | `/echo/memory/search?q=` | 关键词（FTS5/bigram）+ 向量（top_k=10）混合，去重合并返回 |
| POST | `/echo/memory` | 手动添加 `{type, content, importance?}`（LLM 生成 key，embedding 入库） |
| PUT | `/echo/memory/{id}` | 编辑 `{content, importance?, type?}`（重建 embedding） |
| DELETE | `/echo/memory/{id}` | 删除 |
| POST | `/echo/memory/consolidate` | 触发提炼（同步执行，返回提炼摘要） |
| GET | `/echo/memory/profile` | 用户画像详情 |

### ③ 记忆提炼（定时 + 手动）

- **提炼逻辑** `consolidate_memories()`（新文件 `aios/echo/consolidator.py`）：
  1. 取 `consolidated=0` 的记忆条目
  2. LLM 分组摘要：按 type 分组 → 每组去重、合并、提炼为精炼事实 → 输出 `[{type, content, importance, merge_ids[]}]`
  3. 合并：`merge_ids` 对应的原条目更新为新 content（importance 取较大值），置 `consolidated=1`；重复条目删除
  4. 无新增时直接返回"无新增记忆"
- **定时**：`app/main.py` lifespan 中启动 asyncio 后台任务（每日 03:17，时区本地；任务失败静默重试次日）
- **手动**：记忆库页「提炼记忆」按钮 → `POST /echo/memory/consolidate`

**数据库变更**：`memory_entries` 表新增列 `consolidated INTEGER NOT NULL DEFAULT 0`（ALTER TABLE，兼容旧库）

### ④ 前端记忆库页

- **新路由**：`/memory` → `web/src/pages/Memory.vue`；Layout.vue「更多」抽屉加入口（`🧠 记忆库`）
- **页面结构**：
  - 顶部：**用户画像卡片**（GET `/echo/memory/profile`）
  - 操作行：「提炼记忆」按钮 + 搜索框
  - **记忆列表**：按 type 分组（preference/fact/decision/server_info 中文标签），每条显示内容 + importance 星级 + 来源时间 + 操作（编辑/删除）
  - **编辑弹窗**：改 content/importance → PUT
  - **手动添加**：表单（type 下拉 + content + importance）→ POST
  - **提炼结果提示**：consolidate 返回摘要 toast
- **API 封装**：`web/src/services/api.js` 新增 `memoryApi`

### ⑤ 验证方式

1. 后端：`python -m compileall app aios agents`
2. API 实测（curl）：列表/搜索/增删改/提炼全链路
3. 前端：`npm run build`
4. 端到端：起服务 → Echo 聊"我下周末去杭州出差" → 记忆库出现 fact 记忆 → 新会话问"我周末要去哪"能引用记忆

## 不做的事

- 记忆自动遗忘/过期策略（先靠人工删除）
- 多用户与权限
- 修改 Echo 检索注入架构（只新增沉淀环节）
- 修改 `chat_messages`/运维侧任何功能

## 成功标准

1. Echo 对话中产生的事实能在 5 轮内进入记忆库并可检索命中
2. 记忆库页面支持完整的查看/搜索/增/改/删/提炼
3. 重复事实不会被反复沉淀（去重生效）
4. 每日定时提炼可用，手动提炼可同步触发
5. 前后端构建通过，无回归
