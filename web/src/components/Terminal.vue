<template>
  <div v-if="showTerminal" class="terminal-panel" :class="{ collapsed: isCollapsed && !isMobile, 'mobile-fullscreen': isFullscreenMobile }" :style="{ height: isCollapsed && !isMobile ? 'auto' : panelHeight + 'px' }">
    <!-- Resize Handle（移动端隐藏：触摸不可拖拽） -->
    <div v-if="!isCollapsed && !isMobile" class="resize-handle" @mousedown="startResize">
      <div class="resize-grip">
        <span></span><span></span><span></span>
      </div>
    </div>

    <!-- Terminal Header -->
    <div class="terminal-header">
      <div class="terminal-header-left">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="4,17 10,11 4,5"/>
          <line x1="12" y1="19" x2="20" y2="19"/>
        </svg>
        <span class="terminal-title">终端控制台</span>
        <span v-if="connectedServer" class="terminal-server">({{ connectedServer.name }})</span>
        <span v-else class="terminal-server">（未连接服务器）</span>
        <span class="log-count">{{ logEntries.length }} 条日志</span>
      </div>
      <div class="terminal-header-right">
        <button v-if="isMobile" class="terminal-btn" @click="terminalStore.closeMobile()" title="关闭">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          关闭
        </button>
        <button class="terminal-btn" @click="clearLogs" title="清空日志">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3,6 5,6 21,6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
          清空
        </button>
        <button v-if="!isMobile" class="terminal-btn" @click="toggleCollapse" :title="isCollapsed ? '展开' : '折叠'">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" :class="{ 'rotate-180': !isCollapsed }">
            <polyline points="18,15 12,9 6,15"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Terminal Body -->
    <div v-if="showBody" class="terminal-body">
      <!-- Log Area -->
      <div ref="logAreaRef" class="terminal-log">
        <div v-if="logEntries.length === 0" class="terminal-empty">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="opacity:0.3">
            <polyline points="4,17 10,11 4,5"/>
            <line x1="12" y1="19" x2="20" y2="19"/>
          </svg>
          <p>暂无日志。使用下方输入框执行命令，或在与AI对话后查看命令执行日志。</p>
        </div>
        <div v-for="(entry, idx) in logEntries" :key="idx" class="log-entry" :class="'type-' + entry.type">
          <div class="log-line log-meta">
            <span class="log-time">{{ formatTime(entry.timestamp) }}</span>
            <span class="log-type-badge" :class="'badge-' + entry.type">{{ entry.typeLabel }}</span>
          </div>
          <div v-if="entry.command" class="log-line log-command">
            <span class="prompt-sign">$</span>
            <span class="command-text">{{ entry.command }}</span>
          </div>
          <div v-if="entry.stdout" class="log-line log-stdout">
            <pre>{{ entry.stdout }}</pre>
          </div>
          <div v-if="entry.stderr" class="log-line log-stderr">
            <pre>{{ entry.stderr }}</pre>
          </div>
          <div v-if="entry.message && !entry.command" class="log-line log-message">
            {{ entry.message }}
          </div>
          <div v-if="entry.returncode !== undefined && entry.returncode !== null" class="log-line log-returncode">
            <span>Exit code: {{ entry.returncode }}</span>
          </div>
          <div v-if="entry.type === 'output' && entry.output" class="log-line log-stdout">
            <pre>{{ entry.output }}</pre>
          </div>
        </div>
        <div v-if="executing" class="log-entry type-running">
          <div class="log-line log-message">
            <span class="loading-spinner-small"></span>
            正在执行命令...
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="terminal-input-area">
        <div class="terminal-input-line">
          <span class="prompt-sign">$</span>
          <input
            ref="inputRef"
            v-model="currentCommand"
            type="text"
            class="terminal-input"
            placeholder="输入命令并按回车执行..."
            @keydown.enter="executeCommand"
            :disabled="executing || !connectedServer"
          />
          <button
            class="terminal-send-btn"
            @click="executeCommand"
            :disabled="executing || !currentCommand.trim() || !connectedServer"
            title="发送命令 (Enter)"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22,2 15,22 11,13 2,9"/>
            </svg>
          </button>
        </div>
        <div class="terminal-hint">
          <span v-if="!connectedServer" class="hint-warning">⚠ 请先在服务器管理页面选择服务器</span>
          <span v-else>Enter 执行命令 · 支持所有 Linux 命令</span>
        </div>
      </div>
    </div>

    <!-- Collapsed Toggle Bar -->
    <div v-else class="terminal-collapsed-bar" @click="toggleCollapse">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="6,9 12,15 18,9"/>
      </svg>
      <span>终端</span>
      <span v-if="logEntries.length > 0" class="collapsed-badge">{{ logEntries.length }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useServerStore } from '../stores/server'
import { terminalApi } from '../services/api'
import { useTerminalStore } from '../stores/terminal'
import { useIsMobile } from '../composables/useIsMobile'

const terminalStore = useTerminalStore()
const serverStore = useServerStore()
const { isMobile } = useIsMobile()

const logAreaRef = ref(null)
const inputRef = ref(null)
const currentCommand = ref('')
const isCollapsed = ref(true)
const executing = ref(false)
const panelHeight = ref(260)

// 移动端：由 terminalStore.mobileOpen 控制全屏显隐（桌面端保持停靠面板逻辑）
const showTerminal = computed(() => !isMobile.value || terminalStore.mobileOpen)
const showBody = computed(() => !isCollapsed.value || (isMobile.value && terminalStore.mobileOpen))
const isFullscreenMobile = computed(() => isMobile.value && terminalStore.mobileOpen)

const logEntries = computed(() => terminalStore.logEntries)
const connectedServer = computed(() => serverStore.currentServer)

const MIN_HEIGHT = 120
const MAX_HEIGHT = 600
let isResizing = false
let startY = 0
let startHeight = 0

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
  if (!isCollapsed.value) {
    nextTick(() => {
      inputRef.value?.focus()
    })
  }
}

function clearLogs() {
  terminalStore.clearLogs()
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function scrollToBottom() {
  nextTick(() => {
    if (logAreaRef.value) {
      logAreaRef.value.scrollTop = logAreaRef.value.scrollHeight
    }
  })
}

watch(logEntries, () => {
  scrollToBottom()
})

async function executeCommand() {
  const cmd = currentCommand.value.trim()
  if (!cmd || !connectedServer.value || executing.value) return

  currentCommand.value = ''
  executing.value = true

  terminalStore.addEntry({
    type: 'command',
    typeLabel: '命令',
    command: cmd,
    timestamp: Date.now()
  })

  try {
    const server = connectedServer.value
    const response = await terminalApi.execCommand({
      host_id: server.id,
      host: server.host,
      port: server.port || 22,
      username: server.username,
      password: server.last_pwd || '',
      private_key: '',
      command: cmd
    })

    terminalStore.addEntry({
      type: 'result',
      typeLabel: '输出',
      command: cmd,
      stdout: response.data.stdout || '',
      stderr: response.data.stderr || '',
      returncode: response.data.returncode,
      timestamp: Date.now()
    })
  } catch (error) {
    const errMsg = error.response?.data?.message || error.message || '执行失败'
    terminalStore.addEntry({
      type: 'error',
      typeLabel: '错误',
      command: cmd,
      stderr: errMsg,
      timestamp: Date.now()
    })
  } finally {
    executing.value = false
    inputRef.value?.focus()
  }
}

function startResize(e) {
  e.preventDefault()
  isResizing = true
  startY = e.clientY
  startHeight = panelHeight.value
  document.body.style.cursor = 'row-resize'
  document.body.style.userSelect = 'none'

  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
}

function onResize(e) {
  if (!isResizing) return
  const delta = startY - e.clientY
  let newHeight = startHeight + delta
  newHeight = Math.max(MIN_HEIGHT, Math.min(MAX_HEIGHT, newHeight))
  panelHeight.value = newHeight
}

function stopResize() {
  isResizing = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
}

onMounted(() => {
  if (!isCollapsed.value) {
    inputRef.value?.focus()
  }
})

onUnmounted(() => {
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
})
</script>

<style scoped>
.terminal-panel {
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--bg-border);
  background: var(--bg-surface);
  min-height: 36px;
  position: relative;
}

.terminal-panel.collapsed {
  max-height: 36px;
}

/* Resize Handle */
.resize-handle {
  position: absolute;
  top: -4px;
  left: 0;
  right: 0;
  height: 8px;
  cursor: row-resize;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
}

.resize-handle:hover .resize-grip,
.resize-handle:active .resize-grip {
  background: var(--primary);
  border-color: var(--primary);
}

.resize-grip {
  display: flex;
  gap: 3px;
  padding: 2px 8px;
  border-radius: 3px;
  background: var(--bg-border);
  border: 1px solid var(--bg-border-light);
  transition: all var(--transition-fast);
}

.resize-grip span {
  display: block;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--text-tertiary);
}

.resize-handle:hover .resize-grip span,
.resize-handle:active .resize-grip span {
  background: white;
}

/* Header */
.terminal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--bg-border-light);
  min-height: 36px;
  flex-shrink: 0;
}

.terminal-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
}

.terminal-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.terminal-server {
  font-size: 11px;
  color: var(--primary);
  font-weight: 500;
}

.log-count {
  font-size: 10px;
  color: var(--text-tertiary);
  background: var(--bg-hover);
  padding: 1px 6px;
  border-radius: 9999px;
}

.terminal-header-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.terminal-btn {
  height: 24px;
  padding: 0 8px;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  transition: all var(--transition-fast);
}

.terminal-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.terminal-btn svg.rotate-180 {
  transform: rotate(180deg);
}

/* Body */
.terminal-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.terminal-log {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  min-height: 80px;
}

.terminal-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 120px;
  color: var(--text-tertiary);
  gap: 8px;
}

.terminal-empty p {
  font-size: 12px;
  text-align: center;
}

/* Log Entries */
.log-entry {
  margin-bottom: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--bg-border-light);
}

.log-entry:last-child {
  border-bottom: none;
}

.log-line {
  display: flex;
  align-items: flex-start;
  gap: 4px;
}

.log-meta {
  gap: 8px;
  margin-bottom: 2px;
}

.log-time {
  color: var(--text-tertiary);
  font-size: 10px;
  flex-shrink: 0;
}

.log-type-badge {
  font-size: 10px;
  font-weight: 500;
  padding: 0px 6px;
  border-radius: 3px;
  flex-shrink: 0;
}

.badge-command { background: var(--info-light); color: var(--info); }
.badge-result { background: var(--success-light); color: var(--success); }
.badge-error { background: var(--danger-light); color: var(--danger); }
.badge-event { background: var(--warning-light); color: var(--warning); }
.badge-info { background: var(--bg-hover); color: var(--text-secondary); }

.prompt-sign {
  color: var(--success);
  font-weight: 600;
  flex-shrink: 0;
  margin-right: 4px;
}

.log-command .command-text {
  color: var(--text-primary);
  font-weight: 500;
}

.log-stdout pre {
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  padding: 4px 0 4px 20px;
  font-size: 11px;
}

.log-stderr pre {
  color: var(--danger);
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  padding: 4px 0 4px 20px;
  font-size: 11px;
}

.log-message {
  color: var(--text-secondary);
  padding-left: 0;
}

.log-returncode {
  color: var(--text-tertiary);
  font-size: 11px;
  padding-left: 20px;
}

.loading-spinner-small {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid var(--bg-border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 6px;
  vertical-align: middle;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Input Area */
.terminal-input-area {
  padding: 8px 12px;
  border-top: 1px solid var(--bg-border-light);
  background: var(--bg-surface);
  flex-shrink: 0;
}

.terminal-input-line {
  display: flex;
  align-items: center;
  gap: 4px;
}

.terminal-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: var(--text-primary);
  font-family: 'SF Mono', 'Fira Code', 'Consolas', 'Courier New', monospace;
  font-size: 13px;
  padding: 6px 8px;
}

.terminal-input::placeholder {
  color: var(--text-tertiary);
}

.terminal-input:disabled {
  color: var(--text-tertiary);
  cursor: not-allowed;
}

.terminal-send-btn {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  border: none;
  background: var(--primary);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.terminal-send-btn:hover:not(:disabled) {
  background: #3B57DF;
}

.terminal-send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.terminal-hint {
  margin-top: 4px;
  font-size: 10px;
  color: var(--text-tertiary);
}

.hint-warning {
  color: var(--warning);
}

/* Collapsed Bar */
.terminal-collapsed-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 36px;
  cursor: pointer;
  color: var(--text-tertiary);
  font-size: 12px;
  transition: all var(--transition-fast);
}

.terminal-collapsed-bar:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.collapsed-badge {
  font-size: 10px;
  background: var(--primary);
  color: white;
  padding: 0px 6px;
  border-radius: 9999px;
  font-weight: 600;
}

/* ── 移动端：终端全屏浮层 ── */
@media (max-width: 768px) {
  .terminal-panel.mobile-fullscreen {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 80;
    height: 100dvh !important; /* 覆盖内联 panelHeight */
    border-top: none;
  }

  .terminal-panel.mobile-fullscreen .terminal-body {
    flex: 1;
    min-height: 0;
  }

  .terminal-panel.mobile-fullscreen .terminal-log {
    flex: 1;
  }

  .terminal-input {
    font-size: 16px; /* 防 iOS 聚焦缩放 */
  }
}
</style>
