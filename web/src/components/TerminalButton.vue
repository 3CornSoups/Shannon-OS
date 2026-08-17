<template>
  <button v-if="isMobile" class="terminal-header-btn" @click="terminalStore.openMobile()" title="终端控制台">
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="4,17 10,11 4,5"/>
      <line x1="12" y1="19" x2="20" y2="19"/>
    </svg>
  </button>
</template>

<script setup>
import { useIsMobile } from '../composables/useIsMobile'
import { useTerminalStore } from '../stores/terminal'

const { isMobile } = useIsMobile()
const terminalStore = useTerminalStore()
</script>

<style scoped>
.terminal-header-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  border-radius: var(--radius-md);
  flex-shrink: 0;
  -webkit-tap-highlight-color: transparent;
}

.terminal-header-btn:active {
  background: var(--bg-hover);
}
</style>
