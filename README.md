# Shannon OS Agent

智能服务器管理助手，通过 AI 分析用户请求并通过 SSH 执行系统命令。支持多服务器管理、实时监控、代码智能委托、操作历史追踪。

## 核心功能

### Agent 智能运维
- **ReAct 执行循环**：LLM 生成命令 → SSH 执行 → 观察结果 → 决定下一步，最多 40 轮迭代
- **智能风险标注**：LLM 自行判断命令风险等级（LOW/HIGH），硬阻断清单兜底防误判
- **3 种运行模式**：chat（纯对话）/ agent（每步确认）/ auto（LOW 自动 + HIGH 确认）
- **流式思考过程**：实时展示 LLM 的推理、计划和执行决策

### 智能委托（Claude Code）
- **LLM 自主决策**：通过 `delegate_task` 工具判断是否委托，无需规则引擎
- **判断原则**：「改代码 → 委托 Claude Code，改系统 → Agent 自己做」
- **非交互执行**：stdin 管道传入任务 + `--print` 模式，零 PTY 交互复杂度
- **流式输出**：Claude Code 分析过程实时推送到聊天区，markdown 渲染
- **风险分流**：LOW 自动委托 / HIGH 弹确认卡
- **取消回退**：取消委托后自动退回基础 Agent 继续执行
- **权限全自动**：trust/safety check 自动同意，无需用户干预

### 工具面板 + 终端
- **xterm.js 终端**：WebSocket + 二进制帧直通 PTY，完整终端渲染（ANSI 颜色 / 光标 / 交互）
- **远程 CLI 工具探测**：自动检测服务器上的 Claude Code 等工具

### 系统监控
- CPU / 内存 / 磁盘 / 网络 / 进程实时监控
- ECharts 可视化图表，5 秒静默刷新

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python + FastAPI + Uvicorn |
| 数据库 | SQLite (aiosqlite) |
| 前端框架 | Vue 3 + Vite + Pinia + Vue Router + Tailwind CSS |
| 可视化 | ECharts + xterm.js |
| SSH 连接 | asyncssh + paramiko（双引擎） |
| AI 模型 | DeepSeek Chat API（兼容 OpenAI 格式） |
| API 通信 | Axios + SSE + WebSocket |

## 项目结构

```
shannonOS/
├── app/                          # 后端
│   ├── main.py                   # FastAPI 入口
│   ├── agent.py                  # Agent 编排 + ReAct 循环 + 风险评估
│   ├── conversation.py           # 对话上下文管理
│   ├── llm_client.py             # LLM API + tool calling + REACT_TOOLS
│   ├── models.py                 # Pydantic 数据模型
│   ├── prompts.py                # 系统提示词集中管理
│   ├── database.py               # SQLite 数据库操作
│   ├── executor.py               # SSH 命令执行 + stdin 管道
│   ├── connection.py             # SSH 连接池
│   ├── events.py                 # SSE 事件系统 (EventStore)
│   ├── security.py               # 密码管理
│   ├── settings.py               # 应用配置
│   ├── files.py                  # 文件管理
│   ├── repl_sessions.py          # REPL PTY 会话管理
│   ├── delegate/                 # 智能委托模块
│   │   ├── base.py               # SubAgent 抽象基类
│   │   ├── claude_code.py        # ClaudeCodeSubAgent（stdin 管道 + --print）
│   │   ├── context_builder.py    # 委托上下文构建 + LLM 对话摘要
│   │   ├── executor.py           # 委托执行编排器
│   │   ├── reviewer.py           # 分段审核器
│   │   └── install.py            # Node.js + Claude Code 自动安装
│   └── routers/                  # API 路由
│       ├── chat.py               # 聊天 + ReAct + 委托 + 委托 API
│       ├── hosts.py              # 主机管理
│       ├── settings.py           # 设置
│       ├── history.py            # 操作历史
│       ├── monitoring.py         # 监控数据
│       ├── files.py              # 文件浏览
│       ├── terminal.py           # WebSocket 终端
│       ├── tools.py              # 工具面板 + REPL 会话 + xterm WebSocket
│       └── alert_rules.py / alerts.py
├── web/                          # 前端
│   └── src/
│       ├── pages/Dashboard.vue   # 主聊天页面
│       ├── components/
│       │   ├── DelegationCard.vue # 委托卡片（运行/完成/取消/超时/回退）
│       │   ├── ToolChat.vue      # xterm.js 终端 + 工具面板
│       │   └── layout/
│       ├── composables/
│       │   ├── markdown.js       # markdown → HTML 渲染 + XSS 防护
│       │   └── terminal.js       # ANSI → HTML 转换
│       ├── services/api.js       # API 封装
│       └── stores/ / router/ / styles/
├── docs/
│   └── adr/                      # 架构决策记录
│       ├── 0001-dynamic-detection.md
│       ├── 0002-dual-channel.md  （已被 0005 替代）
│       ├── 0003-exclusive-connection.md
│       ├── 0004-risk-based-confirmation.md
│       └── 0005-llm-only-delegation-decision.md
├── CONTEXT.md                    # 领域术语表
├── CLAUDE.md                     # 项目开发文档
├── requirements.txt
├── run.py
└── data/ / logs/
```

## 快速开始

### 1. 配置环境变量

```env
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_API_KEY=sk-your-api-key-here
SHANNON_PORT=8000
```

### 2. 启动

```bash
# 一键启动
python run.py

# 或手动
python -m uvicorn app.main:app --reload
```

前端开发：
```bash
cd web && npm install && npm run dev
```

前端构建：
```bash
cd web && npm run build
```

访问 `http://localhost:8000`

## ReAct 工具

| 工具 | 说明 |
|------|------|
| `execute_command` | 在服务器上执行 shell 命令（含 risk_level 标注） |
| `delegate_task` | 委托 Claude Code 执行代码分析/重构任务 |
| `task_done` | 任务完成，汇报结果 |
| `ask_user` | 需要用户介入时调用 |

## SSE 事件类型

| 事件 | 说明 |
|------|------|
| `thinking` | LLM 思考过程流式输出 |
| `plan` | 执行计划生成 |
| `command_start` / `command_output` / `command_result` | 命令执行全流程 |
| `delegate_confirm_required` | 委托前等待用户确认（阻塞） |
| `delegate_started` / `delegate_progress` / `delegate_completed` | 委托执行全流程 |
| `delegate_review` | 委托结果审核 |
| `delegate_cancelled` / `delegate_timeout` / `delegate_fallback` | 委托异常处理 |
| `delegate_permission_required` | Claude Code 权限请求（当前版本自动同意） |
| `delegation_conflict` | 委托冲突检测 |
| `risk_hold` | 高风险命令等待确认 |

## 委托 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/delegate/cancel` | 取消正在执行的委托 |
| POST | `/api/delegate/confirm-install` | 确认安装 Claude Code |
| POST | `/api/delegate/resolve-conflict` | 解决委托冲突 |
| POST | `/api/delegate/respond-permission` | 响应权限请求（兼容保留） |
| GET | `/api/delegate/status/{task_id}` | 查询委托状态 |

## 架构决策

| ADR | 决策 |
|-----|------|
| 0001 | 动态探测替代 YAML 配置 |
| 0003 | 委托期间独占 SSH 连接 |
| 0004 | 合并确认层 + 风险分流 |
| 0005 | 移除预判器，LLM 自主决策委托 |

## 常见问题

### 委托触发
- 代码分析/重构/审查类任务会自动委托 Claude Code
- 纯运维操作（安装软件、启停服务、查日志）由 Agent 自己执行
- auto 模式下 LOW 风险自动委托，HIGH 弹确认

### SSH 连接
- 支持密码和私钥两种认证
- 委托期间 SSH 连接独占，保证流式输出

### 构建
- `npm run build` 生产构建，输出到 `web/dist/`
- ECharts 和 xterm.js 独立分块，vendor 共享
