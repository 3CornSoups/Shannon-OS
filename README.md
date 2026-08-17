# Shannon OS Agent

智能服务器管理助手：通过 AI 分析用户请求并经 SSH 执行系统命令。支持多服务器管理、实时监控、代码智能委托、操作历史追踪，并持续向 AIOS（AI Operating System）运行时演进。

## 核心功能

### Agent 智能运维
- **ReAct 执行循环**：LLM 生成命令 → SSH 执行 → 观察结果 → 决定下一步，最多 40 轮迭代，失败自动诊断重试
- **3 种运行模式**：chat（纯对话）/ agent（每步确认）/ auto（LOW 自动 + HIGH 确认）
- **智能风险标注**：LLM 自行判断命令风险等级（LOW/HIGH），高危关键词 + 正则硬阻断兜底
- **流式思考过程**：SSE 实时展示 LLM 的推理、计划和执行决策

### 智能委托（Claude Code 子智能体）
- **LLM 自主决策**：通过 `delegate_task` 工具判断是否委托，「改代码 → 委托 Claude Code，改系统 → Agent 自己做」
- **PTY 双向交互**：委托运行于 PTY 伪终端，权限提示实时转发，用户确认/拒绝后才继续
- **分段审核**：输出超过 8000 字符自动分段提交 LLM 审核，退出码 + 命令双审计
- **冲突处理**：委托期间新消息到达时，用户可选择取消委托或排队等待
- **安装引导**：远程缺少 Node.js/Claude Code 时自动引导安装（apt/yum 适配）

### Echo 智能助手
- 面向日常对话的门面 Agent：聊天、信息管理、记忆整理、报告生成（`/echo` 页面）
- 检索增强纯聊天：用户画像 + 记忆条目 + FTS5 全文检索注入 prompt，无 ReAct 循环开销

### 监控与告警
- CPU / 内存 / 磁盘 / 网络 / 进程实时监控，ECharts 可视化，静默刷新
- 自定义告警规则 + 钉钉 / 邮件通知

### 工具与交互
- xterm.js Web 终端（WebSocket 直通 PTY，ANSI/光标/交互完整支持）
- 文件浏览器、命令模板库、远程 CLI 工具探测、语音输入

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python + FastAPI + Uvicorn |
| 前端 | Vue 3 + Vite + Pinia + Vue Router + Tailwind CSS |
| 数据库 | SQLite（aiosqlite） |
| SSH | asyncssh + paramiko 双引擎 |
| AI | DeepSeek Chat API（OpenAI 兼容格式） |
| 实时通信 | SSE 事件流 + WebSocket 终端 |
| 可视化 | ECharts |
| 桌面端 | Electron（desktop/） |

## 快速开始

### 环境要求

| 组件 | 版本 |
|------|------|
| Python | >= 3.11 |
| Node.js | >= 18 |
| npm | >= 9 |

### 安装与启动

```bash
# 一键启动（自动创建 venv、安装依赖、构建前端并打开浏览器）
python run.py

# 或手动
pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 首次使用

1. **设置页** → 填入 DeepSeek API Key → 测试连接 → 保存
2. **服务器管理** → 添加目标服务器（主机、端口、用户名、密码或私钥）→ 测试连接 → 保存
3. **仪表盘** → 选择服务器，输入自然语言指令开始使用

> 所有配置（API Key、服务器凭据）均存储在本地 SQLite 数据库中，数据不会离开你的机器。

## 项目结构

```
shannonos/
├── app/               # FastAPI 后端（agent 编排 / LLM 客户端 / SSH 执行器 / 监控 / 告警 / 路由）
├── aios/              # AIOS 运行时层（Agent 注册表 / 调度 / IPC / 记忆 / Echo Agent）
├── agents/            # 原生 Agent 实现（Server Agent / Code Agent）
├── desktop/           # Electron 桌面端
├── web/               # Vue 3 前端
├── docs/              # ADR 架构决策记录（docs/adr/）
├── run.py             # 一键启动脚本
├── requirements.txt   # Python 依赖
└── .env.example       # 环境变量模板（可选）
```

## 安全体系

- 高危关键词 + 正则模式硬阻断（裸盘写入、fork 炸弹、curl-pipe-shell 等）
- LLM 风险标注：HIGH 命令必须用户确认
- 委托前后双审计（LLM 风险评级 + Agent 命令审计）
- 审计记录（确认/拒绝）+ 操作日志全量入库
- 服务器密码基于 PBKDF2 + XOR 加密存储

## 许可证

Apache License 2.0。详见 [LICENSE](LICENSE)。
