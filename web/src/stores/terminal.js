import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useTerminalStore = defineStore('terminal', () => {
  const logEntries = ref([])

  function addEntry(entry) {
    logEntries.value.push({
      id: Date.now() + Math.random(),
      source: entry.source || 'manual',
      ...entry
    })
    // Keep max 500 entries to prevent memory issues
    if (logEntries.value.length > 500) {
      logEntries.value = logEntries.value.slice(-500)
    }
  }

  function addEvent(event) {
    if (event.type === 'command_start') {
      addEntry({
        type: 'event',
        typeLabel: '执行中',
        source: 'ai',
        command: event.command,
        timestamp: Date.now()
      })
    } else if (event.type === 'command_result') {
      addEntry({
        type: 'result',
        typeLabel: 'AI执行',
        source: 'ai',
        command: event.command,
        stdout: event.stdout || '',
        stderr: event.stderr || '',
        returncode: event.returncode,
        timestamp: Date.now()
      })
    } else if (event.type === 'status') {
      addEntry({
        type: 'info',
        typeLabel: '状态',
        source: 'ai',
        message: event.message,
        timestamp: Date.now()
      })
    } else if (event.type === 'error') {
      addEntry({
        type: 'error',
        typeLabel: '错误',
        source: 'ai',
        message: event.message,
        timestamp: Date.now()
      })
    } else if (event.type === 'self_heal_retry') {
      addEntry({
        type: 'event',
        typeLabel: '重试',
        source: 'ai',
        command: event.new_command,
        timestamp: Date.now()
      })
    } else if (event.type === 'command_output') {
      // live output line - append to last log entry if it's the same command
      const last = logEntries.value[logEntries.value.length - 1]
      if (last && last.type === 'output' && last.command === event.command) {
        last.output += event.line
      } else {
        addEntry({
          type: 'output',
          typeLabel: '输出',
          source: 'ai',
          command: event.command,
          output: event.line,
          timestamp: Date.now()
        })
      }
    } else {
      addEntry({
        type: 'info',
        typeLabel: '日志',
        source: 'ai',
        message: JSON.stringify(event),
        timestamp: Date.now()
      })
    }
  }

  function clearLogs() {
    logEntries.value = []
  }

  return { logEntries, addEntry, addEvent, clearLogs }
})
