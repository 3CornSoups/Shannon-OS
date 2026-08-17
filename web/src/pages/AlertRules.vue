<template>
  <Layout>
    <div class="page-header flex justify-between items-center">
      <div>
        <h1 class="page-title">告警规则</h1>
        <p class="text-sm text-gray-500 mt-1">管理监控告警规则</p>
      </div>
      <div class="flex gap-2">
        <router-link to="/alerts" class="btn btn-outline text-sm">← 告警中心</router-link>
        <button @click="seedRules" class="btn btn-outline text-sm">导入预置规则</button>
        <button @click="showForm = true; editingRule = null" class="btn btn-primary text-sm">新建规则</button>
      </div>
    </div>

    <!-- 规则列表 -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div v-for="rule in rules" :key="rule.id" class="bg-white rounded-lg border border-gray-200 p-5 shadow-sm">
        <div class="flex items-start justify-between mb-2">
          <h3 class="font-semibold text-gray-800">{{ rule.name }}</h3>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" :checked="rule.enabled === 1" @change="toggleRule(rule)" class="sr-only peer">
            <div class="w-9 h-5 bg-gray-200 peer-focus:ring-2 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
          </label>
        </div>
        <div class="flex flex-wrap gap-2 mb-3">
          <span class="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{{ metricLabel(rule.metric_type) }}</span>
          <span class="text-xs font-mono bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{{ rule.operator }} {{ rule.threshold }}</span>
          <span v-if="rule.duration > 0" class="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">持续 {{ rule.duration }}s</span>
          <span class="text-xs px-2 py-0.5 rounded" :class="severityBg(rule.severity)">{{ rule.severity }}</span>
        </div>
        <div class="flex gap-2">
          <button @click="editRule(rule)" class="text-xs text-indigo-600 hover:text-indigo-800">编辑</button>
          <button @click="deleteRule(rule.id)" class="text-xs text-red-500 hover:text-red-700">删除</button>
        </div>
      </div>
      <div v-if="rules.length === 0" class="col-span-2 text-center py-10 text-gray-400">暂无规则，点击"新建规则"或"导入预置规则"</div>
    </div>

    <!-- 新建/编辑弹窗 -->
    <div v-if="showForm" class="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
      <div class="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl">
        <h2 class="text-lg font-semibold mb-4">{{ editingRule ? '编辑规则' : '新建规则' }}</h2>
        <div class="space-y-4">
          <div><label class="form-label">规则名称</label><input v-model="form.name" class="input w-full" required /></div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="form-label">指标类型</label>
              <select v-model="form.metric_type" class="input w-full">
                <option value="cpu">CPU使用率</option>
                <option value="memory">内存使用率</option>
                <option value="disk">磁盘使用率</option>
                <option value="load">系统负载</option>
              </select>
            </div>
            <div>
              <label class="form-label">级别</label>
              <select v-model="form.severity" class="input w-full">
                <option value="critical">严重</option>
                <option value="warning">警告</option>
                <option value="info">通知</option>
              </select>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-2">
            <div>
              <label class="form-label">运算符</label>
              <select v-model="form.operator" class="input w-full">
                <option value=">">&gt;</option>
                <option value="<">&lt;</option>
                <option value=">=">&gt;=</option>
                <option value="<=">&lt;=</option>
              </select>
            </div>
            <div>
              <label class="form-label">阈值</label>
              <input v-model.number="form.threshold" type="number" class="input w-full" />
            </div>
            <div>
              <label class="form-label">持续时间(秒)</label>
              <input v-model.number="form.duration" type="number" class="input w-full" placeholder="0=即时" />
            </div>
          </div>
          <div>
            <label class="form-label">通知渠道</label>
            <div class="flex gap-4 mt-1">
              <label class="flex items-center gap-1 text-sm"><input type="checkbox" value="dingtalk" v-model="form.channels" /> 钉钉</label>
              <label class="flex items-center gap-1 text-sm"><input type="checkbox" value="email" v-model="form.channels" /> 邮件</label>
              <label class="flex items-center gap-1 text-sm"><input type="checkbox" value="webhook" v-model="form.channels" /> Webhook</label>
            </div>
          </div>
        </div>
        <div class="flex justify-end gap-3 mt-6">
          <button @click="showForm = false" class="btn btn-outline">取消</button>
          <button @click="saveRule" class="btn btn-primary">{{ editingRule ? '更新' : '创建' }}</button>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import Layout from '../components/layout/Layout.vue'

const rules = ref([])
const showForm = ref(false)
const editingRule = ref(null)
const form = reactive({ name: '', metric_type: 'cpu', operator: '>', threshold: 90, duration: 0, severity: 'warning', channels: [] })

function metricLabel(t) { return { cpu: 'CPU', memory: '内存', disk: '磁盘', load: '负载' }[t] || t }
function severityBg(s) { return { critical: 'bg-red-100 text-red-700', warning: 'bg-yellow-100 text-yellow-700', info: 'bg-blue-100 text-blue-700' }[s] || '' }

async function fetchRules() {
  try {
    const res = await axios.get('/api/alert-rules')
    if (res.data?.ok) rules.value = res.data.data
  } catch (e) { console.error(e) }
}

function editRule(rule) {
  editingRule.value = rule
  Object.assign(form, {
    name: rule.name, metric_type: rule.metric_type, operator: rule.operator,
    threshold: rule.threshold, duration: rule.duration, severity: rule.severity,
    channels: Array.isArray(rule.channels) ? rule.channels : []
  })
  showForm.value = true
}

async function saveRule() {
  try {
    const payload = { ...form }
    if (editingRule.value) {
      await axios.put(`/api/alert-rules/${editingRule.value.id}`, payload)
    } else {
      await axios.post('/api/alert-rules', payload)
    }
    showForm.value = false
    editingRule.value = null
    fetchRules()
  } catch (e) { alert('保存失败') }
}

async function deleteRule(id) {
  if (!confirm('确定删除此规则？')) return
  try {
    await axios.delete(`/api/alert-rules/${id}`)
    fetchRules()
  } catch (e) { alert('删除失败') }
}

async function toggleRule(rule) {
  try {
    await axios.put(`/api/alert-rules/${rule.id}/toggle`)
    fetchRules()
  } catch (e) { alert('操作失败') }
}

async function seedRules() {
  try {
    const res = await axios.post('/api/alert-rules/seed')
    alert(res.data?.message || '导入完成')
    fetchRules()
  } catch (e) { alert('导入失败') }
}

onMounted(fetchRules)
</script>
