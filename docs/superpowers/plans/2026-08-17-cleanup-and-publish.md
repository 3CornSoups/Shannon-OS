# Shannon-OS 清理优化与发布 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 清理前端"奖状"装饰、治理重复/过时文档、修复明确代码问题，并将完整项目 force-push 到 GitHub 仓库 `3CornSoups/Shannon-OS`。

**Architecture:** 全本地修改 → 分任务提交（每任务一个 commit）→ 最终一次性推送到远程 main（force push 完全替换，保留远程 Apache-2.0 LICENSE）。本项目无测试套件，验证手段为：前端 `npm run build`、后端 `python -m compileall`、grep 引用一致性检查。

**Tech Stack:** Vue 3 + Vite（前端构建验证）、Python 3.11+（compileall 语法验证）、git + GitHub（版本控制与发布）。

**Spec:** `docs/superpowers/specs/2026-08-17-cleanup-and-publish-design.md`（已批准）

## Global Constraints

- 删除范围精确到 spec ① 表中的元素（hero-badge / hero-stats / vision-section / section-badge），Showcase 页面本体与其余 section 一律保留
- 文档治理按 spec ② 表逐文件执行；`PRD_智能委托调用.md`、`.env`、`data/`、`logs/`、`web/node_modules/`、`.venv/` 不参与任何修改（.gitignore 已排除）
- 代码修复只做"明确问题"（可指出具体行、可验证），不做架构重构；不改 `aios/`、`agents/`、`desktop/` 的设计
- 许可证以远程 LICENSE 文件为准（**Apache-2.0**），所有文档不得再声明 MIT
- git 身份为仓库级：`user.name=3CornSoups`，`user.email=3CornSoups@users.noreply.github.com`（已配置）
- 推送使用 force push 到 `main`；认证用用户环境变量 `GITHUB_PERSONAL_ACCESS_TOKEN`

---

### Task 1: Showcase.vue 删除"奖状"装饰元素

**Files:**
- Modify: `web/src/pages/Showcase.vue`（template、script、style 三部分）

**Interfaces:**
- Produces: 无装饰的 Showcase 页面（组件结构与 `Layout.vue` 的 `/showcase` 入口不变）

- [ ] **Step 1: 删除 template 中的 hero-badge 与 hero-stats**

`web/src/pages/Showcase.vue` 第 6-26 行。将：

```html
        <div class="hero-badge">v2.0</div>
        <h1 class="hero-title">Shannon OS Agent</h1>
        <p class="hero-subtitle">AI 驱动的智能运维操作系统</p>
        <div class="hero-stats">
          <div class="stat-item">
            <span class="stat-value">7</span>
            <span class="stat-label">核心模块</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">3</span>
            <span class="stat-label">执行模式</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">20+</span>
            <span class="stat-label">预设模板</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">∞</span>
            <span class="stat-label">可扩展</span>
          </div>
        </div>
```

替换为：

```html
        <h1 class="hero-title">Shannon OS Agent</h1>
        <p class="hero-subtitle">AI 驱动的智能运维操作系统</p>
```

- [ ] **Step 2: 删除 template 中 4 个 section-badge 元素**

删除第 63、97、130、156 行的 4 处 `<span class="section-badge">…</span>`（Prompt Engineering / Risk Control / Features / Scenarios），保留同行的 section-title。

- [ ] **Step 3: 删除 template 中的 vision-section**

删除第 172-181 行的整个 `<section class="section vision-section">…</section>` 块（含 `vision-content`、`vision-tags` 循环）。

- [ ] **Step 4: 删除 script 中的 visionTags 数据**

删除 `visionTags` 常量定义（第 319 行附近）：

```js
const visionTags = ['AI-Native', 'ReActive Agent', 'Multi-Cluster', 'Zero-Trust Security', 'Conversational DevOps', 'Intelligent Observability']
```

- [ ] **Step 5: 删除 style 中已无引用的装饰 CSS**

删除以下 CSS 块（style 部分）：`.hero-badge`（452 行附近）、`.hero-stats`（475 行附近）及其 `.stat-item/.stat-value/.stat-label`、`.section-badge`（521 行附近）、`.vision-section` 及其子规则（911 行附近）、以及响应式媒体查询中仅服务于上述类的规则（如 946-947 行的 `.hero-stats { gap: 20px; }`）。保留 `.hero-title`/`.hero-subtitle`。

- [ ] **Step 6: 验证前端构建**

Run: `cd web && npm run build`
Expected: 构建成功，无未定义变量/样式错误；`git diff --stat` 仅显示 `web/src/pages/Showcase.vue` 1 个文件变更

- [ ] **Step 7: 提交**

```bash
git add web/src/pages/Showcase.vue
git commit -m "refactor(web): 移除 Showcase 页'奖状'类装饰元素（v2.0 徽章/统计/愿景/英文小标签）"
```

---

### Task 2: 文档治理 —— 删除重复文档并补充 CLAUDE.md

**Files:**
- Delete: `技术思路.md`、`设计重点与难点.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: 无
- Produces: `CLAUDE.md` 新增「AIOS 语义抽象层」设计理念小节（信息源为被删的两篇文档）

- [ ] **Step 1: 确认删除目标无引用**

Run: `grep -rn "技术思路\|设计重点" --include="*.md" --include="*.py" --include="*.js" . | grep -v node_modules | grep -v "\.git/"`
Expected: 仅命中被删文件自身，无其他文件引用

- [ ] **Step 2: 删除两个重复文档**

```bash
git rm "技术思路.md" "设计重点与难点.md"
```

- [ ] **Step 3: 在 CLAUDE.md「核心架构」部分之前插入 AIOS 语义抽象层小节**

在 `CLAUDE.md` 的 `## 核心架构：Agent 处理流程` 标题前插入：

```markdown
## 设计理念：AIOS 语义抽象层

Shannon OS 的本质是在 LLM 与 Linux 服务器之间构建一个 **AIOS（AI Operating System）语义抽象层**。传统运维路径是「人 → CLI → 服务器」，本项目将其替换为「人 → 自然语言 → AI Agent → 工具调用 → 服务器」，Agent 承担类似操作系统内核的调度角色：接收高层意图、分解为原子操作、调度执行资源、处理异常并报告结果。

系统遵循三条原则：
1. **LLM 自主决策优先于规则引擎** —— 意图分类、工具选择、终止条件、委托决策全由模型判断，规则只做安全兜底
2. **流式优先** —— 所有长耗时操作通过 SSE 实时推送
3. **连接即会话** —— 委托期间 SSH 连接独占，保持 PTY 会话连续性

（2026-07-10 起，项目向真正的 AIOS 运行时演进：新增 `aios/` 层管理多个 Agent，现有服务器管理能力演化为运行在 AIOS 上的 Server Agent；方向详见 CONTEXT.md）
```

- [ ] **Step 4: 验证**

Run: `git status`
Expected: `技术思路.md`、`设计重点与难点.md` 为 deleted，`CLAUDE.md` 为 modified

- [ ] **Step 5: 提交**

```bash
git add -A CLAUDE.md
git commit -m "docs: 删除重复文档（技术思路/设计重点与难点），AIOS 语义抽象层理念并入 CLAUDE.md"
```

---

### Task 3: 重写 README.md

**Files:**
- Modify: `README.md`（全文替换）

**Interfaces:**
- Consumes: CLAUDE.md 功能清单（Task 2 后为准）
- Produces: 与当前代码一致的项目说明文档

- [ ] **Step 1: 用新内容全文替换 README.md**

将 `README.md` 全文替换为（保留开头 `# Shannon OS Agent`）：

````markdown
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
````

- [ ] **Step 2: 验证**

Run: `grep -n "MIT\|shannonNEW\|权限全自动" README.md`
Expected: 无匹配（许可证声明为 Apache-2.0，无旧项目名与过时描述）

- [ ] **Step 3: 提交**

```bash
git add README.md
git commit -m "docs: 重写 README，同步当前功能（委托 PTY 交互/Echo/告警/桌面端）并统一许可证为 Apache-2.0"
```

---

### Task 4: 重写 DEPLOY.md

**Files:**
- Modify: `DEPLOY.md`（全文替换）

**Interfaces:**
- Consumes: 无
- Produces: 与当前项目结构一致的部署文档

- [ ] **Step 1: 用新内容全文替换 DEPLOY.md**

````markdown
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
| `SHANNON_DEFAULT_SSH_PORT` | 22 | 默认 SSH 端口 |
| `SHANNON_PORT` | 8000 | Web 服务端口 |
| `SHANNON_MONITOR_INTERVAL` | 60 | 监控采集间隔（秒），最低 10 |
| `SHANNON_DINGTALK_WEBHOOK_URL` / `SHANNON_DINGTALK_SECRET` | — | 钉钉机器人通知（可选） |
| `SHANNON_SMTP_HOST` / `PORT` / `USERNAME` / `PASSWORD` / `RECIPIENTS` | — | 邮件通知（可选） |

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
| 开发前端热更新 | `cd web && npm run dev`（Vite 开发服务器，API 自动代理到 8000） |
````

- [ ] **Step 2: 验证**

Run: `grep -n "shannonNEW" DEPLOY.md`
Expected: 无匹配（旧项目名残留已清除）

- [ ] **Step 3: 提交**

```bash
git add DEPLOY.md
git commit -m "docs: 重写 DEPLOY 部署文档，清除旧项目名残留并补充环境变量/数据安全说明"
```

---

### Task 5: 修复 ADR 编号冲突

**Files:**
- Rename: `docs/adr/0005-echo-native-agent.md` → `docs/adr/0007-echo-native-agent.md`
- Modify: `CLAUDE.md`（ADR 列表）

**Interfaces:**
- Consumes: 无
- Produces: `docs/adr/` 下编号唯一（0001-0007），按时间排序

- [ ] **Step 1: 重命名文件并更新文件内标题引用**

```bash
git mv docs/adr/0005-echo-native-agent.md docs/adr/0007-echo-native-agent.md
```

将重命名后文件内的 `# ADR-0005:` 标题改为 `# ADR-0007:`（文档正文中若引用自身编号同步替换）。

- [ ] **Step 2: 更新 CLAUDE.md 中 ADR 列表**

将 CLAUDE.md 中 `docs/adr/` 说明（当前只列 0001-0004）替换为完整列表：

```markdown
├── docs/adr/                      # 架构决策记录
│   ├── 0001-dynamic-detection.md      # 动态探测替代 YAML 配置
│   ├── 0002-dual-channel.md           # 预判器前置 + 双通道设计（已被 0005 部分替代）
│   ├── 0003-exclusive-connection.md   # 委托期间独占 SSH 连接
│   ├── 0004-risk-based-confirmation.md # 合并确认层 + 风险分流
│   ├── 0005-llm-only-delegation-decision.md # 移除预判器，LLM 独立决定委托
│   ├── 0006-mobile-bottom-tab-navigation.md # 移动端底部 Tab 导航
│   └── 0007-echo-native-agent.md     # 自建 Echo Agent 而非部署 hermes-agent
```

- [ ] **Step 3: 验证**

Run: `ls docs/adr/`
Expected: 0001 至 0007 共 7 个文件，编号唯一

- [ ] **Step 4: 提交**

```bash
git add -A docs/adr CLAUDE.md
git commit -m "docs: 修复 ADR 0005 编号冲突，Echo ADR 顺延为 0007"
```

---

### Task 6: 代码质量审查与明确问题修复

**Files:**
- 审查: `app/`（后端）、`web/src/`（前端）、快速扫描 `aios/` `agents/` `desktop/`（与文档一致性）
- Modify: 以审查发现清单为准（仅修"明确问题"）

**Interfaces:**
- Consumes: 无
- Produces: 明确问题修复后的代码（无新接口）

**审查协议（不可放宽）**
- 审查维度：逻辑错误、未定义引用、明显不一致（文档描述 vs 代码行为）、死代码引用
- "明确问题"判定：能指出具体 `文件:行` 且修复方案确定（如：调用了不存在的方法、条件恒真/恒假、引用了未导出的变量）。风格建议、重构建议、性能微优化一律不采纳
- 审查输出：`文件:行号 | 问题描述 | 修复方案` 清单

- [ ] **Step 1: 并行派发两个审查子代理**

派发（同步等待结果）：
- 子代理 A（app/）：审 `app/*.py` 与 `app/routers/*.py`，按上述协议输出发现清单
- 子代理 B（web/）：审 `web/src/**/*.{vue,js}`（排除 node_modules/dist），按上述协议输出发现清单

同时本会话快速扫描 `aios/`、`agents/`、`desktop/`：仅查与 CLAUDE.md/CONTEXT.md 描述的明显出入（如 CLAUDE.md 提到的模块不存在、或存在的模块未被文档提及），不深入审查。

- [ ] **Step 2: 主会话逐项核验发现**

对清单中每项：Read 对应 `文件:行` 确认问题真实存在且修复方案安全 → 修复 → 下一项。核验为误报的项跳过并记录。

- [ ] **Step 3: 验证**

Run: `python -m compileall app aios agents desktop`
Expected: 全部编译通过（含修复后的文件）

- [ ] **Step 4: 提交**

```bash
git add -A app web/src aios agents desktop
git commit -m "fix: 修复代码审查发现的明确问题（详见提交内容）"
```

> 若审查无发现：跳过 Step 3-4，在任务记录中注明"审查无明确问题"。

---

### Task 7: 工程配置核对

**Files:**
- Modify: `.env.example`（如需）、`requirements.txt`（如需）、`run.py`/`build.py`（如需）

**Interfaces:**
- Consumes: 无
- Produces: 与代码一致的配置文件

- [ ] **Step 1: 核对 .env.example 与代码使用**

Run: 对 `.env.example` 中每个变量名，grep 代码引用：

```bash
for var in DEEPSEEK_API_BASE DEEPSEEK_MODEL DEEPSEEK_API_KEY DEEPSEEK_AUX_MODEL DASHSCOPE_API_KEY DASHSCOPE_EMBED_MODEL SHANNON_DEFAULT_SSH_PORT SHANNON_PORT SHANNON_MONITOR_INTERVAL SHANNON_DINGTALK_WEBHOOK_URL SHANNON_DINGTALK_SECRET SHANNON_SMTP_HOST SHANNON_SMTP_PORT SHANNON_SMTP_USERNAME SHANNON_SMTP_PASSWORD SHANNON_SMTP_RECIPIENTS; do echo "$var: $(grep -rl "$var" app/ aios/ agents/ --include='*.py' | tr '\n' ' ')"; done
```

Expected: 每个变量至少有 1 处代码引用（`app/settings.py`、`app/notification.py`、`app/monitor_scheduler.py`、`aios/embedding.py` 等）。**反向核查**：grep `os.getenv` 于 `app/ aios/ agents/`，列出代码中使用但 `.env.example` 缺失的变量，若存在则补充进 `.env.example`。

- [ ] **Step 2: 核对 requirements.txt 与实际 import**

Run: `grep -rhoE "^(import|from) [a-z_]+" app/ aios/ agents/ --include="*.py" | awk '{print $2}' | cut -d. -f1 | sort -u`
Expected: 第三方包（fastapi/uvicorn/httpx/aiosqlite/pydantic/asyncssh/paramiko/dotenv/yaml 等）均已被 `requirements.txt` 覆盖；若发现未覆盖的第三方包（如 pydantic-settings、openai 等），补充进 requirements.txt 并在提交说明中注明。

- [ ] **Step 3: 核对 run.py / build.py 引用的路径**

Run: `grep -n "web/\|dist\|app.main\|requirements" run.py build.py`
Expected: 路径与当前项目结构一致（web/ 存在、`app.main:app` 可导入——Task 6 的 compileall 已间接验证）。发现不一致则修复。

- [ ] **Step 4: 验证**

Run: `python -m compileall app aios agents desktop`（如有代码改动）
Expected: 通过

- [ ] **Step 5: 提交**

```bash
git add .env.example requirements.txt run.py build.py
git commit -m "chore: 核对工程配置（.env.example/requirements/启动脚本）与代码一致性"
```

> 若三处核对均无差异：跳过提交，在任务记录中注明"配置已一致，无改动"。

---

### Task 8: 最终整体验证

**Files:** 无（只验证）

- [ ] **Step 1: 后端语法验证**

Run: `python -m compileall app aios agents desktop 2>&1 | tail -3`
Expected: 无 `SyntaxError`；输出为 `Compiling ...` 或空

- [ ] **Step 2: 前端构建验证**

Run: `cd web && npm run build 2>&1 | tail -5`
Expected: `✓ built in ...`（构建成功）

- [ ] **Step 3: 文档一致性抽查**

Run: `grep -rn "MIT\|shannonNEW\|奖状\|v2.0" README.md DEPLOY.md CLAUDE.md web/src/pages/Showcase.vue docs/adr/`
Expected: 无匹配（或仅命中无意义的词）

- [ ] **Step 4: 预览完整变更集**

Run: `git status --short && git log --oneline`
Expected: 工作区干净（Task 1-7 全部已提交），提交历史为 spec 初始提交 + Task 1-7 各提交

---

### Task 9: 引入 LICENSE 并发布到 GitHub

**Files:**
- Create: `LICENSE`（Apache-2.0，内容从远程仓库复制）

**Interfaces:**
- Consumes: 远程仓库 `3CornSoups/Shannon-OS` 的 LICENSE 文件
- Produces: 本地 LICENSE 文件 + 远程 main 分支完全替换

- [ ] **Step 1: 从远程复制 Apache-2.0 LICENSE 到本地**

用 GitHub API 获取远程 LICENSE 内容并写入本地 `LICENSE`：

```bash
curl -s -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" https://api.github.com/repos/3CornSoups/Shannon-OS/contents/LICENSE -o /tmp/LICENSE.json
python -c "import json; open('LICENSE','w',encoding='utf-8').write(json.load(open('/tmp/LICENSE.json',encoding='utf-8'))['content'].replace('\n','').encode().decode('base64'))"
```

（若 curl/PAT 不可用，改用 GitHub MCP 工具 `get_file_contents` 获取 LICENSE 全文，手动写入本地 `LICENSE`。）

- [ ] **Step 2: 验证 LICENSE**

Run: `head -3 LICENSE`
Expected: `Apache License` / `Version 2.0`

- [ ] **Step 3: 提交 LICENSE**

```bash
git add LICENSE
git commit -m "license: 引入 Apache-2.0 LICENSE（与远程仓库一致）"
```

- [ ] **Step 4: 添加远程并推送（force push 完全替换）**

```bash
git remote add origin https://github.com/3CornSoups/Shannon-OS.git
git push --force --set-upstream origin main
```

Expected: 推送成功；远程 main 与本地历史完全一致

- [ ] **Step 5: 验证远程状态**

Run: `git ls-remote origin main` 与本地 `git rev-parse HEAD` 比对
Expected: 两者 SHA 相同

- [ ] **Step 6: 远程文件核对**

用 GitHub MCP `get_file_contents` 检查远程根目录：
Expected: 包含 README.md（新）、LICENSE、app/、aios/、agents/、desktop/、docs/、web/ 等；不再包含旧 README 冲突标记、README.zh-CN.md、scripts/

- [ ] **Step 7: 完成报告**

在最终报告中列出：远程仓库 URL、推送的提交数、验证结果摘要。

---

## Self-Review 记录

（本计划执行前已核对 spec 与计划的对应关系——见下）

**Spec 覆盖：**
- ① 前端装饰删除 → Task 1 ✓
- ② 文档治理（删重复/重写 README/DEPLOY/CLAUDE/ADR 编号） → Task 2-5 ✓
- ③ 代码质量审查 → Task 6 ✓
- ④ 工程配置核对 → Task 7 ✓
- 验证与推送（compileall/npm build/LICENSE/force push） → Task 8-9 ✓
- 不做的事（PRD/.env/data 不碰） → Global Constraints ✓

**占位符检查：** Task 6 的修复内容以"审查发现清单"为输入，属探索驱动任务，协议已完整定义（判定标准 + 输出格式 + 核验流程），非占位。

**类型/命名一致性：** 全计划引用同一批文件名与路径；Task 3/4 的文档全文与 Task 5 的 CLAUDE.md ADR 列表、Task 2 的 AIOS 小节在内容上互相引用（如"项目结构"段落包含 aios/agents/desktop），彼此一致。
