<template>
  <Layout>
    <div class="page-header">
      <h1 class="page-title">记忆库</h1>
      <div class="flex items-center gap-1">
        <TerminalButton v-if="isMobile" />
        <NotificationBell v-if="isMobile" />
      </div>
    </div>

    <!-- 用户画像 -->
    <div class="memory-card profile-card" v-if="profile">
      <div class="card-title">🧑‍💻 用户画像</div>
      <p class="profile-text">{{ profile }}</p>
    </div>

    <!-- 操作行 -->
    <div class="toolbar">
      <input v-model="searchQuery" class="input flex-1" placeholder="搜索记忆..." @keyup.enter="doSearch" />
      <button @click="doSearch" class="btn btn-outline">搜索</button>
      <button @click="resetSearch" class="btn btn-outline">全部</button>
      <button @click="openCreate" class="btn btn-primary">+ 添加记忆</button>
      <button @click="doConsolidate" class="btn btn-outline" :disabled="consolidating">{{ consolidating ? '提炼中...' : '🧹 提炼记忆' }}</button>
    </div>

    <!-- 记忆列表 -->
    <div v-for="group in groupedMemories" :key="group.type" class="memory-card">
      <div class="card-title">{{ typeLabels[group.type] || group.type }}
        <span class="count-badge">{{ group.items.length }}</span>
      </div>
      <div class="memory-item" v-for="m in group.items" :key="m.id">
        <div class="memory-content">{{ m.content }}</div>
        <div class="memory-meta">
          <span class="stars">{{ '★'.repeat(m.importance || 0) }}<span class="stars-dim">{{ '★'.repeat(5 - (m.importance || 0)) }}</span></span>
          <span class="memory-date">{{ formatDate(m.created_at) }}</span>
          <span v-if="!m.consolidated" class="raw-tag">未提炼</span>
        </div>
        <div class="memory-actions">
          <button class="action-icon" title="编辑" @click="openEdit(m)">✏️</button>
          <button class="action-icon" title="删除" @click="removeMemory(m)">🗑️</button>
        </div>
      </div>
      <div v-if="group.items.length === 0" class="empty-state"><p>暂无{{ typeLabels[group.type] }}记忆</p></div>
    </div>
    <div v-if="!loading && allMemories.length === 0" class="memory-card empty-state">
      <p>暂无记忆。去 Echo 聊聊天，重要信息会自动沉淀在这里。</p>
    </div>

    <!-- 编辑/添加弹窗 -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3 class="modal-title">{{ editing ? '编辑记忆' : '添加记忆' }}</h3>
          <button @click="showModal = false" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="filter-label">类型</label>
            <select v-model="form.type" class="input w-full">
              <option value="preference">偏好</option>
              <option value="fact">事实</option>
              <option value="decision">决定</option>
              <option value="server_info">服务器信息</option>
            </select>
          </div>
          <div class="form-group">
            <label class="filter-label">内容</label>
            <textarea v-model="form.content" class="input w-full form-textarea" rows="4" placeholder="记忆内容..."></textarea>
          </div>
          <div class="form-group">
            <label class="filter-label">重要性 (1-5)</label>
            <input v-model.number="form.importance" type="number" min="1" max="5" class="input w-full" />
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showModal = false" class="btn btn-outline">取消</button>
          <button @click="saveMemory" class="btn btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Layout from '../components/layout/Layout.vue'
import NotificationBell from '../components/NotificationBell.vue'
import TerminalButton from '../components/TerminalButton.vue'
import { useIsMobile } from '../composables/useIsMobile'
import { memoryApi } from '../services/api'

const { isMobile } = useIsMobile()

const typeLabels = { preference: '偏好', fact: '事实', decision: '决定', server_info: '服务器信息' }
const allTypes = ['preference', 'fact', 'decision', 'server_info']

const allMemories = ref([])
const profile = ref('')
const loading = ref(false)
const saving = ref(false)
const consolidating = ref(false)
const searchQuery = ref('')
const showModal = ref(false)
const editing = ref(null)
const form = ref({ type: 'fact', content: '', importance: 3 })

const groupedMemories = computed(() =>
  allTypes.map(type => ({ type, items: allMemories.value.filter(m => m.type === type) }))
)

async function loadMemories(params = {}) {
  loading.value = true
  try {
    const res = await memoryApi.list({ limit: 200, ...params })
    allMemories.value = res.data.memories || []
  } catch (e) {
    console.error('加载记忆失败:', e)
  } finally {
    loading.value = false
  }
}

async function loadProfile() {
  try {
    const res = await memoryApi.profile()
    profile.value = res.data.profile || ''
  } catch (e) {
    console.error('加载画像失败:', e)
  }
}

function doSearch() {
  const q = searchQuery.value.trim()
  if (!q) return resetSearch()
  memoryApi.search(q).then(res => { allMemories.value = res.data.memories || [] })
    .catch(e => console.error('搜索失败:', e))
}

function resetSearch() {
  searchQuery.value = ''
  loadMemories()
}

function openCreate() {
  editing.value = null
  form.value = { type: 'fact', content: '', importance: 3 }
  showModal.value = true
}

function openEdit(m) {
  editing.value = m
  form.value = { type: m.type, content: m.content, importance: m.importance || 3 }
  showModal.value = true
}

async function saveMemory() {
  if (!form.value.content.trim()) return
  saving.value = true
  try {
    if (editing.value) {
      await memoryApi.update(editing.value.id, {
        content: form.value.content, importance: form.value.importance, type: form.value.type
      })
    } else {
      await memoryApi.create(form.value)
    }
    showModal.value = false
    loadMemories()
  } catch (e) {
    console.error('保存失败:', e)
  } finally {
    saving.value = false
  }
}

async function removeMemory(m) {
  if (!confirm(`确定删除这条记忆？\n${m.content.slice(0, 50)}`)) return
  try {
    await memoryApi.remove(m.id)
    loadMemories()
  } catch (e) {
    console.error('删除失败:', e)
  }
}

async function doConsolidate() {
  if (!confirm('将零散记忆提炼为长期事实，确定执行？')) return
  consolidating.value = true
  try {
    const res = await memoryApi.consolidate()
    alert(`提炼完成：处理 ${res.data.processed || 0} 条，合并 ${res.data.merged || 0} 条，删除重复 ${res.data.deleted || 0} 条`)
    loadMemories()
  } catch (e) {
    console.error('提炼失败:', e)
  } finally {
    consolidating.value = false
  }
}

function formatDate(s) {
  if (!s) return ''
  const d = new Date(String(s).replace(' ', 'T'))
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(() => { loadMemories(); loadProfile() })
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 16px; align-items: center; }
.memory-card {
  background: var(--bg-surface); border: 1px solid var(--bg-border);
  border-radius: var(--radius-lg); padding: 20px; margin-bottom: 16px;
}
.card-title { font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 12px; }
.count-badge { font-size: 11px; background: var(--bg-hover); color: var(--text-tertiary); border-radius: 10px; padding: 1px 8px; margin-left: 6px; }
.profile-text { font-size: 13px; line-height: 1.8; color: var(--text-secondary); white-space: pre-wrap; }
.memory-item {
  display: flex; align-items: flex-start; gap: 10px; padding: 10px 0;
  border-top: 1px solid var(--bg-border);
}
.memory-item:first-of-type { border-top: none; }
.memory-content { flex: 1; font-size: 13px; color: var(--text-primary); line-height: 1.6; }
.memory-meta { display: flex; gap: 8px; align-items: center; font-size: 11px; color: var(--text-tertiary); white-space: nowrap; }
.stars { color: var(--primary); }
.stars-dim { color: var(--bg-hover); }
.raw-tag { background: var(--warning-light); color: var(--warning); border-radius: 8px; padding: 1px 6px; }
.memory-actions { display: flex; gap: 4px; }
.action-icon { background: none; border: none; cursor: pointer; font-size: 14px; opacity: 0.7; }
.action-icon:hover { opacity: 1; }
.form-group { margin-bottom: 12px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.empty-state { text-align: center; color: var(--text-tertiary); font-size: 13px; padding: 20px 0; }
</style>
