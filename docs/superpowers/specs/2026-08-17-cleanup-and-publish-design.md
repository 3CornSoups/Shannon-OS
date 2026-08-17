# Shannon-OS 清理、优化与发布设计

> 日期：2026-08-17
> 状态：已批准（用户确认）
> 目标仓库：https://github.com/3CornSoups/Shannon-OS（完全替换推送）

## 背景

本地项目 `D:\信息与重要资料备份\服务器\shannonos` 是当前开发版本，功能完整（含智能委托、Echo、AIOS 演进方向）。远程仓库 `3CornSoups/Shannon-OS` 停留在旧状态：README.md 含未解决的 git 冲突标记（`<<<<<<< HEAD` / `>>>>>>>`），LICENSE（Apache-2.0）与 README 声明的 MIT 许可证矛盾。

用户要求：① 优化完善项目 ② 删除前端"奖状"类展示信息 ③ 合并/删除重复文档 ④ 上传到 GitHub 仓库。

## 范围（已确认）

1. **前端装饰删除** — 保留「关于」页面，仅删"奖状感"装饰元素
2. **文档治理** — 合并/删除重复文档、修复过时内容
3. **代码质量优化** — 修复明确 bug 与文档/代码不一致（不做重构）
4. **工程配置清理** — .env.example、requirements.txt、run.py/build.py 核对
5. **推送** — 完全替换（force push），保留 Apache-2.0 LICENSE

## 详细设计

### ① 前端装饰删除（web/src/pages/Showcase.vue）

删除以下元素及其对应 CSS 与 JS 数据：

| 元素 | 位置 | 说明 |
|------|------|------|
| hero-badge「v2.0」 | template hero-section | 版本徽章 |
| hero-stats（4 项统计） | template hero-section | 7 核心模块 / 3 执行模式 / 20+ 预设模板 / ∞ 可扩展 |
| vision-section | template | "不止于工具，重新定义运维"愿景宣言 + AI-Native 等 tags |
| section-badge（4 个） | 各 section-header | Prompt Engineering / Risk Control / Features / Scenarios 英文小标签 |

**保留**：页面本身、系统架构、提示词工程、风险管控、能力矩阵、业务场景。`Layout.vue` 中「关于」入口不动（页面仍在）。

具体删除点：CSS `.hero-badge`/`.hero-stats`/`.vision-section`/`.section-badge`（含响应式变体）、JS `visionTags` 等关联数据。

### ② 文档治理

| 文件 | 动作 | 说明 |
|------|------|------|
| `技术思路.md` | 删除 | 与 `设计重点与难点.md` 及 CLAUDE.md 高度重复；独有"AIOS 语义抽象层"理念补入 CLAUDE.md |
| `设计重点与难点.md` | 删除 | 同上 |
| `README.md` | 重写 | 修正"权限全自动"（实际为 PTY 权限确认交互）；补智能委托/Echo/告警/移动端功能；更新项目结构（app + aios + agents + desktop + web）；许可证统一 Apache-2.0 |
| `DEPLOY.md` | 重写 | 清除旧项目名 `shannonNEW/` 残留；补充正确部署步骤 |
| `CLAUDE.md` | 更新 | ADR 编号扩至 0001-0007；结构补 `aios/` `agents/` `desktop/`；当前状态更新 |
| `docs/adr/0005-echo-native-agent.md` | 重命名为 `0007-echo-native-agent.md` | 消除 0005 编号冲突（0005 委托决策按时间更早保持原编号；Echo ADR 为最新，顺延为 0007） |
| `CONTEXT.md` | 保留 | 术语表与 CLAUDE.md 互补 |
| `开源代码与组件使用情况说明.md` | 保留 | 开源合规文档 |
| `PRD_智能委托调用.md` | 不处理 | 已被 `.gitignore` 的 `PRD_*.md` 规则排除，不会上传 |

### ③ 代码质量 + 工程配置

- 并行子代理审查 `app/` 与 `web/src`：找出明确 bug、文档/代码不一致，修复
- 核对 `.env.example` 与 `app/settings.py` 的环境变量
- 核对 `requirements.txt` 与实际 import
- 检查 `run.py` / `build.py` 与代码一致性
- 原则：只修明确问题，不做架构重构

### ④ 验证与推送

1. 前端验证：`cd web && npm run build` 通过
2. 后端验证：`python -m compileall app aios agents` 通过
3. 从远程仓库复制 Apache-2.0 `LICENSE` 到本地根目录；README 许可证声明以 LICENSE 文件为准（Apache-2.0）
4. `git init` → 暂存全部（遵循现有 .gitignore）→ 单次提交 → `git remote add origin https://github.com/3CornSoups/Shannon-OS.git` → **force push** `main`（PAT 认证，token 来自用户环境变量 `GITHUB_PERSONAL_ACCESS_TOKEN`）
5. 远程旧文件（含冲突标记的 README、README.zh-CN.md、scripts/）由本地推送自然取代

## 不做的事

- 不重构 `aios/`、`agents/`、`desktop/` 的架构
- 不删除 `web/node_modules`、`.venv` 等（已被 .gitignore 排除，不参与提交）
- 不改动 `data/`、`logs/`、`.env`（敏感/运行时数据，不入库）
- 不修改 `PRD_智能委托调用.md`

## 成功标准

1. 前端构建通过，Showcase 页无装饰残留且样式无破坏
2. 根目录文档无重复、无过时内容（README/DEPLOY/CLAUDE.md 与代码一致）
3. docs/adr/ 编号唯一
4. 远程仓库 main 分支为本地完整新历史，含 Apache-2.0 LICENSE
5. 远程 README 无冲突标记，许可证声明一致
