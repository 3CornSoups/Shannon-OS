import { defineStore } from 'pinia'
import { serverApi } from '../services/api'
import { chatApi } from '../services/api'

export const useServerStore = defineStore('server', {
  state: () => ({
    servers: [],
    currentServer: null,
    loading: false,
    error: null
  }),
  getters: {
    getServerById: (state) => (id) => {
      return state.servers.find(server => server.id === id)
    }
  },
  actions: {
    async fetchServers() {
      this.loading = true
      this.error = null
      try {
        const response = await serverApi.getServers()
        this.servers = response.data
      } catch (error) {
        this.error = error.message
        console.error('Error fetching servers:', error)
      } finally {
        this.loading = false
      }
    },
    async testConnection(host) {
      this.loading = true
      this.error = null
      try {
        const response = await serverApi.testConnection(host)
        return response.data
      } catch (error) {
        this.error = error.message
        console.error('Error testing connection:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    setCurrentServer(server) {
      this.currentServer = server
    },
    async getServerContext(serverId) {
      this.loading = true
      this.error = null
      try {
        const response = await serverApi.getContext(serverId)
        return response.data
      } catch (error) {
        this.error = error.message
        console.error('Error fetching server context:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async loadChatHistory(hostId) {
      this.loading = true
      this.error = null
      try {
        const response = await chatApi.getChatHistory(hostId)
        return response.data
      } catch (error) {
        this.error = error.message
        console.error('Error loading chat history:', error)
        return []
      } finally {
        this.loading = false
      }
    },
    async clearChatHistory(hostId) {
      this.loading = true
      this.error = null
      try {
        await chatApi.clearChatHistory(hostId)
      } catch (error) {
        this.error = error.message
        console.error('Error clearing chat history:', error)
      } finally {
        this.loading = false
      }
    }
  }
})
