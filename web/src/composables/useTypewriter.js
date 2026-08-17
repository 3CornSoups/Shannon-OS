/**
 * 打字机效果 — 逐字显示文本
 * 用于避免大段文本一次性出现
 */
import { ref, watch, onUnmounted } from 'vue'

export function useTypewriter(textRef, { speed = 15, enabled = true } = {}) {
  const displayed = ref('')
  let timer = null
  let idx = 0

  function start(newText) {
    stop()
    if (!newText || !enabled) {
      displayed.value = newText || ''
      return
    }
    idx = 0
    displayed.value = ''
    timer = setInterval(() => {
      if (idx < newText.length) {
        idx++
        displayed.value = newText.slice(0, idx)
      } else {
        stop()
      }
    }, speed)
  }

  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  // 如果传入的是 ref，watch 变化并启动打字
  if (textRef && textRef.value !== undefined) {
    watch(() => {
      if (typeof textRef === 'function') return textRef()
      return textRef.value
    }, (val) => {
      if (val && val !== displayed.value) {
        // 如果新内容比已显示的短（如重置），直接显示
        if (displayed.value && val.startsWith(displayed.value)) {
          // 内容追加，继续打字
          const remaining = val.slice(displayed.value.length)
          let offset = displayed.value.length
          const newTimer = setInterval(() => {
            if (offset < val.length) {
              offset++
              displayed.value = val.slice(0, offset)
            } else {
              clearInterval(newTimer)
            }
          }, speed)
          // 替换旧 timer
          if (timer) clearInterval(timer)
          timer = newTimer
        } else {
          start(val)
        }
      }
    }, { immediate: true })
  }

  onUnmounted(() => stop())

  return { displayed, start, stop }
}
