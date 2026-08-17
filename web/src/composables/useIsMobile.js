import { ref, onMounted, onUnmounted } from 'vue'

/**
 * 响应式移动端判断（单一断点 <768px）。
 * 与 Layout 底部 Tab 栏、聊天页会话抽屉、终端全屏等共用同一判断。
 */
export function useIsMobile() {
  const BREAKPOINT = '(max-width: 768px)'
  const isMobile = ref(typeof window !== 'undefined' ? window.matchMedia(BREAKPOINT).matches : false)

  let mql = null

  onMounted(() => {
    mql = window.matchMedia(BREAKPOINT)
    const handler = (e) => { isMobile.value = e.matches }
    mql.addEventListener('change', handler)
  })

  onUnmounted(() => {
    mql?.removeEventListener('change', handler)
  })

  return { isMobile }
}
