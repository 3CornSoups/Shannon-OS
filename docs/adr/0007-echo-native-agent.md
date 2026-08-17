# ADR-0007: 自建 Echo Agent 而非部署 hermes-agent 本体

## 状态

已采纳（2026-08-07）

## 背景

AIOS 需要一个面向日常聊天的"门面"Agent：理解用户提问、管理信息、整理记忆、生成报告——卖点是「比豆包更好的记忆」。候选方案有两个：

1. **部署 NousResearch/hermes-agent**（MIT 开源，自托管 Agent 运行时）：自带五层记忆（短时上下文 / SKILL.md 技能 / 向量检索 / Honcho 用户建模 / FTS5 全文检索）、20+ 平台网关、70+ 工具、自有 Dashboard。是一个完整可用的独立系统。
2. **在 aios/ 层原生自建 Echo Agent**：借鉴 hermes 的记忆设计，但复用 AIOS 现有基础设施（memory_entries、ConversationManager、SSH、agent_registry）。

hermes-agent 与 AIOS 是**同类架构**（都有网关、记忆、ReAct 循环、工具系统），不是能 import 的零件——两者记忆互相独立，部署 hermes 意味着第二个"孤岛 OS"。

## 决策

**不部署 hermes-agent 本体，在 `aios/` 层原生自建 `EchoAgent`**，注册进 agent_registry 与 Server/Code Agent 平级。

关键子决策：

| 子项 | 决策 |
|------|------|
| **范围边界** | Echo 只做对话 + 记忆 + 报告，不执行 SSH/运维命令；与 Dashboard 聊天页并存 |
| **记忆方案** | 短时上下文复用现有 ConversationManager；**自建用户画像**（LLM 增量维护 `user_profile` 条目）；**FTS5 全文检索** Echo 对话原文；**提问档案**记录用户问题。技能文档 + 向量语义检索暂缓 |
| **用户建模** | **不接 Honcho 外部服务**（Plastic Labs SaaS）——数据不出系统、零外部依赖，用现有 DeepSeek LLM 自行推导画像 |
| **运行时** | 检索增强纯聊天：每轮 1 次 LLM 调用，检索层（画像 + memory_entries + FTS5 + 提问档案）注入 system prompt，无 ReAct/工具循环 |
| **模块结构** | `aios/echo/` 自包含包（agent/router/memory/fts/report/prompts），对话记录单独建表，与 `chat_messages` 隔离 |

## 后果

### 正面
- **统一记忆**：Echo 与 Server/Code Agent 共享一套记忆基础设施，未来可由 Dispatcher/`call_agent()` 统一调度，符合 AIOS「多 Agent 编排」愿景（智能眼镜入口 → shannon 组织 → Echo 交互 / Claude 写码）
- **数据不出系统**：不依赖外部 SaaS，隐私可控
- **零锁定**：记忆、画像、报告全部自控，不依赖第三方服务可用性
- **前端可控**：界面独立设计（参考 nanobot 布局），可嵌入现有 Vue 应用

### 负面
- **工程量大**：记忆、检索、报告系统需从零维护，无法白嫖 hermes 的成熟实现
- **功能范围收敛**：放弃 hermes 的平台网关（Telegram/微信等 20+）、技能库、Honcho 推理深度——这些不是本轮目标
- **记忆质量依赖 prompt**：自建画像的推理质量取决于 LLM prompt 设计，弱于 Honcho 专门的 dialectical reasoning 服务

## 备选方案（未采纳）

- **部署 hermes-agent 本体**：快速可用，但记忆/画像与 AIOS 隔离，形成数据孤岛，无法纳入多 Agent 调度；引入 Honcho 外部依赖与数据出境
- **先部署 hermes 后迁移**：过渡期两套记忆并存，迁移成本高，且过早锁死 UI 形态
