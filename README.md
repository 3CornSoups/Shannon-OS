<<<<<<< HEAD

# Shannon OS Agent

> 用自然语言管理你的服务器 —— AI 运维助手，让基础设施管理像对话一样简单。

Shannon 是一款基于 AI 的智能服务器运维工具。你只需要用自然语言描述你想要完成的操作，Shannon 就会自动规划、执行并监控整个操作流程。无论是日常巡检、软件部署、故障排查还是系统配置，Shannon 都能帮你高效完成。

---

## 功能特性

### 核心能力

- **自然语言驱动运维** — 输入"检查所有服务器的磁盘使用情况"或"部署 Nginx 并配置反向代理"，Shannon 自动生成并执行命令
- **ReAct 智能体循环** — 采用计划-审批-执行的流程，具备风险感知和自我修复能力
- **三模式切换** — 纯聊天模式（chat）、自动执行模式（auto）、Agent 提案模式（agent），灵活匹配不同场景
- **流式 SSE 推送** — 实时推送命令执行输出和 AI 推理过程，体验流畅

### 多服务器管理

- 通过 Web 仪表盘添加、测试、切换 SSH 服务器
- 支持密码和私钥两种认证方式
- 双引擎 SSH 连接池（asyncssh + paramiko 自动切换），保障连接稳定性
- 自动连接健康检查和空闲连接回收
- 连接失败自动降级（asyncssh → paramiko）

### 实时监控

- CPU 使用率（整体 + 每核心）、负载均值
- 内存使用详情（总计、已用、可用、缓存、Swap）
- 磁盘分区使用情况
- 网络接口流量统计
-  Top 10 CPU 消耗进程
- 基于 ECharts 的实时可视化仪表盘

### 安全体系

- **多层风险评估** — 内置 70+ 高危关键词和 10+ 正则模式，覆盖用户管理、权限变更、系统文件修改、防火墙、磁盘操作等
- **命令白名单** — 纯只读命令（cat, ls, ps, df 等）自动标记低风险
- **密码加密存储** — 基于 PBKDF2 + XOR 的密码加密，避免明文存储
- **操作审计** — 完整的操作审批和审计记录

### 用户体验

- 响应式 Web 界面（Vue 3 + Tailwind CSS）
- 操作历史记录与回放
- 命令模板系统，重复性任务一键执行
- 文件浏览器，可视化浏览服务器文件系统
- WebSocket 交互式终端
- 对话管理（多会话、自动标题）
- 一键启动脚本，自动创建虚拟环境和安装依赖

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python / FastAPI / Uvicorn |
| 前端框架 | Vue 3 / Vite / Pinia / Tailwind CSS |
| 数据库 | SQLite（aiosqlite 异步驱动） |
| SSH 引擎 | asyncssh + paramiko（双引擎自动切换） |
| AI 模型 | DeepSeek Chat（兼容 OpenAI API 格式） |
| 实时通信 | SSE 事件流 + WebSocket 终端 |
| 数据可视化 | ECharts |
| 密码加密 | PBKDF2-HMAC-SHA256 + XOR |

---

## 快速开始

### 环境要求

| 组件 | 版本 |
|------|------|
| Python | >= 3.11 |
| Node.js | >= 18 |
| npm | >= 9 |

### 安装与启动

```bash
# 方式一：手动安装
pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 方式二：一键启动（推荐）
python run.py
```

启动后浏览器会自动打开 `http://localhost:8000`。

### 首次使用

1. **设置页面** → 填入 DeepSeek API Key → 点击"测试连接"验证 → 保存
2. **服务器管理** → 添加目标服务器（主机、端口、用户名、密码或私钥） → 测试连接 → 保存
3. **仪表盘** → 选择服务器，输入自然语言指令开始使用

> 所有配置（API Key、服务器凭据）均存储在本地 SQLite 数据库中，数据不会离开你的机器。

---

## 使用模式

| 模式 | 行为 | 适用场景 |
|------|------|----------|
| chat | 纯对话，仅文本问答，不执行命令 | 咨询问题、学习知识 |
| auto | AI 自动分析和执行（低风险命令直接执行） | 熟练用户，日常快速操作 |
| agent | AI 生成执行计划，人工确认后再执行 | 生产环境操作，高风险任务 |

---

## 项目结构

```
shannon/
├── app/                        # Python 后端
│   ├── main.py                 # FastAPI 应用入口，路由注册，SPA 静态文件服务
│   ├── agent.py                # Agent 核心编排（ReAct 循环、风险评估、意图分析、自我修复）
│   ├── llm_client.py           # LLM API 调用层（流式/非流式、JSON 提取、工具调用）
│   ├── executor.py             # SSH/Local 命令执行器（双引擎、工作目录追踪、环境探测）
│   ├── monitor.py              # 系统监控采集器（CPU/内存/磁盘/网络/进程）
│   ├── connection.py           # SSH 连接池（空闲回收、健康检查、自动降级）
│   ├── database.py             # SQLite 数据库 CRUD（主机、日志、审计、设置、会话）
│   ├── events.py               # SSE 事件系统（缓存、重放、自动清理）
│   ├── security.py             # 密码加密管理器（PBKDF2 派生密钥 + XOR 加密）
│   ├── prompts.py              # LLM 系统提示词集中管理（意图分析/计划/修复/ReAct）
│   ├── conversation.py         # 对话上下文管理器
│   ├── models.py               # Pydantic 数据模型
│   ├── errors.py               # 错误处理与重试机制
│   ├── files.py                # 文件浏览器服务
│   ├── terminal.py             # WebSocket 终端服务
│   ├── settings.py             # 应用设置管理
│   └── routers/                # API 路由模块
│       ├── chat.py             # 聊天/Agent 交互接口
│       ├── hosts.py            # 服务器管理接口
│       ├── settings.py         # 设置接口
│       ├── monitoring.py       # 监控数据接口
│       ├── history.py          # 操作历史接口
│       ├── files.py            # 文件浏览接口
│       └── terminal.py         # WebSocket 终端接口
├── web/                        # Vue 3 前端
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.vue    # 主仪表盘（Agent 对话界面）
│   │   │   ├── Servers.vue      # 服务器管理页
│   │   │   ├── Settings.vue     # 设置页（API Key、模型配置）
│   │   │   ├── Monitoring.vue   # 实时监控仪表盘
│   │   │   ├── History.vue      # 操作历史记录
│   │   │   ├── Templates.vue    # 命令模板管理
│   │   │   └── Showcase.vue     # 功能展示页
│   │   ├── components/
│   │   │   ├── FileExplorer.vue # 文件浏览器组件
│   │   │   ├── Terminal.vue     # 交互式终端组件
│   │   │   └── layout/          # 布局组件
│   │   ├── stores/              # Pinia 状态管理
│   │   ├── services/api.js      # Axios API 客户端
│   │   ├── router/index.js      # 路由配置
│   │   └── composables/         # 组合式函数
│   │       ├── useCharts.js     # ECharts 封装
│   │       └── useVoiceInput.js # 语音输入支持
│   └── dist/                    # 构建产物
├── data/                        # SQLite 数据库存储目录
├── scripts/                     # 部署脚本
├── run.py                       # 一键启动脚本（自动创建 venv、安装依赖）
├── requirements.txt             # Python 依赖
└── .env.example                 # 环境变量模板（可选）
```

---

## API 参考

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 发送消息（SSE 流式响应） |
| `/api/stream/{task_id}` | GET | SSE 事件流 |
| `/api/execute/confirm` | POST | 确认/取消执行 |
| `/api/conversations/{host_id}` | GET | 列出对话 |
| `/api/hosts` | GET/POST | 服务器管理 |
| `/api/settings` | GET/POST | 应用设置 |
| `/api/monitor/{host_id}` | GET | 监控数据 |
| `/api/history` | GET | 操作历史 |
| `/api/files/list` | POST | 文件浏览 |
| `/api/files/read` | POST | 读取文件内容 |
| `/api/ws/terminal` | WebSocket | 交互式终端 |

完整 API 文档请访问 `/docs`（Swagger UI）。

---

## 环境变量（可选）

无需 `.env` 文件即可运行，所有配置可通过 Web UI 完成。如需要预设配置，可复制 `.env.example` 为 `.env`：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API 密钥 |
| `DEEPSEEK_API_BASE` | `https://api.deepseek.com` | API 基础地址 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 模型名称 |
| `SHANNON_DEFAULT_SSH_PORT` | `22` | 默认 SSH 端口 |
| `SHANNON_PORT` | `8000` | Web 服务端口 |

---

## 开发

```bash
# 启动后端开发服务器（热重载）
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动前端开发服务器（Vite HMR，端口 5173）
cd web && npm run dev

# 构建前端
cd web && npm run build
```

> 开发模式下，前端开发服务器会自动将 API 请求代理到后端（8000 端口）。

---

## 部署

生产部署请参见 [DEPLOY.md](DEPLOY.md)，包含 Docker 部署、环境变量配置和 API 文档详情。

### 快速生产部署

```bash
# 安装依赖
pip install -r requirements.txt
cd web && npm install && npm run build && cd ..

# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 端口说明

- `8000` — 后端 API + 前端静态文件服务（生产环境）
- `5173` — 前端开发服务器（开发环境）

---

## 路线图

### 近期目标

- **更智能的 Agent** — 改进 ReAct 循环，增强多步推理、错误恢复和上下文感知决策能力
- **多 LLM 支持** — 可插拔后端，支持 Claude、OpenAI、Gemini、本地模型
- **Agent 记忆系统** — 跨会话持久化记忆，学习服务器运维模式

### 移动端与桌面端

- **移动 App** — React Native / Flutter 客户端，随时随地监控和应急操作
- **桌面 GUI** — Tauri / Electron 应用，支持原生终端模拟和离线模式

### 基础设施与生态

- **插件系统** — 社区贡献工具、自定义监控、通知渠道
- **CI/CD 集成** — 从 GitHub Actions、GitLab CI、Webhooks 触发运维操作
- **团队协作** — 基于角色的权限管理、共享服务器清单、操作审批流程
- **Docker 部署** — `docker-compose` 一键部署
- **国际化** — 英文及其他多语言支持
- **模板市场** — 发现和分享运维模板

### 安全与可靠性

- **端到端加密** — 存储凭据的全链路加密
- **全面审计** — 谁在什么时间对哪台服务器做了什么操作
- **告警系统** — Slack / Discord / 邮件阈值告警

---

## 贡献指南

欢迎提交贡献！如果你想参与开发，可以：

1. 查看路线图，找到感兴趣的方向
2. 在 [Issues](https://github.com/yourusername/shannon-os-agent/issues) 中讨论或提出新想法
3. Fork 仓库并提交 Pull Request
4. 添加qq：2661059574
---

## 许可证

MIT License

---

## 感谢

- [FastAPI](https://fastapi.tiangolo.com/) — 高性能 Python Web 框架
- [Vue 3](https://vuejs.org/) — 渐进式前端框架
- [ECharts](https://echarts.apache.org/) — 数据可视化库
- [asyncssh](https://asyncssh.readthedocs.io/) — Python SSH 异步客户端
- [DeepSeek](https://deepseek.com/) — AI 模型支持

---

> 用 AI 赋能运维，让服务器管理变得简单。

# Shannon OS Agent

> AI-powered server operations assistant — talk to your infrastructure.

Shannon turns natural language into server commands. Describe what you need, and it plans, executes, and monitors operations across your machines.

## Features

- **Natural language ops** — "check disk usage on all servers" → AI generates and runs the commands
- **Multi-server management** — add, test, switch between SSH servers from the dashboard
- **Real-time monitoring** — CPU, memory, disk, network, processes with live ECharts dashboards
- **ReAct agent loop** — plan-approve-execute flow with risk assessment and self-healing
- **Operation history** — full audit trail per server with conversation replay
- **Template system** — save and reuse command templates for repetitive tasks
- **SSE streaming** — real-time event push for command output and agent thinking

## Quick Start

```bash
# install dependencies
pip install -r requirements.txt
cd web && npm install && cd ..

# start
python -m uvicorn app.main:app --reload
```

Open `http://localhost:8000`, then:

1. **Settings** → enter your DeepSeek API Key → test → save
2. **Servers** → add target server (host, port, user, password/key) → test → save
3. **Dashboard** → select server, describe what to do

No `.env` required — everything is configurable through the UI.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python / FastAPI / Uvicorn |
| Frontend | Vue 3 / Vite / Pinia / Tailwind |
| Database | SQLite (aiosqlite) |
| SSH | asyncssh + paramiko (dual engine) |
| AI | DeepSeek Chat (OpenAI-compatible API) |
| Realtime | SSE streaming + WebSocket terminal |
| Charts | ECharts |

## Project Structure

```
shannon/
├── app/                # Python backend
│   ├── agent.py        # Agent orchestration (ReAct loop)
│   ├── llm_client.py   # LLM API calls (streaming + tool calling)
│   ├── executor.py     # SSH command execution
│   ├── connection.py   # SSH connection pool
│   ├── database.py     # SQLite CRUD
│   ├── monitor.py      # System monitoring
│   ├── security.py     # Password encryption
│   ├── prompts.py      # System prompt management
│   └── routers/        # API routes (chat, hosts, settings, ...)
├── web/                # Vue 3 frontend
│   └── src/
│       ├── pages/      # Dashboard, Servers, Settings, Monitoring, ...
│       ├── stores/     # Pinia state management
│       └── services/   # Axios API client
├── run.py              # One-click launcher
└── requirements.txt
```

## Roadmap

We're building the next-generation server operations platform and looking for contributors.

**Near-term priorities:**

- **Smarter agent** — improve the ReAct loop with better planning, multi-step reasoning, error recovery, and context-aware decision making
- **Multi-LLM support** — pluggable backends for Claude, OpenAI, Gemini, local models
- **Agent memory** — persistent memory across sessions for learning server patterns and user preferences

**Mobile & desktop:**

- **Mobile app** — React Native / Flutter client for on-the-go monitoring and emergency ops
- **Desktop GUI** — Tauri or Electron app with native terminal emulation and offline mode

**Infrastructure & ecosystem:**

- **Plugin system** — community-contributed tools, custom monitors, notification channels
- **CI/CD integration** — trigger operations from GitHub Actions, GitLab CI, webhooks
- **Team collaboration** — role-based access, shared server inventory, operation approval workflows
- **Docker deployment** — one-command deploy with docker-compose
- **i18n** — English and more language support
- **Template marketplace** — share and discover operation templates

**Security & reliability:**

- **End-to-end encryption** for stored credentials
- **Comprehensive audit** — who did what, when, on which server
- **Alerting** — Slack / Discord / Email notifications on threshold breaches

## Deploy

See [DEPLOY.md](DEPLOY.md) for production deployment, environment variables, and API reference.

## Contributing

Contributions are welcome. Check the roadmap above — if something catches your interest, open an issue or a PR.

## License

MIT
=======
# Shannon-OS
Shannon OS 是一款 AI 驱动的智能服务器运维工具。用自然语言描述运维需求，ReAct 智能体会自动规划、执行并监控操作。核心功能：多服务器 SSH 管理、实时监控仪表盘、风险感知执行、命令模板和完整审计记录。Shannon OS is an AI-powered server operations assistant. Describe tasks in natural language, and its ReAct agent plans, executes, and monitors operations across your servers.
>>>>>>> f11a76d0e15348e71d874ee4d494143d1fb5e387
