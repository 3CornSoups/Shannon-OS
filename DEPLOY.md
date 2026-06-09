# Shannon OS Agent 部署文档

## 环境要求

| 组件 | 版本要求 |
|------|---------|
| Python | >= 3.11 |
| Node.js | >= 18 |
| npm | >= 9 |

## 项目结构

```
shannonNEW/
├── app/                      # 后端 Python 应用
│   ├── main.py              # FastAPI 入口
│   ├── agent.py             # Agent 编排核心
│   ├── conversation.py      # 对话上下文管理
│   ├── llm_client.py        # LLM API 调用 + tool calling
│   ├── models.py            # Pydantic 数据模型
│   ├── prompts.py           # 提示词集中管理
│   ├── database.py          # SQLite 数据库操作
│   ├── executor.py          # SSH 命令执行器
│   ├── connection.py        # SSH 连接池
│   ├── events.py            # SSE 事件系统
│   ├── errors.py            # 异常定义 + 重试工具
│   ├── logger.py            # LLM 调用日志
│   ├── monitor.py           # 系统监控
│   ├── security.py          # 密码管理
│   ├── settings.py          # 应用配置
│   ├── terminal.py          # WebSocket 终端
│   ├── files.py             # 文件管理
│   └── routers/             # API 路由
│       ├── chat.py          # 聊天 + ReAct 循环
│       ├── hosts.py         # 主机管理
│       ├── settings.py      # 设置接口
│       ├── history.py       # 操作历史
│       ├── monitoring.py    # 监控数据
│       ├── files.py         # 文件浏览
│       └── terminal.py      # WebSocket 终端
├── web/                     # Vue 3 前端
│   ├── src/
│   │   ├── pages/           # 页面组件
│   │   ├── components/      # 通用组件
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── services/        # API 封装
│   │   ├── router/          # 路由
│   │   └── styles/          # 样式
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── data/                    # SQLite 数据库文件
├── requirements.txt         # Python 依赖
└── run.py                   # 一键启动脚本
```

## 快速部署

### 1. 配置环境

复制环境变量模板：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
DEEPSEEK_API_KEY=sk-your-api-key-here
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
SHANNON_DEFAULT_SSH_PORT=22
SHANNON_PORT=8000
```

### 2. 后端部署

```bash
# 创建虚拟环境
python -m venv .venv

# 激活
source .venv/bin/activate      # Linux/Mac
.venv\Scripts\activate          # Windows CMD
.venv\Scripts\Activate.ps1     # Windows PowerShell

# 安装依赖
pip install -r requirements.txt

# 启动
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. 前端部署（开发模式）

```bash
cd web
npm install
npm run dev          # 开发服务器，默认 :5173
```

### 4. 前端构建（生产模式）

```bash
cd web
npm run build        # 输出到 web/dist/
```

构建后后端会自动挂载静态文件，无需单独部署前端服务。

### 5. 一键启动

```bash
python run.py
```

自动创建虚拟环境、安装依赖、构建前端、启动服务、打开浏览器。

## API 接口

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 发送聊天消息（SSE 流式响应） |
| `/api/stream/{task_id}` | GET | 获取 SSE 事件流 |
| `/api/execute/confirm` | POST | 确认/取消命令执行 |
| `/api/conversations/{host_id}` | GET | 列出对话 |
| `/api/conversations/{conv_id}/messages` | GET | 获取对话消息 |
| `/api/hosts` | GET/POST | 主机管理 |
| `/api/settings` | GET/PUT | 应用设置 |
| `/api/monitor/{host_id}` | GET | 监控数据 |
| `/api/history` | GET | 操作历史 |
| `/api/files/list` | POST | 文件列表 |
| `/api/ws/terminal` | WebSocket | 交互式终端 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | - | DeepSeek API 密钥 |
| `DEEPSEEK_API_BASE` | https://api.deepseek.com | API 地址 |
| `DEEPSEEK_MODEL` | deepseek-chat | 模型名称 |
| `SHANNON_DEFAULT_SSH_PORT` | 22 | 默认 SSH 端口 |
| `SHANNON_PORT` | 8000 | Web 服务端口 |

## 三种模式

| 模式 | 说明 |
|------|------|
| chat | 纯对话，不执行命令 |
| auto | 自动分析并执行，适合低风险操作 |
| agent | 先给出计划，确认后执行，适合高风险操作 |

## 端口说明

- `8000` — 后端 API + 前端静态文件（生产模式）
- `5173` — 前端开发服务器（代理 API 到后端）
