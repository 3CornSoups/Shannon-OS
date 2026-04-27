<template>
  <Layout>
    <div class="page-header">
      <h1 class="page-title">服务器管理</h1>
      <button class="btn btn-primary" @click="openAddModal">
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        添加服务器
      </button>
    </div>

    <div v-if="loading && servers.length === 0" class="loading-state">
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

    <div v-else class="server-grid">
      <div v-for="server in servers" :key="server.id" class="server-card">
        <div class="server-header">
          <div>
            <h3 class="server-name">{{ server.name }}</h3>
            <p class="server-address">{{ server.host }}:{{ server.port }}</p>
          </div>
          <div class="server-actions">
            <button class="action-btn" @click="editServer(server)" title="编辑">
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

    <!-- Add/Edit Modal -->
    <div v-if="showAddModal || showEditModal" class="modal-overlay" @click.self="cancelEdit">
      <div class="modal">
        <h2 class="modal-title">{{ showEditModal ? '编辑服务器' : '添加服务器' }}</h2>
        <form @submit.prevent="saveServer">
          <div class="form-group">
            <label class="form-label">名称 <span class="text-danger">*</span></label>
            <input v-model="form.name" type="text" class="input w-full" placeholder="服务器名称" required />
          </div>
          <div class="form-group">
            <label class="form-label">主机/IP <span class="text-danger">*</span></label>
            <input v-model="form.host" type="text" class="input w-full" placeholder="主机名或IP地址" required />
          </div>
          <div class="form-group">
            <label class="form-label">端口 <span class="text-danger">*</span></label>
            <input v-model.number="form.port" type="number" class="input w-full" placeholder="SSH端口" required />
          </div>
          <div class="form-group">
            <label class="form-label">用户名 <span class="text-danger">*</span></label>
            <input v-model="form.username" type="text" class="input w-full" placeholder="SSH用户名" required />
          </div>
          <div class="form-group">
            <label class="form-label">密码</label>
            <input v-model="form.password" type="password" class="input w-full" placeholder="SSH密码" />
          </div>
          <div class="form-group">
            <label class="form-label">私钥</label>
            <textarea v-model="form.private_key" class="input w-full resize-none h-24" placeholder="SSH私钥（可选）"></textarea>
          </div>
          <div class="form-group checkbox">
            <input v-model="form.use_local" type="checkbox" />
            <label>使用本地连接</label>
          </div>

          <div v-if="connectionTestResult" class="alert" :class="connectionTestResult.ok ? 'alert-success' : 'alert-danger'">
            <svg v-if="connectionTestResult.ok" class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M9 12l2 2 4-4"></path>
            </svg>
            <svg v-else class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="15" y1="9" x2="9" y2="15"></line>
              <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
            <div>
              <h4 class="alert-title">{{ connectionTestResult.ok ? '连接成功' : '连接失败' }}</h4>
              <p class="alert-message">{{ connectionTestResult.message }}</p>
            </div>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn btn-outline" @click="testFormConnection" :disabled="testingConnection">
              <span v-if="testingConnection" class="flex items-center">
                <svg class="spinner-sm" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="31.4" stroke-dashoffset="0">
                    <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite"/>
                  </circle>
                </svg>
                测试中...
              </span>
              <span v-else>测试连接</span>
            </button>
            <button type="button" class="btn btn-outline" @click="cancelEdit">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="loading">
              <span v-if="loading" class="flex items-center">
                <svg class="spinner-sm" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="31.4" stroke-dashoffset="0">
                    <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite"/>
                  </circle>
                </svg>
                保存中...
              </span>
              <span v-else>保存</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Test Modal -->
    <div v-if="showTestModal" class="modal-overlay" @click.self="closeTestModal">
      <div class="modal">
        <h2 class="modal-title">测试服务器连接</h2>
        <div class="mb-4">
          <p class="mb-2">服务器: <strong>{{ testServerData.name }}</strong></p>
          <p class="text-secondary">{{ testServerData.host }}:{{ testServerData.port }}</p>
        </div>
        <div class="mb-6">
          <div v-if="testing" class="test-loading">
            <svg class="spinner" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="31.4" stroke-dashoffset="0">
                <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite"/>
              </circle>
            </svg>
            <span>正在测试连接...</span>
          </div>
          <div v-else-if="testResult" class="alert" :class="testResult.ok ? 'alert-success' : 'alert-danger'">
            <svg v-if="testResult.ok" class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M9 12l2 2 4-4"></path>
            </svg>
            <svg v-else class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="15" y1="9" x2="9" y2="15"></line>
              <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
            <div>
              <h3 class="alert-title">{{ testResult.ok ? '连接成功' : '连接失败' }}</h3>
              <p class="alert-message">{{ testResult.message }}</p>
            </div>
          </div>
        </div>
        <div class="modal-actions justify-end">
          <button class="btn btn-outline" @click="closeTestModal">关闭</button>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Layout from '../components/layout/Layout.vue'
import { useServerStore } from '../stores/server'
import axios from 'axios'

const router = useRouter()
const serverStore = useServerStore()

const servers = ref([])
const loading = ref(false)
const showAddModal = ref(false)
const showEditModal = ref(false)
const showTestModal = ref(false)
const testServerData = ref({})
const testing = ref(false)
const testResult = ref(null)
const testingConnection = ref(false)
const connectionTestResult = ref(null)

const form = ref({
  name: '',
  host: '',
  port: 22,
  username: '',
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
    const response = await axios.get('/api/hosts')
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
  showEditModal.value = false
}

const editServer = (server) => {
  form.value = {
    name: server.name,
    host: server.host,
    port: server.port,
    username: server.username || '',
    password: '',
    private_key: '',
    use_local: false
  }
  currentEditId.value = server.id
  showEditModal.value = true
  showAddModal.value = false
  connectionTestResult.value = null
}

const cancelEdit = () => {
  showAddModal.value = false
  showEditModal.value = false
  resetForm()
}

const resetForm = () => {
  form.value = {
    name: '',
    host: '',
    port: 22,
    username: '',
    password: '',
    private_key: '',
    use_local: false
  }
  currentEditId.value = null
  connectionTestResult.value = null
}

const testFormConnection = async () => {
  if (!form.value.host || !form.value.username) {
    connectionTestResult.value = {
      ok: false,
      message: '请填写主机和用户名'
    }
    return
  }

  testingConnection.value = true
  connectionTestResult.value = null

  try {
    const response = await axios.post('/api/host/test', {
      host: {
        id: currentEditId.value || 0,
        name: form.value.name || form.value.host,
        host: form.value.host,
        port: form.value.port || 22,
        username: form.value.username,
        password: form.value.password || '',
        private_key: form.value.private_key || '',
        use_local: form.value.use_local
      }
    }, {
      timeout: 15000
    })
    connectionTestResult.value = response.data
  } catch (error) {
    if (error.code === 'ECONNABORTED') {
      connectionTestResult.value = {
        ok: false,
        message: '连接超时，请检查服务器地址和端口是否正确'
      }
    } else if (error.response) {
      connectionTestResult.value = {
        ok: false,
        message: error.response.data?.message || error.response.data?.detail || '连接失败'
      }
    } else {
      connectionTestResult.value = {
        ok: false,
        message: error.message || '连接失败，请检查网络'
      }
    }
  } finally {
    testingConnection.value = false
  }
}

const saveServer = async () => {
  loading.value = true
  try {
    if (showEditModal.value) {
      const response = await axios.put(`/api/hosts/${currentEditId.value}`, {
        name: form.value.name,
        host: form.value.host,
        port: form.value.port || 22,
        username: form.value.username,
        password: form.value.password || '',
        private_key: form.value.private_key || '',
        use_local: form.value.use_local
      })
      if (response.data.ok) {
        await fetchServers()
        cancelEdit()
      } else {
        alert('服务器更新失败：' + response.data.message)
      }
    } else {
      const response = await axios.post('/api/hosts', {
        name: form.value.name,
        host: form.value.host,
        port: form.value.port || 22,
        username: form.value.username,
        password: form.value.password || '',
        private_key: form.value.private_key || '',
        use_local: form.value.use_local
      })
      if (response.data.ok) {
        await fetchServers()
        cancelEdit()
      } else {
        alert('服务器保存失败：' + response.data.message)
      }
    }
  } catch (error) {
    console.error('保存服务器失败:', error)
    alert('保存服务器失败：' + (error.response?.data?.message || error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const deleteServer = async (id) => {
  if (confirm('确定要删除这个服务器吗？')) {
    try {
      const response = await axios.delete(`/api/hosts/${id}`)
      if (response.data.ok) {
        await fetchServers()
      } else {
        alert('服务器删除失败：' + response.data.message)
      }
    } catch (error) {
      console.error('删除服务器失败:', error)
      alert('删除服务器失败：' + (error.response?.data?.message || error.message || '未知错误'))
    }
  }
}

const testServer = (server) => {
  testServerData.value = server
  testResult.value = null
  showTestModal.value = true
  performTest()
}

const closeTestModal = () => {
  showTestModal.value = false
  testServerData.value = {}
  testResult.value = null
}

const performTest = async () => {
  testing.value = true
  try {
    const response = await axios.post('/api/host/test', {
      host: {
        id: testServerData.value.id || 0,
        name: testServerData.value.name,
        host: testServerData.value.host,
        port: testServerData.value.port,
        username: testServerData.value.username || '',
        password: '',
        private_key: '',
        use_local: false
      }
    }, {
      timeout: 15000
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
        message: error.response.data?.message || error.response.data?.detail || '连接失败'
      }
    } else {
      testResult.value = {
        ok: false,
        message: error.message || '连接失败'
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

const formatDate = (dateString) => {
  if (!dateString) return '从未'
  const date = new Date(dateString)
  return date.toLocaleString()
}
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 48px;
}

.spinner {
  width: 24px;
  height: 24px;
  color: var(--primary);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px;
  color: var(--text-secondary);
}

.empty-icon {
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.server-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.server-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  transition: all 0.2s ease;
}

.server-card:hover {
  border-color: var(--primary);
  box-shadow: var(--shadow-md);
}

.server-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.server-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.server-address {
  font-size: 13px;
  color: var(--text-secondary);
}

.server-actions {
  display: flex;
  gap: 4px;
}

.action-btn {
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

.action-btn:hover {
  background: var(--bg-hover);
}

.action-btn svg {
  width: 16px;
  height: 16px;
  color: var(--text-tertiary);
  transition: color 0.15s ease;
}

.action-btn:hover svg {
  color: var(--primary);
}

.action-btn.delete:hover svg {
  color: var(--danger);
}

.server-info {
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 13px;
}

.info-label {
  color: var(--text-secondary);
}

.info-value {
  color: var(--text-primary);
}

.server-footer {
  display: flex;
  justify-content: flex-end;
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
  padding: 24px;
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.form-group.checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
}

.form-group.checkbox label {
  font-size: 14px;
  color: var(--text-secondary);
}

.alert {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.alert-success {
  background: #F0FDF4;
  border: 1px solid #BBF7D0;
}

.alert-danger {
  background: #FEF2F2;
  border: 1px solid #FECACA;
}

.alert-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  margin-top: 2px;
}

.alert-success .alert-icon {
  color: var(--success);
}

.alert-danger .alert-icon {
  color: var(--danger);
}

.alert-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
}

.alert-success .alert-title {
  color: var(--success);
}

.alert-danger .alert-title {
  color: var(--danger);
}

.alert-message {
  font-size: 12px;
  color: var(--text-secondary);
}

.modal-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.spinner-sm {
  width: 16px;
  height: 16px;
  margin-right: 8px;
  animation: spin 1s linear infinite;
}

.test-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  color: var(--text-secondary);
}

.test-loading .spinner {
  width: 24px;
  height: 24px;
  color: var(--primary);
}

.text-secondary {
  color: var(--text-secondary);
}

.mb-2 {
  margin-bottom: 8px;
}

.mb-4 {
  margin-bottom: 16px;
}

.mb-6 {
  margin-bottom: 24px;
}

strong {
  color: var(--text-primary);
}

@media (max-width: 768px) {
  .server-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .modal {
    margin: 16px;
    max-height: calc(100vh - 32px);
  }
}
</style>