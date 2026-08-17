# CLAUDE.md — Shannon OS Agent 项目文档

## 项目概述

Shannon OS Agent 是一个智能服务器管理助手，基于 Python FastAPI + Vue 3，通过 AI 分析用户请求并通过 SSH 执行系统命令。支持多服务器管理、实时监控、操作历史追踪。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python + FastAPI + Uvicorn |
| 数据库 | SQLite (aiosqlite) |
| 前端框架 | Vue 3 + Vite + Pinia + Vue Router + Tailwind CSS |
| 可视化 | ECharts |
| SSH 连接 | asyncssh + paramiko（双引擎） |
| AI 模型 | DeepSeek Chat API (兼容 OpenAI 格式) |
| API 通信 | Axios + SSE |

## 项目结构

```
shannonOS/
├── app/                          # 后端 Python 应用
│   ├── main.py                   # FastAPI 入口
│   ├── agent.py                  # Agent 编排核心 + ReAct 循环
│   ├── conversation.py           # 对话上下文管理
│   ├── llm_client.py             # LLM API 调用（流式/非流式/tool calling）
│   ├── models.py                 # Pydantic 数据模型
│   ├── prompts.py                # 系统提示词集中管理
│   ├── database.py               # SQLite 数据库操作
│   ├── executor.py               # SSH 命令执行器 + 连接池
│   ├── connection.py             # SSH 连接池
│   ├── events.py                 # SSE 事件系统 (EventStore)
│   ├── security.py               # 安全：密码管理 + HIGH_RISK_KEYWORDS + assess_risk()
│   ├── settings.py               # 应用配置
│   ├── files.py                  # 文件管理
│   ├── delegate/                 # 【新增】智能委托模块
│   │   ├── base.py               # SubAgent 抽象基类 + DelegationContext + DelegateResult
│   │   ├── claude_code.py        # ClaudeCodeSubAgent（动态探测 + 执行 + 取消）
│   │   ├── pre_judger.py         # 保守型规则预判器（双条件 AND 触发）
│   │   ├── context_builder.py    # 委托上下文构建 + LLM 对话摘要生成
│   │   ├── executor.py           # 委托执行编排器（探测/执行/取消/冲突处理）
│   │   ├── reviewer.py           # 分段审核器（退出码检查 + 命令审计 + 目标达成判断）
│   │   └── install.py            # Node.js + Claude Code 自动安装（apt/yum 双发行版）
│   └── routers/                  # API 路由
│       ├── chat.py               # 聊天 + ReAct 循环 + 委托流程 + 委托 API 路由
│       ├── hosts.py / settings.py / history.py / monitoring.py / files.py / terminal.py
│       └── alert_rules.py / alerts.py
├── web/                          # Vue 3 前端
│   └── src/
│       ├── pages/Dashboard.vue   # 主聊天页面（含委托 SSE 事件处理 + 委托状态管理）
│       ├── pages/Echo.vue        # Echo 助手对话页（/echo）
│       ├── components/
│       │   ├── DelegationCard.vue          # 【新增】委托卡片（6 状态：suggested/running/completed/cancelled/timeout/fallback）
│       │   ├── DelegationInstallModal.vue  # 【新增】安装引导弹窗
│       │   ├── DelegationConflictModal.vue # 【新增】冲突解决弹窗（取消/排队）
│       │   ├── Terminal.vue / FileExplorer.vue / NotificationBell.vue
│       │   └── layout/
│       ├── services/api.js       # API 封装（含 delegateApi）
│       └── stores/ / router/ / composables/ / styles/
├── aios/                         # AIOS 运行时层（agent_registry / dispatcher / ipc / memory / echo / embedding / tools）
├── agents/                       # 原生 Agent 实现（code_agent / server_agent）
├── desktop/                      # Electron 桌面端
├── docs/
│   └── adr/                      # 架构决策记录（0001-0007）
├── CONTEXT.md                    # 领域术语表
├── PRD_智能委托调用.md            # 智能委托 PRD（原始需求文档，保持不动）
├── DEPLOY.md / README.md
├── requirements.txt / run.py / build.py / build.bat
└── data/ / logs/
```

## 设计理念：AIOS 语义抽象层

Shannon OS 的本质是在 LLM 与 Linux 服务器之间构建一个 **AIOS（AI Operating System）语义抽象层**。传统运维路径是「人 → CLI → 服务器」，本项目将其替换为「人 → 自然语言 → AI Agent → 工具调用 → 服务器」，Agent 承担类似操作系统内核的调度角色：接收高层意图、分解为原子操作、调度执行资源、处理异常并报告结果。

系统遵循三条原则：
1. **LLM 自主决策优先于规则引擎** —— 意图分类、工具选择、终止条件、委托决策全由模型判断，规则只做安全兜底
2. **流式优先** —— 所有长耗时操作通过 SSE 实时推送
3. **连接即会话** —— 委托期间 SSH 连接独占，保持 PTY 会话连续性

（2026-07-10 起，项目向真正的 AIOS 运行时演进：新增 `aios/` 层管理多个 Agent（注册表/调度/IPC/记忆），现有服务器管理能力演化为运行在 AIOS 上的 Server Agent；方向与术语详见 CONTEXT.md）

## 核心架构：Agent 处理流程

```
用户输入 → api_chat()
    → 委托冲突检查（get_active_delegation）
    → chat 模式：直接流式回复
    → agent/auto 模式：
        → LLM 调用（含 delegate_task 工具，LLM 自主决策是否委托）
        → 如果 LLM 返回 ReActDelegate：
            → LOW 风险：自动委托（分析/只读类任务）
            → HIGH 风险：delegate_confirm_required → 弹卡片等待用户确认
            → 委托执行（PTY 交互模式，权限提示转发用户确认）→ 审核 → 融入对话
        → 如果 LLM 返回 ReActCommand/ReActDone/ReActAsk：
            → 正常 ReAct 循环
        → ReAct 循环中任意轮 LLM 均可调用 delegate_task
```

## ReAct 动作类型

- `ReActCommand` (action="run") — 在服务器上执行命令
- `ReActDone` (action="done") — 任务完成
- `ReActAsk` (action="ask") — 需要用户介入
- `ReActDelegate` (action="delegate") — 委托给子智能体【新增】

## ReAct 工具（tool calling）

- `execute_command` — 执行 shell 命令
- `task_done` — 完成任务
- `ask_user` — 询问用户
- `delegate_task` — 委托给子智能体【新增】

## 智能委托核心设计决策

1. **LLM 自主决策**：LLM 通过 `delegate_task` 工具自主判断是否委托，无前置规则引擎。判断原则：「改代码 → 委托 Claude Code，改系统 → Agent 自己做」
2. **动态探测**：远程服务器探测可用子智能体，自动注册，无需 YAML 配置
3. **独占连接**：委托期间 SSH 连接不归还池，保证流式输出和取消
4. **合并确认层**：LOW 风险自动委托（零点击），HIGH 风险弹卡片（一次点击）
6. **分段审核**：输出 > 8000 字符时自动分段提交 LLM 审核
7. **委托冲突**：新消息到达时让用户选择取消+执行新任务，或排队等待
8. **安装引导**：缺少 Node.js 则自动安装 Node.js + Claude Code（apt/yum 适配）

## SSE 事件类型

| 事件 | 说明 |
|------|------|
| delegate_confirm_required | 预判命中或 LLM 建议委托，等待用户确认（阻塞） |
| delegate_started | 委托开始执行 |
| delegate_progress | 委托实时流式输出（逐行推送） |
| delegate_completed | Claude Code 进程退出 |
| delegate_review | Agent 审核结果 |
| delegate_cancelled | 用户取消委托 |
| delegate_timeout | 委托超时 |
| delegate_install_required | 远程服务器缺少 Claude Code |
| delegate_permission_required | Claude Code 请求权限，等待用户确认（阻塞）|
| delegate_fallback | 退回 Agent 模式 |
| delegation_conflict | 委托期间有新消息到达 |

## 委托 API 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/delegate/cancel | 取消正在执行的委托 |
| POST | /api/delegate/confirm-install | 确认/拒绝安装 Claude Code |
| POST | /api/delegate/resolve-conflict | 解决委托冲突（cancel_and_new / queue） |
| POST | /api/delegate/respond-permission | 响应 Claude Code 权限请求（同意/拒绝） |
| GET | /api/delegate/status/{task_id} | 查询委托状态 |

## 安全体系

- `HIGH_RISK_KEYWORDS` — 高危关键词列表（agent.py）
- `HIGH_RISK_PATTERNS` — 高危正则模式
- `SAFE_COMMAND_PREFIXES` — 安全命令白名单
- `assess_risk()` — 命令风险等级评估
- `audit_records` 表 — 审计记录（确认/拒绝）
- `operation_logs` 表 — 操作日志（含 delegate 模式）
- 委托前后双审计（LLM 风险评级 + Agent 命令审计）

## 启动方式

```bash
# Windows
python run.py

# Linux/Mac
bash scripts/start.sh

# 或手动
python -m uvicorn app.main:app --reload
# 前端开发：cd web && npm run dev
# 前端构建：cd web && npm run build
```

## 当前状态 (2026-05-14)

智能委托功能已完整实现，包括：
- 全部 13 个功能需求（FR-01 ~ FR-13）
- 全部 6 个用户故事
- 全部 10 种 SSE 事件（新增 `delegate_permission_required`）
- 全部委托 API 路由（新增 `/api/delegate/respond-permission`）
- **PTY 双向交互**：Claude Code 委托改为交互 REPL 模式，支持权限提示检测 + 用户确认
- 前端委托卡片 + 安装弹窗 + 冲突弹窗 + **权限确认条**
- CONTEXT.md + 4 个 ADR
- 前后端构建均通过

待测试验证：
1. 在 agent/auto 模式下用代码重构类提示词触发委托流程
2. PTY 权限提示检测在真实 Claude Code 环境中的正则会话匹配效果
