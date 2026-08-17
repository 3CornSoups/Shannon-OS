<template>
  <div class="thinking-panel" :class="{ expanded: isExpanded }">
    <button class="thinking-toggle" @click="toggle">
      <span class="thinking-toggle-icon">💭</span>
      <span class="thinking-toggle-label">思考过程</span>
      <svg
        class="thinking-chevron"
        :class="{ open: isExpanded }"
        width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"
      >
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </button>
    <div class="thinking-content" ref="contentEl">
      <div class="thinking-text" v-html="renderedContent"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { renderMarkdown } from '../composables/markdown.js'

const props = defineProps({
  content: { type: String, default: '' },
  autoExpand: { type: Boolean, default: false },  // 流式时自动展开
})

const isExpanded = ref(false)
const contentEl = ref(null)

const renderedContent = computed(() => renderMarkdown(props.content || ''))

watch(() => props.autoExpand, (val) => {
  if (val) isExpanded.value = true
})

// 首次有内容且 autoExpand 时展开
watch(() => props.content, (val) => {
  if (val && props.autoExpand) {
    isExpanded.value = true
  }
})

function toggle() {
  isExpanded.value = !isExpanded.value
}
</script>

<style scoped>
.thinking-panel {
  margin-bottom: 10px;
  border-left: 3px solid var(--primary);
  border-radius: 0 6px 6px 0;
  background: var(--primary-lighter);
  overflow: hidden;
}

.thinking-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 6px 12px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  color: var(--text-secondary);
  transition: background var(--transition-fast);
  user-select: none;
}

.thinking-toggle:hover {
  background: rgba(79, 110, 247, 0.08);
}

.thinking-toggle-icon {
  font-size: 13px;
  flex-shrink: 0;
}

.thinking-toggle-label {
  font-weight: 500;
}

.thinking-chevron {
  margin-left: auto;
  flex-shrink: 0;
  transition: transform 0.2s ease;
  color: var(--text-tertiary);
}

.thinking-chevron.open {
  transform: rotate(180deg);
}

.thinking-content {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
}

.thinking-panel.expanded .thinking-content {
  max-height: 3000px;
}

.thinking-text {
  padding: 0 12px 10px 32px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
}

/* inner markdown styles for thinking content */
.thinking-text :deep(h1),
.thinking-text :deep(h2),
.thinking-text :deep(h3) {
  font-size: 0.95em;
  margin: 6px 0 3px;
  color: var(--text-primary);
}

.thinking-text :deep(p) {
  margin: 3px 0 5px;
}

.thinking-text :deep(code) {
  background: rgba(0, 0, 0, 0.06);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 0.9em;
}

.thinking-text :deep(pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 8px 10px;
  border-radius: 5px;
  overflow-x: auto;
  margin: 5px 0;
  font-size: 0.85em;
}

.thinking-text :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.thinking-text :deep(ul),
.thinking-text :deep(ol) {
  padding-left: 16px;
  margin: 3px 0 5px;
}

.thinking-text :deep(blockquote) {
  border-left: 2px solid var(--primary);
  padding: 3px 8px;
  margin: 4px 0;
  opacity: 0.8;
}

.thinking-text :deep(a) {
  color: var(--primary);
}
</style>
