const { contextBridge } = require('electron')

// 暴露安全的 API 给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  backendURL: 'http://127.0.0.1:8000',
})
