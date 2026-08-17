<template>
  <Layout>
    <div class="page-header flex justify-between items-center">
      <h1 class="page-title">告警中心</h1>
      <div class="flex items-center gap-2">
        <TerminalButton v-if="isMobile" />
        <NotificationBell v-if="isMobile" />
        <router-link to="/alerts/rules" class="btn btn-outline text-sm">告警规则管理 →</router-link>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-4 gap-4 mb-6">
      <div class="bg-white rounded-lg border border-gray-200 p-4 shadow-sm text-center">
        <div class="text-2xl font-bold text-gray-800">{{ stats.total }}</div>
        <div class="text-xs text-gray-500 mt-1">今日总告警</div>
      </div>
      <div class="bg-white rounded-lg border border-gray-200 p-4 shadow-sm text-center">
        <div class="text-2xl font-bold text-red-600">{{ stats.critical }}</div>
        <div class="text-xs text-gray-500 mt-1">严重</div>
      </div>
      <div class="bg-white rounded-lg border border-gray-200 p-4 shadow-sm text-center">
        <div class="text-2xl font-bold text-yellow-600">{{ stats.warning }}</div>
        <div class="text-xs text-gray-500 mt-1">警告</div>
      </div>
      <div class="bg-white rounded-lg border border-gray-200 p-4 shadow-sm text-center">
        <div class="text-2xl font-bold text-green-600">{{ stats.recovered }}</div>
        <div class="text-xs text-gray-500 mt-1">已恢复</div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="bg-white rounded-lg border border-gray-200 p-4 mb-4 shadow-sm flex flex-wrap gap-4 items-center">
      <select v-model="filters.status" class="input text-sm w-32">
        <option value="">全部状态</option>
        <option value="alerting">告警中</option>
        <option value="acknowledged">已确认</option>
        <option value="recovered">已恢复</option>
        <option value="archived">已归档</option>
      </select>
      <select v-model="filters.severity" class="input text-sm w-28">
        <option value="">全部级别</option>
        <option value="critical">严重</option>
        <option value="warning">警告</option>
        <option value="info">通知</option>
      </select>
      <button @click="fetchAlerts" class="btn btn-outline text-sm">查询</button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-10">
      <div class="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500 border-t-transparent"></div>
    </div>

    <!-- 告警列表 -->
    <div v-else class="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
      <table class="w-full mobile-cards-table">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr class="text-left text-xs text-gray-500 uppercase">
            <th class="px-4 py-3">级别</th>
            <th class="px-4 py-3">规则</th>
            <th class="px-4 py-3">服务器</th>
            <th class="px-4 py-3">当前值</th>
            <th class="px-4 py-3">阈值</th>
            <th class="px-4 py-3">触发时间</th>
            <th class="px-4 py-3">状态</th>
            <th class="px-4 py-3">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in items" :key="a.id" class="border-b border-gray-100 hover:bg-gray-50">
            <td class="px-4 py-3" data-label="级别">
              <span class="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full"
                :class="severityClass(a.severity)">
                {{ severityLabel(a.severity) }}
              </span>
            </td>
            <td class="px-4 py-3 text-sm text-gray-700" data-label="规则">{{ a.rule_name }}</td>
            <td class="px-4 py-3 text-sm text-gray-500" data-label="服务器">{{ a.host_name || a.host_ip }}</td>
            <td class="px-4 py-3 text-sm font-mono" data-label="当前值">{{ a.current_value }}</td>
            <td class="px-4 py-3 text-sm font-mono text-gray-400" data-label="阈值">{{ a.threshold }}</td>
            <td class="px-4 py-3 text-xs text-gray-400" data-label="触发时间">{{ a.triggered_at }}</td>
            <td class="px-4 py-3" data-label="状态">
              <span class="text-xs px-2 py-0.5 rounded-full" :class="statusClass(a.status)">
                {{ statusLabel(a.status) }}
              </span>
            </td>
            <td class="px-4 py-3" data-label="操作">
              <button v-if="a.status === 'alerting'" @click="acknowledge(a.id)" class="text-xs text-indigo-600 hover:text-indigo-800 mr-2">确认</button>
              <button v-if="a.status === 'recovered' || a.status === 'acknowledged'" @click="archive(a.id)" class="text-xs text-gray-400 hover:text-gray-600">归档</button>
            </td>
          </tr>
          <tr v-if="items.length === 0">
            <td colspan="8" class="px-4 py-10 text-center text-gray-400">暂无告警记录</td>
          </tr>
        </tbody>
      </table>
      <div v-if="total > pageSize" class="flex justify-between items-center px-4 py-3 border-t border-gray-200 text-sm text-gray-500">
        <span>共 {{ total }} 条</span>
        <div class="flex gap-2">
          <button :disabled="page === 1" @click="page--; fetchAlerts()" class="btn btn-outline text-xs px-3 py-1">上一页</button>
          <button :disabled="page * pageSize >= total" @click="page++; fetchAlerts()" class="btn btn-outline text-xs px-3 py-1">下一页</button>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import Layout from '../components/layout/Layout.vue'
import NotificationBell from '../components/NotificationBell.vue'
import TerminalButton from '../components/TerminalButton.vue'
import { useIsMobile } from '../composables/useIsMobile'

const { isMobile } = useIsMobile()
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(true)
const filters = reactive({ status: '', severity: '' })
const stats = ref({ total: 0, critical: 0, warning: 0, info: 0, recovered: 0 })
let refreshTimer = null

function severityClass(s) { return { critical: 'bg-red-50 text-red-700', warning: 'bg-yellow-50 text-yellow-700', info: 'bg-blue-50 text-blue-700' }[s] || '' }
function severityLabel(s) { return { critical: '严重', warning: '警告', info: '通知' }[s] || s }
function statusClass(s) { return { alerting: 'bg-red-50 text-red-600', acknowledged: 'bg-blue-50 text-blue-600', recovered: 'bg-green-50 text-green-600', archived: 'bg-gray-100 text-gray-500' }[s] || '' }
function statusLabel(s) { return { alerting: '告警中', acknowledged: '已确认', recovered: '已恢复', archived: '已归档' }[s] || s }

async function fetchAlerts() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filters.status) params.status = filters.status
    if (filters.severity) params.severity = filters.severity
    const res = await axios.get('/api/alerts', { params })
    if (res.data?.ok) {
      items.value = res.data.data.items || []
      total.value = res.data.data.total || 0
    }
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

async function fetchStats() {
  try {
    const res = await axios.get('/api/alerts/stats')
    if (res.data?.ok) stats.value = res.data.data
  } catch (e) { console.error(e) }
}

async function acknowledge(id) {
  try {
    await axios.post(`/api/alerts/${id}/acknowledge`)
    fetchAlerts()
  } catch (e) { alert('操作失败') }
}

async function archive(id) {
  try {
    await axios.post(`/api/alerts/${id}/archive`)
    fetchAlerts()
  } catch (e) { alert('操作失败') }
}

onMounted(() => {
  fetchStats()
  fetchAlerts()
  refreshTimer = setInterval(() => {
    fetchStats()
    fetchAlerts()
  }, 5000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>
