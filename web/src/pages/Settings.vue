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

    <!-- 通知设置 -->
    <div class="settings-card mt-6">
      <h2 class="section-title">通知设置</h2>

      <!-- 钉钉配置 -->
      <div class="mb-6 p-4 bg-gray-50 rounded-lg">
        <h3 class="text-sm font-semibold text-gray-700 mb-3">钉钉机器人</h3>
        <div class="space-y-3">
          <div>
            <label class="form-label text-xs">Webhook URL</label>
            <input v-model="notifyForm.dingtalk_webhook_url" class="input w-full" placeholder="https://oapi.dingtalk.com/robot/send?access_token=xxx" />
          </div>
          <div>
            <label class="form-label text-xs">签名密钥（可选）</label>
            <input :type="showDingSecret ? 'text' : 'password'" v-model="notifyForm.dingtalk_secret" class="input w-full" placeholder="SEC..." />
          </div>
          <button @click="testNotification('dingtalk')" class="btn btn-outline text-xs" :disabled="testingChannel !== null">
            {{ testingChannel === 'dingtalk' ? '测试中...' : '测试发送' }}
          </button>
        </div>
      </div>

      <!-- 邮件配置 -->
      <div class="mb-6 p-4 bg-gray-50 rounded-lg">
        <h3 class="text-sm font-semibold text-gray-700 mb-3">邮件通知</h3>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label text-xs">SMTP 服务器</label>
            <input v-model="notifyForm.smtp_host" class="input w-full" placeholder="smtp.qq.com" />
          </div>
          <div>
            <label class="form-label text-xs">端口</label>
            <input v-model="notifyForm.smtp_port" class="input w-full" placeholder="465" />
          </div>
          <div>
            <label class="form-label text-xs">发件人邮箱</label>
            <input v-model="notifyForm.smtp_username" class="input w-full" placeholder="sender@qq.com" />
          </div>
          <div>
            <label class="form-label text-xs">SMTP 密码/授权码</label>
            <input :type="showMailPwd ? 'text' : 'password'" v-model="notifyForm.smtp_password" class="input w-full" placeholder="授权码" />
          </div>
        </div>
        <div class="mt-3">
          <label class="form-label text-xs">收件人列表（逗号分隔）</label>
          <input v-model="notifyForm.smtp_recipients" class="input w-full" placeholder="admin@qq.com, ops@qq.com" />
        </div>
        <button @click="testNotification('email')" class="btn btn-outline text-xs mt-3" :disabled="testingChannel !== null">
          {{ testingChannel === 'email' ? '测试中...' : '测试发送' }}
        </button>
      </div>

      <!-- Webhook 配置 -->
      <div class="mb-6 p-4 bg-gray-50 rounded-lg">
        <h3 class="text-sm font-semibold text-gray-700 mb-3">Webhook</h3>
        <div class="space-y-3">
          <div>
            <label class="form-label text-xs">回调 URL</label>
            <input v-model="notifyForm.webhook_url" class="input w-full" placeholder="https://your-system.com/alert-callback" />
          </div>
          <div>
            <label class="form-label text-xs">自定义 Headers（JSON 格式）</label>
            <input v-model="notifyForm.webhook_headers" class="input w-full" placeholder='{"Authorization": "Bearer xxx"}' />
          </div>
          <button @click="testNotification('webhook')" class="btn btn-outline text-xs" :disabled="testingChannel !== null">
            {{ testingChannel === 'webhook' ? '测试中...' : '测试发送' }}
          </button>
        </div>
      </div>

      <div class="form-actions">
        <button @click="saveNotificationSettings" class="btn btn-primary" :disabled="savingNotify">
          {{ savingNotify ? '保存中...' : '保存通知设置' }}
        </button>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import Layout from '../components/layout/Layout.vue'
import { useSettingsStore } from '../stores/settings'
import { settingsApi } from '../services/api'
import axios from 'axios'

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

const notifyForm = reactive({
  dingtalk_webhook_url: '',
  dingtalk_secret: '',
  smtp_host: '',
  smtp_port: '465',
  smtp_username: '',
  smtp_password: '',
  smtp_recipients: '',
  webhook_url: '',
  webhook_headers: '',
})
const showDingSecret = ref(false)
const showMailPwd = ref(false)
const savingNotify = ref(false)
const testingChannel = ref(null)

async function loadNotificationSettings() {
  try {
    const res = await axios.get('/api/settings/notifications')
    if (res.data?.ok) {
      Object.assign(notifyForm, res.data.data)
    }
  } catch (e) { console.error('加载通知设置失败:', e) }
}

async function saveNotificationSettings() {
  savingNotify.value = true
  try {
    await axios.put('/api/settings/notifications', notifyForm)
    alert('通知设置已保存')
  } catch (e) { alert('保存失败: ' + e.message) }
  finally { savingNotify.value = false }
}

async function testNotification(channel) {
  testingChannel.value = channel
  try {
    const payload = { channel, ...notifyForm }
    const res = await axios.post('/api/settings/notifications/test', payload)
    alert(res.data?.message || '测试完成')
  } catch (e) { alert('测试失败: ' + e.message) }
  finally { testingChannel.value = null }
}

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
  loadNotificationSettings()
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