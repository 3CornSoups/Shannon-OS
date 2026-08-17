<template>
  <Layout>
    <div class="page-header">
      <h1 class="page-title">执行计划模板</h1>
      <div class="flex items-center gap-2">
        <TerminalButton v-if="isMobile" />
        <NotificationBell v-if="isMobile" />
        <button class="btn btn-primary" @click="openAddModal">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          添加模板
        </button>
      </div>
    </div>

    <!-- Search & Filter -->
    <div class="search-card">
      <div class="search-row">
        <div class="search-input-wrap">
          <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input 
            v-model="searchKeyword" 
            type="text" 
            class="input search-input"
            placeholder="搜索模板名称或描述"
          />
        </div>
        <div class="select-wrap">
          <select v-model="selectedCategory" class="input w-full">
            <option value="">所有分类</option>
            <option v-for="category in categories" :key="category" :value="category">
              {{ category }}
            </option>
          </select>
        </div>
        <div>
          <button class="btn btn-outline" @click="clearSearch">重置</button>
        </div>
      </div>
    </div>

    <!-- Template Grid -->
    <div class="template-grid">
      <div v-for="template in filteredTemplates" :key="template.id" class="template-card">
        <div class="template-header">
          <div>
            <span class="template-category">{{ template.category }}</span>
            <h3 class="template-name">{{ template.name }}</h3>
          </div>
          <div class="template-actions">
            <button class="action-btn" @click="editTemplate(template)" title="编辑">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
              </svg>
            </button>
            <button class="action-btn delete" @click="deleteTemplate(template.id)" title="删除">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        </div>
        <p class="template-desc">{{ template.description }}</p>
        <div class="template-code">
          <pre>{{ template.prompt }}</pre>
        </div>
        <div class="template-footer">
          <button class="btn btn-outline" @click="useTemplate(template)">使用模板</button>
        </div>
      </div>
    </div>

    <!-- Add/Edit Modal -->
    <div v-if="showAddModal || showEditModal" class="modal-overlay" @click.self="cancelEdit">
      <div class="modal">
        <h2 class="modal-title">{{ showEditModal ? '编辑模板' : '添加模板' }}</h2>

        <!-- AI 生成区域 -->
        <div class="ai-section">
          <label class="form-label">自然语言描述（AI 生成）</label>
          <div class="ai-row">
            <input v-model="aiDescription" type="text" class="input w-full" placeholder="例如：帮我创建一个安装 mysql 的模板" @keydown.enter.prevent="generateWithAI" />
            <button type="button" class="btn btn-outline" @click="generateWithAI" :disabled="aiGenerating || !aiDescription.trim()">
              <svg v-if="aiGenerating" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" class="loading-spinner"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/></svg>
              <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
              {{ aiGenerating ? '生成中...' : 'AI 生成' }}
            </button>
          </div>
          <p v-if="aiError" class="ai-error">{{ aiError }}</p>
        </div>

        <div class="ai-divider"><span>或手动填写</span></div>

        <form @submit.prevent="saveTemplate">
          <div class="form-group">
            <label class="form-label">名称</label>
            <input v-model="form.name" type="text" class="input w-full" placeholder="模板名称" required />
          </div>
          <div class="form-group">
            <label class="form-label">分类</label>
            <select v-model="form.category" class="input w-full" required>
              <option value="">选择分类</option>
              <option v-for="category in categories" :key="category" :value="category">
                {{ category }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">描述</label>
            <input v-model="form.description" type="text" class="input w-full" placeholder="模板描述" required />
          </div>
          <div class="form-group">
            <label class="form-label">执行命令</label>
            <textarea v-model="form.prompt" class="input w-full resize-none h-32" placeholder="执行命令或问题" required></textarea>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-outline" @click="cancelEdit">取消</button>
            <button type="submit" class="btn btn-primary">保存</button>
          </div>
        </form>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import Layout from '../components/layout/Layout.vue'
import { useTemplateStore } from '../stores/template'
import { settingsApi } from '../services/api'
import NotificationBell from '../components/NotificationBell.vue'
import TerminalButton from '../components/TerminalButton.vue'
import { useIsMobile } from '../composables/useIsMobile'

const router = useRouter()
const templateStore = useTemplateStore()
const { isMobile } = useIsMobile()

const showAddModal = ref(false)
const showEditModal = ref(false)
const searchKeyword = ref('')
const selectedCategory = ref('')

const form = ref({
  name: '',
  category: '',
  description: '',
  prompt: ''
})

const currentEditId = ref(null)

// AI 生成
const aiDescription = ref('')
const aiGenerating = ref(false)
const aiError = ref('')

const templates = computed(() => templateStore.templates)
const categories = computed(() => templateStore.categories)

const filteredTemplates = computed(() => {
  let result = templates.value
  
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(template => 
      template.name.toLowerCase().includes(keyword) ||
      template.description.toLowerCase().includes(keyword) ||
      template.prompt.toLowerCase().includes(keyword)
    )
  }
  
  if (selectedCategory.value) {
    result = result.filter(template => template.category === selectedCategory.value)
  }
  
  return result
})

const openAddModal = () => {
  resetForm()
  aiDescription.value = ''
  aiError.value = ''
  showAddModal.value = true
  showEditModal.value = false
}

const editTemplate = (template) => {
  form.value = {
    name: template.name,
    category: template.category,
    description: template.description,
    prompt: template.prompt
  }
  currentEditId.value = template.id
  aiDescription.value = ''
  aiError.value = ''
  showEditModal.value = true
  showAddModal.value = false
}

const cancelEdit = () => {
  showAddModal.value = false
  showEditModal.value = false
  resetForm()
  aiDescription.value = ''
  aiError.value = ''
}

const resetForm = () => {
  form.value = {
    name: '',
    category: '',
    description: '',
    prompt: ''
  }
  currentEditId.value = null
}

const saveTemplate = () => {
  if (showEditModal.value && currentEditId.value) {
    templateStore.updateTemplate(currentEditId.value, form.value)
  } else {
    templateStore.addTemplate(form.value)
  }
  cancelEdit()
}

const deleteTemplate = (id) => {
  if (confirm('确定要删除这个模板吗？')) {
    templateStore.deleteTemplate(id)
  }
}

const useTemplate = (template) => {
  router.push('/')
  localStorage.setItem('selectedTemplate', JSON.stringify(template))
}

const clearSearch = () => {
  searchKeyword.value = ''
  selectedCategory.value = ''
}

const generateWithAI = async () => {
  if (!aiDescription.value.trim()) return
  aiGenerating.value = true
  aiError.value = ''
  try {
    const response = await settingsApi.generateTemplate(aiDescription.value.trim())
    const data = response.data
    if (data.ok && data.template) {
      const t = data.template
      form.value = {
        name: t.name || '',
        category: t.category || '',
        description: t.description || '',
        prompt: t.prompt || ''
      }
    } else {
      aiError.value = data.message || '生成失败'
    }
  } catch (error) {
    aiError.value = error.response?.data?.detail || error.message || '请求失败'
  } finally {
    aiGenerating.value = false
  }
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

.search-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 16px;
  margin-bottom: 20px;
}

.search-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-input-wrap {
  flex: 1;
  position: relative;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  color: var(--text-tertiary);
  pointer-events: none;
}

.search-input {
  padding-left: 36px;
}

.select-wrap {
  width: 100%;
  max-width: 192px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.template-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  transition: all 0.2s ease;
}

.template-card:hover {
  border-color: var(--primary);
  box-shadow: var(--shadow-md);
}

.template-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.template-category {
  display: inline-block;
  font-size: 11px;
  font-weight: 500;
  color: var(--primary);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.template-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.template-actions {
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

.template-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 12px;
  line-height: 1.5;
}

.template-code {
  background: var(--bg-input);
  border-radius: var(--radius-md);
  padding: 12px;
  margin-bottom: 16px;
}

.template-code pre {
  font-size: 12px;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
  color: var(--success);
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  line-height: 1.5;
}

.template-footer {
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

/* AI 生成区域 */
.ai-section {
  margin-bottom: 8px;
}

.ai-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.ai-error {
  font-size: 12px;
  color: var(--danger);
  margin-top: 4px;
}

.ai-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 16px 0;
  color: var(--text-tertiary);
  font-size: 12px;
}

.ai-divider::before,
.ai-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--bg-border);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

@media (max-width: 768px) {
  .search-row {
    flex-direction: column;
    align-items: stretch;
  }

  .select-wrap {
    max-width: none;
  }

  .template-grid {
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