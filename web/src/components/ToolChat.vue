<template>
  <div class="tool-chat">
    <div class="chat-header">
      <button @click="$emit('back')" class="btn btn-icon">&larr; 返回</button>
      <h3>{{ tool.display_name }}</h3>
      <span class="session-status" :class="statusClass">{{ statusText }}</span>
      <button @click="endSession" class="btn btn-outline btn-sm" v-if="!closed">结束会话</button>
    </div>

    <div ref="terminalContainer" class="terminal-container" @click="focusTerminal"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { toolApi } from '../services/api'

const props = defineProps({
  tool: { type: Object, required: true },
  sessionId: { type: String, required: true },
})

const emit = defineEmits(['back', 'closed'])

const terminalContainer = ref(null)
const closed = ref(false)
const statusText = ref('连接中...')
const statusClass = ref('status-connecting')

let ws = null
let term = null
let fitAddon = null

const COLORS = {
  background: '#1e1e1e',
  foreground: '#d4d4d4',
  cursor: '#d4d4d4',
  black: '#1e1e1e',
  red: '#cd3131',
  green: '#0dbc79',
  yellow: '#e5e510',
  blue: '#2472c8',
  magenta: '#bc3fbc',
  cyan: '#11a8cd',
  white: '#e5e5e5',
  brightBlack: '#666666',
  brightRed: '#f14c4c',
  brightGreen: '#23d18b',
  brightYellow: '#f5f543',
  brightBlue: '#3b8eea',
  brightMagenta: '#d670d6',
  brightCyan: '#29b8db',
  brightWhite: '#ffffff',
}

onMounted(() => {
  startTerminal()
})

onUnmounted(() => {
  cleanup()
})

function startTerminal() {
  fitAddon = new FitAddon()
  term = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    fontFamily: "'SF Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace",
    theme: COLORS,
    allowProposedApi: true,
  })
  term.loadAddon(fitAddon)

  term.open(terminalContainer.value)

  // 自适应容器大小
  fitAddon.fit()

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${location.host}/api/tools/sessions/${props.sessionId}/ws`

  ws = new WebSocket(wsUrl)
  ws.binaryType = 'arraybuffer'

  ws.onopen = () => {
    statusText.value = '已连接'
    statusClass.value = 'status-active'
    // 连接成功后自动聚焦终端
    focusTerminal()
  }

  ws.onmessage = (event) => {
    if (event.data instanceof ArrayBuffer) {
      term.write(new Uint8Array(event.data))
    } else if (typeof event.data === 'string') {
      term.write(event.data)
    }
  }

  ws.onclose = (ev) => {
    if (!closed.value) {
      statusText.value = `断开 (${ev.code})`
      statusClass.value = 'status-error'
      closed.value = true
    }
  }

  ws.onerror = () => {
    if (!closed.value) {
      term.write('\r\n\x1b[31m连接失败\x1b[0m\r\n')
    }
  }

  term.onData((data) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(data)
    }
  })

  // 容器大小变化时自动调整终端尺寸
  const ro = new ResizeObserver(() => {
    if (fitAddon) {
      try { fitAddon.fit() } catch (e) { /* ignore */ }
    }
  })
  ro.observe(terminalContainer.value)
}

function focusTerminal() {
  if (term) {
    term.focus()
  }
}

function cleanup() {
  if (ws) { ws.close(); ws = null }
  if (term) { term.dispose(); term = null }
}

async function endSession() {
  try {
    await toolApi.closeSession(props.sessionId)
  } catch (e) { /* ignore */ }
  cleanup()
  closed.value = true
  statusText.value = '已结束'
  statusClass.value = 'status-closed'
  emit('closed')
}
</script>

<style scoped>
.tool-chat {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}
.chat-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}
.chat-header h3 { margin: 0; font-size: 15px; flex: 1; }
.session-status { font-size: 11px; padding: 2px 8px; border-radius: 10px; }
.status-connecting { background: #fef3c7; color: #92400e; }
.status-active { background: #d1fae5; color: #065f46; }
.status-closed { background: #e5e7eb; color: #6b7280; }
.status-error { background: #fee2e2; color: #991b1b; }

.terminal-container {
  flex: 1;
  overflow: hidden;
  background: #1e1e1e;
}
.terminal-container :deep(.xterm) {
  height: 100%;
}
.terminal-container :deep(.xterm-viewport) {
  scrollbar-width: thin;
  scrollbar-color: #555 #1e1e1e;
}

.btn-icon { background: none; border: none; cursor: pointer; font-size: 16px; color: #6b7280; }
.btn-icon:hover { color: #111827; }
.btn-sm { font-size: 12px; padding: 4px 10px; }
</style>
