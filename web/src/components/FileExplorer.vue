<template>
  <div class="file-explorer">
    <!-- Header -->
    <div class="explorer-header">
      <span class="explorer-title">资源管理器</span>
      <div class="explorer-actions">
        <button class="explorer-action-btn" @click="showNewEntryInput" title="新建文件">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
        </button>
        <button class="explorer-action-btn" @click="refreshCurrent" title="刷新">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23,4 23,10 17,10"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>
        </button>
      </div>
    </div>

    <!-- Server Selector -->
    <div v-if="servers.length > 0" class="server-selector">
      <select v-model="selectedServerId" @change="onServerChange" class="server-select">
        <option :value="null">选择服务器...</option>
        <option v-for="s in servers" :key="s.id" :value="s.id">{{ s.name }} ({{ s.host }})</option>
      </select>
    </div>
    <div v-else class="no-server-hint">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>
      <span>请先添加服务器</span>
    </div>

    <!-- Breadcrumb -->
    <div v-if="currentServer" class="explorer-breadcrumb">
      <button v-for="(segment, idx) in pathSegments" :key="idx" class="breadcrumb-seg" @click="navigateTo(segment.path)">
        <svg v-if="idx === 0" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>
        <span>{{ segment.name }}</span>
        <svg v-if="idx < pathSegments.length - 1" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9,18 15,12 9,6"/></svg>
      </button>
    </div>

    <!-- New Entry Input -->
    <div v-if="showNewInput" class="new-entry-row">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14,2 14,8 20,8"/></svg>
      <input
        ref="newInputRef"
        v-model="newEntryName"
        class="new-entry-input"
        placeholder="文件名 或 目录名/"
        @keydown.enter="createNewEntry"
        @keydown.esc="showNewInput = false"
      />
      <button class="new-entry-confirm" @click="createNewEntry" title="确认">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20,6 9,17 4,12"/></svg>
      </button>
      <button class="new-entry-cancel" @click="showNewInput = false" title="取消">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>

    <!-- File List -->
    <div v-if="currentServer" class="explorer-content" @contextmenu.prevent="onContextMenu">
      <!-- Loading -->
      <div v-if="loading" class="explorer-loading">
        <div class="loading-spinner"></div>
        <span>加载中...</span>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="explorer-error">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
        <span>{{ error }}</span>
        <button class="retry-btn" @click="refreshCurrent">重试</button>
      </div>

      <!-- Empty -->
      <div v-else-if="entries.length === 0" class="explorer-empty">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity:0.3"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
        <span>空目录</span>
      </div>

      <!-- Entries -->
      <div v-else class="file-list">
        <div
          v-for="entry in entries"
          :key="entry.path"
          class="file-item"
          :class="{ selected: selectedPath === entry.path }"
          @click="onEntryClick(entry)"
          @dblclick="onEntryDblClick(entry)"
          @contextmenu.stop.prevent="onEntryContext($event, entry)"
        >
          <div class="file-icon" :class="'icon-' + entry.icon_type">
            <svg v-if="entry.is_dir" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
            <svg v-else-if="entry.icon_type === 'code'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="16,18 22,12 16,6"/><polyline points="8,6 2,12 8,18"/></svg>
            <svg v-else-if="entry.icon_type === 'config'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9c.26.604.852.997 1.51 1H21a2 2 0 010 4h-.09c-.658.003-1.25.396-1.51 1z"/></svg>
            <svg v-else-if="entry.icon_type === 'document'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            <svg v-else-if="entry.icon_type === 'image'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21,15 16,10 5,21"/></svg>
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14,2 14,8 20,8"/></svg>
          </div>
          <span class="file-name" :title="entry.path">{{ entry.name }}</span>
          <span v-if="!entry.is_dir" class="file-size">{{ formatSize(entry.size) }}</span>
        </div>
      </div>
    </div>

    <!-- File Preview Modal -->
    <div v-if="previewVisible" class="preview-overlay" @click.self="previewVisible = false">
      <div class="preview-panel">
        <div class="preview-header">
          <span class="preview-title">{{ previewPath }}</span>
          <div class="preview-actions">
            <button v-if="previewEditable" class="preview-btn save-btn" @click="savePreview" :disabled="previewSaving">
              {{ previewSaving ? '保存中...' : '保存' }}
            </button>
            <button class="preview-btn" @click="previewVisible = false">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
        </div>
        <div class="preview-body">
          <div v-if="previewLoading" class="preview-loading">
            <div class="loading-spinner"></div>
            <span>加载文件内容...</span>
          </div>
          <div v-else-if="previewError" class="preview-error">{{ previewError }}</div>
          <textarea
            v-else-if="previewEditable"
            v-model="previewContent"
            class="preview-editor"
            spellcheck="false"
          ></textarea>
          <pre v-else class="preview-code">{{ previewContent }}</pre>
        </div>
        <div class="preview-footer">
          <span>{{ previewLanguage }} · {{ formatSize(previewSize) }}</span>
        </div>
      </div>
    </div>

    <!-- Context Menu -->
    <div v-if="contextMenu.visible" class="context-menu" :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }">
      <button v-if="contextMenu.entry?.is_dir" class="ctx-item" @click="openDir(contextMenu.entry)">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
        打开目录
      </button>
      <button v-if="!contextMenu.entry?.is_dir" class="ctx-item" @click="previewFile(contextMenu.entry)">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
        预览文件
      </button>
      <button class="ctx-item" @click="startRename(contextMenu.entry)">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        重命名
      </button>
      <div class="ctx-divider"></div>
      <button class="ctx-item danger" @click="deleteEntry(contextMenu.entry)">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3,6 5,6 21,6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
        删除
      </button>
    </div>

    <!-- Rename Input -->
    <div v-if="renamingEntry" class="rename-overlay" @click.self="cancelRename">
      <div class="rename-dialog">
        <div class="rename-title">重命名</div>
        <input ref="renameInputRef" v-model="renameValue" class="rename-input" @keydown.enter="confirmRename" @keydown.esc="cancelRename" />
        <div class="rename-actions">
          <button class="rename-btn cancel" @click="cancelRename">取消</button>
          <button class="rename-btn confirm" @click="confirmRename">确认</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { filesApi } from '../services/api'
import { useServerStore } from '../stores/server'

const serverStore = useServerStore()

const servers = computed(() => serverStore.servers)
const selectedServerId = ref(null)
const currentServer = computed(() => servers.value.find(s => s.id === selectedServerId.value))
const currentPath = ref('/')
const entries = ref([])
const loading = ref(false)
const error = ref('')
const selectedPath = ref(null)

const showNewInput = ref(false)
const newEntryName = ref('')
const newInputRef = ref(null)

const previewVisible = ref(false)
const previewPath = ref('')
const previewContent = ref('')
const previewLanguage = ref('text')
const previewSize = ref(0)
const previewLoading = ref(false)
const previewError = ref('')
const previewEditable = ref(false)
const previewSaving = ref(false)

const contextMenu = ref({ visible: false, x: 0, y: 0, entry: null })

const renamingEntry = ref(null)
const renameValue = ref('')
const renameInputRef = ref(null)

const pathSegments = computed(() => {
  const parts = currentPath.value.split('/').filter(Boolean)
  const segs = [{ name: '/', path: '/' }]
  let acc = ''
  for (const p of parts) {
    acc += '/' + p
    segs.push({ name: p, path: acc })
  }
  return segs
})

function getServerPayload() {
  if (!currentServer.value) return null
  return {
    host_id: currentServer.value.id,
    host: currentServer.value.host,
    port: currentServer.value.port || 22,
    username: currentServer.value.username,
    password: currentServer.value.last_pwd || '',
    private_key: '',
  }
}

async function loadDirectory(path) {
  const payload = getServerPayload()
  if (!payload) return

  loading.value = true
  error.value = ''
  entries.value = []

  try {
    payload.path = path
    const response = await filesApi.listDirectory(payload)
    if (response.data.ok) {
      currentPath.value = response.data.path
      entries.value = response.data.entries || []
    } else {
      error.value = response.data.message || '加载失败'
    }
  } catch (err) {
    error.value = err.message || '网络错误'
  } finally {
    loading.value = false
  }
}

function onServerChange() {
  if (selectedServerId.value) {
    loadDirectory('/')
  } else {
    entries.value = []
    currentPath.value = '/'
  }
}

function navigateTo(path) {
  loadDirectory(path)
}

function refreshCurrent() {
  if (currentServer.value) {
    loadDirectory(currentPath.value)
  }
}

function onEntryClick(entry) {
  selectedPath.value = entry.path
}

function onEntryDblClick(entry) {
  if (entry.is_dir) {
    loadDirectory(entry.path)
  } else {
    previewFile(entry)
  }
}

function openDir(entry) {
  if (entry.is_dir) {
    loadDirectory(entry.path)
  }
  contextMenu.value.visible = false
}

async function previewFile(entry) {
  contextMenu.value.visible = false
  const payload = getServerPayload()
  if (!payload) return

  payload.path = entry.path
  previewVisible.value = true
  previewPath.value = entry.path
  previewContent.value = ''
  previewLanguage.value = 'text'
  previewSize.value = 0
  previewLoading.value = true
  previewError.value = ''
  previewEditable.value = true
  previewSaving.value = false

  try {
    const response = await filesApi.readFile(payload)
    if (response.data.ok) {
      previewContent.value = response.data.content
      previewLanguage.value = response.data.language || 'text'
      previewSize.value = response.data.size || 0
    } else {
      previewError.value = response.data.message || '读取失败'
      previewEditable.value = false
    }
  } catch (err) {
    previewError.value = err.message || '网络错误'
    previewEditable.value = false
  } finally {
    previewLoading.value = false
  }
}

async function savePreview() {
  const payload = getServerPayload()
  if (!payload) return

  payload.path = previewPath.value
  payload.content = previewContent.value
  previewSaving.value = true

  try {
    const response = await filesApi.writeFile(payload)
    if (!response.data.ok) {
      alert(response.data.message || '保存失败')
    }
  } catch (err) {
    alert(err.message || '保存失败')
  } finally {
    previewSaving.value = false
  }
}

function showNewEntryInput() {
  showNewInput.value = true
  newEntryName.value = ''
  nextTick(() => newInputRef.value?.focus())
}

async function createNewEntry() {
  const name = newEntryName.value.trim()
  if (!name) return

  const payload = getServerPayload()
  if (!payload) return

  payload.path = currentPath.value
  payload.new_name = name

  try {
    const response = await filesApi.createEntry(payload)
    if (response.data.ok) {
      showNewInput.value = false
      newEntryName.value = ''
      refreshCurrent()
    } else {
      alert(response.data.message || '创建失败')
    }
  } catch (err) {
    alert(err.message || '创建失败')
  }
}

async function deleteEntry(entry) {
  contextMenu.value.visible = false
  if (!entry) return

  const confirmed = confirm(`确定要删除 "${entry.name}" 吗？${entry.is_dir ? '这将删除目录下的所有内容！' : ''}`)
  if (!confirmed) return

  const payload = getServerPayload()
  if (!payload) return

  payload.path = entry.path

  try {
    const response = await filesApi.deleteEntry(payload)
    if (response.data.ok) {
      refreshCurrent()
    } else {
      alert(response.data.message || '删除失败')
    }
  } catch (err) {
    alert(err.message || '删除失败')
  }
}

function startRename(entry) {
  contextMenu.value.visible = false
  if (!entry) return
  renamingEntry.value = entry
  renameValue.value = entry.name
  nextTick(() => renameInputRef.value?.focus())
}

function cancelRename() {
  renamingEntry.value = null
  renameValue.value = ''
}

async function confirmRename() {
  if (!renamingEntry.value || !renameValue.value.trim()) return

  const payload = getServerPayload()
  if (!payload) return

  payload.path = renamingEntry.value.path
  payload.new_name = renameValue.value.trim()

  try {
    const response = await filesApi.renameEntry(payload)
    if (response.data.ok) {
      cancelRename()
      refreshCurrent()
    } else {
      alert(response.data.message || '重命名失败')
    }
  } catch (err) {
    alert(err.message || '重命名失败')
  }
}

function onContextMenu(e) {
  contextMenu.value = { visible: true, x: e.clientX, y: e.clientY, entry: null }
}

function onEntryContext(e, entry) {
  selectedPath.value = entry.path
  contextMenu.value = { visible: true, x: e.clientX, y: e.clientY, entry }
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return size.toFixed(i > 0 ? 1 : 0) + ' ' + units[i]
}

function closeContextMenu() {
  contextMenu.value.visible = false
}

onMounted(() => {
  document.addEventListener('click', closeContextMenu)
  tryAutoSelect()
})

onUnmounted(() => {
  document.removeEventListener('click', closeContextMenu)
})

function tryAutoSelect() {
  if (servers.value.length > 0 && !selectedServerId.value) {
    const stored = localStorage.getItem('shannon_file_server')
    if (stored && servers.value.find(s => s.id === parseInt(stored))) {
      selectedServerId.value = parseInt(stored)
      onServerChange()
    } else {
      selectedServerId.value = servers.value[0].id
      onServerChange()
    }
  }
}

watch(() => servers.value.length, () => {
  tryAutoSelect()
})

watch(selectedServerId, (val) => {
  if (val) localStorage.setItem('shannon_file_server', String(val))
})
</script>

<script>
import { watch } from 'vue'
</script>

<style scoped>
.file-explorer {
  display: flex;
  flex-direction: column;
  height: 100%;
  font-size: 12px;
}

.explorer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  flex-shrink: 0;
}

.explorer-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.explorer-actions {
  display: flex;
  gap: 2px;
}

.explorer-action-btn {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.explorer-action-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.server-selector {
  margin-bottom: 6px;
}

.server-select {
  width: 100%;
  height: 28px;
  padding: 0 8px;
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-sm);
  background: var(--bg-page);
  color: var(--text-primary);
  font-size: 11px;
  outline: none;
  cursor: pointer;
}

.server-select:focus {
  border-color: var(--primary);
}

.no-server-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px;
  color: var(--text-tertiary);
  font-size: 11px;
  background: var(--bg-hover);
  border-radius: var(--radius-sm);
}

.explorer-breadcrumb {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 2px;
  padding: 4px 0;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--bg-border-light);
  flex-shrink: 0;
}

.breadcrumb-seg {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 4px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  font-size: 11px;
  cursor: pointer;
  border-radius: 3px;
}

.breadcrumb-seg:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.new-entry-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;
  background: var(--bg-hover);
  border-radius: var(--radius-sm);
  margin-bottom: 4px;
  flex-shrink: 0;
}

.new-entry-row svg {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.new-entry-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 11px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  padding: 2px 4px;
  min-width: 0;
}

.new-entry-confirm,
.new-entry-cancel {
  width: 20px;
  height: 20px;
  border-radius: 3px;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.new-entry-confirm { color: var(--success); }
.new-entry-confirm:hover { background: var(--success-light); }
.new-entry-cancel { color: var(--text-tertiary); }
.new-entry-cancel:hover { background: var(--bg-border); color: var(--danger); }

.explorer-content {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.explorer-loading,
.explorer-error,
.explorer-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px 12px;
  color: var(--text-tertiary);
  font-size: 12px;
}

.explorer-error {
  color: var(--danger);
}

.retry-btn {
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--bg-border);
  background: var(--bg-surface);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 11px;
}

.retry-btn:hover {
  background: var(--bg-hover);
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--bg-border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.file-list {
  display: flex;
  flex-direction: column;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 6px;
  border-radius: 4px;
  cursor: pointer;
  user-select: none;
}

.file-item:hover {
  background: var(--bg-hover);
}

.file-item.selected {
  background: var(--primary-light);
}

.file-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.icon-folder svg { color: #E8A838; }
.icon-folder-special svg { color: #5C6BC0; }
.icon-code svg { color: #4FC3F7; }
.icon-config svg { color: #AB47BC; }
.icon-document svg { color: #66BB6A; }
.icon-image svg { color: #FF7043; }
.icon-data svg { color: #26A69A; }
.icon-hidden svg { color: var(--text-tertiary); opacity: 0.6; }
.icon-file svg { color: var(--text-tertiary); }

.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
  font-size: 12px;
}

.file-size {
  font-size: 10px;
  color: var(--text-tertiary);
  flex-shrink: 0;
}

/* Context Menu */
.context-menu {
  position: fixed;
  background: var(--bg-surface);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xl);
  padding: 4px;
  z-index: 200;
  min-width: 160px;
}

.ctx-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 6px 10px;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 12px;
  cursor: pointer;
  border-radius: 4px;
  text-align: left;
}

.ctx-item:hover {
  background: var(--bg-hover);
}

.ctx-item.danger {
  color: var(--danger);
}

.ctx-item.danger:hover {
  background: var(--danger-light);
}

.ctx-divider {
  height: 1px;
  background: var(--bg-border-light);
  margin: 4px 0;
}

/* Preview Modal */
.preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 150;
  backdrop-filter: blur(4px);
}

.preview-panel {
  width: 90%;
  max-width: 800px;
  max-height: 80vh;
  background: var(--bg-surface);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--bg-border-light);
  min-height: 44px;
}

.preview-title {
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.preview-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

.preview-btn {
  height: 28px;
  padding: 0 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--bg-border);
  background: var(--bg-surface);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.preview-btn:hover {
  background: var(--bg-hover);
}

.save-btn {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

.save-btn:hover {
  background: #3B57DF;
}

.save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.preview-body {
  flex: 1;
  overflow: auto;
  min-height: 0;
}

.preview-loading,
.preview-error {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.preview-error {
  color: var(--danger);
}

.preview-editor {
  width: 100%;
  min-height: 300px;
  padding: 16px;
  border: none;
  outline: none;
  background: var(--bg-page);
  color: var(--text-primary);
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: none;
  tab-size: 4;
}

.preview-code {
  padding: 16px;
  margin: 0;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-all;
  background: var(--bg-page);
}

.preview-footer {
  padding: 6px 16px;
  border-top: 1px solid var(--bg-border-light);
  font-size: 10px;
  color: var(--text-tertiary);
}

/* Rename Dialog */
.rename-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.rename-dialog {
  background: var(--bg-surface);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  min-width: 320px;
  box-shadow: var(--shadow-xl);
}

.rename-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.rename-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-sm);
  background: var(--bg-page);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
}

.rename-input:focus {
  border-color: var(--primary);
}

.rename-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}

.rename-btn {
  padding: 6px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--bg-border);
  background: var(--bg-surface);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 12px;
}

.rename-btn.confirm {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

.rename-btn:hover {
  opacity: 0.9;
}
</style>
