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
  sendMessage: (prompt, mode, host, conversationId, reactEnabled = true, hosts = null) => {
    const payload = { prompt, mode, host, conversation_id: conversationId, react_enabled: reactEnabled }
    if (hosts && hosts.length > 0) {
      payload.hosts = hosts
    }
    return api.post('/chat', payload)
  },
  executePlan: (commands, hosts) => api.post('/chat/execute-plan', { commands, hosts }),
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

// 委托管理
export const delegateApi = {
  // 取消委托
  cancel: (taskId) => api.post('/delegate/cancel', { task_id: taskId }),
  // 确认安装 Claude Code
  confirmInstall: (taskId, forceExecute) => api.post('/delegate/confirm-install', { task_id: taskId, force_execute: forceExecute }),
  // 解决委托冲突
  resolveConflict: (taskId, action) => api.post('/delegate/resolve-conflict', { task_id: taskId, action }),
  // 查询委托状态
  getStatus: (taskId) => api.get(`/delegate/status/${taskId}`),
  // 响应权限请求
  respondPermission: (taskId, permissionId, approved) => api.post('/delegate/respond-permission', { task_id: taskId, permission_id: permissionId, approved }),
}

export const toolApi = {
  // 探测远程服务器上的大工具
  listTools: (hostId) => api.get('/tools/list', { params: { host_id: hostId } }),
  // 启动 REPL 会话
  createSession: (toolName, hostId, password) => api.post(`/tools/${toolName}/sessions`, { host_id: hostId, password }),
  // 向会话发送消息
  sendMessage: (sessionId, message) => api.post(`/tools/sessions/${sessionId}/send`, { message }),
  // 关闭会话
  closeSession: (sessionId) => api.delete(`/tools/sessions/${sessionId}`),
  // 查询会话状态
  getSessionStatus: (sessionId) => api.get(`/tools/sessions/${sessionId}/status`),
  // 发送特殊按键 (方向键、Enter 等)
  sendKey: (sessionId, key) => api.post(`/tools/sessions/${sessionId}/key`, { key }),
}

export default api
