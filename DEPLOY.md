# Shannon OS Agent 部署文档

## 环境要求

| 组件 | 版本要求 |
|------|---------|
| Python | >= 3.11 |
| Node.js | >= 18 |
| npm | >= 9 |

## 快速部署

### 方式一：一键启动（开发/体验）

```bash
python run.py
```

脚本会自动：创建 `.venv` 虚拟环境并安装依赖 → 构建前端 → 启动服务 → 打开浏览器（http://localhost:8000）。

### 方式二：手动部署（生产）

```bash
# 1. 安装后端依赖
pip install -r requirements.txt

# 2. 构建前端
cd web && npm install && npm run build && cd ..

# 3. 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

生产环境建议配合 systemd / Nginx 反向代理使用，前端构建产物由 FastAPI 静态文件服务直接托管。

## 环境变量（可选）

无需 `.env` 文件即可运行，所有配置可通过 Web UI 完成。如需要预设配置，复制 `.env.example` 为 `.env`：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API 密钥 |
| `DEEPSEEK_API_BASE` | https://api.deepseek.com | API 基础地址 |
| `DEEPSEEK_MODEL` | deepseek-chat | 模型名称 |
| `DEEPSEEK_AUX_MODEL` | — | 辅助模型（可选，用于摘要/审核） |
| `DASHSCOPE_API_KEY` | — | 通义千问 API 密钥（可选，用于 embedding） |
| `DASHSCOPE_EMBED_MODEL` | — | 通义千问 embedding 模型名 |
| `SHANNON_DEFAULT_SSH_PORT` | 22 | 默认 SSH 端口 |
| `SHANNON_MONITOR_INTERVAL` | 60 | 监控采集间隔（秒），最低 10 |

> 钉钉 / 邮件通知配置在 Web UI「设置」页中维护（存入数据库），不走环境变量。

## 数据与安全

- 数据存储于 `data/` 目录（SQLite：主机、会话、日志、审计记录）；`data/` 与 `.env` 已在 .gitignore 中排除，不会入库
- 服务器密码基于 PBKDF2 + XOR 加密存储，API Key 明文存储于本地数据库——请勿将数据库文件泄露到公网

## 桌面端（可选）

```bash
cd desktop
npm install
npm start   # 开发运行
```

桌面端为 Electron 壳，加载同一套 Web 前端。

## 常见问题

| 问题 | 解决 |
|------|------|
| 8000 端口被占用 | 设置 `SHANNON_PORT` 环境变量或修改启动命令端口 |
| 前端修改不生效（生产模式） | 重新执行 `cd web && npm run build` |
| 开发前端热更新 | `cd web && npm run dev`（Vite 开发服务器，API 自动代理到后端） |
