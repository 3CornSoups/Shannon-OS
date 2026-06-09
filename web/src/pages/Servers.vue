<template>
  <Layout>
    <div class="servers-page">
      <div class="page-header">
        <h1>服务器管理</h1>
        <button @click="openAddModal" class="btn btn-primary">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          添加服务器
        </button>
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
    </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useServerStore } from '../stores/server'
import Layout from '../components/layout/Layout.vue'
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
    await axios.post('/api/host', form.value)
    showAddModal.value = false
    await fetchServers()
  } catch (error) {
    alert('添加失败: ' + (error.response?.data?.detail || error.message))
  }
}

const updateServer = async () => {
  try {
    await axios.put(`/api/host/${currentEditId.value}`, {
      ...form.value,
      id: currentEditId.value
    })
    showEditModal.value = false
    await fetchServers()
  } catch (error) {
    alert('更新失败: ' + (error.response?.data?.detail || error.message))
  }
}

const deleteServer = async (id) => {
  if (!confirm('确定删除该服务器？')) return
  try {
    await axios.delete(`/api/host/${id}`)
    await fetchServers()
  } catch (error) {
    alert('删除失败: ' + (error.response?.data?.detail || error.message))
  }
}

const testServer = (server) => {
  testServerData.value = { ...server }
  testResult.value = null
  showTestModal.value = true
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
.server-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }
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
</style>
