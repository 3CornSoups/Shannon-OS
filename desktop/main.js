const { app, BrowserWindow } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const http = require('http')
const net = require('net')

// 项目根目录（desktop/ 的上一级）
const ROOT = path.resolve(__dirname, '..')
const BACKEND_PORT = 8000
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`
let backendProcess = null
let mainWindow = null

// ── 后端管理 ──

function startBackend() {
  const python = process.platform === 'win32' ? 'python' : 'python3'
  const cmd = '-m'

  // 优先在项目 .venv 中找 Python
  const venvPython = process.platform === 'win32'
    ? path.join(ROOT, '.venv', 'Scripts', 'python.exe')
    : path.join(ROOT, '.venv', 'bin', 'python3')

  console.log('[Shannon] 启动后端...')
  backendProcess = spawn(python, [cmd, 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)], {
    cwd: ROOT,
    env: { ...process.env, PATH: `${path.dirname(venvPython)}${path.delimiter}${process.env.PATH}` },
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  backendProcess.stdout.on('data', (d) => {
    const line = d.toString().trim()
    if (line) console.log(`[backend] ${line}`)
  })
  backendProcess.stderr.on('data', (d) => {
    const line = d.toString().trim()
    if (line) console.error(`[backend:err] ${line}`)
  })
  backendProcess.on('exit', (code) => {
    console.log(`[Shannon] 后端已退出 (code=${code})`)
    backendProcess = null
  })
}

function stopBackend() {
  if (backendProcess) {
    console.log('[Shannon] 关闭后端...')
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', String(backendProcess.pid), '/f', '/t'])
    } else {
      backendProcess.kill('SIGTERM')
      setTimeout(() => {
        if (backendProcess) backendProcess.kill('SIGKILL')
      }, 3000)
    }
  }
}

function waitForBackend(retries = 30, delay = 1000) {
  return new Promise((resolve, reject) => {
    let attempts = 0
    function check() {
      attempts++
      const req = http.get(`${BACKEND_URL}/api/health`, (res) => {
        // 任何响应（包括 404）都说明后端在运行
        resolve()
      })
      req.on('error', () => {
        if (attempts >= retries) {
          reject(new Error(`后端启动超时 (${retries} 次尝试)`))
        } else {
          setTimeout(check, delay)
        }
      })
      req.setTimeout(2000, () => {
        req.destroy()
        if (attempts >= retries) {
          reject(new Error(`后端启动超时 (${retries} 次尝试)`))
        } else {
          setTimeout(check, delay)
        }
      })
    }
    check()
  })
}

// ── 窗口管理 ──

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 640,
    title: 'Shannon OS',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
    icon: path.join(__dirname, 'icon.png'),
  })

  mainWindow.loadURL(BACKEND_URL)
  mainWindow.on('closed', () => { mainWindow = null })
}

// ── 应用生命周期 ──

app.on('ready', async () => {
  try {
    startBackend()
    await waitForBackend()
    console.log('[Shannon] 后端就绪，打开窗口')
    createWindow()
  } catch (err) {
    console.error('[Shannon] 启动失败:', err.message)
    app.quit()
  }
})

app.on('window-all-closed', () => {
  stopBackend()
  app.quit()
})

app.on('before-quit', () => {
  stopBackend()
})

app.on('will-quit', () => {
  stopBackend()
})

// macOS: 保持应用运行直到用户主动退出
app.on('activate', () => {
  if (mainWindow === null) createWindow()
})
