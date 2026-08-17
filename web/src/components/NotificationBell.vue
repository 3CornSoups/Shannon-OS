<template>
  <div class="relative">
    <button @click="showPanel = !showPanel" class="relative p-2 rounded-md hover:bg-gray-100 transition-colors">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" :class="alertCount > 0 ? 'text-yellow-500' : 'text-gray-400'">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
      </svg>
      <span v-if="alertCount > 0" class="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-medium">
        {{ alertCount > 99 ? '99+' : alertCount }}
      </span>
    </button>

    <!-- 下拉面板 -->
    <div v-if="showPanel" class="absolute right-0 top-full mt-2 w-80 bg-white rounded-lg border border-gray-200 shadow-lg z-50">
      <div class="px-4 py-3 border-b border-gray-100 flex justify-between items-center">
        <span class="font-semibold text-sm text-gray-800">告警通知</span>
        <router-link to="/alerts" class="text-xs text-indigo-600 hover:text-indigo-800" @click="showPanel = false">查看全部</router-link>
      </div>
      <div class="max-h-80 overflow-y-auto">
        <div v-if="recentAlerts.length === 0" class="px-4 py-8 text-center text-sm text-gray-400">暂无告警</div>
        <div v-for="a in recentAlerts" :key="a.id" class="px-4 py-3 border-b border-gray-50 hover:bg-gray-50 cursor-pointer" @click="goToAlert(a.id)">
          <div class="flex items-start gap-2">
            <span class="w-2 h-2 rounded-full mt-1.5 flex-shrink-0" :class="severityDot(a.severity)"></span>
            <div class="flex-1 min-w-0">
              <p class="text-sm text-gray-700 truncate">{{ a.rule_name }}</p>
              <p class="text-xs text-gray-400 mt-0.5">{{ a.host_name || a.host_ip }} · {{ a.triggered_at }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const alertCount = ref(0)
const recentAlerts = ref([])
const showPanel = ref(false)
let timer = null

function severityDot(s) {
  return { critical: 'bg-red-500', warning: 'bg-yellow-500', info: 'bg-blue-500' }[s] || 'bg-gray-300'
}

function goToAlert(id) {
  showPanel.value = false
  router.push('/alerts')
}

async function fetchAlerts() {
  try {
    const res = await axios.get('/api/alerts', { params: { status: 'alerting', page: 1, page_size: 10 } })
    if (res.data?.ok) {
      const items = res.data.data.items || []
      const prevCount = alertCount.value
      alertCount.value = items.length
      recentAlerts.value = items

      // 新的告警，尝试桌面通知
      if (items.length > prevCount && window.Notification && Notification.permission === 'granted') {
        const latest = items[0]
        new Notification('Shannon OS 告警', { body: `${latest.rule_name} - ${latest.host_name || ''}` })
      }
    }
  } catch (e) { console.error(e) }
}

onMounted(() => {
  fetchAlerts()
  timer = setInterval(fetchAlerts, 10000)
  // 请求桌面通知权限
  if (window.Notification && Notification.permission === 'default') {
    Notification.requestPermission()
  }
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
