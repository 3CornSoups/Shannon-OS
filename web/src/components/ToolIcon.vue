<template>
  <span class="tool-logo">
    <img v-if="src" :src="src" :alt="props.tool?.display_name || 'tool'" class="tool-logo-img" />
    <span v-else class="tool-logo-fallback">{{ emoji }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import claudeCodeIcon from '../assets/tools/claude-code.svg'
import codexIcon from '../assets/tools/codex.svg'
import hermesIcon from '../assets/tools/hermes.svg'
import manusIcon from '../assets/tools/manus.svg'
import openclawIcon from '../assets/tools/openclaw.svg'

const props = defineProps({
  tool: { type: Object, required: true },
})

const ICONS = {
  claude_code: claudeCodeIcon,
  codex: codexIcon,
  hermes: hermesIcon,
  manus: manusIcon,
  openclaw: openclawIcon,
}

// 归一化工具 key（按 name 优先，display_name 兜底）
const key = computed(() => {
  const name = String(props.tool?.name || '').toLowerCase()
  const display = String(props.tool?.display_name || '').toLowerCase()
  if (['claude_code', 'openclaw', 'codex', 'manus', 'hermes'].includes(name)) return name
  if (name.includes('claude')) return 'claude_code'
  if (name.includes('openclaw') || name.includes('claw')) return 'openclaw'
  if (name.includes('codex')) return 'codex'
  if (name.includes('manus')) return 'manus'
  if (name.includes('hermes')) return 'hermes'
  if (display.includes('claude')) return 'claude_code'
  if (display.includes('openclaw') || display.includes('claw')) return 'openclaw'
  if (display.includes('codex')) return 'codex'
  if (display.includes('manus')) return 'manus'
  if (display.includes('hermes')) return 'hermes'
  return 'unknown'
})

const src = computed(() => ICONS[key.value] || null)

// 回退 emoji（沿用旧的 icon 映射）
const emoji = computed(() => {
  const icon = props.tool?.icon || props.tool?.name || ''
  if (icon === 'brain') return '🧠'
  return '🔧'
})
</script>

<style scoped>
.tool-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.tool-logo-img {
  width: 36px;
  height: 36px;
  object-fit: contain;
}

.tool-logo-fallback {
  font-size: 36px;
  line-height: 1;
}
</style>
