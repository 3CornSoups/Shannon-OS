# Shannon OS → AIOS — 领域术语表

> **方向声明 (2026-07-10)**：Shannon OS 正在从「AI Server Management Agent」演进为真正的 **AIOS（AI Operating System）**——一个管理多个 AI Agent 的运行时。现有服务器管理能力降级为运行在 AIOS 上的一个 Agent 类型（Server Agent）。

## 核心概念

| 术语 | 定义 | 别名（避免使用） |
|------|------|-----------------|
| **AIOS** | AI Operating System — 管理多个 AI Agent 的运行时，提供调度、通信、共享记忆、安全审计、工具注册等基础设施 | Agent 运行时、Agent 平台 |
| **Agent** | 运行在 AIOS 上的独立 AI 工作单元：拥有独立的 LLM 会话 + 工具集 + 私有记忆，由 AIOS 统一调度和管理 | AI 助手、机器人、Skill |
| **Server Agent** | 一种具体的 Agent 类型，负责 SSH 到远程服务器执行运维管理任务（原 Shannon Agent 的角色） | 运维 Agent |
| **Echo Agent** | 一种具体的 Agent 类型，面向用户的日常聊天门面：理解用户提问、管理信息、整理记忆、生成报告。原生实现（继承 BaseAgent），与 Server/Code Agent 平级注册进 agent_registry。设计上借鉴 Nous Research Hermes Agent 的五层记忆 + 技能学习闭环，但全部复用 AIOS 现有基础设施。**范围边界（2026-08-07）**：只做对话 + 记忆 + 报告，不执行 SSH/运维命令；与现有 Dashboard 聊天页并存，运维操作仍走 Dashboard。**用户可见名（2026-08-08）：助手**——仅改前端显示文案，技术标识保持 `echo` | 回声 Agent、Hermes |
| **ReAct 循环** | Agent 的核心执行模式：LLM 生成动作 → 执行 → 观察结果 → 决定下一步。每种 Agent 可以有自己版本的动作类型 | 推理循环 |
| **AIOS Dispatcher** | AIOS 入口层，由 LLM 驱动的意图分析 + 任务路由。接收用户请求，输出 `{agents: [...], plan: "..."}`，将任务分派到合适的 Agent（支持并行分派）。一次请求一次 LLM 调用，不需规则引擎 | 路由器、调度器 |
| **Agent 间通信 (IPC)** | Agent 之间传递消息和协作的机制，分两种：① **直接调用**（Agent A 调用 Agent B 的 `run()`，阻塞等返回，如 Server → Code 委托写脚本）② **事件总线**（异步发布/订阅，如 Server 通知 Monitor 开始监听，Phase 2 实现） | Agent 通信、消息传递 |
| **智能委托 (Delegation)** | Agent 将子任务转交给更专业的外部智能体（如 Claude Code），是 Agent 间通信的一种特例 | 转发、代理 |
| **子智能体 (SubAgent)** | 可被委托的外部 AI 工具（如 Claude Code），通过动态探测自动注册到 AIOS 工具注册表 | 外部 Agent、插件 |
| **Claude Code** | Anthropic 的 CLI 编程智能体，首个被支持的 SubAgent 实现 | CC、Claude CLI |
| **委托上下文 (Delegation Context)** | 传递给子智能体的完整任务信息包：用户需求 + 服务器环境 + 对话摘要 | 任务包 |

## 架构

| 术语 | 定义 |
|------|------|
| **AgentHandle** | AIOS 核心与 Agent 之间的唯一接口契约：`.run(task)`、`.cancel()`、`.status()`、`.tools()`。AIOS 代码只认 AgentHandle，不关心背后是 Python 类还是外部进程 |
| **BaseAgent** | Python 原生 Agent 的抽象基类，实现 AgentHandle 接口。Server Agent、Code Agent 等本地 Agent 均继承此基类 |
| **AgentAdapter** | 外部 Agent（如 Claude Code）的协议翻译层——把子进程的 stdin/stdout 翻译成 AgentHandle 接口。一个 Adapter 对应一种外部 Agent 协议 |
| **工具注册表 (Tool Registry)** | AIOS 管理工具的三层结构：① 基础工具池（`ask_user`、`task_done`、`delegate_task`，所有 Agent 共享）② Agent 专属工具（各 Agent 类型自行声明，如 `execute_command` 仅 Server Agent）③ LLM tool calling schema 从注册表自动生成 |
| **Echo 模块结构** | Echo 后端自包含于 `aios/echo/` 包（agent.py + router.py + memory.py + fts.py + report.py + prompts.py），`app/main.py` 一行 include_router 接入。对话记录**单独建表**（echo_conversations / echo_messages），不与 `chat_messages` 混用，保证与运维聊天数据独立 |
| **Echo 运行时** | 检索增强纯聊天：每轮仅 1 次 LLM 调用，检索层（用户画像 + memory_entries + FTS5 原文 + 提问档案）注入 system prompt，**无 ReAct/工具循环**。报告生成与深度搜索为独立 API endpoint，不由 LLM 在闲聊中调用 |
| **模型分配** | 主聊天 ReAct（Dashboard）用 `api_model`（DB 已配 `deepseek-v4-flash`，2026-08-07 验证 API 可用）；Echo、摘要、记忆提取、Dispatcher 等辅助任务用新增 `aux_model`（默认 `deepseek-chat`）；Claude Code 委托用 Claude 自身模型 |
| **LLM 自主决策** | LLM 通过 `delegate_task` 工具自主判断是否委托，无需前置规则引擎。判断原则：「改代码 → 委托 Claude Code，改系统 → Agent 自己做」 |
| **动态探测** | 委托前通过 SSH 自动检测远程服务器上可用的子智能体，探测到的自动注册，无需静态配置 |
| **独占连接** | 委托执行期间，SSH 连接专属用于子智能体子进程，不归还连接池，保证流式输出和取消操作可用 |
| **分段审核** | 子智能体输出过长时，分段提交给 LLM 审核，最后汇总判断目标达成状态 |

## 记忆

| 术语 | 定义 |
|------|------|
| **对话记录 (Conversation Log)** | 单次对话的完整记录：消息、blocks（思考/命令/委托）、时间戳、Agent 类型。存储：SQLite `chat_messages` 表（已有），不做 JSON 文件 |
| **全局记忆 (Global Memory)** | 跨对话提炼的持久知识：用户偏好、项目背景、关键决策、常用服务器信息。存储：SQLite 新表。更新机制：① 任务完成时 → LLM 增量追加摘要 ② 会话关闭时 → LLM 全量重新梳理 |
| **记忆条目 (Memory Entry)** | 全局记忆的基本单元，存储在 `memory_entries` 表中。字段：`type`（preference/fact/decision/server_info/**user_profile**）、`key`（标签）、`content`（正文）、`importance`（1-5）、`source_conv_id`（来源对话）。LLM 总结时产出条目，Agent 启动时检索相关条目注入 system prompt |
| **用户画像 (User Profile)** | 持续演化的用户画像条目（`type=user_profile`），由 LLM 每次对话后增量维护——提炼用户背景、偏好、习惯、项目上下文。**自建实现，不接入 Honcho 外部服务**（避免 SaaS 依赖 + 数据出境） |
| **跨会话全文检索 (FTS5 Recall)** | 用 SQLite FTS5 给 Echo 聊天原文建全文索引，支持按时间/主题回找"当时到底说了什么"。与蒸馏型 `memory_entries` 互补：前者搜原话，后者取结论 |
| **提问档案 (Question Log)** | Echo 记录用户问过的问题（话题、频次、时间戳），是「了解用户提问了什么」的数据基础，也是报告生成的数据源之一 |
| **记忆摘要 (Memory Summary)** | 当前请求相关的记忆条目拼接成的文本片段，注入到 Agent 的 system prompt 头部。格式：`## 用户记忆\n- [偏好] xxx\n- [事实] xxx\n` |
| **记忆触发器** | 两个触发时机：① **任务级**（每次 ReAct 循环结束，`task_done`/`done` 事件后，LLM 提取本次任务的关键信息追加到全局记忆）② **会话级**（用户关闭/切换对话时，LLM 全量梳理整个会话，更新用户画像） |
| **Echo 后台节奏** | 实时：每条消息记录提问档案（原文+时间戳+bigram 话题关键词）+ 建 FTS5 索引；对话关闭时：异步 LLM 增量更新 `user_profile` 画像 + 顺带补当日小结（若当天未生成）；定时 cron 每日小结留 Phase 2 |
| **Echo 记忆边界** | 回声共享 `memory_entries` 全局蒸馏记忆（运维 agent 也会写入），但 FTS5 只索引 `echo_messages` 自身对话，**不索引 `chat_messages` 运维原始对话**（方案 A，2026-08-07 确认） |
| **Agent 私有记忆** | 每个 Agent 实例独立持有的对话上下文：ReAct 执行历史、当前任务状态。机制：ConversationManager（每 Agent 独立实例） |
| **长期记忆** | 跨会话持久化的知识：用户习惯、项目偏好、历史决策。机制：现有 SQLite + Claude Memory 机制，提升为 AIOS 共享层 |
| **上下文窗口** | LLM 单次调用的 token 上限。AIOS 暂不做自动换页（Letta 方案），优先保持 Agent 数少 + 上下文精简 |

## 报告（Echo 输出）(2026-08-07)

| 术语 | 定义 |
|------|------|
| **主题报告** | 用户指定话题，Echo 跨会话汇总所有相关讨论生成的结构化报告 |
| **每日小结** | 一天内对话/提问/结论/待办的小结报告；初始以「对话关闭时生成」顶替定时任务 |
| **报告库** | 已生成报告的持久化存储 + 前端回看入口；报告本体为 Markdown |
| **报告数据源** | 提问档案 + memory_entries + 对话原文，三者合成报告内容 |
| **Echo 前端结构** | `/echo` = 双栏聊天（nanobot 布局：会话列表 + 线程）；`/echo/reports` = 报告库回看。**记忆/画像/提问档案不设独立 UI**，仅作为后端数据经聊天与报告体现 |

## 移动端（前端）(2026-08-08)

| 术语 | 定义 |
|------|------|
| **移动端适配 (Mobile Adaptation)** | 整个前端在手机浏览器可用，覆盖全部页面，重点打磨聊天页（Dashboard + Echo）。桌面端保留 VS Code 风格（Activity Bar + 主侧边栏），移动端（<768px）切换移动布局 |
| **底部 Tab 导航 (Bottom Tab Navigation)** | 移动端主导航形态：底部固定 Tab 栏，5 槽位「聊天 / 助手 / 服务器 / 监控 / 更多」，拇指可及。替代桌面端的 48px Activity Bar |
| **更多抽屉 (More Drawer)** | 底部 Tab 第 5 槽位展开的次级导航面板，收纳长尾页面：历史 / 模板 / 告警 / 工具 / 设置 / 关于 |
| **助手 (Assistant)** | Echo Agent 的用户可见名（2026-08-08 改名）。仅前端显示层使用，技术标识仍为 `echo`（路由 `/echo`、包 `aios/echo/`、表 `echo_*`） |
| **会话抽屉 (Conversation Drawer)** | 移动端聊天页的会话列表形态：从左侧滑出的遮罩抽屉，顶部可选服务器（Dashboard），下面是对话记录。替代桌面端常驻的会话侧栏 |

## Agent 生命周期

| 术语 | 定义 |
|------|------|
| **Agent 状态机** | 所有 Agent 统一状态：`idle`（等待任务）→ `running`（执行中）→ `done` / `failed` / `cancelled`（终结）。`pause` / `resume` 留 Phase 2 |
| **Agent 超时** | Agent 执行超过时限自动终止，状态标记 `failed`（原因=timeout），不另设独立状态 |

## 安全

| 术语 | 定义 |
|------|------|
| **风险评级** | LOW（低风险，自动委托）/ HIGH（高风险，用户确认后才委托） |
| **委托审计** | 委托操作写入 operation_logs 表，mode=delegate，commands_plan 存储委托详情 JSON |
| **前后双审计** | 委托前 LLM 对任务做风险评级 + 委托后 Agent 审核子智能体输出中的实际命令 |

## 状态

| 术语 | 定义 |
|------|------|
| **委托冲突** | 委托执行期间用户发送新消息时，前端弹窗让用户选择「取消当前 + 执行新任务」或「排队等待」 |
