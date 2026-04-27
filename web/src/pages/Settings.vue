<template>
  <Layout>
    <div class="page-header">
      <h1 class="page-title">应用设置</h1>
    </div>

    <!-- API Settings Form -->
    <div class="settings-card">
      <h2 class="section-title">API 设置</h2>
      <form @submit.prevent="saveSettings">
        <div class="form-group">
          <label class="form-label">API Base URL</label>
          <input 
            v-model="form.api_base" 
            type="text" 
            class="input w-full"
            placeholder="https://api.deepseek.com"
            required
          />
        </div>
        <div class="form-group">
          <label class="form-label">API Model</label>
          <input 
            v-model="form.api_model" 
            type="text" 
            class="input w-full"
            placeholder="deepseek-chat"
            required
          />
        </div>
        <div class="form-group">
          <label class="form-label">API Key</label>
          <div class="input-with-icon">
            <input 
              v-model="form.api_key" 
              :type="showApiKey ? 'text' : 'password'" 
              class="input flex-1"
              placeholder="API Key"
              required
            />
            <button 
              type="button" 
              @click="showApiKey = !showApiKey" 
              class="btn btn-outline"
            >
              <svg v-if="!showApiKey" class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
              <svg v-else class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                <line x1="1" y1="1" x2="23" y2="23"></line>
              </svg>
            </button>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">默认 SSH 端口</label>
          <input 
            v-model.number="form.default_ssh_port" 
            type="number" 
            class="input w-full"
            placeholder="22"
            required
          />
        </div>
        <div class="form-actions">
          <button type="button" @click="testApiConnection" class="btn btn-outline" :disabled="testing">
            <span v-if="testing" class="flex items-center">
              <svg class="spinner-sm" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="31.4" stroke-dashoffset="0">
                  <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite"/>
                </circle>
              </svg>
              测试中...
            </span>
            <span v-else>测试连通</span>
          </button>
          <button type="submit" class="btn btn-primary" :disabled="saving">
            <span v-if="saving" class="flex items-center">
              <svg class="spinner-sm" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="31.4" stroke-dashoffset="0">
                  <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite"/>
                </circle>
              </svg>
              保存中...
            </span>
            <span v-else>保存设置</span>
          </button>
        </div>
      </form>
    </div>

    <!-- API Test Result -->
    <div v-if="apiTestResult" class="alert" :class="apiTestResult.ok ? 'alert-success' : 'alert-danger'">
      <svg v-if="apiTestResult.ok" class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"></circle>
        <path d="M9 12l2 2 4-4"></path>
      </svg>
      <svg v-else class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="15" y1="9" x2="9" y2="15"></line>
        <line x1="9" y1="9" x2="15" y2="15"></line>
      </svg>
      <div>
        <h3 class="alert-title">{{ apiTestResult.ok ? '连接成功' : '连接失败' }}</h3>
        <p class="alert-message">{{ apiTestResult.message }}</p>
      </div>
    </div>

    <!-- System Info -->
    <div class="settings-card">
      <h2 class="section-title">系统信息</h2>
      <div class="info-grid">
        <div class="info-item">
          <h3 class="info-item-label">前端版本</h3>
          <p class="info-item-value">1.0.0</p>
        </div>
        <div class="info-item">
          <h3 class="info-item-label">后端版本</h3>
          <p class="info-item-value">0.1.0</p>
        </div>
        <div class="info-item">
          <h3 class="info-item-label">浏览器</h3>
          <p class="info-item-value">{{ browserInfo }}</p>
        </div>
        <div class="info-item">
          <h3 class="info-item-label">系统</h3>
          <p class="info-item-value">{{ systemInfo }}</p>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Layout from '../components/layout/Layout.vue'
import { useSettingsStore } from '../stores/settings'
import { settingsApi } from '../services/api'

const settingsStore = useSettingsStore()

const form = ref({
  api_base: 'https://api.deepseek.com',
  api_model: 'deepseek-chat',
  api_key: '',
  default_ssh_port: 22
})

const showApiKey = ref(false)
const saving = ref(false)
const testing = ref(false)
const apiTestResult = ref(null)

// 浏览器信息
const browserInfo = ref('')
// 系统信息
const systemInfo = ref('')

// 加载设置
onMounted(async () => {
  await settingsStore.fetchSettings()
  form.value = {
    api_base: settingsStore.settings.api_base,
    api_model: settingsStore.settings.api_model,
    api_key: settingsStore.settings.api_key,
    default_ssh_port: settingsStore.settings.default_ssh_port
  }
  
  // 获取浏览器和系统信息
  browserInfo.value = navigator.userAgent
  systemInfo.value = `${navigator.platform} ${navigator.language}`
})

// 保存设置
const saveSettings = async () => {
  saving.value = true
  try {
    await settingsStore.updateSettings(form.value)
    alert('设置保存成功')
  } catch (error) {
    console.error('保存设置失败:', error)
    alert('保存设置失败: ' + error.message)
  } finally {
    saving.value = false
  }
}

// 测试API连接
const testApiConnection = async () => {
  testing.value = true
  try {
    const result = await settingsApi.testApiConnection(form.value)
    apiTestResult.value = result.data
  } catch (error) {
    console.error('测试API连接失败:', error)
    apiTestResult.value = {
      ok: false,
      message: error.message
    }
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.settings-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 20px;
}

.section-title {
  font-size: 18px;
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

.input-with-icon {
  display: flex;
  gap: 8px;
  align-items: center;
}

.icon-sm {
  width: 16px;
  height: 16px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.alert {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: var(--radius-md);
  margin-bottom: 20px;
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
  font-size: 13px;
  color: var(--text-secondary);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.info-item {
  background: var(--bg-input);
  border-radius: var(--radius-md);
  padding: 12px;
}

.info-item-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-item-value {
  font-size: 13px;
  color: var(--text-primary);
  word-break: break-all;
}

.spinner-sm {
  width: 16px;
  height: 16px;
  margin-right: 8px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.flex {
  display: flex;
}

.items-center {
  align-items: center;
}

@media (max-width: 768px) {
  .info-grid {
    grid-template-columns: 1fr;
  }

  .form-actions {
    flex-direction: column;
  }

  .form-actions .btn {
    width: 100%;
  }
}
</style>