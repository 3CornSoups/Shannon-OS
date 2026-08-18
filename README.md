# Shannon OS Agent

> 用自然语言管理你的服务器 —— AI 驱动的智能运维助手

Shannon OS Agent 通过 AI 分析用户请求并经 SSH 执行系统命令。你只需用自然语言描述运维需求，ReAct 智能体就会自动规划、执行并监控整个操作流程——从日常巡检、软件部署到故障排查，并持续向 AIOS（AI Operating System）运行时演进：新增的 `aios/` 层统一调度多个 Agent（Server Agent / Code Agent / Echo Agent）。

---

## 功能特性

### Agent 智能运维
- **ReAct 执行循环** — LLM 生成命令 → SSH 执行 → 观察结果 → 决定下一步，最多 40 轮迭代，失败自动诊断并尝试替代方案
- **3 种运行模式** — chat（纯对话）/ agent（每步确认）/ auto（LOW 自动 + HIGH 确认），灵活匹配不同场景
- **智能风险标注** — LLM 自行判断命令风险等级（LOW/HIGH），高危关键词 + 正则硬阻断兜底防误判
- **流式思考过程** — SSE 实时展示 LLM 的推理、计划和执行决策，全程透明可追溯

### 智能委托（Claude Code 子智能体）
- **LLM 自主决策** — 通过 `delegate_task` 工具判断是否委托，无需规则引擎。「改代码 → 委托 Claude Code，改系统 → Agent 自己做」
- **PTY 双向交互** — 委托运行于 PTY 伪终端（交互 REPL 模式），权限提示检测 + 用户确认条
- **分段审核** — 输出超过 8000 字符自动分段提交 LLM 审核，退出码检查 + 命令审计 + 目标达成判断
- **冲突处理** — 委托期间新消息到达时，用户可选择取消委托或排队等待
- **安装引导** — 远程缺少 Node.js/Claude Code 时自动引导安装（apt/yum 双发行版适配）

### Echo 智能助手（AIOS）
- 面向日常对话的门面 Agent：聊天、信息管理、记忆整理、报告生成（`/echo` 页面）
- 检索增强纯聊天：用户画像 + 记忆条目 + FTS5 全文检索注入 prompt，每轮仅 1 次 LLM 调用

### 监控与告警
- CPU / 内存 / 磁盘 / 网络 / 进程实时监控，ECharts 可视化，静默刷新不干扰操作
- 自定义告警规则，支持钉钉 / 邮件 / Webhook 多渠道通知，告警合并与恢复事件

### 工具与交互
- **xterm.js Web 终端** — WebSocket 直通 PTY，完整终端渲染（ANSI 颜色 / 光标 / 交互）
- **REPL 工具会话** — 远程 CLI 工具（claude code 等）交互式会话面板
- 文件浏览器（可视化浏览服务器文件系统）、命令模板库（一键复用）、语音输入

### 安全体系
- 高危关键词 + 正则模式硬阻断（裸盘写入、fork 炸弹、curl-pipe-shell 等）
- LLM 风险标注：HIGH 命令必须用户确认；委托前后双审计
- 审计记录（确认/拒绝）+ 操作日志全量入库
- 服务器密码基于 PBKDF2 + XOR 加密存储

### 用户体验
- 响应式 Web 界面（Vue 3 + Tailwind CSS），移动端底部 Tab 导航适配
- 多会话对话管理（自动标题）、操作历史记录与回放、一键重新执行
- Electron 桌面端（desktop/）、一键启动脚本

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python + FastAPI + Uvicorn |
| 前端框架 | Vue 3 + Vite + Pinia + Vue Router + Tailwind CSS |
| 数据库 | SQLite（aiosqlite） |
| SSH 引擎 | asyncssh + paramiko 双引擎（自动降级） |
| AI 模型 | DeepSeek Chat API（OpenAI 兼容格式） |
| 实时通信 | SSE 事件流 + WebSocket 终端 |
| 数据可视化 | ECharts |
| 桌面端 | Electron |

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
# 方式一：一键启动（自动创建 venv、安装依赖、构建前端并打开浏览器）
python run.py

# 方式二：手动
pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 首次使用

1. **设置页** → 填入 DeepSeek API Key → 测试连接 → 保存
2. **服务器管理** → 添加目标服务器（主机、端口、用户名、密码或私钥）→ 测试连接 → 保存
3. **仪表盘** → 选择服务器，输入自然语言指令开始使用

> 所有配置（API Key、服务器凭据）均存储在本地 SQLite 数据库中，数据不会离开你的机器。

### 使用模式

| 模式 | 行为 | 适用场景 |
|------|------|----------|
| chat | 纯对话，仅文本问答，不执行命令 | 咨询问题、学习知识 |
| auto | AI 自动分析和执行（低风险命令直接执行） | 熟练用户，日常快速操作 |
| agent | AI 生成执行计划，人工确认后再执行 | 生产环境操作，高风险任务 |

---

## 项目结构

```
shannonos/
├── app/                        # Python 后端
│   ├── main.py                 # FastAPI 入口，路由注册，SPA 静态文件服务
│   ├── agent.py                # Agent 核心编排（ReAct 循环、风险标注、批处理）
│   ├── llm_client.py           # LLM API 调用层（流式/非流式、tool calling）
│   ├── executor.py             # SSH 命令执行器（双引擎、stdin 管道、PTY）
│   ├── connection.py           # SSH 连接池（空闲回收、健康检查、paramiko 降级）
│   ├── database.py             # SQLite CRUD（主机、日志、审计、设置、会话）
│   ├── events.py               # SSE 事件系统（缓存、重放、自动清理）
│   ├── security.py             # 密码加密（PBKDF2 + XOR）、高危关键词、assess_risk()
│   ├── delegate/               # 智能委托模块
│   │   ├── base.py             # SubAgent 抽象基类 + DelegationContext
│   │   ├── claude_code.py      # ClaudeCodeSubAgent（探测/执行/超时/取消）
│   │   ├── executor.py         # 委托执行编排器（冲突处理、超时、活跃会话管理）
│   │   ├── reviewer.py         # 分段审核器（退出码 + 命令审计 + 目标达成）
│   │   └── install.py          # Node.js + Claude Code 自动安装（apt/yum）
│   ├── notification.py         # 告警通知（钉钉/邮件/Webhook）
│   ├── monitor_scheduler.py    # 监控采集调度器
│   ├── repl_sessions.py        # 工具 REPL 会话管理
│   └── routers/                # API 路由（chat/hosts/settings/history/monitoring/
│                               #   files/terminal/tools/alert_rules/alerts）
├── aios/                       # AIOS 运行时层
│   ├── agent_registry.py       # Agent 注册表
│   ├── dispatcher.py           # LLM 驱动的任务分派
│   ├── ipc.py                  # Agent 间通信
│   ├── memory.py / embedding.py # 记忆与向量检索
│   ├── security.py             # 硬阻断清单（is_blocked）
│   ├── tools.py / tool_registry.py
│   └── echo/                   # Echo Agent（agent/router/db/fts/memory/report/prompts）
├── agents/                     # 原生 Agent 实现
│   ├── server_agent.py         # Server Agent（运维）
│   └── code_agent.py           # Code Agent（代码操作，shlex 防注入 + 硬阻断）
├── desktop/                    # Electron 桌面端
├── web/                        # Vue 3 前端（pages/ components/ stores/ composables/）
├── docs/adr/                   # 架构决策记录（0001-0007）
├── run.py                      # 一键启动脚本
├── build.py                    # 发布打包脚本（敏感文件自动排除）
├── requirements.txt
└── .env.example                # 环境变量模板（可选）
```

---

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
| `thinking` / `plan` | LLM 思考过程与执行计划流式输出 |
| `command_start` / `command_output` / `command_result` | 命令执行全流程 |
| `risk_hold` | 高风险命令等待用户确认 |
| `react` / `react_ask` / `react_done` | ReAct 决策步骤（推理/询问/完成） |
| `delegate_confirm_required` | 委托前等待用户确认（阻塞） |
| `delegate_started` / `delegate_progress` / `delegate_completed` | 委托执行全流程（逐行流式） |
| `delegate_review` | 委托结果审核（目标达成/变更文件/风险警告） |
| `delegate_cancelled` / `delegate_timeout` / `delegate_fallback` | 委托异常处理 |
| `delegate_install_required` | 远程缺少 Claude Code，引导安装 |
| `delegate_permission_required` | Claude Code 权限请求确认（前端已就绪，后端发射待实现） |
| `delegation_conflict` | 委托期间新消息到达（取消/排队二选一） |

## 委托 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/delegate/cancel` | 取消正在执行的委托 |
| POST | `/api/delegate/confirm-install` | 确认/拒绝安装 Claude Code |
| POST | `/api/delegate/resolve-conflict` | 解决委托冲突（cancel_and_new / queue） |
| POST | `/api/delegate/respond-permission` | 响应 Claude Code 权限请求 |
| GET | `/api/delegate/status/{task_id}` | 查询委托状态 |

## API 参考（主要端点）

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 发送消息（SSE 流式响应，含 ReAct/委托流程） |
| `/api/chat/execute-plan` | POST | 批处理执行命令计划 |
| `/api/stream/{task_id}` | GET | SSE 事件流 |
| `/api/execute/confirm` | POST | 确认/取消命令执行 |
| `/api/hosts` | GET/POST | 服务器管理 |
| `/api/hosts/{id}` | PUT/DELETE | 更新/删除服务器 |
| `/api/host/test` | POST | 测试服务器连接 |
| `/api/context/{host_id}` | GET | 服务器上下文（不返回解密凭据） |
| `/api/settings` | GET/POST | 应用设置 |
| `/api/settings/test` | POST | 测试 LLM API 连接 |
| `/api/monitor/{host_id}` | POST | 监控数据 |
| `/api/history/actions/{host_id}` | GET | 操作历史 |
| `/api/files/list` `/api/files/read` | POST | 文件浏览 |
| `/api/ws/terminal` | WebSocket | 交互式终端 |
| `/api/tools/sessions` 及 `/sessions/{id}/ws` | POST/WS | 工具 REPL 会话 |
| `/api/alerts` `/api/alert-rules` | GET/POST | 告警与规则 |
| `/api/echo/*` | — | Echo 助手（chat/conversations/reports） |

完整 API 文档请访问 `/docs`（Swagger UI）。

---

## 环境变量（可选）

无需 `.env` 文件即可运行，所有配置可通过 Web UI 完成。如需要预设配置，复制 `.env.example` 为 `.env`：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API 密钥 |
| `DEEPSEEK_API_BASE` | https://api.deepseek.com | API 基础地址 |
| `DEEPSEEK_MODEL` | deepseek-chat | 模型名称 |
| `DEEPSEEK_AUX_MODEL` | — | 辅助模型（可选，用于摘要/审核） |
| `DASHSCOPE_API_KEY` / `DASHSCOPE_EMBED_MODEL` | — | 通义千问（可选，用于 embedding 检索） |
| `SHANNON_DEFAULT_SSH_PORT` | 22 | 默认 SSH 端口 |
| `SHANNON_MONITOR_INTERVAL` | 60 | 监控采集间隔（秒），最低 10 |

> 钉钉 / 邮件通知配置在 Web UI「设置」页中维护（存入数据库），不走环境变量。

---

## 架构决策（ADR）

| ADR | 决策 |
|-----|------|
| [0001](docs/adr/0001-dynamic-detection.md) | 动态探测替代 YAML 配置 |
| [0002](docs/adr/0002-dual-channel.md) | 预判器前置 + 双通道设计（已被 0005 部分替代） |
| [0003](docs/adr/0003-exclusive-connection.md) | 委托期间独占 SSH 连接 |
| [0004](docs/adr/0004-risk-based-confirmation.md) | 合并确认层 + 风险分流 |
| [0005](docs/adr/0005-llm-only-delegation-decision.md) | 移除预判器，LLM 独立决定委托 |
| [0006](docs/adr/0006-mobile-bottom-tab-navigation.md) | 移动端底部 Tab 导航 |
| [0007](docs/adr/0007-echo-native-agent.md) | 自建 Echo Agent 而非部署 hermes-agent |

---

## 开发指南

```bash
# 后端开发（热重载）
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端开发（Vite HMR，API 自动代理到后端）
cd web && npm run dev

# 前端构建
cd web && npm run build
```

## 部署

生产部署请参见 [DEPLOY.md](DEPLOY.md)（含环境变量、数据安全、桌面端说明）。

## 路线图

- **PTY 权限检测发射** — 后端实现 `delegate_permission_required` 事件（前端确认条已就绪）
- **多 LLM 支持** — 可插拔后端（Claude / OpenAI / Gemini / 本地模型）
- **Agent 记忆系统** — 跨会话持久化记忆，学习服务器运维模式
- **插件系统 / 模板市场** — 社区贡献工具、共享运维模板
- **CI/CD 集成** — 从 GitHub Actions / Webhooks 触发运维操作
- **团队协作** — 角色权限管理、共享服务器清单、操作审批流程

## 常见问题

| 问题 | 解决 |
|------|------|
| 委托不触发 | 代码分析/重构/审查类任务会自动委托；纯运维操作由 Agent 自己执行 |
| 8000 端口被占用 | 修改启动命令端口，或设置 `SHANNON_PORT` |
| 前端修改不生效 | 重新执行 `cd web && npm run build` |
| SSH 连接失败 | 系统自动 asyncssh → paramiko 降级；检查防火墙与密钥权限 |

---

## 许可证

[Apache License 2.0](LICENSE)

> 用 AI 赋能运维，让服务器管理变得简单。
