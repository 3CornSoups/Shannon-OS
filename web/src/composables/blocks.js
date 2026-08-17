/**
 * Block-based message model utilities.
 *
 * Block types:
 *   thinking   — 思考过程，可折叠
 *   plan       — 执行计划（含命令列表和风险）
 *   command    — 命令生命周期（state: running|done|error）
 *   react      — ReAct 决策步骤
 *   text       — 最终文本回复
 *   delegation — 委托子智能体
 */

// ── normalizeBlocks: 统一新旧格式为 blocks[] ──

export function normalizeBlocks(message) {
  if (!message || !message.meta) return []

  // 新格式：meta.blocks 直接存在
  if (Array.isArray(message.meta.blocks)) {
    return message.meta.blocks
  }

  // 老格式兼容：从 meta 散字段推断 blocks
  const blocks = []

  // thinking → thinking block
  if (message.meta.thinking) {
    blocks.push({ type: 'thinking', content: message.meta.thinking })
  }

  // plan → plan block
  if (message.meta.plan) {
    blocks.push({
      type: 'plan',
      reasoning: message.meta.plan.reasoning || '',
      commands: message.meta.plan.commands_plan || [],
      risk: message.meta.plan.risk_level || 'LOW',
    })
  }

  // react_action → react block
  if (message.meta.type === 'react_action') {
    blocks.push({
      type: 'react',
      action: message.meta.action || 'run',
      reasoning: message.meta.reasoning || '',
      command: message.meta.command || '',
      purpose: message.meta.purpose || '',
    })
  }

  // _delegationActive → delegation block（兼容老格式流式委托未持久化 blocks）
  if (message.meta._delegationActive || message.meta._delegationState) {
    blocks.push({
      type: 'delegation',
      state: message.meta._delegationState || 'completed',
      agent: 'Claude Code',
      reason: '',
      riskLevel: 'LOW',
    })
  }

  // react_result / command_start → command block
  if (message.meta.type === 'react_result' || message.meta.type === 'command_result') {
    blocks.push({
      type: 'command',
      state: (message.meta.returncode === 0) ? 'done' : 'error',
      command: message.meta.command || '',
      output: message.meta.stdout || message.meta.stderr || '',
      exitCode: message.meta.returncode ?? -1,
    })
  }

  if (message.meta.type === 'command_start') {
    blocks.push({
      type: 'command',
      state: 'done',
      command: message.meta.command || '',
      purpose: message.meta.purpose || '',
      reasoning: message.meta.reasoning || '',
    })
  }

  return blocks
}

// ── appendBlock: 追加 block 到消息的 meta.blocks ──

export function appendBlock(message, block) {
  if (!message.meta) {
    message.meta = {}
  }
  if (!Array.isArray(message.meta.blocks)) {
    message.meta.blocks = []
  }
  message.meta.blocks.push({ ...block, ts: Date.now() })
  return message.meta.blocks
}

// ── updateLastBlock: 更新最后一个 block（用于 command state 迁移等） ──

export function updateLastBlock(message, updates) {
  const blocks = message.meta?.blocks
  if (!blocks || blocks.length === 0) return null
  const last = blocks[blocks.length - 1]
  Object.assign(last, updates)
  return last
}

// ── getLastBlock: 获取最后一个 block ──

export function getLastBlock(message) {
  const blocks = message.meta?.blocks
  if (!blocks || blocks.length === 0) return null
  return blocks[blocks.length - 1]
}

// ── hasBlockType: 检查消息是否包含某种类型的 block ──

export function hasBlockType(message, type) {
  const blocks = message.meta?.blocks
  if (!blocks) return false
  return blocks.some(b => b.type === type)
}

// ── delegation block helpers ──

// 获取或创建 delegation block（同一个消息中只有一个 delegation block）
export function getDelegationBlock(message) {
  const blocks = message.meta?.blocks
  if (!blocks) return null
  return blocks.find(b => b.type === 'delegation') || null
}

// 确保存在 delegation block，不存在则创建
export function ensureDelegationBlock(message, initial) {
  let block = getDelegationBlock(message)
  if (!block) {
    block = { type: 'delegation', state: 'suggested', agent: 'Claude Code', ...initial, ts: Date.now() }
    if (!message.meta) message.meta = {}
    if (!message.meta.blocks) message.meta.blocks = []
    message.meta.blocks.push(block)
  }
  return block
}

// 更新 delegation block（原地修改，保持响应性）
export function updateDelegationBlock(message, updates) {
  const block = getDelegationBlock(message)
  if (block) Object.assign(block, updates)
  return block
}
