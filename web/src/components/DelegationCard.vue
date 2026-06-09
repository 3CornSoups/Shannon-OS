<template>
  <div v-if="visible" class="delegation-card" :class="`delegation-${state}`">
    <!-- 委托建议 -->
    <div v-if="state === 'suggested'" class="delegation-suggestion">
      <div class="delegation-header">
        <span class="delegation-icon">&#129504;</span>
        <span class="delegation-title">智能调用建议</span>
      </div>
      <p class="delegation-reason">{{ reason }}</p>
      <p class="delegation-agent">建议委托给 <strong>{{ agent }}</strong> 执行</p>
      <div v-if="riskLevel === 'HIGH'" class="delegation-risk-high">
        &#9888;&#65039; 高风险任务：{{ riskReason || '该操作可能影响系统关键文件' }}
      </div>
      <div class="delegation-actions">
        <button @click="$emit('delegate')" class="delegation-btn delegation-btn-primary">
          &#128640; 委托执行
        </button>
        <button @click="$emit('reject')" class="delegation-btn delegation-btn-outline">
          我方处理
        </button>
      </div>
    </div>

    <!-- 执行进度 -->
    <div v-else-if="state === 'running'" class="delegation-progress">
      <div class="delegation-header">
        <span class="delegation-icon spinning">&#9881;&#65039;</span>
        <span class="delegation-title">委托执行中 - {{ agent }}</span>
        <span class="delegation-timer">{{ elapsedDisplay }}</span>
      </div>
      <div v-if="outputLines.length" class="delegation-output">
        <pre>{{ outputLines.slice(-15).join('\n') }}</pre>
      </div>
      <!-- 权限确认条 -->
      <div v-if="waitingPermission" class="delegation-permission-bar">
        <div class="delegation-permission-icon">&#128274;</div>
        <div class="delegation-permission-body">
          <div class="delegation-permission-label">{{ autoApproved ? '自动同意权限请求' : 'Claude Code 请求权限' }}</div>
          <div class="delegation-permission-prompt">{{ permissionPrompt }}</div>
        </div>
        <div class="delegation-permission-actions">
          <template v-if="autoApproved">
            <span class="delegation-auto-approved">&#10004; 已自动同意</span>
          </template>
          <template v-else>
            <button @click="$emit('respondPermission', permissionId, true)" class="delegation-btn delegation-btn-approve">
              &#10004; 同意
            </button>
            <button @click="$emit('respondPermission', permissionId, false)" class="delegation-btn delegation-btn-deny">
              &#10008; 拒绝
            </button>
          </template>
        </div>
      </div>
      <div class="delegation-actions">
        <button @click="$emit('cancel')" class="delegation-btn delegation-btn-danger">
          &#10060; 取消委托
        </button>
      </div>
    </div>

    <!-- 执行完成 -->
    <div v-else-if="state === 'completed'" class="delegation-result">
      <div class="delegation-header">
        <span class="delegation-icon">{{ goalAchieved === '✅ 达成' ? '&#9989;' : '&#9888;&#65039;' }}</span>
        <span class="delegation-title">委托执行完成</span>
      </div>
      <div class="delegation-summary">
        <div class="delegation-stat">
          <span class="delegation-stat-label">目标达成</span>
          <span class="delegation-stat-value">{{ goalAchieved }}</span>
        </div>
        <div class="delegation-stat">
          <span class="delegation-stat-label">耗时</span>
          <span class="delegation-stat-value">{{ executionTime }}秒</span>
        </div>
        <div class="delegation-stat">
          <span class="delegation-stat-label">变更文件</span>
          <span class="delegation-stat-value">{{ filesChangedCount }}个</span>
        </div>
      </div>
      <div v-if="goalReasoning" class="delegation-reasoning">
        <strong>判断理由:</strong> {{ goalReasoning }}
      </div>
      <div v-if="filesChanged && filesChanged.length" class="delegation-files">
        <strong>变更文件:</strong>
        <ul>
          <li v-for="file in filesChanged.slice(0, 10)" :key="file">{{ file }}</li>
          <li v-if="filesChanged.length > 10">...及其他 {{ filesChanged.length - 10 }} 个文件</li>
        </ul>
      </div>
      <div v-if="riskWarnings && riskWarnings.length" class="delegation-risk-warnings">
        <strong>&#9888;&#65039; 风险警告:</strong>
        <ul>
          <li v-for="w in riskWarnings" :key="w">{{ w }}</li>
        </ul>
      </div>
      <div v-if="outputSummary" class="delegation-output">
        <details>
          <summary>执行摘要</summary>
          <pre>{{ outputSummary }}</pre>
        </details>
      </div>
    </div>

    <!-- 已取消 -->
    <div v-else-if="state === 'cancelled'" class="delegation-cancelled">
      <div class="delegation-header">
        <span class="delegation-icon">&#10060;</span>
        <span class="delegation-title">委托已取消</span>
      </div>
      <p>{{ message || '用户取消了委托执行' }}</p>
    </div>

    <!-- 超时 -->
    <div v-else-if="state === 'timeout'" class="delegation-timeout">
      <div class="delegation-header">
        <span class="delegation-icon">&#9203;</span>
        <span class="delegation-title">委托超时</span>
      </div>
      <p>{{ message || '委托执行超时，已收集部分结果' }}</p>
    </div>

    <!-- 退回 Agent -->
    <div v-else-if="state === 'fallback'" class="delegation-fallback">
      <div class="delegation-header">
        <span class="delegation-icon">&#128260;</span>
        <span class="delegation-title">已退回 Agent 模式</span>
      </div>
      <p>{{ message || '委托未执行，已退回 Agent 模式处理' }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted, computed } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  state: { type: String, default: 'suggested' }, // suggested | running | completed | cancelled | timeout | fallback
  agent: { type: String, default: 'Claude Code' },
  reason: { type: String, default: '' },
  riskLevel: { type: String, default: 'LOW' },
  riskReason: { type: String, default: '' },
  goalAchieved: { type: String, default: '' },
  goalReasoning: { type: String, default: '' },
  executionTime: { type: Number, default: 0 },
  filesChanged: { type: Array, default: () => [] },
  filesChangedCount: { type: Number, default: 0 },
  riskWarnings: { type: Array, default: () => [] },
  outputSummary: { type: String, default: '' },
  outputLines: { type: Array, default: () => [] },
  message: { type: String, default: '' },
  waitingPermission: { type: Boolean, default: false },
  permissionPrompt: { type: String, default: '' },
  permissionId: { type: String, default: '' },
  autoApproved: { type: Boolean, default: false },
})

defineEmits(['delegate', 'reject', 'cancel', 'respondPermission'])

const elapsed = ref(0)
let timer = null

watch(() => props.state, (newVal) => {
  if (newVal === 'running') {
    elapsed.value = 0
    timer = setInterval(() => { elapsed.value++ }, 1000)
  } else {
    if (timer) { clearInterval(timer); timer = null }
  }
}, { immediate: true })

const elapsedDisplay = computed(() => {
  const m = Math.floor(elapsed.value / 60)
  const s = elapsed.value % 60
  return m > 0 ? `${m}分${s}秒` : `${s}秒`
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.delegation-card {
  margin: 12px 0;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #fff;
  overflow: hidden;
}
.delegation-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}
.delegation-icon { font-size: 18px; }
.spinning { animation: spin 2s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.delegation-title { font-weight: 600; font-size: 14px; }
.delegation-timer { margin-left: auto; font-size: 12px; color: #6b7280; }
.delegation-reason, .delegation-agent { padding: 6px 14px; margin: 0; font-size: 13px; color: #374151; }
.delegation-risk-high { margin: 6px 14px; padding: 8px 12px; background: #fef3c7; border-radius: 6px; font-size: 12px; color: #92400e; }
.delegation-actions { display: flex; gap: 8px; padding: 10px 14px; }
.delegation-btn { padding: 6px 16px; border-radius: 6px; border: none; font-size: 13px; cursor: pointer; font-weight: 500; }
.delegation-btn-primary { background: #4f46e5; color: #fff; }
.delegation-btn-primary:hover { background: #4338ca; }
.delegation-btn-outline { background: #fff; color: #374151; border: 1px solid #d1d5db; }
.delegation-btn-outline:hover { background: #f9fafb; }
.delegation-btn-danger { background: #ef4444; color: #fff; }
.delegation-btn-danger:hover { background: #dc2626; }
.delegation-output { margin: 8px 14px; padding: 8px 12px; background: #1e1e1e; border-radius: 6px; }
.delegation-output pre { color: #d4d4d4; font-size: 11px; margin: 0; white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow-y: auto; }
.delegation-summary { display: flex; gap: 16px; padding: 10px 14px; }
.delegation-stat { text-align: center; }
.delegation-stat-label { display: block; font-size: 11px; color: #6b7280; }
.delegation-stat-value { display: block; font-size: 16px; font-weight: 600; color: #111827; }
.delegation-reasoning, .delegation-files, .delegation-risk-warnings { padding: 4px 14px; font-size: 12px; color: #374151; }
.delegation-files ul, .delegation-risk-warnings ul { margin: 4px 0; padding-left: 18px; }
.delegation-cancelled, .delegation-timeout, .delegation-fallback { padding: 10px 14px; font-size: 13px; color: #6b7280; }
.delegation-permission-bar { display: flex; align-items: center; gap: 10px; margin: 8px 14px; padding: 10px 12px; background: #fffbeb; border: 1px solid #fcd34d; border-radius: 8px; }
.delegation-permission-icon { font-size: 20px; flex-shrink: 0; }
.delegation-permission-body { flex: 1; min-width: 0; }
.delegation-permission-label { font-size: 12px; font-weight: 600; color: #92400e; margin-bottom: 2px; }
.delegation-permission-prompt { font-size: 11px; color: #78350f; white-space: pre-wrap; word-break: break-all; max-height: 60px; overflow-y: auto; font-family: monospace; }
.delegation-permission-actions { display: flex; gap: 6px; flex-shrink: 0; }
.delegation-btn-approve { background: #059669; color: #fff; }
.delegation-btn-approve:hover { background: #047857; }
.delegation-btn-deny { background: #dc2626; color: #fff; }
.delegation-btn-deny:hover { background: #b91c1c; }
</style>
