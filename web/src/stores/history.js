import { defineStore } from 'pinia'
import { historyApi } from '../services/api'

export const useHistoryStore = defineStore('history', {
  state: () => ({
    history: [],
    loading: false,
    error: null,
    filters: {
      serverId: null,
      user: null,
      dateRange: null,
      status: null
    }
  }),
  getters: {
    filteredHistory: (state) => {
      let filtered = [...state.history]
      
      if (state.filters.serverId) {
        filtered = filtered.filter(item => item.host_id === state.filters.serverId)
      }
      
      if (state.filters.status) {
        filtered = filtered.filter(item => item.status === state.filters.status)
      }

      if (state.filters.mode) {
        filtered = filtered.filter(item => item.mode === state.filters.mode)
      }

      if (state.filters.dateRange) {
        const [start, end] = state.filters.dateRange
        filtered = filtered.filter(item => {
          const itemDate = new Date(item.created_at)
          return itemDate >= start && itemDate <= end
        })
      }
      
      return filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    }
  },
  actions: {
    setHistory(history) {
      this.history = history
    },
    addHistoryItem(item) {
      this.history.unshift(item)
    },
    async fetchActions(hostId) {
      this.loading = true
      this.error = null
      try {
        const response = await historyApi.getActions(hostId)
        // user_actions 表无 status 列，按 executed 派生展示状态
        this.history = (response.data || []).map(item => ({
          ...item,
          status: item.executed ? 'success' : 'chat_only'
        }))
      } catch (error) {
        this.error = error.message
        console.error('加载操作历史失败:', error)
      } finally {
        this.loading = false
      }
    },
    setFilters(filters) {
      this.filters = {
        ...this.filters,
        ...filters
      }
    },
    clearFilters() {
      this.filters = {
        serverId: null,
        user: null,
        dateRange: null,
        status: null,
        mode: null
      }
    }
  }
})
