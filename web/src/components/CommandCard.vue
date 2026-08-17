<template>
  <div class="command-card" :class="'cmd-state-' + state">
    <div class="cmd-header">
      <span class="cmd-badge" :class="stateBadgeClass">{{ stateLabel }}</span>
      <code class="cmd-text">{{ command }}</code>
      <button v-if="output" class="cmd-toggle-btn" @click="expanded = !expanded">
        <svg
          class="cmd-chevron"
          :class="{ open: expanded }"
          width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"
        >
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </button>
    </div>
    <div v-if="purpose" class="cmd-purpose">{{ purpose }}</div>
    <div v-if="reasoning" class="cmd-reasoning">{{ reasoning }}</div>

    <!-- 输出区域（可折叠） -->
    <div v-if="output" class="cmd-output-wrapper" :class="{ expanded }">
      <pre class="cmd-output"><code>{{ output }}</code></pre>
    </div>

    <!-- 退出码 -->
    <div v-if="exitCode !== undefined && exitCode !== null" class="cmd-exit">
      退出码: <code>{{ exitCode }}</code>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  command: { type: String, default: '' },
  state: { type: String, default: 'done' },  // running | done | error
  purpose: { type: String, default: '' },
  reasoning: { type: String, default: '' },
  output: { type: String, default: '' },
  exitCode: { type: Number, default: undefined },
})

const expanded = ref(false)

const stateLabel = computed(() => {
  switch (props.state) {
    case 'running': return '执行中'
    case 'done': return '完成'
    case 'error': return '失败'
    default: return props.state
  }
})

const stateBadgeClass = computed(() => {
  switch (props.state) {
    case 'running': return 'badge-running'
    case 'done': return 'badge-ok'
    case 'error': return 'badge-fail'
    default: return 'badge-ok'
  }
})
</script>

<style scoped>
.command-card {
  margin: 8px 0;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background: var(--bg-page);
  border: 1px solid var(--bg-border);
  border-left: 3px solid var(--success);
}

.command-card.cmd-state-running {
  border-left-color: var(--info);
}

.command-card.cmd-state-error {
  border-left-color: var(--danger);
}

.cmd-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cmd-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 9999px;
  white-space: nowrap;
  flex-shrink: 0;
}

.badge-running {
  background: var(--info-light);
  color: var(--info);
  animation: pulse 2s ease-in-out infinite;
}

.badge-ok {
  background: var(--success-light);
  color: var(--success);
}

.badge-fail {
  background: var(--danger-light);
  color: var(--danger);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.cmd-text {
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace;
  color: var(--text-primary);
  background: var(--bg-surface);
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cmd-toggle-btn {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  border-radius: var(--radius-sm);
}

.cmd-toggle-btn:hover {
  background: var(--bg-hover);
}

.cmd-chevron {
  transition: transform 0.2s ease;
}

.cmd-chevron.open {
  transform: rotate(180deg);
}

.cmd-purpose {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 4px;
}

.cmd-reasoning {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 2px;
  font-style: italic;
}

.cmd-output-wrapper {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
  margin-top: 0;
}

.cmd-output-wrapper.expanded {
  max-height: 2000px;
  margin-top: 8px;
}

.cmd-output {
  font-size: 11px;
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  margin: 0;
  max-height: 250px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.4;
}

.cmd-output code {
  background: transparent;
  color: inherit;
  font-size: inherit;
}

.cmd-exit {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 4px;
}

.cmd-exit code {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px;
  background: var(--bg-hover);
  padding: 1px 5px;
  border-radius: 3px;
}
</style>
