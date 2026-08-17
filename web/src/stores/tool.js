import { defineStore } from 'pinia'
import { ref } from 'vue'
import { toolApi } from '../services/api'

export const useToolStore = defineStore('tool', () => {
  const tools = ref([])
  const activeSession = ref(null)
  const messages = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchTools(hostId) {
    loading.value = true
    error.value = null
    try {
      const res = await toolApi.listTools(hostId)
      tools.value = res.data.tools || []
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  function addMessage(msg) {
    messages.value.push(msg)
  }

  function clearSession() {
    activeSession.value = null
    messages.value = []
    error.value = null
  }

  return { tools, activeSession, messages, loading, error, fetchTools, addMessage, clearSession }
})
