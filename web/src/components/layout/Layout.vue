<template>
  <div class="app-layout" :class="{ 'is-mobile': isMobile }">
    <!-- Activity Bar (Leftmost thin bar) -->
    <aside class="activity-bar">
      <div class="activity-brand">
        <div class="brand-logo">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
      </div>
      <nav class="activity-nav">
        <router-link to="/" class="activity-item" :class="{ active: $route.path === '/' }" title="仪表盘">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="7" rx="1"/>
            <rect x="14" y="3" width="7" height="7" rx="1"/>
            <rect x="3" y="14" width="7" height="7" rx="1"/>
            <rect x="14" y="14" width="7" height="7" rx="1"/>
          </svg>
        </router-link>
        <router-link to="/echo" class="activity-item" :class="{ active: $route.path.startsWith('/echo') }" title="助手">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            <path d="M8 9h8"/><path d="M8 13h5"/>
          </svg>
        </router-link>
        <router-link to="/servers" class="activity-item" :class="{ active: $route.path === '/servers' }" title="服务器">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="2" width="20" height="8" rx="2"/>
            <rect x="2" y="14" width="20" height="8" rx="2"/>
            <line x1="6" y1="6" x2="6.01" y2="6"/>
            <line x1="6" y1="18" x2="6.01" y2="18"/>
          </svg>
        </router-link>
        <router-link to="/monitoring" class="activity-item" :class="{ active: $route.path === '/monitoring' }" title="监控">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
          </svg>
        </router-link>
        <router-link to="/history" class="activity-item" :class="{ active: $route.path === '/history' }" title="历史">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12,6 12,12 16,14"/>
          </svg>
        </router-link>
        <router-link to="/templates" class="activity-item" :class="{ active: $route.path === '/templates' }" title="模板">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
            <polyline points="14,2 14,8 20,8"/>
          </svg>
        </router-link>
        <router-link to="/showcase" class="activity-item" :class="{ active: $route.path === '/showcase' }" title="关于">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
        </router-link>
        <router-link to="/monitor-overview" class="activity-item" :class="{ active: $route.path === '/monitor-overview' }" title="监控仪表盘">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <line x1="3" y1="9" x2="21" y2="9"/>
            <line x1="9" y1="21" x2="9" y2="9"/>
          </svg>
        </router-link>
        <router-link to="/alerts" class="activity-item" :class="{ active: $route.path.startsWith('/alerts') }" title="告警中心">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
          </svg>
        </router-link>
        <router-link to="/tools" class="activity-item" :class="{ active: $route.path === '/tools' }" title="工具面板">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
          </svg>
        </router-link>
      </nav>
      <div class="activity-bottom">
        <router-link to="/settings" class="activity-item" :class="{ active: $route.path === '/settings' }" title="设置">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
          </svg>
        </router-link>
      </div>
    </aside>

    <!-- Primary Sidebar（回声页面不显示：资源管理器/仪表盘等运维导航不出现） -->
    <aside v-if="!isEcho" class="primary-sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <h2 class="sidebar-title">资源管理器</h2>
        <button class="sidebar-toggle" @click="sidebarCollapsed = !sidebarCollapsed" title="折叠侧边栏">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" :class="{ 'rotate-180': !sidebarCollapsed }">
            <polyline points="15,18 9,12 15,6"/>
          </svg>
        </button>
      </div>
      <div class="sidebar-content">
        <slot name="sidebar"></slot>
        <FileExplorer />
      </div>
    </aside>

    <!-- Main Content Area -->
    <div class="main-wrapper">
      <!-- Top Navigation Bar -->
      <header class="top-bar">
        <div class="top-bar-right">
          <div class="top-bar-actions">
            <NotificationBell />
            <button class="action-btn" title="命令面板" @click="showCommandPalette = true">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="4,17 10,11 4,5"/>
                <line x1="12" y1="19" x2="20" y2="19"/>
              </svg>
            </button>
          </div>
        </div>
      </header>

      <!-- Page Content -->
      <main class="page-content">
        <slot></slot>
      </main>

      <!-- Terminal Console -->
      <TerminalPanel />
    </div>

    <!-- Command Palette Modal -->
    <div v-if="showCommandPalette" class="command-palette-overlay" @click="showCommandPalette = false">
      <div class="command-palette" @click.stop>
        <div class="palette-input-wrap">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input ref="paletteInput" type="text" class="palette-input" placeholder="输入命令或搜索..." @keydown.esc="showCommandPalette = false" />
          <kbd class="palette-kbd">ESC</kbd>
        </div>
        <div class="palette-results">
          <router-link to="/" class="palette-item" @click="showCommandPalette = false">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
            <span>仪表盘</span>
          </router-link>
          <router-link to="/servers" class="palette-item" @click="showCommandPalette = false">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>
            <span>服务器管理</span>
          </router-link>
          <router-link to="/monitoring" class="palette-item" @click="showCommandPalette = false">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/></svg>
            <span>系统监控</span>
          </router-link>
          <router-link to="/history" class="palette-item" @click="showCommandPalette = false">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><polyline points="12,6 12,12 16,14"/></svg>
            <span>操作历史</span>
          </router-link>
          <router-link to="/templates" class="palette-item" @click="showCommandPalette = false">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14,2 14,8 20,8"/></svg>
            <span>执行模板</span>
          </router-link>
          <router-link to="/showcase" class="palette-item" @click="showCommandPalette = false">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
            <span>系统展示</span>
          </router-link>
          <router-link to="/settings" class="palette-item" @click="showCommandPalette = false">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
            <span>设置</span>
          </router-link>
        </div>
        <div class="palette-footer">
          <span><kbd>↑</kbd><kbd>↓</kbd> 导航</span>
          <span><kbd>↵</kbd> 选择</span>
          <span><kbd>ESC</kbd> 关闭</span>
        </div>
      </div>
    </div>

    <!-- Bottom Tab Bar（移动端主导航） -->
    <nav v-if="isMobile" class="bottom-tab-bar">
      <router-link to="/" class="tab-item" :class="{ active: $route.path === '/' }">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
        <span>聊天</span>
      </router-link>
      <router-link to="/echo" class="tab-item" :class="{ active: $route.path.startsWith('/echo') }">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 9h8"/><path d="M8 13h5"/></svg>
        <span>助手</span>
      </router-link>
      <router-link to="/servers" class="tab-item" :class="{ active: $route.path === '/servers' }">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>
        <span>服务器</span>
      </router-link>
      <router-link to="/monitoring" class="tab-item" :class="{ active: $route.path === '/monitoring' }">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/></svg>
        <span>监控</span>
      </router-link>
      <button class="tab-item" :class="{ active: showMoreDrawer }" @click="showMoreDrawer = !showMoreDrawer">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/></svg>
        <span>更多</span>
      </button>
    </nav>

    <!-- More Drawer（移动端长尾页面面板） -->
    <transition name="more-slide">
      <div v-if="isMobile && showMoreDrawer" class="more-drawer-overlay" @click="showMoreDrawer = false">
        <div class="more-drawer" @click.stop>
          <div class="more-drawer-handle"></div>
          <div class="more-drawer-grid">
            <router-link
              v-for="item in moreItems"
              :key="item.path"
              :to="item.path"
              class="more-item"
              :class="{ active: item.path === '/' ? $route.path === '/' : $route.path.startsWith(item.path) }"
              @click="showMoreDrawer = false"
            >
              <span class="more-item-icon">{{ item.icon }}</span>
              <span class="more-item-label">{{ item.label }}</span>
            </router-link>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import TerminalPanel from '../Terminal.vue'
import FileExplorer from '../FileExplorer.vue'
import NotificationBell from '../NotificationBell.vue'
import { useIsMobile } from '../../composables/useIsMobile'
const router = useRouter()
const route = useRoute()

const sidebarCollapsed = ref(false)
const showCommandPalette = ref(false)
const paletteInput = ref(null)
const { isMobile } = useIsMobile()
const showMoreDrawer = ref(false)

// 「更多」抽屉收纳的长尾页面（移动端）
const moreItems = [
  { path: '/history', label: '历史', icon: '🕘' },
  { path: '/templates', label: '模板', icon: '📋' },
  { path: '/alerts', label: '告警', icon: '🚨' },
  { path: '/tools', label: '工具', icon: '🧰' },
  { path: '/monitor-overview', label: '监控仪表盘', icon: '📊' },
  { path: '/settings', label: '设置', icon: '⚙️' },
  { path: '/showcase', label: '关于', icon: 'ℹ️' },
]

// 回声相关页面（/echo、/echo/reports）：隐藏主侧边栏（资源管理器 + 仪表盘导航）
const isEcho = computed(() => route.path.startsWith('/echo'))

// Command palette keyboard shortcut
onMounted(() => {
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault()
      showCommandPalette.value = true
    }
  })
})

watch(showCommandPalette, async (val) => {
  if (val) {
    await nextTick()
    paletteInput.value?.focus()
  }
})
</script>

<style scoped>
.app-layout {
  height: 100vh;
  display: flex;
  background: var(--bg-page);
  overflow: hidden;
}

/* ===== Activity Bar ===== */
.activity-bar {
  width: 48px;
  min-width: 48px;
  background: var(--bg-surface);
  border-right: 1px solid var(--bg-border);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 0;
  z-index: 20;
}

.activity-brand {
  margin-bottom: 16px;
}

.brand-logo {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
}

.activity-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.activity-item {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  text-decoration: none;
  transition: all var(--transition-fast);
  position: relative;
}

.activity-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.activity-item.active {
  color: var(--primary);
  background: var(--primary-light);
}

.activity-item.active::before {
  content: '';
  position: absolute;
  left: -6px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  border-radius: 0 2px 2px 0;
  background: var(--primary);
}

.activity-bottom {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* ===== Primary Sidebar ===== */
.primary-sidebar {
  width: 240px;
  min-width: 240px;
  max-width: 240px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--bg-border);
  display: flex;
  flex-direction: column;
  transition: all var(--transition-base);
  overflow: hidden;
}

.primary-sidebar.collapsed {
  width: 0;
  min-width: 0;
  max-width: 0;
  border-right: none;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--bg-border-light);
  min-height: 48px;
}

.sidebar-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-toggle {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.sidebar-toggle:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.sidebar-toggle svg.rotate-180 {
  transform: rotate(180deg);
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.sidebar-placeholder {
  padding: 12px;
  color: var(--text-tertiary);
  font-size: 12px;
  line-height: 1.6;
}

/* ===== Main Wrapper ===== */
.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  min-height: 0;
}

/* ===== Top Bar ===== */
.top-bar {
  height: 40px;
  min-height: 40px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 16px;
  border-bottom: 1px solid var(--bg-border-light);
  background: var(--bg-surface);
}

.top-bar-right {
  display: flex;
  align-items: center;
}

.top-bar-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.action-btn {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.action-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

/* ===== Page Content ===== */
.page-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

/* ===== Command Palette ===== */
.command-palette-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 120px;
  z-index: 100;
  backdrop-filter: blur(4px);
  animation: fadeIn 0.15s ease;
}

.command-palette {
  width: 100%;
  max-width: 560px;
  background: var(--bg-surface);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-12px); }
  to { opacity: 1; transform: translateY(0); }
}

.palette-input-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--bg-border-light);
}

.palette-input-wrap svg {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.palette-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  color: var(--text-primary);
}

.palette-input::placeholder {
  color: var(--text-tertiary);
}

.palette-kbd {
  font-size: 10px;
  padding: 2px 6px;
  background: var(--bg-hover);
  border: 1px solid var(--bg-border);
  border-radius: 4px;
  color: var(--text-tertiary);
  font-family: inherit;
}

.palette-results {
  padding: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.palette-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  color: var(--text-primary);
  text-decoration: none;
  font-size: 13px;
  transition: all var(--transition-fast);
}

.palette-item:hover {
  background: var(--bg-hover);
}

.palette-item svg {
  color: var(--text-tertiary);
}

.palette-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  border-top: 1px solid var(--bg-border-light);
  font-size: 11px;
  color: var(--text-tertiary);
}

.palette-footer kbd {
  font-size: 10px;
  padding: 1px 5px;
  background: var(--bg-hover);
  border: 1px solid var(--bg-border);
  border-radius: 3px;
  margin: 0 2px;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@media (max-width: 768px) {
  .primary-sidebar { display: none; }
  .page-content { padding: 16px; }
  /* 移动端删除独立顶栏：铃铛/命令面板并入各页面标题行 */
  .top-bar { display: none; }
}

/* ===== Mobile Bottom Tab Bar ===== */
.app-layout.is-mobile {
  height: 100dvh; /* 移动端浏览器地址栏伸缩时高度不跳变 */
  flex-direction: column; /* 移动端改为纵向：主区在上，底部 Tab 栏贴底 */
}

.app-layout.is-mobile .activity-bar,
.app-layout.is-mobile .primary-sidebar {
  display: none;
}

.bottom-tab-bar {
  display: flex;
  min-height: 48px;
  border-top: 1px solid var(--bg-border);
  background: var(--bg-surface);
  z-index: 30;
  flex-shrink: 0;
  padding-bottom: env(safe-area-inset-bottom);
}

.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 4px 0 3px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  text-decoration: none;
  font-size: 11px;
  line-height: 1.2;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: color var(--transition-fast);
}

.tab-item.active {
  color: var(--primary);
}

.tab-item:active {
  opacity: 0.7;
}

/* ===== More Drawer ===== */
.more-drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 90;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.more-drawer {
  width: 100%;
  max-width: 640px;
  background: var(--bg-surface);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  padding: 8px 16px calc(16px + env(safe-area-inset-bottom));
  box-shadow: var(--shadow-xl);
}

.more-drawer-handle {
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background: var(--bg-border);
  margin: 4px auto 12px;
}

.more-drawer-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
}

.more-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 0;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 12px;
  min-height: 44px;
}

.more-item:active {
  background: var(--bg-hover);
}

.more-item.active {
  color: var(--primary);
}

.more-item-icon {
  font-size: 20px;
  line-height: 1;
}

.more-slide-enter-active,
.more-slide-leave-active {
  transition: opacity 0.2s ease;
}

.more-slide-enter-active .more-drawer,
.more-slide-leave-active .more-drawer {
  transition: transform 0.25s ease;
}

.more-slide-enter-from,
.more-slide-leave-to {
  opacity: 0;
}

.more-slide-enter-from .more-drawer,
.more-slide-leave-to .more-drawer {
  transform: translateY(100%);
}
</style>