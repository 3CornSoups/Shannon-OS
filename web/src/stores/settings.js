import { defineStore } from 'pinia'
import { settingsApi } from '../services/api'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    settings: {
      api_base: 'https://api.deepseek.com',
      api_model: 'deepseek-chat',
      api_key: '',
      api_key_masked: '',
      default_ssh_port: 22
    },
    loading: false,
    error: null
  }),
  actions: {
    async fetchSettings() {
      this.loading = true
      this.error = null
      try {
        const response = await settingsApi.getSettings()
        this.settings = {
          ...this.settings,
          ...response.data
        }
      } catch (error) {
        this.error = error.message
        console.error('Error fetching settings:', error)
      } finally {
        this.loading = false
      }
    },
    async updateSettings(settings) {
      this.loading = true
      this.error = null
      try {
        await settingsApi.updateSettings(settings)
        this.settings = {
          ...this.settings,
          ...settings
        }
        // 重新获取设置以确保数据一致
        await this.fetchSettings()
      } catch (error) {
        this.error = error.message
        console.error('Error updating settings:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async testApiConnection() {
      this.loading = true
      this.error = null
      try {
        const response = await settingsApi.testApiConnection(this.settings)
        return response.data
      } catch (error) {
        this.error = error.message
        console.error('Error testing API connection:', error)
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})
