import { defineStore } from 'pinia'
import { serverApi } from '../services/api'
import { chatApi } from '../services/api'

export const useServerStore = defineStore('server', {
  state: () => ({
    servers: [],
    currentServer: null,
    selectedServers: [],
    serverPasswords: {},
    loading: false,
    error: null
  }),
  getters: {
    getServerById: (state) => (id) => {
      return state.servers.find(server => server.id === id)
    },
    selectedCount: (state) => state.selectedServers.length,
    isMultiMode: (state) => state.selectedServers.length > 1,
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
      this.selectedServers = server ? [server] : []
    },
    toggleServerSelection(server) {
      const idx = this.selectedServers.findIndex(s => s.id === server.id)
      if (idx >= 0) {
        this.selectedServers.splice(idx, 1)
      } else {
        this.selectedServers.push(server)
      }
      this._syncCurrentServer()
    },
    removeServer(server) {
      this.selectedServers = this.selectedServers.filter(s => s.id !== server.id)
      this._syncCurrentServer()
    },
    _syncCurrentServer() {
      if (this.selectedServers.length === 1) {
        this.currentServer = this.selectedServers[0]
      } else if (this.selectedServers.length === 0) {
        this.currentServer = null
      }
    },
    setSelectedServers(servers) {
      this.selectedServers = servers
      if (servers.length === 1) {
        this.currentServer = servers[0]
      }
    },
    clearSelection() {
      this.selectedServers = []
      this.serverPasswords = {}
    },
    setServerPassword(hostId, password) {
      this.serverPasswords[hostId] = password
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
