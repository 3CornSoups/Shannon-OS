<template>
  <Layout>
    <div class="page-header">
      <h1 class="page-title">监控仪表盘</h1>
      <p class="text-sm text-gray-500 mt-1">所有服务器健康状态总览</p>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-3 gap-4 mb-6">
      <div class="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-3 h-3 rounded-full bg-green-500"></div>
          <div>
            <div class="text-2xl font-bold text-gray-800">{{ healthyCount }}</div>
            <div class="text-xs text-gray-500">正常</div>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-3 h-3 rounded-full bg-yellow-500"></div>
          <div>
            <div class="text-2xl font-bold text-gray-800">{{ warningCount }}</div>
            <div class="text-xs text-gray-500">警告</div>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-3 h-3 rounded-full bg-red-500"></div>
          <div>
            <div class="text-2xl font-bold text-gray-800">{{ criticalCount }}</div>
            <div class="text-xs text-gray-500">严重</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center items-center py-20">
      <div class="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500 border-t-transparent"></div>
      <span class="ml-3 text-gray-500">加载中...</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loading && overview.length === 0" class="text-center py-20 bg-white rounded-lg border border-gray-200">
      <svg class="mx-auto mb-4 text-gray-300" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
        <line x1="8" y1="21" x2="16" y2="21"></line>
        <line x1="12" y1="17" x2="12" y2="21"></line>
      </svg>
      <p class="text-gray-400">暂无监控数据，请先添加服务器并等待采集</p>
    </div>

    <!-- 服务器卡片网格 -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <div
        v-for="item in overview"
        :key="item.host_id"
        class="bg-white rounded-lg border border-gray-200 p-5 shadow-sm hover:shadow-md hover:border-indigo-200 transition-all cursor-pointer"
        @click="goToMonitor(item.host_id)"
      >
        <div class="flex items-start justify-between mb-3">
          <div class="flex-1 min-w-0">
            <h3 class="font-semibold text-gray-800 truncate">{{ item.host_name }}</h3>
            <p class="text-xs text-gray-400 mt-0.5">{{ item.host_ip }}</p>
          </div>
          <span
            class="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium"
            :class="statusBadgeClass(item.status)"
          >
            <span class="w-2 h-2 rounded-full" :class="statusDotClass(item.status)"></span>
            {{ statusLabel(item.status) }}
          </span>
        </div>

        <!-- 指标进度条 -->
        <div class="space-y-3 mb-4">
          <div v-if="item.cpu_usage !== null">
            <div class="flex justify-between text-xs text-gray-500 mb-1">
              <span>CPU</span>
              <span>{{ item.cpu_usage }}%</span>
            </div>
            <div class="w-full bg-gray-100 rounded-full h-2">
              <div class="h-2 rounded-full transition-all" :class="progressColor(item.cpu_usage)" :style="{ width: item.cpu_usage + '%' }"></div>
            </div>
          </div>
          <div v-if="item.memory_usage !== null">
            <div class="flex justify-between text-xs text-gray-500 mb-1">
              <span>内存</span>
              <span>{{ item.memory_usage }}%</span>
            </div>
            <div class="w-full bg-gray-100 rounded-full h-2">
              <div class="h-2 rounded-full transition-all" :class="progressColor(item.memory_usage)" :style="{ width: item.memory_usage + '%' }"></div>
            </div>
          </div>
          <div v-if="item.disk_usage !== null">
            <div class="flex justify-between text-xs text-gray-500 mb-1">
              <span>磁盘</span>
              <span>{{ item.disk_usage }}%</span>
            </div>
            <div class="w-full bg-gray-100 rounded-full h-2">
              <div class="h-2 rounded-full transition-all" :class="progressColor(item.disk_usage)" :style="{ width: item.disk_usage + '%' }"></div>
            </div>
          </div>
          <div v-if="item.cpu_usage === null" class="text-xs text-gray-300 italic">等待首次采集...</div>
        </div>

        <!-- 底部信息 -->
        <div class="flex items-center justify-between text-xs text-gray-400 border-t border-gray-100 pt-3">
          <span v-if="item.last_collected_at">采集: {{ item.last_collected_at }}</span>
          <span v-else>未采集</span>
          <span
            v-if="item.active_alerts > 0"
            class="inline-flex items-center justify-center bg-red-100 text-red-600 px-2 py-0.5 rounded-full font-medium text-xs"
          >
            {{ item.active_alerts }} 条告警
          </span>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import Layout from '../components/layout/Layout.vue'

const router = useRouter()
const overview = ref([])
const loading = ref(true)
let timer = null

const healthyCount = computed(() => overview.value.filter(i => i.status === 'healthy').length)
const warningCount = computed(() => overview.value.filter(i => i.status === 'warning').length)
const criticalCount = computed(() => overview.value.filter(i => i.status === 'critical').length)

function statusBadgeClass(status) {
  return {
    healthy: 'bg-green-50 text-green-700',
    warning: 'bg-yellow-50 text-yellow-700',
    critical: 'bg-red-50 text-red-700',
  }[status] || 'bg-gray-50 text-gray-500'
}
function statusDotClass(status) {
  return {
    healthy: 'bg-green-500',
    warning: 'bg-yellow-500',
    critical: 'bg-red-500',
  }[status] || 'bg-gray-400'
}
function statusLabel(status) {
  return {
    healthy: '正常',
    warning: '警告',
    critical: '严重',
  }[status] || '未知'
}
function progressColor(val) {
  if (val >= 90) return 'bg-red-500'
  if (val >= 70) return 'bg-yellow-500'
  return 'bg-green-500'
}
function goToMonitor(hostId) {
  router.push('/monitoring')
}

async function fetchOverview() {
  try {
    const res = await axios.get('/api/monitor/overview')
    if (res.data?.ok) {
      overview.value = res.data.data || []
    }
  } catch (e) {
    console.error('获取监控概览失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchOverview()
  timer = setInterval(fetchOverview, 30000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
