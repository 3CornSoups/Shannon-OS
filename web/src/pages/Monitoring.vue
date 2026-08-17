<template>
  <Layout>
    <div class="page-header">
      <h1 class="page-title">系统监控</h1>
      <div class="page-actions">
        <div class="server-selector">
          <span class="server-label">当前服务器</span>
          <span class="server-name">{{ currentServer ? currentServer.name : '未选择' }}</span>
        </div>
        <button @click="router.push('/servers')" class="btn btn-outline">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
            <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
            <line x1="6" y1="6" x2="6.01" y2="6"/>
            <line x1="6" y1="18" x2="6.01" y2="18"/>
          </svg>
          选择服务器
        </button>
        <TerminalButton v-if="isMobile" />
        <NotificationBell v-if="isMobile" />
      </div>
    </div>

    <div v-if="!currentServer" class="empty-state">
      <div class="empty-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
          <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
          <line x1="6" y1="6" x2="6.01" y2="6"/>
          <line x1="6" y1="18" x2="6.01" y2="18"/>
        </svg>
      </div>
      <h2 class="empty-title">请选择服务器</h2>
      <p class="empty-desc">要查看系统监控数据，请先选择一个服务器</p>
      <button @click="router.push('/servers')" class="btn btn-primary btn-lg">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
          <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
          <line x1="6" y1="6" x2="6.01" y2="6"/>
          <line x1="6" y1="18" x2="6.01" y2="18"/>
        </svg>
        管理服务器
      </button>
    </div>

    <div v-if="error && !systemData.cpu.usage_percent" class="error-state">
      <div class="error-icon">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
      </div>
      <h3 class="error-title">数据采集失败</h3>
      <p class="error-message">{{ error }}</p>
      <button @click="fetchMonitorData" class="btn btn-primary">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="23,4 23,10 17,10"/>
          <polyline points="1,20 1,14 7,14"/>
          <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
        </svg>
        重新采集
      </button>
    </div>

    <div v-if="currentServer" class="dashboard">
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-header">
            <span class="stat-label">CPU 使用率</span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="stat-icon-primary">
              <rect x="4" y="4" width="16" height="16" rx="2" ry="2"/>
              <rect x="9" y="9" width="6" height="6"/>
              <line x1="9" y1="1" x2="9" y2="4"/>
              <line x1="15" y1="1" x2="15" y2="4"/>
              <line x1="9" y1="20" x2="9" y2="23"/>
              <line x1="15" y1="20" x2="15" y2="23"/>
              <line x1="20" y1="9" x2="23" y2="9"/>
              <line x1="20" y1="14" x2="23" y2="14"/>
              <line x1="1" y1="9" x2="4" y2="9"/>
              <line x1="1" y1="14" x2="4" y2="14"/>
            </svg>
          </div>
          <div class="stat-value-row">
            <span class="stat-value">{{ systemData.cpu.usage_percent }}%</span>
            <span class="stat-unit">{{ systemData.cpu.cpu_count }} 核心</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill progress-primary" :style="{ width: systemData.cpu.usage_percent + '%' }"></div>
          </div>
          <div class="stat-footer">
            <span>负载</span>
            <span class="font-mono">{{ systemData.cpu.load_avg_1 }} / {{ systemData.cpu.load_avg_5 }} / {{ systemData.cpu.load_avg_15 }}</span>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-header">
            <span class="stat-label">内存使用率</span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="stat-icon-success">
              <rect x="2" y="6" width="20" height="12" rx="2"/>
              <line x1="6" y1="12" x2="6.01" y2="12"/>
              <line x1="10" y1="12" x2="10.01" y2="12"/>
              <line x1="14" y1="12" x2="14.01" y2="12"/>
              <line x1="18" y1="12" x2="18.01" y2="12"/>
            </svg>
          </div>
          <div class="stat-value-row">
            <span class="stat-value">{{ systemData.memory.usage_percent }}%</span>
            <span class="stat-unit">{{ systemData.memory.used }} / {{ systemData.memory.total }}</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill progress-success" :style="{ width: systemData.memory.usage_percent + '%' }"></div>
          </div>
          <div class="stat-footer-row">
            <div class="stat-footer">
              <span>缓存</span>
              <span>{{ systemData.memory.cached }}</span>
            </div>
            <div class="stat-footer">
              <span>Swap</span>
              <span>{{ systemData.memory.swap_used }} / {{ systemData.memory.swap_total }} ({{ systemData.memory.swap_percent }}%)</span>
            </div>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-header">
            <span class="stat-label">磁盘使用率</span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="stat-icon-warning">
              <rect x="2" y="2" width="20" height="20" rx="2"/>
              <line x1="2" y1="12" x2="22" y2="12"/>
              <line x1="12" y1="2" x2="12" y2="22"/>
            </svg>
          </div>
          <div class="stat-value-row">
            <span class="stat-value">{{ mainDiskUsage }}%</span>
            <span class="stat-unit">{{ mainDiskUsed }} / {{ mainDiskTotal }}</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" :class="mainDiskUsage > 90 ? 'progress-danger' : mainDiskUsage > 70 ? 'progress-warning' : 'progress-success'" :style="{ width: mainDiskUsage + '%' }"></div>
          </div>
          <div class="stat-footer">
            <span>分区数</span>
            <span>{{ systemData.disk.partitions.length }}</span>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-header">
            <span class="stat-label">网络流量</span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="stat-icon-info">
              <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
            </svg>
          </div>
          <div class="stat-value-row">
            <span class="stat-value">{{ systemData.network.interfaces.length }}</span>
            <span class="stat-unit">接口</span>
          </div>
          <div class="stat-footer-row">
            <div class="stat-footer">
              <span>总接收</span>
              <span class="text-success">{{ systemData.network.total_rx_formatted }}</span>
            </div>
            <div class="stat-footer">
              <span>总发送</span>
              <span class="text-primary">{{ systemData.network.total_tx_formatted }}</span>
            </div>
          </div>
        </div>
      </div>

    <!-- 历史查询时间选择器 -->
    <div class="flex flex-wrap items-center gap-3 px-4 py-3 bg-white rounded-lg border border-gray-200 mb-4 shadow-sm">
      <span class="text-sm text-gray-600 font-medium">历史趋势：</span>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="opt in timeRangeOptions"
          :key="opt.value"
          @click="selectedTimeRange = opt.value; fetchHistory()"
          class="px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
          :class="selectedTimeRange === opt.value ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
        >
          {{ opt.label }}
        </button>
      </div>
      <div v-if="selectedTimeRange === 'custom'" class="flex items-center gap-2">
        <input type="datetime-local" v-model="customFrom" class="input text-xs w-44" />
        <span class="text-xs text-gray-400">至</span>
        <input type="datetime-local" v-model="customTo" class="input text-xs w-44" />
        <button @click="fetchHistory" class="btn btn-outline text-xs px-3 py-1.5">查询</button>
      </div>
    </div>

      <div class="charts-grid">
        <div class="chart-card">
          <h3 class="chart-title">CPU 核心使用率</h3>
          <div ref="cpuChartRef" class="chart-container"></div>
        </div>
        <div class="chart-card">
          <h3 class="chart-title">内存使用情况</h3>
          <div ref="memoryChartRef" class="chart-container"></div>
        </div>
        <div class="chart-card">
          <h3 class="chart-title">磁盘使用情况</h3>
          <div ref="diskChartRef" class="chart-container"></div>
        </div>
        <div class="chart-card">
          <h3 class="chart-title">网络接口流量</h3>
          <div ref="networkChartRef" class="chart-container"></div>
        </div>
      </div>

      <div class="chart-card full-width">
        <div class="chart-title-row">
          <h3 class="chart-title">CPU 使用率历史趋势</h3>
          <span class="chart-badge">最近 {{ cpuHistory.length }} 次采样</span>
        </div>
        <div ref="cpuHistoryChartRef" class="chart-container"></div>
      </div>

      <div class="chart-card full-width">
        <div class="chart-title-row">
          <h3 class="chart-title">内存使用率历史趋势</h3>
          <span class="chart-badge">最近 {{ memoryHistory.length }} 次采样</span>
        </div>
        <div ref="memoryHistoryChartRef" class="chart-container"></div>
      </div>

      <div class="table-card">
        <div class="table-header">
          <h3 class="table-title">磁盘分区详情</h3>
        </div>
        <table class="data-table mobile-cards">
          <thead>
            <tr>
              <th>文件系统</th>
              <th>挂载点</th>
              <th>总容量</th>
              <th>已使用</th>
              <th>可用</th>
              <th>使用率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="partition in systemData.disk.partitions" :key="partition.mount">
              <td class="font-mono" data-label="文件系统">{{ partition.filesystem }}</td>
              <td class="font-mono" data-label="挂载点">{{ partition.mount }}</td>
              <td data-label="总容量">{{ partition.total }}</td>
              <td data-label="已使用">{{ partition.used }}</td>
              <td data-label="可用">{{ partition.available }}</td>
              <td data-label="使用率">
                <div class="usage-cell">
                  <div class="progress-bar mini">
                    <div class="progress-fill" :class="partition.usage_percent > 90 ? 'progress-danger' : partition.usage_percent > 70 ? 'progress-warning' : 'progress-success'" :style="{ width: partition.usage_percent + '%' }"></div>
                  </div>
                  <span :class="partition.usage_percent > 90 ? 'text-danger' : partition.usage_percent > 70 ? 'text-warning' : 'text-success'">{{ partition.usage_percent }}%</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="table-card">
        <div class="table-header">
          <h3 class="table-title">资源占用 Top 进程</h3>
          <button @click="fetchMonitorData" class="btn btn-outline btn-sm">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="23,4 23,10 17,10"/>
              <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
            </svg>
            刷新
          </button>
        </div>
        <table class="data-table mobile-cards">
          <thead>
            <tr>
              <th>PID</th>
              <th>进程名</th>
              <th>用户</th>
              <th>CPU%</th>
              <th>内存%</th>
              <th>状态</th>
              <th>启动时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="process in systemData.processes.top_processes" :key="process.pid">
              <td class="font-mono" data-label="PID">{{ process.pid }}</td>
              <td class="font-mono" data-label="进程名">{{ process.name }}</td>
              <td data-label="用户">{{ process.user }}</td>
              <td data-label="CPU%">
                <span :class="process.cpu > 50 ? 'text-danger' : process.cpu > 10 ? 'text-warning' : 'text-success'">{{ process.cpu }}%</span>
              </td>
              <td data-label="内存%">
                <span :class="process.memory > 50 ? 'text-danger' : process.memory > 10 ? 'text-warning' : 'text-success'">{{ process.memory }}%</span>
              </td>
              <td data-label="状态">
                <span class="status-badge" :class="process.stat.includes('R') ? 'status-running' : 'status-other'">{{ process.stat }}</span>
              </td>
              <td data-label="启动时间">{{ process.start }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import Layout from '../components/layout/Layout.vue'
import { useServerStore } from '../stores/server'
import { monitoringApi } from '../services/api'
import { ChartManager, ChartOptions } from '../composables/useCharts'
import axios from 'axios'
import NotificationBell from '../components/NotificationBell.vue'
import TerminalButton from '../components/TerminalButton.vue'
import { useIsMobile } from '../composables/useIsMobile'

const router = useRouter()
const serverStore = useServerStore()
const { isMobile } = useIsMobile()

const currentServer = computed(() => serverStore.currentServer)

const systemData = ref({
  cpu: { cpu_count: 0, usage_percent: 0, per_core_usage: [], load_avg_1: 0, load_avg_5: 0, load_avg_15: 0 },
  memory: { total: '0 MB', used: '0 MB', free: '0 MB', buffers: '0 MB', cached: '0 MB', usage_percent: 0, swap_total: '0 MB', swap_used: '0 MB', swap_free: '0 MB', swap_percent: 0 },
  disk: { partitions: [] },
  network: { total_rx: 0, total_tx: 0, total_rx_formatted: '0 B', total_tx_formatted: '0 B', interfaces: [] },
  processes: { top_processes: [], total_count: 0 },
})

const mainDiskUsage = computed(() => {
  if (systemData.value.disk.partitions.length === 0) return 0
  const root = systemData.value.disk.partitions.find(p => p.mount === '/')
  return root ? root.usage_percent : systemData.value.disk.partitions[0].usage_percent
})

const mainDiskUsed = computed(() => {
  if (systemData.value.disk.partitions.length === 0) return '0 GB'
  const root = systemData.value.disk.partitions.find(p => p.mount === '/')
  return root ? root.used : systemData.value.disk.partitions[0].used
})

const mainDiskTotal = computed(() => {
  if (systemData.value.disk.partitions.length === 0) return '0 GB'
  const root = systemData.value.disk.partitions.find(p => p.mount === '/')
  return root ? root.total : systemData.value.disk.partitions[0].total
})

const cpuChartRef = ref(null)
const memoryChartRef = ref(null)
const diskChartRef = ref(null)
const networkChartRef = ref(null)
const cpuHistoryChartRef = ref(null)
const memoryHistoryChartRef = ref(null)

const chartManager = new ChartManager()

const error = ref('')
let refreshTimer = null
let chartsInitialized = false
const cpuHistory = ref([])
const memoryHistory = ref([])
const historyMaxSize = 20

const timeRangeOptions = [
  { label: '15分钟', value: '15m' },
  { label: '1小时', value: '1h' },
  { label: '6小时', value: '6h' },
  { label: '24小时', value: '24h' },
  { label: '7天', value: '7d' },
  { label: '自定义', value: 'custom' },
]
const selectedTimeRange = ref('1h')
const customFrom = ref('')
const customTo = ref('')

function getTimeRange() {
  const now = new Date()
  let from = new Date()
  switch (selectedTimeRange.value) {
    case '15m': from = new Date(now.getTime() - 15 * 60 * 1000); break
    case '1h': from = new Date(now.getTime() - 60 * 60 * 1000); break
    case '6h': from = new Date(now.getTime() - 6 * 60 * 60 * 1000); break
    case '24h': from = new Date(now.getTime() - 24 * 60 * 60 * 1000); break
    case '7d': from = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000); break
    case 'custom':
      if (customFrom.value && customTo.value) {
        return { from: customFrom.value, to: customTo.value }
      }
      from = new Date(now.getTime() - 60 * 60 * 1000)
      break
  }
  return {
    from: formatLocalTime(from),
    to: formatLocalTime(now),
  }
}

function formatLocalTime(d) {
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function fetchHistory() {
  if (!currentServer.value?.id) return
  const { from, to } = getTimeRange()
  try {
    const res = await axios.get(`/api/monitor/history/${currentServer.value.id}`, { params: { from_time: from, to_time: to } })
    if (res.data?.ok) {
      const data = res.data.data
      if (data.timestamps && data.timestamps.length > 0) {
        const merged = []
        const len = data.timestamps.length
        for (let i = 0; i < len; i++) {
          merged.push({ time: data.timestamps[i], cpu: data.cpu_usage[i] || 0, memory: data.memory_usage[i] || 0 })
        }
        dbHistory.value = merged
        await nextTick()
        updateAllCharts()
      }
    }
  } catch (e) {
    console.error('获取历史数据失败:', e)
  }
}

const getTimeLabel = () => {
  const now = new Date()
  return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
}

const dbHistory = ref([])

const addHistory = () => {
  const time = getTimeLabel()
  cpuHistory.value.push({ time, usage: systemData.value.cpu.usage_percent })
  memoryHistory.value.push({ time, usage: systemData.value.memory.usage_percent })
  if (cpuHistory.value.length > historyMaxSize) cpuHistory.value = cpuHistory.value.slice(-historyMaxSize)
  if (memoryHistory.value.length > historyMaxSize) memoryHistory.value = memoryHistory.value.slice(-historyMaxSize)
}

const fetchMonitorData = async () => {
  if (!currentServer.value) return
  error.value = ''
  
  try {
    const response = await monitoringApi.getMonitorData(currentServer.value.id)
    if (response.data.ok) {
      systemData.value = response.data.data
      addHistory()
      
      if (!chartsInitialized) {
        await nextTick()
        await nextTick()
        await new Promise(r => setTimeout(r, 300))
        await initAllCharts()
        chartsInitialized = true
      }
      
      updateAllCharts()
    } else {
      error.value = response.data.message || '数据采集失败'
    }
  } catch (err) {
    error.value = `请求失败: ${err.message}`
    console.error('获取监控数据失败:', err)
  }
}

const initAllCharts = async () => {
  const chartsToInit = [
    { name: 'cpu', ref: cpuChartRef },
    { name: 'memory', ref: memoryChartRef },
    { name: 'disk', ref: diskChartRef },
    { name: 'network', ref: networkChartRef },
    { name: 'cpuHistory', ref: cpuHistoryChartRef },
    { name: 'memoryHistory', ref: memoryHistoryChartRef },
  ]

  for (const { name, ref: chartRef } of chartsToInit) {
    try {
      const el = chartRef.value
      if (!el) {
        console.warn(`[Chart] ${name} ref is null, skipping`)
        continue
      }
      const rect = el.getBoundingClientRect()
      if (rect.width === 0 || rect.height === 0) {
        console.warn(`[Chart] ${name} zero size: ${rect.width}x${rect.height}`)
        continue
      }
      const chart = await chartManager.initChart(name, el)
      if (chart) {
        console.log(`[Chart] ${name} initialized OK`)
      }
    } catch (e) {
      console.error(`[Chart] init ${name} failed:`, e)
    }
  }
}

const updateAllCharts = () => {
  const cpu = systemData.value.cpu
  if (chartManager.getChart('cpu') && cpu.per_core_usage.length > 0) {
    chartManager.updateChart('cpu', ChartOptions.cpuCoreUsage(cpu.per_core_usage, cpu.usage_percent))
  }

  if (chartManager.getChart('memory')) {
    chartManager.updateChart('memory', ChartOptions.memoryUsage(systemData.value.memory.usage_percent))
  }

  if (chartManager.getChart('disk') && systemData.value.disk.partitions.length > 0) {
    chartManager.updateChart('disk', ChartOptions.diskUsage(systemData.value.disk.partitions))
  }

  if (chartManager.getChart('network') && systemData.value.network.interfaces.length > 0) {
    chartManager.updateChart('network', ChartOptions.networkTraffic(systemData.value.network.interfaces))
  }

  if (chartManager.getChart('cpuHistory')) {
    const history = dbHistory.value.length > 0 ? dbHistory.value : cpuHistory.value
    if (history.length > 1) {
      chartManager.updateChart('cpuHistory', ChartOptions.historyTrend(
        history.map(h => h.time),
        history.map(h => h.cpu !== undefined ? h.cpu : h.usage),
        '#4F6EF7', 'CPU'
      ))
    }
  }

  if (chartManager.getChart('memoryHistory')) {
    const history = dbHistory.value.length > 0 ? dbHistory.value : memoryHistory.value
    if (history.length > 1) {
      chartManager.updateChart('memoryHistory', ChartOptions.historyTrend(
        history.map(h => h.time),
        history.map(h => h.memory !== undefined ? h.memory : h.usage),
        '#22C55E', '内存'
      ))
    }
  }
}

let resizeTimer = null
const handleResize = () => {
  if (resizeTimer) clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    chartManager.resizeAll()
  }, 200)
}

onMounted(async () => {
  window.__monitoringChartManager = chartManager
  if (!serverStore.servers.length) await serverStore.fetchServers()
  if (!currentServer.value && serverStore.servers.length > 0) serverStore.setCurrentServer(serverStore.servers[0])
  await fetchMonitorData()
  if (currentServer.value?.id) await fetchHistory()
  refreshTimer = setInterval(fetchMonitorData, 5000)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  window.removeEventListener('resize', handleResize)
  if (resizeTimer) clearTimeout(resizeTimer)
  chartManager.dispose()
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.server-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.server-label {
  font-size: 13px;
  color: var(--text-tertiary);
}

.server-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.empty-state, .error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px;
  text-align: center;
}

.empty-icon, .error-icon {
  color: var(--text-tertiary);
  margin-bottom: 16px;
}

.error-icon { color: var(--danger); }

.empty-title, .error-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.empty-desc, .error-message {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 24px;
}

.dashboard { display: flex; flex-direction: column; gap: 20px; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--bg-border);
  padding: 20px;
}

.stat-card:hover {
  box-shadow: var(--shadow-md);
  border-color: #D1D5DB;
}

.stat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.stat-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.stat-icon-primary { color: var(--primary); opacity: 0.6; }
.stat-icon-success { color: var(--success); opacity: 0.6; }
.stat-icon-warning { color: var(--warning); opacity: 0.6; }
.stat-icon-info { color: var(--info); opacity: 0.6; }

.stat-value-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 12px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  line-height: 1;
}

.stat-unit {
  font-size: 13px;
  color: var(--text-tertiary);
}

.progress-bar {
  height: 6px;
  background: var(--bg-border-light);
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar.mini { width: 80px; }

.progress-fill {
  height: 100%;
  border-radius: 3px;
}

.progress-primary { background: var(--primary); }
.progress-success { background: var(--success); }
.progress-warning { background: var(--warning); }
.progress-danger { background: var(--danger); }

.stat-footer, .stat-footer > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 12px;
}

.stat-footer-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 12px;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.chart-card {
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--bg-border);
  padding: 20px;
}

.chart-card.full-width {
  grid-column: 1 / -1;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.chart-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.chart-badge {
  font-size: 12px;
  color: var(--text-tertiary);
  background: var(--bg-hover);
  padding: 2px 10px;
  border-radius: 9999px;
}

.chart-container {
  height: 256px;
}

.table-card {
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--bg-border);
  overflow: hidden;
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--bg-border-light);
}

.table-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  text-align: left;
  padding: 10px 20px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  background: var(--bg-page);
  border-bottom: 1px solid var(--bg-border);
}

.data-table td {
  padding: 10px 20px;
  font-size: 13px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--bg-border-light);
}

.data-table tbody tr:hover {
  background: var(--bg-hover);
}

.data-table tbody tr:last-child td {
  border-bottom: none;
}

.font-mono { font-family: 'SF Mono', 'Fira Code', monospace; font-size: 12px; }

.usage-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-badge {
  display: inline-flex;
  padding: 1px 8px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 500;
}

.status-running {
  background: var(--success-light);
  color: var(--success);
}

.status-other {
  background: var(--bg-hover);
  color: var(--text-tertiary);
}

@media (max-width: 1200px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: 1fr; }
  .charts-grid { grid-template-columns: 1fr; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 12px; }
}
</style>