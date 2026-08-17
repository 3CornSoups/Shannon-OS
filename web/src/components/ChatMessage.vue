<template>
  <div class="message-row" :class="message.role === 'user' ? 'message-user' : 'message-assistant'">
    <div class="message-bubble" :class="message.role === 'user' ? 'bubble-user' : 'bubble-assistant'">
      <!-- 消息头部 -->
      <div class="message-header">
        <div class="avatar" :class="message.role === 'user' ? 'avatar-user' : 'avatar-assistant'">
          <svg v-if="message.role === 'user'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="11" width="18" height="10" rx="2"/>
            <circle cx="12" cy="5" r="2"/>
            <path d="M12 7v4"/>
            <line x1="8" y1="16" x2="8" y2="16"/>
            <line x1="16" y1="16" x2="16" y2="16"/>
          </svg>
        </div>
        <span class="message-sender">{{ message.role === 'user' ? '你' : 'Shannon' }}</span>
      </div>

      <!-- ── Blocks 渲染区 ── -->
      <template v-if="blocks.length > 0">
        <!-- thinking 始终在最前面（独立折叠面板） -->
        <template v-for="(block, i) in blocks" :key="'t'+i">
          <ThinkingPanel
            v-if="block.type === 'thinking'"
            :content="block.content"
            :auto-expand="isStreaming"
          />
        </template>

        <!-- 过程折叠按钮（plan / command / react） -->
        <div v-if="processBlocks.length > 0" class="process-section">
          <button class="process-toggle" @click="processExpanded = !processExpanded">
            <svg
              class="process-chevron"
              :class="{ open: processExpanded }"
              width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"
            >
              <polyline points="6 9 12 15 18 9"/>
            </svg>
            <span class="process-toggle-label">
              {{ processExpanded ? '折叠执行过程' : '展开执行过程' }}
            </span>
            <span class="process-toggle-count">{{ processBlocks.length }} 步</span>
          </button>

          <!-- 折叠内容区 -->
          <div class="process-content" :class="{ expanded: processExpanded }">
            <template v-for="(block, i) in blocks" :key="'p'+i">
              <!-- plan: 执行计划卡片 -->
              <div v-if="block.type === 'plan'" class="plan-section">
                <div class="plan-header">
                  <h4 class="plan-title">执行计划</h4>
                  <span class="risk-badge" :class="block.risk === 'HIGH' ? 'risk-high' : 'risk-low'">
                    {{ block.risk || 'LOW' }}
                  </span>
                </div>
                <div v-if="block.reasoning" class="plan-reasoning">{{ block.reasoning }}</div>
                <div v-if="block.commands && block.commands.length" class="commands-section">
                  <h5 class="commands-title">执行命令</h5>
                  <div class="commands-list">
                    <div v-for="(cmd, ci) in block.commands" :key="ci" class="command-item">
                      <div class="command-purpose">{{ cmd.purpose || '执行命令' }}</div>
                      <pre class="command-code">{{ cmd.command }}</pre>
                    </div>
                  </div>
                </div>
              </div>

              <!-- command: 命令执行卡片 -->
              <CommandCard
                v-else-if="block.type === 'command'"
                :command="block.command"
                :state="block.state"
                :purpose="block.purpose"
                :reasoning="block.reasoning"
                :output="block.output"
                :exit-code="block.exitCode"
              />

              <!-- react: ReAct 步骤 -->
              <div v-else-if="block.type === 'react'" class="react-step" :class="block.action === 'ask' ? 'react-action-step' : 'react-result-step'">
                <div class="step-header">
                  <span class="step-badge" :class="block.action === 'ask' ? 'step-run' : 'step-ok'">
                    {{ block.action === 'ask' ? '询问' : block.action === 'done' ? '完成' : '执行' }}
                  </span>
                  <span v-if="block.reasoning" class="step-reasoning">{{ block.reasoning }}</span>
                </div>
                <div v-if="block.command" class="step-command">
                  <pre class="command-code">{{ block.command }}</pre>
                  <span v-if="block.purpose" class="step-purpose">{{ block.purpose }}</span>
                </div>
                <div v-if="block.message" class="step-message">{{ block.message }}</div>
              </div>
            </template>
          </div>
        </div>
      </template>

      <!-- 正文（markdown 渲染）— blocks 渲染完后显示最终文字 -->
      <div v-if="message.content && !hasDelegation" class="message-content" v-html="renderedContent"></div>

      <!-- ── 兼容：老格式 plan（无 blocks 时有 meta.plan 渲染）── -->
      <div v-if="blocks.length === 0 && message.meta?.plan && !message.meta?._delegationActive" class="plan-section">
        <div class="plan-header">
          <h4 class="plan-title">执行计划</h4>
          <span class="risk-badge" :class="message.meta.plan.risk_level === 'HIGH' ? 'risk-high' : 'risk-low'">
            {{ message.meta.plan.risk_level }}
          </span>
        </div>
        <div class="plan-reasoning">{{ message.meta.plan.reasoning || '' }}</div>
        <div v-if="message.meta.plan.commands_plan?.length" class="commands-section">
          <h5 class="commands-title">执行命令</h5>
          <div class="commands-list">
            <div v-for="(cmd, ci) in message.meta.plan.commands_plan" :key="ci" class="command-item">
              <div class="command-purpose">{{ cmd.purpose || '执行命令' }}</div>
              <pre class="command-code">{{ cmd.command }}</pre>
            </div>
          </div>
        </div>
      </div>

      <!-- ── 兼容：老格式 react_action / react_result（无 blocks 时直接渲染）── -->
      <div v-if="blocks.length === 0 && message.meta?.type === 'react_action'" class="react-step react-action-step">
        <div class="step-header">
          <span class="step-badge step-run">{{ message.meta.action === 'done' ? '完成' : message.meta.action === 'ask' ? '询问' : '执行' }}</span>
          <span v-if="message.meta.reasoning" class="step-reasoning">{{ message.meta.reasoning }}</span>
        </div>
        <div v-if="message.meta.command" class="step-command">
          <pre class="command-code">{{ message.meta.command }}</pre>
          <span v-if="message.meta.purpose" class="step-purpose">{{ message.meta.purpose }}</span>
        </div>
        <div v-if="message.meta.message" class="step-message">{{ message.meta.message }}</div>
      </div>

      <div v-if="blocks.length === 0 && message.meta?.type === 'react_result'" class="react-step react-result-step">
        <div class="step-header">
          <span class="step-badge" :class="message.meta.returncode === 0 ? 'step-ok' : 'step-fail'">
            {{ message.meta.returncode === 0 ? '成功' : '失败' }}
          </span>
          <span class="step-returncode">返回码: {{ message.meta.returncode }}</span>
        </div>
        <div v-if="message.meta.stdout" class="step-output">
          <div class="step-output-label">标准输出</div>
          <pre class="step-output-text">{{ message.meta.stdout }}</pre>
        </div>
        <div v-if="message.meta.stderr" class="step-output">
          <div class="step-output-label step-output-label-error">错误输出</div>
          <pre class="step-output-text step-output-text-error">{{ message.meta.stderr }}</pre>
        </div>
      </div>

      <!-- 确认执行按钮 -->
      <div v-if="message.meta?.pendingConfirmation" class="confirmation-section">
        <div class="confirmation-actions">
          <button @click="$emit('cancel-execution', message.meta.plan?.task_id)" class="btn btn-outline btn-sm">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            取消
          </button>
          <button
            v-if="message.meta.plan?.risk_level === 'HIGH'"
            @click="$emit('confirm-execution', message.meta.plan?.task_id, true)"
            class="btn btn-sm btn-danger"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            确认执行（高风险）
          </button>
          <button v-else @click="$emit('confirm-execution', message.meta.plan?.task_id, true)" class="btn btn-primary btn-sm">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20,6 9,17 4,12"/></svg>
            确认执行
          </button>
        </div>
      </div>

      <!-- 委托卡片：流式时用 delegationState prop，历史加载时用 delegation block -->
      <DelegationCard
        v-if="hasDelegation"
        :visible="delegationData.visible"
        :state="delegationData.state"
        :agent="delegationData.agent"
        :reason="delegationData.reason"
        :risk-level="delegationData.riskLevel"
        :goal-achieved="delegationData.goalAchieved"
        :goal-reasoning="delegationData.goalReasoning"
        :execution-time="delegationData.executionTime"
        :files-changed="delegationData.filesChanged"
        :files-changed-count="delegationData.filesChangedCount"
        :risk-warnings="delegationData.riskWarnings"
        :output-summary="delegationData.outputSummary"
        :output-lines="delegationData.outputLines"
        :message="delegationData.message"
        :waiting-permission="delegationData.waitingPermission"
        :permission-prompt="delegationData.permissionPrompt"
        :permission-id="delegationData.permissionId"
        :auto-approved="delegationData.autoApproved"
        @delegate="$emit('delegate', delegationState.currentTaskId)"
        @reject="$emit('reject-delegation', delegationState.currentTaskId)"
        @cancel="$emit('cancel-delegation', delegationState.currentTaskId)"
        @respond-permission="(pid, approved) => $emit('respond-permission', pid, approved)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { renderMarkdown } from '../composables/markdown.js'
import { normalizeBlocks, getDelegationBlock } from '../composables/blocks.js'
import ThinkingPanel from './ThinkingPanel.vue'
import CommandCard from './CommandCard.vue'
import DelegationCard from './DelegationCard.vue'

const props = defineProps({
  message: { type: Object, required: true },
  delegationState: { type: Object, default: () => ({}) },
  isStreaming: { type: Boolean, default: false },
})

defineEmits([
  'confirm-execution',
  'cancel-execution',
  'delegate',
  'reject-delegation',
  'cancel-delegation',
  'respond-permission',
])

const blocks = computed(() => normalizeBlocks(props.message))

// 过程块（plan、command、react）— 不包括 thinking（有独立折叠面板）
const processBlocks = computed(() => blocks.value.filter(b =>
  b.type === 'plan' || b.type === 'command' || b.type === 'react'
))

// 执行过程折叠：流式时默认展开，完成后默认折叠
const processExpanded = ref(props.isStreaming)

watch(() => props.isStreaming, (val) => {
  if (val) {
    processExpanded.value = true
  } else if (processBlocks.value.length > 0) {
    // 流式结束时，短暂保持展开后折叠
    setTimeout(() => { processExpanded.value = false }, 800)
  }
})

// 过程中有新 block 追加时，保持展开
watch(() => blocks.value.length, (newLen, oldLen) => {
  if (props.isStreaming && newLen > oldLen) {
    processExpanded.value = true
  }
})

// 委托数据：优先从 delegation block（历史兼容），fallback delegationState prop（流式实时）
const delegationBlock = computed(() => getDelegationBlock(props.message))
const hasDelegation = computed(() => {
  return !!(props.message.meta?._delegationActive || delegationBlock.value)
})
const delegationData = computed(() => {
  const block = delegationBlock.value
  const ds = props.delegationState || {}
  // 历史加载：从 block 取数据
  if (block && !props.message.meta?._delegationActive) {
    return {
      visible: true,
      state: block.state || 'completed',
      agent: block.agent || 'Claude Code',
      reason: block.reason || '',
      riskLevel: block.riskLevel || 'LOW',
      goalAchieved: block.goalAchieved || '',
      goalReasoning: block.goalReasoning || '',
      executionTime: block.executionTime || 0,
      filesChanged: block.filesChanged || [],
      filesChangedCount: block.filesChangedCount || 0,
      riskWarnings: block.riskWarnings || [],
      outputSummary: block.outputSummary || '',
      outputLines: block.outputLines || [],
      message: block.message || '',
      waitingPermission: false,
      permissionPrompt: '',
      permissionId: '',
      autoApproved: false,
    }
  }
  // 流式过程：从 delegationState prop 取数据
  return {
    visible: ds.visible || false,
    state: ds.state || 'suggested',
    agent: ds.agent || 'Claude Code',
    reason: ds.reason || '',
    riskLevel: ds.riskLevel || 'LOW',
    goalAchieved: ds.goalAchieved || '',
    goalReasoning: ds.goalReasoning || '',
    executionTime: ds.executionTime || 0,
    filesChanged: ds.filesChanged || [],
    filesChangedCount: ds.filesChangedCount || 0,
    riskWarnings: ds.riskWarnings || [],
    outputSummary: ds.outputSummary || '',
    outputLines: ds.outputLines || [],
    message: ds.message || '',
    waitingPermission: ds.waitingPermission || false,
    permissionPrompt: ds.permissionPrompt || '',
    permissionId: ds.permissionId || '',
    autoApproved: ds.autoApproved || false,
  }
})

const renderedContent = computed(() => {
  const text = props.message.content
  if (!text || (text.startsWith('_') && text.endsWith('_') && text.length < 20)) return ''
  return renderMarkdown(text)
})
</script>

<style scoped>
/* ── 执行过程折叠 ── */
.process-section {
  margin: 6px 0;
}

.process-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 5px 10px;
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  background: var(--bg-page);
  cursor: pointer;
  font-size: 12px;
  color: var(--text-secondary);
  transition: background var(--transition-fast);
  user-select: none;
}

.process-toggle:hover {
  background: var(--bg-hover);
}

.process-chevron {
  flex-shrink: 0;
  transition: transform 0.2s ease;
  color: var(--text-tertiary);
}

.process-chevron.open {
  transform: rotate(90deg);
}

.process-toggle-label {
  font-weight: 500;
}

.process-toggle-count {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-tertiary);
  background: var(--bg-surface);
  padding: 1px 6px;
  border-radius: 10px;
}

.process-content {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.35s ease;
}

.process-content.expanded {
  max-height: 5000px;
}
</style>
