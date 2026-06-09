<template>
  <Layout>
    <div class="tools-page">
      <div class="page-header">
        <h1>工具面板</h1>
        <p class="page-desc">远程服务器上检测到的智能工具，点击即可交互</p>
      </div>

      <!-- 工具卡片网格 -->
      <div v-if="!activeSession" class="tools-content">
        <div v-if="toolStore.loading" class="loading-state">正在探测远程工具...</div>
        <div v-else-if="toolStore.error" class="error-state">
          <p>探测失败: {{ toolStore.error }}</p>
          <button @click="refreshTools" class="btn btn-outline">重试</button>
        </div>
        <div v-else class="tools-grid">
          <div
            v-for="tool in toolStore.tools"
            :key="tool.name"
            class="tool-card"
            :class="{ 'tool-unavailable': !tool.available }"
            @click="openTool(tool)"
          >
            <div class="tool-icon">{{ toolIcon(tool) }}</div>
            <div class="tool-info">
              <h3>{{ tool.display_name }}</h3>
              <p>{{ tool.description }}</p>
              <div class="tool-tags">
                <span v-for="tag in tool.capability_tags" :key="tag" class="tag">{{ tag }}</span>
              </div>
            </div>
          </div>
          <div v-if="toolStore.tools.length === 0 && !toolStore.loading" class="empty-state">
            <p>未检测到任何智能工具</p>
            <p class="hint">请先在远程服务器上安装 Claude Code 等工具</p>
          </div>
        </div>
      </div>

      <!-- 工具聊天界面 -->
      <ToolChat
        v-else
        :tool="activeTool"
        :session-id="activeSession"
        @back="closeChat"
        @closed="closeChat"
      />
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useServerStore } from '../stores/server'
import { useToolStore } from '../stores/tool'
import { toolApi } from '../services/api'
import Layout from '../components/layout/Layout.vue'
import ToolChat from '../components/ToolChat.vue'

const serverStore = useServerStore()
const toolStore = useToolStore()

const activeSession = ref(null)
const activeTool = ref(null)

const currentServer = computed(() => serverStore.currentServer)

onMounted(() => {
  refreshTools()
})

onUnmounted(() => {
  if (activeSession.value) {
    toolApi.closeSession(activeSession.value).catch(() => {})
  }
})

async function refreshTools() {
  if (!currentServer.value?.id) return
  await toolStore.fetchTools(currentServer.value.id)
}

async function openTool(tool) {
  if (!tool.available) return
  if (!currentServer.value?.id) return

  try {
    const res = await toolApi.createSession(
      tool.name,
      currentServer.value.id,
      serverStore.serverPasswords[currentServer.value.id] || ''
    )
    activeSession.value = res.data.session_id
    activeTool.value = tool
  } catch (e) {
    alert(`启动会话失败: ${e.response?.data?.detail || e.message}`)
  }
}

function closeChat() {
  activeSession.value = null
  activeTool.value = null
}

function toolIcon(tool) {
  const icons = {
    claude_code: '\u{1F9E0}',
    brain: '\u{1F9E0}',
  }
  return icons[tool.icon] || icons[tool.name] || '\u{1F527}'
}
</script>

<style scoped>
.tools-page { padding: 20px 24px; max-width: 1200px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-header h1 { font-size: 22px; font-weight: 700; margin: 0 0 4px; }
.page-desc { color: #6b7280; font-size: 13px; margin: 0; }

.loading-state, .error-state, .empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #6b7280;
}
.error-state p { color: #ef4444; }
.hint { font-size: 12px; color: #9ca3af; margin-top: 8px; }

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.tool-card {
  display: flex;
  gap: 14px;
  padding: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.tool-card:hover:not(.tool-unavailable) { border-color: #4f46e5; box-shadow: 0 2px 8px rgba(79,70,229,0.12); }
.tool-unavailable { opacity: 0.5; cursor: not-allowed; }
.tool-icon { font-size: 36px; line-height: 1; }
.tool-info { flex: 1; min-width: 0; }
.tool-info h3 { margin: 0 0 4px; font-size: 15px; }
.tool-info p { margin: 0 0 8px; font-size: 12px; color: #6b7280; }
.tool-tags { display: flex; gap: 4px; flex-wrap: wrap; }
.tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: #eef2ff;
  color: #4f46e5;
  border: 1px solid #e0e7ff;
}
.tool-status { display: flex; align-items: flex-start; }
.badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; }
.badge-ok { background: #d1fae5; color: #065f46; }
.badge-na { background: #fef3c7; color: #92400e; }
</style>
