<template>
  <Layout>
  <div class="reports-page">
    <!-- 左侧：报告列表 -->
    <aside class="reports-sidebar">
      <div class="reports-sidebar-header">
        <span class="reports-title">报告库</span>
        <button class="mini-btn" title="生成每日小结" @click="generateDaily">今日小结</button>
      </div>
      <div class="reports-generate">
        <input
          v-model="topic"
          class="topic-input"
          placeholder="输入主题，生成主题报告…"
          @keydown.enter="generateTopic"
        />
        <button class="mini-btn primary" @click="generateTopic">生成</button>
      </div>
      <div class="reports-list">
        <div
          v-for="r in reports"
          :key="r.id"
          class="report-item"
          :class="{ active: r.id === currentReportId }"
          @click="viewReport(r.id)"
        >
          <span class="report-type">{{ r.type === 'daily' ? '小结' : '主题' }}</span>
          <div class="report-item-body">
            <div class="report-item-title">{{ r.title }}</div>
            <div class="report-item-meta">{{ r.period || '' }} · {{ fmtTime(r.created_at) }}</div>
          </div>
          <button class="report-del" title="删除" @click.stop="removeReport(r.id)">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <div v-if="!reports.length" class="reports-empty">还没有报告。点「今日小结」或输入主题生成。</div>
      </div>
    </aside>

    <!-- 右侧：报告正文 -->
    <div class="report-content">
      <div v-if="currentReport" class="report-md" v-html="renderMarkdown(currentReport.content)"></div>
      <div v-else class="report-placeholder">
        <div class="report-placeholder-logo">◇</div>
        <p>选择左侧报告查看内容</p>
      </div>
    </div>
  </div>
  </Layout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Layout from '../components/layout/Layout.vue'
import { echoApi } from '../services/api'
import { renderMarkdown } from '../composables/markdown'

const reports = ref([])
const currentReportId = ref(null)
const currentReport = ref(null)
const topic = ref('')
const generating = ref(false)

function fmtTime(t) {
  if (!t) return ''
  return String(t).slice(5, 16).replace('T', ' ')
}

async function loadReports() {
  const res = await echoApi.listReports()
  reports.value = res.data.reports || []
}

async function viewReport(id) {
  currentReportId.value = id
  const res = await echoApi.getReport(id)
  currentReport.value = res.data
}

async function generateDaily() {
  if (generating.value) return
  generating.value = true
  try {
    const res = await echoApi.generateDailyReport()
    await loadReports()
    currentReportId.value = res.data.id
    currentReport.value = res.data
  } catch (e) {
    alert('生成失败，请重试')
  } finally {
    generating.value = false
  }
}

async function generateTopic() {
  const t = topic.value.trim()
  if (!t || generating.value) return
  generating.value = true
  try {
    const res = await echoApi.generateTopicReport(t)
    await loadReports()
    currentReportId.value = res.data.id
    currentReport.value = res.data
    topic.value = ''
  } catch (e) {
    alert('生成失败，请重试')
  } finally {
    generating.value = false
  }
}

async function removeReport(id) {
  if (!confirm('删除这份报告？')) return
  await echoApi.deleteReport(id)
  if (currentReportId.value === id) {
    currentReportId.value = null
    currentReport.value = null
  }
  await loadReports()
}

onMounted(loadReports)
</script>

<style scoped>
.reports-page {
  height: calc(100vh - 88px);
  display: flex;
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--bg-page);
}
.reports-sidebar {
  width: 280px;
  min-width: 280px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--bg-border);
  background: var(--bg-sidebar);
}
.reports-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--bg-border-light);
}
.reports-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
.reports-generate {
  display: flex;
  gap: 6px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--bg-border-light);
}
.topic-input {
  flex: 1;
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-sm);
  background: var(--bg-page);
  color: var(--text-primary);
  font-size: 12px;
  padding: 6px 8px;
  outline: none;
  font-family: inherit;
}
.topic-input:focus { border-color: var(--primary); }
.mini-btn {
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 12px;
  padding: 6px 10px;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-fast);
}
.mini-btn:hover { border-color: var(--primary); color: var(--primary); }
.mini-btn.primary { background: var(--primary); border-color: var(--primary); color: #fff; }
.reports-list { flex: 1; overflow-y: auto; padding: 8px; }
.report-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--transition-fast);
}
.report-item:hover { background: var(--bg-hover); }
.report-item.active { background: var(--primary-light); }
.report-type {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--bg-hover);
  color: var(--text-secondary);
  flex-shrink: 0;
}
.report-item.active .report-type { background: var(--primary); color: #fff; }
.report-item-body { flex: 1; min-width: 0; }
.report-item-title {
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.report-item-meta { font-size: 11px; color: var(--text-tertiary); }
.report-del {
  width: 22px; height: 22px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  border-radius: 4px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  opacity: 0;
  transition: all var(--transition-fast);
}
.report-item:hover .report-del { opacity: 1; }
.report-del:hover { background: var(--bg-hover); color: var(--danger, #e5484d); }
.reports-empty { padding: 16px 10px; font-size: 12px; color: var(--text-tertiary); text-align: center; }

.report-content {
  flex: 1;
  overflow-y: auto;
  padding: 28px 36px;
  background: var(--bg-page);
}
.report-md {
  max-width: 760px;
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.75;
}
.report-md :deep(pre) {
  background: var(--bg-code, #0d1117);
  color: #e6edf3;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
}
.report-md :deep(h1) { font-size: 22px; }
.report-md :deep(h2) { font-size: 18px; margin-top: 20px; }
.report-md :deep(h3) { font-size: 15px; }
.report-md :deep(ul), .report-md :deep(ol) { padding-left: 20px; }
.report-md :deep(table) { border-collapse: collapse; }
.report-md :deep(td), .report-md :deep(th) { border: 1px solid var(--bg-border); padding: 6px 10px; }
.report-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  font-size: 13px;
}
.report-placeholder-logo { font-size: 36px; color: var(--primary); margin-bottom: 10px; }
</style>
