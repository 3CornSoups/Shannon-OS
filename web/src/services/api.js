import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 服务器管理
export const serverApi = {
  // 获取服务器列表
  getServers: () => api.get('/hosts'),
  // 测试服务器连接
  testConnection: (host) => api.post('/host/test', { host }),
  // 获取服务器上下文
  getContext: (hostId) => api.get(`/context/${hostId}`)
}

// 聊天和命令执行
export const chatApi = {
  // 发送聊天请求
  sendMessage: (prompt, mode, host, conversationId) => api.post('/chat', { prompt, mode, host, conversation_id: conversationId }),
  // 确认执行
  confirmExecution: (taskId, forceExecute, operatorName) => api.post('/execute/confirm', { task_id: taskId, force_execute: forceExecute, operator_name: operatorName }),
  // 获取对话历史
  getChatHistory: (hostId) => api.get(`/chat/${hostId}`),
  // 清除对话历史
  clearChatHistory: (hostId) => api.delete(`/chat/${hostId}`),
  // 会话管理
  getConversations: (hostId) => api.get(`/conversations/${hostId}`),
  createConversation: (hostId, title = '新对话') => api.post('/conversations', { host_id: hostId, title }),
  updateConversationTitle: (convId, title) => api.patch(`/conversations/${convId}`, { title }),
  deleteConversation: (convId) => api.delete(`/conversations/${convId}`),
  getConversationMessages: (convId) => api.get(`/conversations/${convId}/messages`),
}

// 设置管理
export const settingsApi = {
  // 获取设置
  getSettings: () => api.get('/settings'),
  // 更新设置
  updateSettings: (settings) => api.post('/settings', settings),
  // 测试API连接
  testApiConnection: (settings) => api.post('/settings/test', settings),
  // AI生成模板
  generateTemplate: (description) => api.post('/templates/generate', { description })
}

// 系统健康
export const healthApi = {
  // 检查健康状态
  checkHealth: () => api.get('/health')
}

export const monitoringApi = {
  getMonitorData: (hostId) => api.post(`/monitor/${hostId}`)
}

export const terminalApi = {
  execCommand: (payload) => api.post('/terminal/exec', payload)
}

export const filesApi = {
  listDirectory: (payload) => api.post('/files/list', payload),
  readFile: (payload) => api.post('/files/read', payload),
  writeFile: (payload) => api.post('/files/write', payload),
  createEntry: (payload) => api.post('/files/create', payload),
  deleteEntry: (payload) => api.post('/files/delete', payload),
  renameEntry: (payload) => api.post('/files/rename', payload),
}

export default api
