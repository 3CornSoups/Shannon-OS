<template>
  <Layout>
  <div class="echo-page">
    <!-- 移动端遮罩 -->
    <div v-if="isMobile && drawerOpen" class="echo-backdrop" @click="drawerOpen = false"></div>

    <!-- 左侧：会话列表（移动端为滑出抽屉） -->
    <aside class="echo-sidebar" :class="{ 'open': drawerOpen }">
      <div class="echo-sidebar-header">
        <span class="echo-logo">◇</span>
        <span class="echo-title">助手</span>
        <button class="icon-btn" title="新建对话" @click="newConversation">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        </button>
      </div>
      <div class="echo-list">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="echo-conv-item"
          :class="{ active: conv.id === currentConvId }"
          @click="selectConversation(conv)"
        >
          <div class="echo-conv-title">{{ conv.title || '新对话' }}</div>
          <div class="echo-conv-meta">
            <span class="echo-conv-preview">{{ conv.last_message || '还没有消息' }}</span>
            <span class="echo-conv-time">{{ fmtTime(conv.updated_at) }}</span>
          </div>
        </div>
        <div v-if="!conversations.length" class="echo-empty-list">还没有会话，点右上角「+」开始</div>
      </div>
      <div class="echo-sidebar-footer">
        <router-link to="/echo/reports" class="echo-reports-link" @click="closeDrawerMobile">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14,2 14,8 20,8"/></svg>
          报告库
        </router-link>
      </div>
    </aside>

    <!-- 右侧：聊天线程 -->
    <div class="echo-thread">
      <header class="echo-thread-header">
        <button v-if="isMobile" class="icon-btn echo-menu-btn" title="会话列表" @click="drawerOpen = true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>
        <div class="echo-thread-title">{{ currentTitle }}</div>
        <div class="echo-thread-actions">
          <TerminalButton v-if="isMobile" />
          <NotificationBell v-if="isMobile" />
          <button v-if="currentConvId" class="icon-btn" title="删除会话" @click="deleteConversation">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3,6 5,6 21,6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          </button>
        </div>
      </header>

      <div ref="msgScroll" class="echo-messages">
        <template v-if="messages.length">
          <div v-for="msg in messages" :key="msg.key" class="echo-msg" :class="msg.role">
            <div class="echo-msg-avatar">{{ msg.role === 'user' ? '我' : '◇' }}</div>
            <div v-if="msg.role === 'assistant'" class="echo-msg-bubble md" v-html="renderMarkdown(msg.content)"></div>
            <div v-else class="echo-msg-bubble">{{ msg.content }}</div>
          </div>
        </template>
        <div v-else class="echo-empty-thread">
          <div class="echo-empty-logo">◇</div>
          <p>我是「助手」，你的管理助手。</p>
        </div>
      </div>

      <footer class="echo-composer">
        <textarea
          ref="inputRef"
          v-model="input"
          class="echo-input"
          rows="1"
          :placeholder="isMobile ? '和助手聊聊…' : '和助手聊聊…（Enter 发送 / Shift+Enter 换行）'"
          :disabled="isStreaming"
          @keydown.enter.exact.prevent="send"
        ></textarea>
        <button class="echo-send-btn" :disabled="isStreaming || !input.trim()" @click="send">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22,2 15,22 11,13 2,9 22,2"/></svg>
        </button>
      </footer>
    </div>
  </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import Layout from '../components/layout/Layout.vue'
import { echoApi } from '../services/api'
import { renderMarkdown } from '../composables/markdown'
import { useIsMobile } from '../composables/useIsMobile'
import NotificationBell from '../components/NotificationBell.vue'
import TerminalButton from '../components/TerminalButton.vue'

const conversations = ref([])
const currentConvId = ref(null)
const messages = ref([])
const input = ref('')
const isStreaming = ref(false)
const msgScroll = ref(null)
const inputRef = ref(null)
const currentSSE = ref(null)
let msgKey = 0

// 移动端：会话列表 → 左侧滑出抽屉
const { isMobile } = useIsMobile()
const drawerOpen = ref(false)

function closeDrawerMobile() {
  if (isMobile.value) drawerOpen.value = false
}

const currentTitle = computed(() => {
  const c = conversations.value.find(x => x.id === currentConvId.value)
  return c?.title || '助手'
})

function fmtTime(t) {
  if (!t) return ''
  const d = new Date(String(t).replace(' ', 'T'))
  const now = new Date()
  if (d.toDateString() === now.toDateString()) {
    return d.toTimeString().slice(0, 5)
  }
  return `${d.getMonth() + 1}/${d.getDate()}`
}

async function loadConversations() {
  const res = await echoApi.listConversations()
  conversations.value = res.data.conversations || []
}

async function newConversation() {
  closeCurrent()
  const res = await echoApi.createConversation()
  currentConvId.value = res.data.conversation_id
  messages.value = []
  await loadConversations()
  closeDrawerMobile()
  focusInput()
}

async function selectConversation(conv) {
  if (conv.id === currentConvId.value) return
  closeCurrent()
  currentConvId.value = conv.id
  await loadMessages()
  closeDrawerMobile()
}

async function loadMessages() {
  const res = await echoApi.getMessages(currentConvId.value)
  messages.value = (res.data.messages || []).map(m => ({
    ...m,
    key: m.id ? `db-${m.id}` : `tmp-${msgKey++}`,
  }))
  scrollToBottom()
}

function closeCurrent() {
  if (currentConvId.value && !isStreaming.value) {
    echoApi.closeConversation(currentConvId.value).catch(() => {})
  }
  if (currentSSE.value) {
    currentSSE.value.close()
    currentSSE.value = null
  }
}

async function send() {
  const message = input.value.trim()
  if (!message || isStreaming.value) return
  if (!currentConvId.value) {
    const res = await echoApi.createConversation()
    currentConvId.value = res.data.conversation_id
  }

  input.value = ''
  messages.value.push({ role: 'user', content: message, key: `u-${msgKey++}` })
  const live = { role: 'assistant', content: '', key: `a-${msgKey++}` }
  messages.value.push(live)
  scrollToBottom()

  isStreaming.value = true
  try {
    const res = await echoApi.sendMessage(currentConvId.value, message)
    const taskId = res.data.task_id
    await stream(taskId, live)
  } catch (e) {
    live.content = '（发送失败，请重试）'
    live.key = `a-${msgKey++}`
  } finally {
    isStreaming.value = false
    await loadConversations()
    focusInput()
  }
}

function stream(taskId, live) {
  return new Promise((resolve) => {
    const sse = new EventSource(`/api/stream/${taskId}`)
    currentSSE.value = sse
    sse.onmessage = (event) => {
      const payload = JSON.parse(event.data)
      if (payload.type === 'raw_content') {
        live.content += payload.content || ''
        scrollToBottom()
      } else if (payload.type === 'done') {
        live.content = payload.message || live.content
        sse.close()
        currentSSE.value = null
        resolve()
      } else if (payload.type === 'error') {
        live.content = payload.message || '出错了'
        sse.close()
        currentSSE.value = null
        resolve()
      }
    }
    sse.onerror = () => {
      if (!live.content) live.content = '（连接中断）'
      sse.close()
      currentSSE.value = null
      resolve()
    }
  })
}

async function deleteConversation() {
  if (!currentConvId.value) return
  if (!confirm('删除这个会话？对话内容将被清除。')) return
  const id = currentConvId.value
  currentSSE.value?.close()
  currentSSE.value = null
  await echoApi.deleteConversation(id)
  currentConvId.value = null
  messages.value = []
  await loadConversations()
}

function scrollToBottom() {
  nextTick(() => {
    const el = msgScroll.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function focusInput() {
  nextTick(() => inputRef.value?.focus())
}

onMounted(async () => {
  await loadConversations()
  const first = conversations.value[0]
  if (first) {
    currentConvId.value = first.id
    await loadMessages()
  }
  focusInput()
})

onBeforeUnmount(() => {
  closeCurrent()
})

watch(input, () => {
  // 自动增高输入框
  const el = inputRef.value
  if (el) {
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }
})
</script>

<style scoped>
.echo-page {
  height: calc(100vh - 88px);
  display: flex;
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--bg-page);
}

/* 左侧会话列表 */
.echo-sidebar {
  width: 250px;
  min-width: 250px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--bg-border);
  background: var(--bg-sidebar);
}
.echo-sidebar-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--bg-border-light);
}
.echo-logo {
  color: var(--primary);
  font-size: 16px;
  font-weight: 700;
}
.echo-title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
.echo-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.echo-conv-item {
  padding: 9px 10px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--transition-fast);
}
.echo-conv-item:hover { background: var(--bg-hover); }
.echo-conv-item.active { background: var(--primary-light); }
.echo-conv-title {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}
.echo-conv-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 11px;
  color: var(--text-tertiary);
}
.echo-conv-preview {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.echo-empty-list {
  padding: 16px 10px;
  font-size: 12px;
  color: var(--text-tertiary);
  text-align: center;
}
.echo-sidebar-footer {
  padding: 10px 14px;
  border-top: 1px solid var(--bg-border-light);
}
.echo-reports-link {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  text-decoration: none;
}
.echo-reports-link:hover { color: var(--primary); }

/* 右侧线程 */
.echo-thread {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.echo-thread-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--bg-border-light);
  background: var(--bg-surface);
}
.echo-thread-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.echo-thread-actions { display: flex; gap: 4px; }
.icon-btn {
  width: 28px; height: 28px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all var(--transition-fast);
}
.icon-btn:hover { background: var(--bg-hover); color: var(--text-primary); }

/* 消息流 */
.echo-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.echo-msg {
  display: flex;
  gap: 10px;
  max-width: 78%;
}
.echo-msg.user { align-self: flex-end; flex-direction: row-reverse; }
.echo-msg-avatar {
  width: 28px; height: 28px;
  border-radius: 8px;
  background: var(--bg-hover);
  color: var(--text-secondary);
  font-size: 12px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.echo-msg.user .echo-msg-avatar { background: var(--primary); color: #fff; }
.echo-msg-bubble {
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  border: 1px solid var(--bg-border);
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}
.echo-msg.user .echo-msg-bubble {
  background: var(--primary-light);
  border-color: transparent;
}
.echo-msg-bubble.md :deep(pre) {
  background: var(--bg-code, #0d1117);
  color: #e6edf3;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 13px;
}
.echo-msg-bubble.md :deep(code) {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}
.echo-msg-bubble.md :deep(p) { margin: 0 0 8px; }
.echo-msg-bubble.md :deep(ul), .echo-msg-bubble.md :deep(ol) { margin: 0 0 8px; padding-left: 20px; }
.echo-msg-bubble.md :deep(h1), .echo-msg-bubble.md :deep(h2), .echo-msg-bubble.md :deep(h3) { margin: 10px 0 6px; }
.echo-empty-thread {
  margin: auto;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
  line-height: 1.8;
}
.echo-empty-logo { font-size: 34px; color: var(--primary); margin-bottom: 8px; }

/* 输入区 */
.echo-composer {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--bg-border-light);
  background: var(--bg-surface);
}
.echo-input {
  flex: 1;
  resize: none;
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  background: var(--bg-page);
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.5;
  padding: 10px 12px;
  outline: none;
  max-height: 160px;
  font-family: inherit;
}
.echo-input:focus { border-color: var(--primary); }
.echo-send-btn {
  width: 36px; height: 36px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--primary);
  color: #fff;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: opacity var(--transition-fast);
}
.echo-send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* ── 移动端适配 ── */
@media (max-width: 768px) {
  .echo-page {
    height: 100%;
  }

  /* 会话列表 → 左侧滑出抽屉 */
  .echo-sidebar {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    width: 280px;
    max-width: 85vw;
    z-index: 70;
    border-radius: 0;
    border-right: 1px solid var(--bg-border);
    padding-top: env(safe-area-inset-top);
    box-shadow: var(--shadow-xl);
    transform: translateX(-100%);
    transition: transform 0.25s ease;
  }

  .echo-sidebar.open {
    transform: translateX(0);
  }

  .echo-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    z-index: 60;
  }

  .echo-menu-btn {
    width: 40px;
    height: 40px;
  }

  .echo-thread-header {
    gap: 4px;
  }

  .echo-msg {
    max-width: 88%;
  }

  .echo-msg-bubble {
    font-size: 13px;
  }

  .echo-messages {
    padding: 16px 14px;
  }

  .echo-input {
    font-size: 16px; /* 防 iOS 聚焦缩放 */
  }

  .echo-thread-header {
    padding: 6px 10px;
  }

  .echo-composer {
    padding: 8px 12px;
    gap: 6px;
  }

  .echo-input {
    padding: 8px 10px;
  }
}
</style>
