<template>
  <Layout>
    <div class="servers-page">
      <div class="page-header">
        <h1>服务器管理</h1>
        <div class="flex items-center gap-2">
          <TerminalButton v-if="isMobile" />
          <NotificationBell v-if="isMobile" />
          <button @click="openAddModal" class="btn btn-primary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            添加服务器
          </button>
        </div>
      </div>

    <div v-if="loading" class="loading-state">
      <svg class="spinner" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="31.4" stroke-dashoffset="0">
          <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite"/>
        </circle>
      </svg>
    </div>

    <div v-else-if="servers.length === 0" class="empty-state">
      <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="2" y="3" width="20" height="6" rx="1"></rect>
        <rect x="2" y="15" width="20" height="6" rx="1"></rect>
        <line x1="6" y1="9" x2="6" y2="9.01"></line>
        <line x1="6" y1="21" x2="6" y2="21.01"></line>
      </svg>
      <p>暂无服务器，请点击上方按钮添加</p>
    </div>

    <div v-else>
    <div v-if="serverStore.selectedServers.length > 0" class="flex items-center gap-3 px-4 py-2 bg-indigo-50 rounded-lg mb-4">
      <span class="text-sm font-medium text-indigo-700">已选 {{ serverStore.selectedServers.length }} 台</span>
      <button @click="confirmSelection" class="btn btn-primary text-xs px-4 py-1.5">确认选择</button>
      <button @click="serverStore.clearSelection()" class="btn btn-outline text-xs px-4 py-1.5">取消全选</button>
    </div>
    <div class="server-grid">
      <div v-for="server in servers" :key="server.id" class="server-card">
          <div class="absolute top-2 left-2 z-10">
            <input
              type="checkbox"
              :checked="isServerSelected(server)"
              @change="toggleServer(server)"
              class="w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
            />
          </div>
        <div class="server-header">
          <div>
            <h3 class="server-name">{{ server.name }}</h3>
            <p class="server-address">{{ server.host }}:{{ server.port }}</p>
          </div>
          <div class="server-actions">
            <button class="action-btn" @click="openEditModal(server)" title="编辑">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
              </svg>
            </button>
            <button class="action-btn" @click="testServer(server)" title="测试连接">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 12h14"></path>
                <path d="M12 5l7 7-7 7"></path>
              </svg>
            </button>
            <button class="action-btn delete" @click="deleteServer(server.id)" title="删除">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        </div>
        <div class="server-info">
          <div class="info-row">
            <span class="info-label">用户名:</span>
            <span class="info-value">{{ server.username || '未设置' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">操作系统:</span>
            <span class="info-value">{{ server.os_name || '未知' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">发行版:</span>
            <span class="info-value">{{ server.distro || '未知' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">最后连接:</span>
            <span class="info-value">{{ formatDate(server.last_seen) }}</span>
          </div>
        </div>
        <div class="server-footer">
          <button class="btn btn-outline" @click="selectServer(server)">选择使用</button>
        </div>
      </div>
    </div>
    </div>
    </div>

    <!-- 添加/编辑服务器弹窗 -->
    <div v-if="showAddModal || showEditModal" class="modal-overlay" @click.self="showAddModal = false; showEditModal = false; resetForm()">
      <div class="modal-content">
        <h2 class="modal-title">{{ showEditModal ? '编辑服务器' : '添加服务器' }}</h2>
        <form @submit.prevent="showEditModal ? updateServer() : addServer()">
          <div class="form-group">
            <label class="form-label">名称 <span class="required">*</span></label>
            <input v-model="form.name" type="text" class="input" placeholder="例如: 生产服务器" required />
          </div>
          <div class="form-group">
            <label class="form-label">地址 <span class="required">*</span></label>
            <input v-model="form.host" type="text" class="input" placeholder="例如: 192.168.1.100" required />
          </div>
          <div class="form-group">
            <label class="form-label">端口</label>
            <input v-model.number="form.port" type="number" class="input" placeholder="22" />
          </div>
          <div class="form-group">
            <label class="form-label">用户名 <span class="required">*</span></label>
            <input v-model="form.username" type="text" class="input" placeholder="例如: root" required />
          </div>
          <div class="form-group">
            <label class="form-label">密码</label>
            <input v-model="form.password" type="password" class="input" placeholder="SSH 密码（留空则使用已保存密码）" />
          </div>
          <div class="form-group">
            <label class="form-label">私钥</label>
            <textarea v-model="form.private_key" class="input textarea" rows="3" placeholder="SSH 私钥内容（可选）"></textarea>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-outline" @click="showAddModal = false; showEditModal = false; resetForm()">取消</button>
            <button type="submit" class="btn btn-primary">{{ showEditModal ? '保存修改' : '添加' }}</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 测试连接弹窗 -->
    <div v-if="showTestModal" class="modal-overlay" @click.self="showTestModal = false">
      <div class="modal-content">
        <h2 class="modal-title">测试连接 — {{ testServerData.name }}</h2>
        <div class="modal-body">
          <p class="test-target">{{ testServerData.host }}:{{ testServerData.port }} · {{ testServerData.username }}</p>
          <div v-if="testing" class="test-loading">
            <svg class="spinner" viewBox="0 0 24 24" width="20" height="20">
              <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="31.4" stroke-dashoffset="0">
                <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite"/>
              </circle>
            </svg>
            <span>正在测试连接...</span>
          </div>
          <div v-if="testResult && !testing" :class="['test-result', testResult.ok ? 'test-success' : 'test-fail']">
            <svg v-if="testResult.ok" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            <span>{{ testResult.message }}</span>
          </div>
        </div>
        <div class="modal-actions">
          <button v-if="!testing" class="btn btn-primary" @click="performTest">{{ testResult ? '重新测试' : '测试连接' }}</button>
          <button class="btn btn-outline" @click="showTestModal = false">关闭</button>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useServerStore } from '../stores/server'
import { serverApi } from '../services/api'
import Layout from '../components/layout/Layout.vue'
import NotificationBell from '../components/NotificationBell.vue'
import TerminalButton from '../components/TerminalButton.vue'
import { useIsMobile } from '../composables/useIsMobile'

const router = useRouter()
const serverStore = useServerStore()
const { isMobile } = useIsMobile()

const servers = ref([])
const loading = ref(false)
const showAddModal = ref(false)
const showEditModal = ref(false)
const showTestModal = ref(false)
const testServerData = ref({})
const testing = ref(false)
const testResult = ref(null)
const testingConnection = ref(false)

const form = ref({
  name: '',
  host: '',
  port: 22,
  username: 'root',
  password: '',
  private_key: '',
  use_local: false
})

const currentEditId = ref(null)

onMounted(async () => {
  await fetchServers()
})

const fetchServers = async () => {
  loading.value = true
  try {
    const response = await serverApi.getServers()
    servers.value = response.data
  } catch (error) {
    console.error('获取服务器列表失败:', error)
  } finally {
    loading.value = false
  }
}

const openAddModal = () => {
  resetForm()
  showAddModal.value = true
}

const openEditModal = (server) => {
  currentEditId.value = server.id
  form.value = {
    name: server.name,
    host: server.host,
    port: server.port,
    username: server.username,
    password: '',
    private_key: '',
    use_local: false
  }
  showEditModal.value = true
}

const resetForm = () => {
  currentEditId.value = null
  form.value = {
    name: '',
    host: '',
    port: 22,
    username: 'root',
    password: '',
    private_key: '',
    use_local: false
  }
}

const addServer = async () => {
  try {
    const res = await serverApi.createServer(form.value)
    if (res.data.ok) {
      showAddModal.value = false
      resetForm()
      await serverStore.fetchServers()
      servers.value = serverStore.servers
    } else {
      alert(res.data.message || '添加失败')
    }
  } catch (error) {
    alert('添加失败: ' + (error.response?.data?.detail || error.message))
  }
}

const updateServer = async () => {
  try {
    const res = await serverApi.updateServer(currentEditId.value, {
      ...form.value,
      id: currentEditId.value
    })
    if (res.data.ok) {
      showEditModal.value = false
      resetForm()
      await serverStore.fetchServers()
      servers.value = serverStore.servers
    } else {
      alert(res.data.message || '更新失败')
    }
  } catch (error) {
    alert('更新失败: ' + (error.response?.data?.detail || error.message))
  }
}

const deleteServer = async (id) => {
  if (!confirm('确定删除该服务器？')) return
  try {
    await serverApi.deleteServer(id)
    await serverStore.fetchServers()
    servers.value = serverStore.servers
  } catch (error) {
    alert('删除失败: ' + (error.response?.data?.detail || error.message))
  }
}

const testServer = (server) => {
  testServerData.value = { ...server }
  testResult.value = null
  showTestModal.value = true
  performTest()
}

const performTest = async () => {
  testing.value = true
  try {
    const response = await serverApi.testConnection({
      id: testServerData.value.id || 0,
      name: testServerData.value.name,
      host: testServerData.value.host,
      port: testServerData.value.port,
      username: testServerData.value.username || '',
      password: '',
      private_key: '',
      use_local: false
    })
    testResult.value = response.data
  } catch (error) {
    if (error.code === 'ECONNABORTED') {
      testResult.value = {
        ok: false,
        message: '连接超时，请检查服务器地址和端口是否正确'
      }
    } else if (error.response) {
      testResult.value = {
        ok: false,
        message: error.response.data?.detail || '连接失败'
      }
    } else {
      testResult.value = {
        ok: false,
        message: '网络错误: ' + error.message
      }
    }
  } finally {
    testing.value = false
  }
}

const selectServer = (server) => {
  serverStore.setCurrentServer(server)
  router.push('/')
}

function isServerSelected(server) {
  return serverStore.selectedServers.some(s => s.id === server.id)
}

function toggleServer(server) {
  serverStore.toggleServerSelection(server)
}

function confirmSelection() {
  router.push('/')
}

const formatDate = (dateString) => {
  if (!dateString) return '从未'
  const date = new Date(dateString)
  return date.toLocaleString()
}
</script>

<style scoped>
.servers-page { padding: 20px 24px; max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-header h1 { font-size: 22px; font-weight: 700; margin: 0; }
.loading-state { text-align: center; padding: 60px 20px; }
.spinner { width: 32px; height: 32px; color: #6366f1; }
.empty-state { text-align: center; padding: 60px 20px; color: #6b7280; }
.empty-icon { width: 48px; height: 48px; margin: 0 auto 12px; color: #9ca3af; }
.server-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.server-card { position: relative; background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 18px; }
.server-card:hover { border-color: #a5b4fc; box-shadow: 0 2px 8px rgba(99,102,241,0.08); }
.server-header { display: flex; justify-content: space-between; align-items: flex-start; margin-left: 24px; margin-bottom: 10px; }
.server-name { font-size: 15px; font-weight: 600; margin: 0; }
.server-address { font-size: 12px; color: #6b7280; margin: 2px 0 0; }
.server-actions { display: flex; gap: 2px; }
.action-btn { background: none; border: none; cursor: pointer; padding: 4px; border-radius: 4px; color: #6b7280; }
.action-btn:hover { background: #f3f4f6; color: #111827; }
.action-btn svg { width: 14px; height: 14px; }
.action-btn.delete:hover { color: #ef4444; }
.server-info { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 12px; margin-left: 24px; margin-bottom: 10px; }
.info-row { display: flex; gap: 4px; font-size: 11px; }
.info-label { color: #9ca3af; }
.info-value { color: #374151; }
.server-footer { margin-left: 24px; }
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 6px; font-size: 13px; cursor: pointer; border: none; font-weight: 500; }
.btn-primary { background: #4f46e5; color: #fff; }
.btn-primary:hover { background: #4338ca; }
.btn-outline { background: #fff; color: #374151; border: 1px solid #d1d5db; }
.btn-outline:hover { background: #f9fafb; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal-content {
  background: #fff; border-radius: 12px; padding: 24px;
  max-width: 480px; width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.15);
  max-height: 90vh; overflow-y: auto;
}
.modal-title { margin: 0 0 20px; font-size: 17px; font-weight: 700; }
.form-group { margin-bottom: 14px; }
.form-label { display: block; font-size: 13px; font-weight: 500; color: #374151; margin-bottom: 4px; }
.form-label .required { color: #ef4444; }
.input { width: 100%; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; box-sizing: border-box; }
.input:focus { outline: none; border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }
.textarea { resize: vertical; font-family: 'Consolas', 'Courier New', monospace; }
.modal-body { margin: 16px 0; font-size: 14px; color: #374151; line-height: 1.6; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 20px; }

/* Test connection */
.test-target { color: #6b7280; font-size: 13px; margin-bottom: 12px; }
.test-loading { display: flex; align-items: center; gap: 8px; color: #6366f1; font-size: 14px; }
.test-result { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: 8px; font-size: 14px; }
.test-success { background: #ecfdf5; color: #065f46; }
.test-fail { background: #fef2f2; color: #991b1b; }
</style>
