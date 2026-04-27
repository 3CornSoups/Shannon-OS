<template>
  <Layout>
    <div class="showcase">
      <!-- Hero -->
      <section class="hero-section">
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
      </section>

      <!-- Architecture -->
      <section class="section">
        <div class="section-header">
          <span class="section-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
          </span>
          <h2 class="section-title">系统架构</h2>
        </div>
        <div class="arch-grid">
          <div class="arch-layer" v-for="layer in architecture" :key="layer.name">
            <div class="layer-label" :style="{ background: layer.color }">{{ layer.name }}</div>
            <div class="layer-modules">
              <div class="module-chip" v-for="mod in layer.modules" :key="mod" @click="highlighted = highlighted === mod ? '' : mod" :class="{ active: highlighted === mod }">
                {{ mod }}
              </div>
            </div>
          </div>
        </div>
        <div class="arch-flow">
          <div class="flow-step" v-for="(step, i) in flow" :key="step">
            <div class="flow-dot">{{ i + 1 }}</div>
            <span>{{ step }}</span>
            <svg v-if="i < flow.length - 1" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9,18 15,12 9,6"/></svg>
          </div>
        </div>
      </section>

      <!-- Prompt Showcase -->
      <section class="section">
        <div class="section-header">
          <span class="section-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16,18 22,12 16,6"/><polyline points="8,6 2,12 8,18"/></svg>
          </span>
          <h2 class="section-title">提示词工程</h2>
          <span class="section-badge">Prompt Engineering</span>
        </div>
        <div class="prompt-showcase">
          <div class="prompt-tabs">
            <button v-for="tab in promptTabs" :key="tab.id" :class="['prompt-tab', { active: activePromptTab === tab.id }]" @click="activePromptTab = tab.id">
              {{ tab.label }}
            </button>
          </div>
          <div class="prompt-panel">
            <div class="prompt-meta">
              <span class="meta-tag role">system</span>
              <span class="meta-tag stage">{{ currentPrompt.stage }}</span>
              <span class="meta-tag model">DeepSeek Chat</span>
            </div>
            <div class="prompt-content">
              <pre>{{ currentPrompt.content }}</pre>
            </div>
            <div class="prompt-demo" v-if="currentPrompt.demo">
              <div class="demo-label">LLM 输出示例</div>
              <div class="demo-output">
                <pre>{{ currentPrompt.demo }}</pre>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Risk Control -->
      <section class="section">
        <div class="section-header">
          <span class="section-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          </span>
          <h2 class="section-title">风险管控体系</h2>
          <span class="section-badge">Risk Control</span>
        </div>
        <div class="risk-grid">
          <div class="risk-card" v-for="item in riskItems" :key="item.level">
            <div class="risk-level" :style="{ color: item.color }">{{ item.level }}</div>
            <div class="risk-commands">
              <code v-for="cmd in item.commands" :key="cmd">{{ cmd }}</code>
            </div>
            <div class="risk-desc">{{ item.desc }}</div>
          </div>
          <div class="risk-flow">
            <h3 class="risk-flow-title">执行流程</h3>
            <div class="risk-flow-steps">
              <div class="rf-step" v-for="(step, i) in riskFlow" :key="step">
                <div class="rf-step-num">{{ i + 1 }}</div>
                <div class="rf-step-content">
                  <div class="rf-step-title">{{ step.title }}</div>
                  <div class="rf-step-desc">{{ step.desc }}</div>
                </div>
                <svg v-if="i < riskFlow.length - 1" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" stroke-width="2"><polyline points="9,18 15,12 9,6"/></svg>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Features -->
      <section class="section">
        <div class="section-header">
          <span class="section-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26 12,2"/></svg>
          </span>
          <h2 class="section-title">能力矩阵</h2>
          <span class="section-badge">Features</span>
        </div>
        <div class="features-grid">
          <div class="feature-card" v-for="feat in features" :key="feat.title" @click="toggleFeature(feat.title)" :class="{ expanded: expandedFeature === feat.title }">
            <div class="feature-icon" v-html="feat.icon"></div>
            <div class="feature-info">
              <h3 class="feature-title">{{ feat.title }}</h3>
              <p class="feature-brief">{{ feat.brief }}</p>
              <div class="feature-detail" v-if="expandedFeature === feat.title">
                <p>{{ feat.detail }}</p>
              </div>
            </div>
            <div class="feature-expand">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :class="{ rotated: expandedFeature === feat.title }"><polyline points="6,9 12,15 18,9"/></svg>
            </div>
          </div>
        </div>
      </section>

      <!-- Business Scenarios -->
      <section class="section">
        <div class="section-header">
          <span class="section-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 002 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><polyline points="3.27,6.96 12,12.01 20.73,6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
          </span>
          <h2 class="section-title">业务场景</h2>
          <span class="section-badge">Scenarios</span>
        </div>
        <div class="scenarios-grid">
          <div class="scenario-card" v-for="s in scenarios" :key="s.title">
            <div class="scenario-header">
              <span class="scenario-emoji">{{ s.icon }}</span>
              <h3>{{ s.title }}</h3>
            </div>
            <p class="scenario-desc">{{ s.desc }}</p>
            <ul class="scenario-points">
              <li v-for="p in s.points" :key="p">{{ p }}</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- Vision -->
      <section class="section vision-section">
        <div class="vision-content">
          <h2>不止于工具，重新定义运维</h2>
          <p>Shannon OS Agent 不是一个简单的 SSH 客户端。它是一个将 AI 能力深度注入运维工作流的新一代操作系统人机交互界面。从单机巡检到多集群编排，从被动响应到主动预测，每一行代码都在重新审视"运维"这个古老命题。</p>
          <div class="vision-tags">
            <span v-for="tag in visionTags" :key="tag">{{ tag }}</span>
          </div>
        </div>
      </section>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed } from 'vue'
import Layout from '../components/layout/Layout.vue'

const highlighted = ref('')
const activePromptTab = ref('react')
const expandedFeature = ref('')

const toggleFeature = (title) => {
  expandedFeature.value = expandedFeature.value === title ? '' : title
}

const riskItems = [
  {
    level: 'HIGH',
    color: '#ef4444',
    commands: ['useradd', 'chmod 777', 'dd if=', 'reboot', 'iptables -F', 'yum remove'],
    desc: '需要人工确认后才能执行'
  },
  {
    level: 'LOW',
    color: '#10b981',
    commands: ['cat', 'ls', 'ps aux', 'df -h', 'free -m', 'ping'],
    desc: '自动执行，实时显示结果'
  },
]

const riskFlow = [
  { title: '意图分析', desc: 'LLM 识别用户意图，匹配风险关键词' },
  { title: '风险评级', desc: '根据关键词和命令类型自动判定 LOW / HIGH' },
  { title: '人工确认', desc: '高风险操作进入 agent 模式，等待用户确认' },
  { title: '安全执行', desc: '通过后执行，结果实时回传 LLM 分析' },
  { title: '审计追溯', desc: '所有操作记录入库，支持审计追踪' },
]

const features = [
  {
    title: 'AI 对话式运维',
    brief: '自然语言描述需求，AI 自主完成',
    detail: '告别记忆复杂命令。用中文描述"帮我查一下磁盘空间，找出超过 80% 的分区"，Shannon 自动拆解为 df -h 并分析结果。支持 chat / auto / agent 三种模式，从闲聊到高危操作全覆盖。',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>'
  },
  {
    title: 'ReAct 循环执行',
    brief: '执行→观察→思考→调整，像人类一样工作',
    detail: '传统的 "计划→执行" 模式一旦出错就会功亏一篑。Shannon 采用 ReAct 循环：执行一条命令 → 观察输出 → 让 LLM 分析结果 → 决定下一步。命令失败了？自动诊断原因换一种方式重试。',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23,4 23,10 17,10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>'
  },
  {
    title: '语音输入',
    brief: '解放双手，说出你的运维需求',
    detail: '集成 Web Speech API，点击麦克风直接说话。"检查一下 Nginx 状态"→ 自动转文字 → AI 分析并执行。巡检场景下尤其高效，边喝茶边巡检不是梦。',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>'
  },
  {
    title: '交互式控制台',
    brief: '内置 Web Terminal，随时介入',
    detail: '当 AI 需要人工介入或你想亲自操作时，随时打开内置 Web 终端。支持完整的上/下键历史、Tab 补全、Ctrl+C 中断。AI 和手动操作无缝切换。',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4,17 10,11 4,5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>'
  },
  {
    title: '文件管理系统',
    brief: '可视化浏览服务器文件，一键操作',
    detail: '类 IDE 的文件树面板，支持目录展开/折叠、文件预览、路径导航。结合 AI 上下文理解，当你说"看看 /var/log 下的错误日志"时，AI 自动定位目录并读取关键文件。',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>'
  },
  {
    title: '预设模板库',
    brief: '17 个开箱即用的运维模板',
    detail: '覆盖系统巡检、磁盘检查、Docker 管理、软件安装、安全审计等常见场景。支持 AI 辅助生成模板：描述需求自动生成模板，也支持手动创建和分类管理。一次配置，团队复用。',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14,2 14,8 20,8"/></svg>'
  },
  {
    title: '记忆系统',
    brief: '每轮对话自动持久化，刷新不丢失',
    detail: 'LLM 的每次思考、每条命令的执行结果，都结构化保存到 SQLite。ReAct 循环中旧的工具调用结果会被智能折叠为摘要，确保上下文窗口不被撑爆。刷新页面后，历史消息完整还原，ReAct 执行步骤以卡片形式展现。',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>'
  },
  {
    title: '实时监控大屏',
    brief: 'CPU、内存、磁盘、网络 5 秒刷新',
    detail: 'ECharts 驱动的可视化监控面板，支持 CPU 核心负载、内存趋势、网络流量等多维度图表。数据静默刷新不干扰操作。每个主机独立监控，多机器情况一目了然。',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/></svg>'
  },
]

const scenarios = [
  {
    icon: '🏢',
    title: '多集群服务器管理',
    desc: '政企事业单位普遍存在服务器资源闲置问题——各部门独立采购、独立管理，利用率不到 30%。',
    points: [
      '统一纳管所有服务器，资源池化',
      'AI 自动巡检闲置资源并生成优化建议',
      '跨集群批量执行运维操作',
      '资源利用率从 30% 提升至 70%+'
    ]
  },
  {
    icon: '🔄',
    title: '自动化日常巡检',
    desc: '每天重复的 "ps aux、df -h、free -m" 三部曲，交给 AI 自动完成。',
    points: [
      '定时巡检 + 异常告警',
      '巡检报告自动生成',
      '历史趋势对比分析',
      '从被动救火到主动预防'
    ]
  },
  {
    icon: '🔧',
    title: '标准化软件部署',
    desc: '新机器到手后的环境初始化——装 Nginx、配防火墙、开 SSH，十几台机器逐个操作？',
    points: [
      '通过模板一键批量部署',
      '幂等安装：检查→安装→验证',
      '支持回滚和版本管理',
      '从小时级部署到分钟级完成'
    ]
  },
  {
    icon: '🔒',
    title: '安全审计与合规',
    desc: '等保合规要求记录所有操作、高危操作需审批、定期审计。',
    points: [
      '所有命令执行记录入库',
      '高危操作自动拦截 + 人工确认',
      '审计日志支持追溯查询',
      '操作人、时间、内容全链路可查'
    ]
  },
]

const visionTags = ['AI-Native', 'ReActive Agent', 'Multi-Cluster', 'Zero-Trust Security', 'Conversational DevOps', 'Intelligent Observability']

const architecture = [
  { name: '展示层', color: '#3b82f6', modules: ['Vue 3', 'Pinia', 'Tailwind CSS', 'ECharts', 'SSE'] },
  { name: 'API 层', color: '#8b5cf6', modules: ['FastAPI', 'WebSocket', 'REST', 'SSE Stream'] },
  { name: 'Agent 层', color: '#f59e0b', modules: ['ReAct Loop', 'Tool Calling', 'Conversation Manager', 'Prompt Engine'] },
  { name: '执行引擎', color: '#10b981', modules: ['AsyncSSH', 'Paramiko', 'Executor Router', 'Connection Pool'] },
  { name: '数据层', color: '#ef4444', modules: ['SQLite', 'Event Store', 'Operation Log', 'Audit Trail'] },
]

const flow = ['用户输入', '意图分析', 'Tool Calling', '命令执行', '结果反馈', 'LLM 决策', '任务完成']

const promptTabs = [
  { id: 'react', label: 'ReAct 循环' },
  { id: 'risk', label: '风险管控' },
  { id: 'efficiency', label: '效率规则' },
  { id: 'install', label: '安装模板' },
]

const currentPrompt = computed(() => {
  const prompts = {
    react: {
      stage: 'ReAct Execution',
      content: `当前阶段: ReAct 执行循环
你有三个工具可以使用：
  1. execute_command: 执行 shell 命令
  2. task_done: 任务完成，汇报结果
  3. ask_user: 需要用户帮助

命令执行结果会以用户消息返回：
「## 命令执行结果」
包含返回码、标准输出、错误输出

终止条件：
- 目标已达成 → task_done
- 不可恢复错误 → task_done
- 需要用户介入 → ask_user

规则：
- 每次一条命令，观察结果再决策
- 失败时诊断原因，尝试替代方案
- 禁止相同参数重复重试
- 最多 20 轮迭代`,
      demo: `{
  "action": "run",
  "command": "cat /etc/os-release",
  "purpose": "查看系统版本",
  "reasoning": "先确认操作系统发行版"
}`
    },
    risk: {
      stage: 'Risk Assessment',
      content: `HIGH 风险命令包括：
- 用户管理：useradd, userdel, usermod
- 权限管理：chmod 777, chown
- 系统配置：/etc/passwd, /etc/sudoers
- 服务管理：systemctl stop/start/restart
- 网络安全：iptables, firewalld
- 软件安装：yum/apt install/remove
- 内核驱动：modprobe, rmmod, insmod
- 数据销毁：dd, shred, mkfs
- 重启关机：reboot, shutdown, poweroff

LOW 风险命令：
- 信息查询：ps, top, df, free, uname
- 文件读取：cat, head, tail, grep
- 网络检查：ping, curl, netstat, ss
- 系统信息：uptime, arch, env`,
      demo: `// LLM 自动标记风险等级
{
  "risk_level": "HIGH",
  "reasoning": "检测到 useradd 命令，涉及用户创建，已提升风险等级。"
}`
    },
    efficiency: {
      stage: 'Command Efficiency',
      content: `=== 命令效率规则 ===
合并相关操作为一个命令：
用 && 或 ; 连接多个步骤

示例：安装软件
❌ 错误：分三条命令
  which java
  yum install -y java
  java -version

✅ 正确：合并为一条
  java -version 2>&1 || (yum install -y java-11-openjdk && java -version)

条件检查的正确写法：
✅ java -version 2>&1 || echo 'not found'
❌ java -version || exit 1`,
      demo: `// 效率对比：3条 → 1条
实际发送: "yum install -y nginx && systemctl start nginx && nginx -v"
3步合并为1轮迭代，提速 60%`
    },
    install: {
      stage: 'Installation Templates',
      content: `=== 安装类任务模板 ===
Java 安装（1条命令）：
yum install -y java-11-openjdk wget tar && java -version

Hadoop 安装（3条命令）：
1. 检查 java
2. 下载解压
3. 配置环境变量

Nginx 安装（2条命令）：
1. yum install -y nginx
2. systemctl start nginx && nginx -v

Docker 安装（2条命令）：
1. curl -fsSL get.docker.com | bash
2. systemctl start docker && docker info`,
      demo: `// 完整安装 + 验证 一条搞定
"yum install -y nginx && systemctl enable nginx && systemctl start nginx && nginx -t && curl -I 127.0.0.1"`
    }
  }
  return prompts[activePromptTab.value] || prompts.react
})
</script>
<style scoped>
.showcase {
  max-width: 960px;
  margin: 0 auto;
  padding-bottom: 60px;
}

/* Hero */
.hero-section {
  text-align: center;
  padding: 48px 0 40px;
}
.hero-badge {
  display: inline-block;
  padding: 2px 12px;
  background: var(--primary-light);
  color: var(--primary);
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
  margin-bottom: 16px;
}
.hero-title {
  font-size: 36px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.03em;
  margin: 0 0 8px;
}
.hero-subtitle {
  font-size: 15px;
  color: var(--text-secondary);
  margin: 0 0 32px;
}
.hero-stats {
  display: flex;
  justify-content: center;
  gap: 32px;
}
.stat-item {
  text-align: center;
}
.stat-value {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: var(--primary);
  line-height: 1.2;
}
.stat-label {
  font-size: 11px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Section Common */
.section {
  background: var(--bg-surface);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-lg);
  padding: 28px;
  margin-bottom: 20px;
}
.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}
.section-icon {
  display: flex;
  color: var(--primary);
}
.section-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}
.section-badge {
  font-size: 10px;
  padding: 2px 8px;
  background: var(--bg-hover);
  border-radius: 8px;
  color: var(--text-tertiary);
  letter-spacing: 0.3px;
  text-transform: uppercase;
}

/* Architecture */
.arch-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 24px;
}
.arch-layer {
  display: flex;
  align-items: center;
  gap: 12px;
}
.layer-label {
  min-width: 68px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  text-align: center;
  flex-shrink: 0;
  letter-spacing: 0.3px;
}
.layer-modules {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.module-chip {
  padding: 3px 10px;
  background: var(--bg-hover);
  border-radius: 6px;
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}
.module-chip:hover, .module-chip.active {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-light);
}
.arch-flow {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 16px;
  background: var(--bg-hover);
  border-radius: var(--radius-md);
}
.flow-step {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}
.flow-step svg {
  color: var(--text-tertiary);
  flex-shrink: 0;
}
.flow-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--primary);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* Prompt */
.prompt-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--bg-border-light);
}
.prompt-tab {
  padding: 8px 16px;
  border: none;
  background: transparent;
  font-size: 12px;
  color: var(--text-tertiary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.15s;
}
.prompt-tab:hover { color: var(--text-primary); }
.prompt-tab.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}
.prompt-panel {
  background: #1a1a2e;
  border-radius: var(--radius-md);
  overflow: hidden;
}
.prompt-meta {
  display: flex;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(255,255,255,0.05);
}
.meta-tag {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}
.meta-tag.role { background: #3b82f6; color: #fff; }
.meta-tag.stage { background: #8b5cf6; color: #fff; }
.meta-tag.model { background: transparent; border: 1px solid rgba(255,255,255,0.15); color: #aaa; }
.prompt-content {
  padding: 16px;
}
.prompt-content pre {
  margin: 0;
  font-size: 12px;
  line-height: 1.7;
  color: #e2e8f0;
  font-family: 'SF Mono', Monaco, 'Roboto Mono', monospace;
  white-space: pre-wrap;
}
.prompt-demo {
  border-top: 1px solid rgba(255,255,255,0.08);
}
.demo-label {
  font-size: 10px;
  padding: 8px 16px;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.demo-output {
  padding: 0 16px 16px;
}
.demo-output pre {
  margin: 0;
  font-size: 11px;
  line-height: 1.6;
  color: #10b981;
  font-family: 'SF Mono', Monaco, 'Roboto Mono', monospace;
  white-space: pre-wrap;
}

/* Risk */
.risk-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.risk-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  background: var(--bg-hover);
  border-radius: var(--radius-md);
}
.risk-level {
  font-size: 13px;
  font-weight: 700;
  min-width: 48px;
  padding-top: 1px;
}
.risk-commands {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  flex: 1;
}
.risk-commands code {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--bg-surface);
  border: 1px solid var(--bg-border);
  border-radius: 4px;
  color: var(--text-secondary);
  font-family: 'SF Mono', Monaco, 'Roboto Mono', monospace;
}
.risk-desc {
  font-size: 11px;
  color: var(--text-tertiary);
  min-width: 120px;
  text-align: right;
}
.risk-flow {
  padding: 20px;
  background: var(--bg-hover);
  border-radius: var(--radius-md);
}
.risk-flow-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 16px;
}
.risk-flow-steps {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rf-step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.rf-step svg {
  flex-shrink: 0;
  margin-top: 4px;
}
.rf-step-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--bg-surface);
  border: 1px solid var(--bg-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  flex-shrink: 0;
}
.rf-step-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}
.rf-step-desc {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

/* Features */
.features-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.feature-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--bg-border);
  cursor: pointer;
  transition: all 0.2s;
}
.feature-card:hover {
  border-color: var(--primary);
  box-shadow: var(--shadow-sm);
}
.feature-card.expanded {
  grid-column: 1 / -1;
}
.feature-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.feature-icon :deep(svg) {
  width: 18px;
  height: 18px;
  color: var(--primary);
}
.feature-info {
  flex: 1;
  min-width: 0;
}
.feature-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px;
}
.feature-brief {
  font-size: 11px;
  color: var(--text-tertiary);
  margin: 0;
  line-height: 1.5;
}
.feature-detail {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--bg-border-light);
}
.feature-detail p {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.7;
  margin: 0;
}
.feature-expand {
  flex-shrink: 0;
  color: var(--text-tertiary);
  padding-top: 3px;
}
.feature-expand svg { transition: transform 0.2s; }
.feature-expand svg.rotated { transform: rotate(180deg); }

/* Scenarios */
.scenarios-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.scenario-card {
  padding: 20px;
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  transition: all 0.2s;
}
.scenario-card:hover {
  border-color: var(--primary);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.scenario-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.scenario-emoji {
  font-size: 20px;
}
.scenario-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}
.scenario-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0 0 12px;
}
.scenario-points {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.scenario-points li {
  font-size: 11px;
  color: var(--text-tertiary);
  padding-left: 14px;
  position: relative;
}
.scenario-points li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 6px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--primary);
}

/* Vision */
.vision-section {
  background: linear-gradient(135deg, var(--primary), #7c3aed);
  color: #fff;
  text-align: center;
  border: none;
}
.vision-content h2 {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 16px;
}
.vision-content p {
  font-size: 13px;
  line-height: 1.8;
  opacity: 0.85;
  max-width: 640px;
  margin: 0 auto 20px;
}
.vision-tags {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
}
.vision-tags span {
  padding: 4px 14px;
  background: rgba(255,255,255,0.15);
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
  backdrop-filter: blur(4px);
}

@media (max-width: 768px) {
  .hero-title { font-size: 26px; }
  .hero-stats { gap: 20px; }
  .features-grid { grid-template-columns: 1fr; }
  .scenarios-grid { grid-template-columns: 1fr; }
  .arch-layer { flex-direction: column; align-items: flex-start; }
  .risk-card { flex-direction: column; }
  .risk-desc { text-align: left; }
}
</style>
