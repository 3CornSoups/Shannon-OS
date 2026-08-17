import { ref, onUnmounted } from 'vue'

export function useVoiceInput() {
  const isListening = ref(false)
  const isSupported = ref(false)
  const errorMessage = ref('')

  let recognition = null

  if (typeof window !== 'undefined') {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRecognition) {
      isSupported.value = true
      recognition = new SpeechRecognition()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'zh-CN'
    }
  }

  function startListening(onResult, onEnd) {
    if (!recognition) {
      errorMessage.value = '当前浏览器不支持语音识别，请使用 Chrome 浏览器'
      return
    }

    errorMessage.value = ''
    isListening.value = true

    recognition.onresult = (event) => {
      let interimTranscript = ''
      let finalTranscript = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript
        if (event.results[i].isFinal) {
          finalTranscript += transcript
        } else {
          interimTranscript += transcript
        }
      }
      if (onResult) onResult(finalTranscript, interimTranscript)
    }

    recognition.onerror = (event) => {
      if (event.error === 'no-speech') {
        errorMessage.value = '未检测到语音输入'
      } else if (event.error === 'audio-capture') {
        errorMessage.value = '未找到麦克风，请检查设备'
      } else if (event.error === 'not-allowed') {
        errorMessage.value = '麦克风权限被拒绝，请在浏览器设置中允许'
      } else {
        errorMessage.value = `语音识别错误: ${event.error}`
      }
      isListening.value = false
    }

    recognition.onend = () => {
      isListening.value = false
      if (onEnd) onEnd()
    }

    try {
      recognition.start()
    } catch (e) {
      isListening.value = false
      errorMessage.value = '启动语音识别失败，请重试'
    }
  }

  function stopListening() {
    if (recognition && isListening.value) {
      recognition.stop()
      isListening.value = false
    }
  }

  onUnmounted(() => {
    stopListening()
  })

  return {
    isListening,
    isSupported,
    errorMessage,
    startListening,
    stopListening,
  }
}
