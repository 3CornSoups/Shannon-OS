<template>
  <Layout>
    <div class="page-header">
      <h1 class="page-title">操作历史</h1>
    </div>

    <!-- Filters -->
    <div class="filter-card">
      <h2 class="section-title">筛选条件</h2>
      <div class="filter-grid">
        <div class="filter-item">
          <label class="filter-label">服务器</label>
          <select v-model="filters.serverId" class="input w-full">
            <option value="">所有服务器</option>
            <option v-for="server in servers" :key="server.id" :value="server.id">
              {{ server.name }} ({{ server.host }})
            </option>
          </select>
        </div>
        <div class="filter-item">
          <label class="filter-label">状态</label>
          <select v-model="filters.status" class="input w-full">
            <option value="">所有状态</option>
            <option value="success">成功</option>
            <option value="failed">失败</option>
            <option value="chat_only">仅聊天</option>
          </select>
        </div>
        <div class="filter-item">
          <label class="filter-label">模式</label>
          <select v-model="filters.mode" class="input w-full">
            <option value="">所有模式</option>
            <option value="chat">Chat</option>
            <option value="agent">Agent</option>
            <option value="auto">Auto</option>
          </select>
        </div>
      </div>
      <div class="filter-actions">
        <button @click="clearFilters" class="btn btn-outline">重置筛选</button>
        <button @click="applyFilters" class="btn btn-primary">应用筛选</button>
      </div>
    </div>

    <!-- History List -->
    <div class="history-card">
      <div class="history-header">
        <h2 class="section-title mb-0">操作记录</h2>
      </div>
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>服务器</th>
              <th>模式</th>
              <th>用户请求</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in filteredHistory" :key="record.id" class="table-row">
              <td class="table-cell">{{ formatDate(record.created_at) }}</td>
              <td class="table-cell">{{ getServerName(record.host_id) }}</td>
              <td class="table-cell">
                <span class="badge" :class="`badge-${record.mode}`">{{ record.mode.toUpperCase() }}</span>
              </td>
              <td class="table-cell text-truncate" :title="record.user_prompt">{{ record.user_prompt }}</td>
              <td class="table-cell">
                <span class="badge" :class="`badge-${record.status}`">{{ record.status }}</span>
              </td>
              <td class="table-cell">
                <div class="table-actions">
                  <button @click="viewDetails(record)" class="action-icon" title="查看详情">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>
                  </button>
                  <button @click="reexecute(record)" class="action-icon" title="重新执行">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="23 4 23 10 17 10"></polyline>
                      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="filteredHistory.length === 0" class="empty-state">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
        </svg>
        <p>暂无操作记录</p>
      </div>
    </div>

    <!-- Details Modal -->
    <div v-if="showDetailsModal" class="modal-overlay" @click.self="showDetailsModal = false">
      <div class="modal modal-lg">
        <div class="modal-header">
          <h3 class="modal-title">操作详情</h3>
          <button @click="showDetailsModal = false" class="close-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div v-if="selectedRecord" class="modal-body">
          <div class="detail-grid">
            <div class="detail-item">
              <h4 class="detail-label">时间</h4>
              <p class="detail-value">{{ formatDate(selectedRecord.created_at) }}</p>
            </div>
            <div class="detail-item">
              <h4 class="detail-label">服务器</h4>
              <p class="detail-value">{{ getServerName(selectedRecord.host_id) }}</p>
            </div>
            <div class="detail-item">
              <h4 class="detail-label">模式</h4>
              <p class="detail-value">{{ selectedRecord.mode.toUpperCase() }}</p>
            </div>
            <div class="detail-item">
              <h4 class="detail-label">状态</h4>
              <p class="detail-value">
                <span class="badge" :class="`badge-${selectedRecord.status}`">{{ selectedRecord.status }}</span>
              </p>
            </div>
          </div>
          <div class="detail-section">
            <h4 class="detail-label">用户请求</h4>
            <div class="code-block">{{ selectedRecord.user_prompt }}</div>
          </div>
          <div v-if="selectedRecord.parsed_commands" class="detail-section">
            <h4 class="detail-label">执行命令</h4>
            <div class="code-block code-green">{{ formatCommands(selectedRecord.parsed_commands) }}</div>
          </div>
          <div v-if="selectedRecord.result_summary" class="detail-section">
            <h4 class="detail-label">执行结果</h4>
            <div class="code-block">{{ selectedRecord.result_summary }}</div>
          </div>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Layout from '../components/layout/Layout.vue'
import { useServerStore } from '../stores/server'
import { useHistoryStore } from '../stores/history'

const router = useRouter()
const serverStore = useServerStore()
const historyStore = useHistoryStore()

const servers = ref([])
const filters = ref({
  serverId: '',
  status: '',
  mode: ''
})
const showDetailsModal = ref(false)
const selectedRecord = ref(null)

const filteredHistory = computed(() => {
  return [
    {
      id: 1,
      host_id: 1,
      mode: 'chat',
      user_prompt: '帮我查看系统信息',
      parsed_commands: 'ls -la',
      executed: true,
      result_summary: '系统信息已获取',
      status: 'success',
      created_at: new Date().toISOString()
    },
    {
      id: 2,
      host_id: 1,
      mode: 'agent',
      user_prompt: '帮我检查磁盘使用情况',
      parsed_commands: 'df -h',
      executed: true,
      result_summary: '磁盘使用情况已检查',
      status: 'success',
      created_at: new Date(Date.now() - 3600000).toISOString()
    },
    {
      id: 3,
      host_id: 2,
      mode: 'auto',
      user_prompt: '帮我安装nginx',
      parsed_commands: 'apt update && apt install nginx -y',
      executed: true,
      result_summary: 'nginx已安装',
      status: 'success',
      created_at: new Date(Date.now() - 7200000).toISOString()
    }
  ]
})

onMounted(async () => {
  await serverStore.fetchServers()
  servers.value = serverStore.servers
})

const applyFilters = () => {
  historyStore.setFilters(filters.value)
}

const clearFilters = () => {
  filters.value = {
    serverId: '',
    status: '',
    mode: ''
  }
  historyStore.clearFilters()
}

const viewDetails = (record) => {
  selectedRecord.value = record
  showDetailsModal.value = true
}

const reexecute = (record) => {
  router.push('/')
  localStorage.setItem('reexecuteRecord', JSON.stringify(record))
}

const getServerName = (hostId) => {
  const server = servers.value.find(s => s.id === hostId)
  return server ? server.name : '未知服务器'
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString()
}

const formatCommands = (commands) => {
  try {
    const parsed = JSON.parse(commands)
    if (Array.isArray(parsed)) {
      return parsed.map(cmd => typeof cmd === 'string' ? cmd : cmd.command).join('\n')
    }
    return commands
  } catch (e) {
    return commands
  }
}
</script>

<style scoped>
.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.filter-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.section-title.mb-0 {
  margin-bottom: 0;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.filter-item {
  display: flex;
  flex-direction: column;
}

.filter-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.filter-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.history-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.history-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  padding: 12px 16px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: var(--bg-input);
  border-bottom: 1px solid var(--border);
}

.data-table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}

.table-row:hover {
  background: var(--bg-hover);
}

.table-cell {
  font-size: 13px;
  color: var(--text-primary);
}

.text-truncate {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-actions {
  display: flex;
  gap: 8px;
}

.action-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-icon:hover {
  background: var(--bg-hover);
}

.action-icon svg {
  width: 14px;
  height: 14px;
  color: var(--text-tertiary);
}

.action-icon:hover svg {
  color: var(--primary);
}

.badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.badge-chat {
  background: #EFF6FF;
  color: #3B82F6;
}

.badge-agent {
  background: #F0FDF4;
  color: #22C55E;
}

.badge-auto {
  background: #FFFBEB;
  color: #F59E0B;
}

.badge-success {
  background: #F0FDF4;
  color: #22C55E;
}

.badge-failed {
  background: #FEF2F2;
  color: #EF4444;
}

.badge-chat_only {
  background: #EFF6FF;
  color: #3B82F6;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px;
  color: var(--text-secondary);
}

.empty-icon {
  width: 48px;
  height: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  backdrop-filter: blur(4px);
}

.modal {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 480px;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-lg {
  max-width: 640px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
}

.close-btn:hover {
  background: var(--bg-hover);
}

.close-btn svg {
  width: 18px;
  height: 18px;
  color: var(--text-secondary);
}

.modal-body {
  padding: 20px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.detail-item {
  display: flex;
  flex-direction: column;
}

.detail-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-value {
  font-size: 14px;
  color: var(--text-primary);
}

.detail-section {
  margin-bottom: 16px;
}

.detail-section .detail-label {
  margin-bottom: 8px;
}

.code-block {
  background: var(--bg-input);
  border-radius: var(--radius-md);
  padding: 12px;
  font-size: 13px;
  font-family: monospace;
  color: var(--text-primary);
  white-space: pre-wrap;
}

.code-green {
  color: var(--success);
}

@media (max-width: 768px) {
  .filter-grid {
    grid-template-columns: 1fr;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .modal {
    margin: 16px;
    max-height: calc(100vh - 32px);
  }
}
</style>