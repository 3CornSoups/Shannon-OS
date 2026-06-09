<template>
  <Layout>
    <div class="dashboard-layout">
      <div class="page-header">
        <h1 class="page-title">Shannon OS Agent</h1>
        <div class="page-actions">
          <div class="server-selector">
            <span class="server-label">当前服务器</span>
            <span class="server-name" v-if="!serverStore.isMultiMode">{{ currentServer ? currentServer.name : '未选择' }}</span>
            <span class="server-name" v-else-if="serverStore.selectedServers.length === 0">未选择</span>
            <span class="server-name" v-else>{{ serverStore.selectedServers.map(s => s.name).join('、') }}</span>
          </div>
          <button @click="toggleSidebar" class="btn btn-outline" title="对话列表">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
            对话列表
          </button>
          <button @click="router.push('/servers')" class="btn btn-outline">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
              <line x1="6" y1="6" x2="6.01" y2="6"/>
              <line x1="6" y1="18" x2="6.01" y2="18"/>
            </svg>
            管理服务器
          </button>
        </div>
      </div>

        <!-- 多服务器标签栏 -->
        <div v-if="serverStore.isMultiMode && serverStore.selectedServers.length > 0" class="flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-lg mb-3 overflow-x-auto">
          <span class="text-xs text-gray-500 flex-shrink-0">📊 已选服务器:</span>
          <span
            v-for="server in serverStore.selectedServers"
            :key="server.id"
            class="inline-flex items-center gap-1 px-2 py-0.5 bg-white rounded-full text-xs border border-gray-200 whitespace-nowrap"
          >
            {{ server.name }}
            <button @click="removeServer(server)" class="ml-1 text-gray-400 hover:text-red-500">&times;</button>
          </span>
        </div>

      <div class="dashboard-container">
      <div class="chat-main-area">

      <div v-if="!apiKeySet" class="alert alert-danger">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="alert-icon">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <div class="alert-content">
          <h3 class="alert-title">API Key 未设置</h3>
          <p class="alert-desc">请先在设置页面配置 API Key 才能使用聊天功能。</p>
          <button @click="router.push('/settings')" class="btn btn-outline btn-sm">前往设置</button>
        </div>
      </div>

      <div class="chat-card">
        <div class="chat-header">
          <h2 class="chat-title">聊天与命令执行</h2>
        </div>

        <div ref="chatContainer" class="chat-messages">
        <!-- 批量 Tab 面板 -->
        <div v-if="serverStore.isMultiMode && batchTabs.length > 0" class="mb-4">
          <div class="flex border-b border-gray-200 gap-0">
            <button
              v-for="tab in batchTabs"
              :key="tab.hostId"
              @click="activeTab = tab.hostId"
              class="px-4 py-2 text-xs font-medium border-b-2 transition-colors"
              :class="activeTab === tab.hostId ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'"
            >
              <span class="mr-1">{{ tab.status === 'running' ? '🔵' : tab.status === 'success' ? '🟢' : tab.status === 'failed' ? '🔴' : '🟡' }}</span>
              {{ tab.name }}
            </button>
          </div>
        </div>
          <div
            v-for="(message, index) in messages"
            :key="index"
            class="message-row"
            :class="message.role === 'user' ? 'message-user' : 'message-assistant'"
          >
            <div class="message-bubble" :class="message.role === 'user' ? 'bubble-user' : 'bubble-assistant'">
              <div class="message-header">
                <div class="avatar" :class="message.role === 'user' ? 'avatar-user' : 'avatar-assistant'">
                  <svg v-if="message.role === 'user'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
                    <circle cx="12" cy="7" r="4"/>
                  </svg>
                  <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="11" width="18" height="10" rx="2"/>
                    <circle cx="12" cy="5" r="2"/>
                    <path d="M12 7v4"/>
                    <line x1="8" y1="16" x2="8" y2="16"/>
                    <line x1="16" y1="16" x2="16" y2="16"/>
                  </svg>
                </div>
                <span class="message-sender">{{ message.role === 'user' ? '你' : 'Shannon' }}</span>
              </div>
              <div class="message-content" v-html="renderMarkdown(message.content)"></div>

              <!-- 委托卡片（嵌入聊天流） -->
              <DelegationCard
                v-if="message.meta && message.meta._delegationActive"
                :visible="delegationState.visible"
                :state="delegationState.state"
                :agent="delegationState.agent"
                :reason="delegationState.reason"
                :risk-level="delegationState.riskLevel"
                :goal-achieved="delegationState.goalAchieved"
                :goal-reasoning="delegationState.goalReasoning"
                :execution-time="delegationState.executionTime"
                :files-changed="delegationState.filesChanged"
                :files-changed-count="delegationState.filesChangedCount"
                :risk-warnings="delegationState.riskWarnings"
                :output-summary="delegationState.outputSummary"
                :output-lines="delegationState.outputLines"
                :message="delegationState.message"
                :waiting-permission="delegationState.waitingPermission"
                :permission-prompt="delegationState.permissionPrompt"
                :permission-id="delegationState.permissionId"
                :auto-approved="delegationState.autoApproved"
                @delegate="confirmDelegation(delegationState.currentTaskId)"
                @reject="rejectDelegation(delegationState.currentTaskId)"
                @cancel="cancelDelegation(delegationState.currentTaskId)"
                @respond-permission="respondPermission"
              />

              <div v-if="message.meta && message.meta.plan && !message.meta._delegationActive" class="plan-section">
                <div class="plan-header">
                  <h4 class="plan-title">执行计划</h4>
                  <span class="risk-badge" :class="message.meta.plan.risk_level === 'HIGH' ? 'risk-high' : 'risk-low'">
                    {{ message.meta.plan.risk_level }}
                  </span>
                </div>
                <div class="plan-reasoning">{{ message.meta.plan.reasoning || '' }}</div>
                <div v-if="message.meta.plan.commands_plan && message.meta.plan.commands_plan.length" class="commands-section">
                  <h5 class="commands-title">执行命令</h5>
                  <div class="commands-list">
                    <div v-for="(cmd, cmdIndex) in message.meta.plan.commands_plan" :key="cmdIndex" class="command-item">
                      <div class="command-purpose">{{ cmd.purpose || '执行命令' }}</div>
                      <pre class="command-code">{{ cmd.command }}</pre>
                    </div>
                  </div>
                </div>
              </div>

              <!-- ReAct 步骤卡片 -->
              <div v-if="message.meta && message.meta.type === 'react_action'" class="react-step react-action-step">
                <div class="step-header">
                  <span class="step-badge step-run">{{ message.meta.action === 'done' ? '完成' : message.meta.action === 'ask' ? '询问' : '执行' }}</span>
                  <span v-if="message.meta.reasoning" class="step-reasoning">{{ message.meta.reasoning }}</span>
                </div>
                <div v-if="message.meta.command" class="step-command">
                  <pre class="command-code">{{ message.meta.command }}</pre>
                  <span v-if="message.meta.purpose" class="step-purpose">{{ message.meta.purpose }}</span>
                </div>
                <div v-if="message.meta.message" class="step-message">{{ message.meta.message }}</div>
              </div>
              <div v-if="message.meta && message.meta.type === 'react_result'" class="react-step react-result-step">
                <div class="step-header">
                  <span class="step-badge" :class="message.meta.returncode === 0 ? 'step-ok' : 'step-fail'">
                    {{ message.meta.returncode === 0 ? '成功' : '失败' }}
                  </span>
                  <span class="step-returncode">返回码: {{ message.meta.returncode }}</span>
                </div>
                <div v-if="message.meta.stdout" class="step-output">
                  <div class="step-output-label">标准输出</div>
                  <pre class="step-output-text">{{ message.meta.stdout }}</pre>
                </div>
                <div v-if="message.meta.stderr" class="step-output">
                  <div class="step-output-label step-output-label-error">错误输出</div>
                  <pre class="step-output-text step-output-text-error">{{ message.meta.stderr }}</pre>
                </div>
              </div>

              <div v-if="message.meta && message.meta.pendingConfirmation" class="confirmation-section">
                <div class="confirmation-actions">
                  <button @click="cancelExecution(message.meta.plan.task_id)" class="btn btn-outline btn-sm">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    取消
                  </button>
                  <button
                    v-if="message.meta.plan.risk_level === 'HIGH'"
                    @click="confirmExecution(message.meta.plan.task_id, true)"
                    class="btn btn-sm btn-danger"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    确认执行（高风险）
                  </button>
                  <button v-else @click="confirmExecution(message.meta.plan.task_id, true)" class="btn btn-primary btn-sm">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20,6 9,17 4,12"/></svg>
                    确认执行
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div v-if="loading" class="message-row message-assistant">
            <div class="message-bubble bubble-assistant">
              <div class="message-header">
                <div class="avatar avatar-assistant">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="11" width="18" height="10" rx="2"/>
                    <circle cx="12" cy="5" r="2"/>
                    <path d="M12 7v4"/>
                  </svg>
                </div>
                <span class="message-sender">Shannon</span>
              </div>
              <div class="typing-indicator">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
              </div>
            </div>
          </div>
        <!-- 批量状态栏 -->
        <div v-if="serverStore.isMultiMode && batchTabs.length > 0" class="flex items-center gap-3 px-3 py-1.5 bg-gray-100 rounded text-xs text-gray-600 mt-2">
          <span>🟢 成功 {{ batchSuccessCount }}</span>
          <span>🔵 执行中 {{ batchRunningCount }}</span>
          <span>🔴 失败 {{ batchFailedCount }}</span>
        </div>
        </div>

        <div class="chat-input-area">
          <div class="mode-selector">
            <span class="mode-label">运行模式</span>
            <div class="mode-buttons">
              <button
                v-for="mode in modes"
                :key="mode.id"
                @click="selectedMode = mode.id"
                class="mode-btn"
                :class="{ active: selectedMode === mode.id }"
              >
                {{ mode.label }}
              </button>
            </div>
          <!-- ReAct Toggle（仅多服务器时显示） -->
          <label v-if="serverStore.isMultiMode" class="flex items-center gap-1.5 cursor-pointer text-xs">
            <span class="text-gray-500">ReAct</span>
            <div class="relative">
              <input type="checkbox" v-model="reactEnabled" class="sr-only peer" />
              <div class="w-8 h-4 bg-gray-200 peer-focus:ring-2 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-indigo-600"></div>
            </div>
          </label>
          </div>
          <textarea
            v-model="prompt"
            class="chat-textarea"
            :class="{ 'voice-active': isListening }"
            placeholder="输入命令或问题，例如：帮我检查系统状态&#10;&#10;按 Ctrl + Enter 发送"
            @keydown.ctrl.enter.prevent="sendMessage"
          ></textarea>
          <div v-if="isListening && voiceInterimText" class="voice-interim">{{ voiceInterimText }}</div>
          <div v-if="voiceError" class="voice-error">{{ voiceError }}</div>
          <div class="chat-actions">
            <div class="chat-actions-left">
              <button @click="showTemplates = !showTemplates" class="btn btn-outline btn-sm">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="8" y1="6" x2="21" y2="6"/>
                  <line x1="8" y1="12" x2="21" y2="12"/>
                  <line x1="8" y1="18" x2="21" y2="18"/>
                  <line x1="3" y1="6" x2="3.01" y2="6"/>
                  <line x1="3" y1="12" x2="3.01" y2="12"/>
                  <line x1="3" y1="18" x2="3.01" y2="18"/>
                </svg>
                模板
              </button>
              <button
                v-if="voiceSupported"
                @click="toggleVoiceInput"
                class="btn btn-outline btn-sm voice-btn"
                :class="{ 'voice-btn-active': isListening }"
                :title="isListening ? '停止语音输入' : '语音输入'"
              >
                <svg v-if="!isListening" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                  <line x1="12" y1="19" x2="12" y2="23"/>
                  <line x1="8" y1="23" x2="16" y2="23"/>
                </svg>
                <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="voice-pulse">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                  <line x1="12" y1="19" x2="12" y2="23"/>
                  <line x1="8" y1="23" x2="16" y2="23"/>
                </svg>
                {{ isListening ? '停止' : '语音' }}
              </button>
            </div>
            <button
              @click="sendMessage"
              class="btn btn-primary"
              :disabled="!prompt.trim() || loading || !currentServer"
            >
              <span v-if="loading">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="loading-spinner"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/></svg>
                发送中...
              </span>
              <span v-else>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13"/>
                  <polygon points="22,2 15,22 11,13 2,9"/>
                </svg>
                发送
              </span>
            </button>
          </div>
        </div>
      </div>

      </div><!-- .chat-main-area -->

      <transition name="sidebar-slide">
        <aside v-if="sidebarVisible" class="conversation-sidebar">
          <div class="sidebar-header">
            <h3 class="sidebar-title">对话记录</h3>
            <button @click="createNewConversation" class="btn btn-sm btn-primary" :disabled="!currentServer">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              新对话
            </button>
          </div>

          <div v-if="!currentServer" class="sidebar-empty">
            <p>请先选择服务器</p>
          </div>
          <div v-else-if="conversations.length === 0" class="sidebar-empty">
            <p>暂无对话</p>
            <p class="sidebar-empty-hint">发送消息将自动创建新对话</p>
          </div>

          <div v-else class="sidebar-list">
            <div
              v-for="conv in conversations"
              :key="conv.id"
              class="sidebar-conv-item"
              :class="{ active: conv.id === activeConversationId }"
              @click="switchConversation(conv.id)"
            >
              <div v-if="editingConvId === conv.id" class="conv-rename-form" @click.stop>
                <input
                  v-model="editingTitle"
                  class="conv-rename-input"
                  @keydown.enter.prevent="submitRename"
                  @keydown.escape.prevent="cancelRename"
                  @blur="submitRename"
                  ref="renameInput"
                />
              </div>
              <template v-else>
                <div class="conv-item-main">
                  <svg class="conv-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
                  </svg>
                  <div class="conv-info">
                    <span class="conv-title">{{ conv.title }}</span>
                    <span class="conv-meta">{{ conv.message_count || 0 }} 条消息</span>
                  </div>
                </div>
                <div class="conv-actions" @click.stop>
                  <button @click="startRename(conv)" class="conv-action-btn" title="重命名">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                  </button>
                  <button @click="confirmDelete(conv.id)" class="conv-action-btn conv-action-delete" title="删除">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                  </button>
                </div>
              </template>
            </div>
          </div>

          <div v-if="confirmDeleteId" class="delete-confirm" @click.stop>
            <p>确认删除此对话？</p>
            <div class="delete-confirm-actions">
              <button @click="confirmDeleteId = null" class="btn btn-outline btn-sm">取消</button>
              <button @click="executeDelete" class="btn btn-sm btn-danger">删除</button>
            </div>
          </div>
        </aside>
      </transition>
      </div><!-- .dashboard-container -->

      <div v-if="showTemplates" class="templates-card">
        <div class="templates-header">
          <h2 class="templates-title">执行计划模板</h2>
          <div class="templates-header-actions">
            <button @click="showCustomTemplateForm = !showCustomTemplateForm" class="btn btn-outline btn-sm">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              {{ showCustomTemplateForm ? '收起' : '自定义模板' }}
            </button>
            <button @click="showTemplates = false" class="close-btn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        </div>

        <div v-if="showCustomTemplateForm" class="custom-template-form">
          <h3 class="form-title">创建自定义模板</h3>
          <div class="form-group">
            <label class="form-label">模板名称</label>
            <input v-model="customTemplate.name" class="input" placeholder="例如：磁盘检查" />
          </div>
          <div class="form-group">
            <label class="form-label">分类</label>
            <select v-model="customTemplate.category" class="input">
              <option v-for="cat in templateStore.categories" :key="cat" :value="cat">{{ cat }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">提示词</label>
            <textarea v-model="customTemplate.prompt" class="input form-textarea" placeholder="发送给运维助手的提示词" rows="3"></textarea>
          </div>
          <div class="form-group">
            <label class="form-label">描述</label>
            <input v-model="customTemplate.description" class="input" placeholder="一句话描述用途" />
          </div>
          <div class="form-actions">
            <div class="form-actions-left">
              <button @click="generateWithAI" class="btn btn-outline btn-sm" :disabled="aiGenerating || !customTemplate.description">
                <svg v-if="aiGenerating" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" class="loading-spinner"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/></svg>
                <svg v-else width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                {{ aiGenerating ? '生成中...' : 'AI 生成' }}
              </button>
              <span v-if="aiError" class="ai-error">{{ aiError }}</span>
            </div>
            <div class="form-actions-right">
              <button @click="resetCustomTemplate" class="btn btn-outline btn-sm">清空</button>
              <button @click="saveCustomTemplate" class="btn btn-primary btn-sm" :disabled="!customTemplate.name || !customTemplate.prompt">保存模板</button>
            </div>
          </div>
        </div>

        <div class="templates-grid">
          <div
            v-for="template in templates"
            :key="template.id"
            class="template-card"
            @click="applyTemplate(template)"
          >
            <div class="template-category">{{ template.category }}</div>
            <h3 class="template-name">{{ template.name }}</h3>
            <p class="template-desc">{{ template.description }}</p>
            <button v-if="template.userCreated" @click.stop="deleteUserTemplate(template.id)" class="template-delete-btn" title="删除模板">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
            </button>
          </div>
        </div>
      </div>

      <div v-if="showPasswordModal" class="modal-overlay" @click.self="showPasswordModal = false">
        <div class="modal">
          <h2 class="modal-title">服务器密码</h2>
          <div class="modal-body">
            <p class="modal-server">服务器: {{ currentServer ? currentServer.name : '未知' }}</p>
            <p class="modal-address">{{ currentServer ? `${currentServer.host}:${currentServer.port}` : '未知' }}</p>
          </div>
          <div class="modal-input-group">
            <label class="modal-label">SSH 密码</label>
            <input
              v-model="serverPassword"
              type="password"
              class="input"
              placeholder="请输入服务器SSH密码"
              @keydown.enter.prevent="confirmPassword"
            />
          </div>
          <div class="modal-checkbox">
            <input v-model="rememberPassword" type="checkbox" id="rememberPassword" class="checkbox" />
            <label for="rememberPassword" class="checkbox-label">记住密码（服务器端存储）</label>
          </div>
          <div class="modal-actions">
            <button @click="showPasswordModal = false" class="btn btn-outline">取消</button>
            <button @click="confirmPassword" class="btn btn-primary">确认</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 委托相关弹窗 -->
    <DelegationInstallModal
      :visible="delegationInstallModal.visible"
      :host-name="delegationInstallModal.hostName"
      @install="confirmInstall"
      @reject="rejectInstall"
      @close="delegationInstallModal.visible = false"
    />
    <DelegationConflictModal
      :visible="delegationConflictModal.visible"
      @cancel-and-new="resolveConflictCancelAndNew"
      @queue="resolveConflictQueue"
    />
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, reactive, watch } from 'vue'
import { renderMarkdown } from '../composables/markdown.js'
import { useRouter } from 'vue-router'
import Layout from '../components/layout/Layout.vue'
import { useServerStore } from '../stores/server'
import { useTemplateStore } from '../stores/template'
import { useTerminalStore } from '../stores/terminal'
import { chatApi, settingsApi, delegateApi } from '../services/api'
import { useVoiceInput } from '../composables/useVoiceInput'
import DelegationCard from '../components/DelegationCard.vue'
import DelegationInstallModal from '../components/DelegationInstallModal.vue'
import DelegationConflictModal from '../components/DelegationConflictModal.vue'

const router = useRouter()
const serverStore = useServerStore()
const templateStore = useTemplateStore()
const terminalStore = useTerminalStore()

const chatContainer = ref(null)
const messages = ref([])
const prompt = ref('')
const loading = ref(false)
const selectedMode = ref('chat')
const showTemplates = ref(false)
const showPasswordModal = ref(false)
const apiKeySet = ref(true)
const serverPassword = ref('')
const rememberPassword = ref(true)
const currentSSE = ref(null)

const reactEnabled = ref(true)
const batchTabs = ref([])
const activeTab = ref(null)
const batchOutputs = ref({})

const batchSuccessCount = computed(() => batchTabs.value.filter(t => t.status === 'success').length)
const batchRunningCount = computed(() => batchTabs.value.filter(t => t.status === 'running').length)
const batchFailedCount = computed(() => batchTabs.value.filter(t => t.status === 'failed').length)

// 委托状态管理
const delegationState = reactive({
  visible: false,
  state: 'suggested', // suggested | running | completed | cancelled | timeout | fallback
  agent: 'Claude Code',
  reason: '',
  riskLevel: 'LOW',
  riskReason: '',
  goalAchieved: '',
  goalReasoning: '',
  executionTime: 0,
  filesChanged: [],
  filesChangedCount: 0,
  riskWarnings: [],
  outputSummary: '',
  outputLines: [],
  stderr: '',
  exitCode: null,
  message: '',
  currentTaskId: null,
  pendingConfirmTaskId: null,
  waitingPermission: false,
  permissionPrompt: '',
  permissionId: '',
  autoApproved: false,
})
const delegationInstallModal = reactive({
  visible: false,
  hostName: '',
  taskId: null,
})
const delegationConflictModal = reactive({
  visible: false,
  existingTaskId: '',
  newTaskId: '',
})

function removeServer(server) {
  serverStore.selectedServers = serverStore.selectedServers.filter(s => s.id !== server.id)
}

function initBatchTabs() {
  batchTabs.value = serverStore.selectedServers.map(s => ({
    hostId: s.id,
    name: s.name,
    status: 'pending',
    output: '',
  }))
  activeTab.value = serverStore.selectedServers[0]?.id || null
  batchOutputs.value = {}
}

function updateBatchTab(hostId, status, line) {
  const tab = batchTabs.value.find(t => t.hostId === hostId)
  if (tab) tab.status = status
  if (!batchOutputs.value[hostId]) batchOutputs.value[hostId] = []
  if (line) batchOutputs.value[hostId].push(line)
}

// 对话管理
const conversations = ref([])
const activeConversationId = ref(null)
const sidebarVisible = ref(true)
const editingConvId = ref(null)
const editingTitle = ref('')
const confirmDeleteId = ref(null)
const renameInput = ref(null)

// 自定义模板
const showCustomTemplateForm = ref(false)
const aiGenerating = ref(false)
const aiError = ref('')
const customTemplate = reactive({
  name: '',
  category: '基础管理',
  prompt: '',
  description: ''
})

const { isListening, isSupported: voiceSupported, errorMessage: voiceError, startListening, stopListening } = useVoiceInput()

const voiceInterimText = ref('')

const toggleVoiceInput = () => {
  if (isListening.value) {
    stopListening()
    voiceInterimText.value = ''
    return
  }
  startListening(
    (finalText, interimText) => {
      if (finalText) {
        prompt.value += finalText
      }
      voiceInterimText.value = interimText
    },
    () => {
      voiceInterimText.value = ''
    }
  )
}

const currentServer = computed(() => serverStore.currentServer)
const templates = computed(() => templateStore.templates)

const modes = [
  { id: 'chat', label: 'Chat 模式' },
  { id: 'agent', label: 'Agent 模式' },
  { id: 'auto', label: 'Auto 模式' }
]

// ---- 对话管理方法 ----

const loadConversations = async () => {
  if (!currentServer.value) return
  try {
    const response = await chatApi.getConversations(currentServer.value.id)
    conversations.value = response.data || []
  } catch (error) {
    console.error('加载对话列表失败:', error)
    conversations.value = []
  }
}

const createNewConversation = async () => {
  if (!currentServer.value) return
  try {
    const response = await chatApi.createConversation(currentServer.value.id, '新对话')
    const convId = response.data.id
    await loadConversations()
    await switchConversation(convId)
  } catch (error) {
    console.error('创建对话失败:', error)
  }
}

const switchConversation = async (convId) => {
  if (convId === activeConversationId.value) return
  activeConversationId.value = convId
  messages.value = []
  if (!convId) return
  try {
    const response = await chatApi.getConversationMessages(convId)
    const history = response.data || []
    if (history.length > 0) {
      messages.value = history.map(msg => ({
        role: msg.role,
        content: msg.content,
        meta: msg.meta || {}
      }))
    }
    await loadConversations()
    scrollToBottom()
  } catch (error) {
    console.error('加载对话消息失败:', error)
  }
}

const startRename = (conv) => {
  editingConvId.value = conv.id
  editingTitle.value = conv.title
  nextTick(() => {
    const el = document.querySelector('.conv-rename-input')
    if (el) el.focus()
  })
}

const submitRename = async () => {
  const convId = editingConvId.value
  const title = editingTitle.value.trim()
  editingConvId.value = null
  editingTitle.value = ''
  if (!convId || !title) return
  try {
    await chatApi.updateConversationTitle(convId, title)
    await loadConversations()
  } catch (error) {
    console.error('重命名失败:', error)
  }
}

const cancelRename = () => {
  editingConvId.value = null
  editingTitle.value = ''
}

const confirmDelete = (convId) => {
  confirmDeleteId.value = convId
}

const executeDelete = async () => {
  const convId = confirmDeleteId.value
  confirmDeleteId.value = null
  if (!convId) return
  try {
    await chatApi.deleteConversation(convId)
    if (activeConversationId.value === convId) {
      activeConversationId.value = null
      messages.value = []
    }
    await loadConversations()
  } catch (error) {
    console.error('删除对话失败:', error)
  }
}

const toggleSidebar = () => {
  sidebarVisible.value = !sidebarVisible.value
}

const loadChatHistory = async () => {
  if (!currentServer.value) return
  await loadConversations()
  // 自动加载最近一个对话
  if (conversations.value.length > 0) {
    const mostRecent = conversations.value[0]
    await switchConversation(mostRecent.id)
  } else {
    messages.value = []
  }
}

watch(currentServer, async (newServer, oldServer) => {
  if (newServer && newServer.id !== oldServer?.id) {
    activeConversationId.value = null
    messages.value = []
    await loadChatHistory()
  }
})

onMounted(async () => {
  if (!serverStore.servers.length) {
    await serverStore.fetchServers()
  }
  if (!currentServer.value && serverStore.servers.length > 0) {
    serverStore.setCurrentServer(serverStore.servers[0])
  }

  if (currentServer.value) {
    await loadChatHistory()
  }

  // 检查是否有从模板页面"使用模板"跳转过来的待处理模板
  const pendingTemplate = localStorage.getItem('selectedTemplate')
  if (pendingTemplate) {
    localStorage.removeItem('selectedTemplate')
    try {
      const template = JSON.parse(pendingTemplate)
      // 等 nextTick 确保视图已渲染
      nextTick(() => applyTemplate(template))
    } catch (e) {
      console.error('解析模板失败:', e)
    }
  }

  try {
    const settingsResponse = await settingsApi.getSettings()
    const settings = settingsResponse.data
    if (!settings.api_key) {
      apiKeySet.value = false
    }
  } catch (error) {
    console.error('获取设置失败:', error)
    apiKeySet.value = false
  }
})

const sendMessage = async () => {
  if (!prompt.value.trim()) return
  if (!currentServer.value) {
    alert('请先选择服务器')
    return
  }

  if (currentServer.value.last_pwd) {
    serverPassword.value = currentServer.value.last_pwd
    await confirmPassword()
  } else {
    showPasswordModal.value = true
    serverPassword.value = ''
  }
}

const confirmPassword = async () => {
  if (!serverPassword.value.trim()) {
    alert('请输入服务器密码')
    return
  }

  // 多服务器模式：将密码缓存到所有已选服务器
  if (serverStore.isMultiMode) {
    serverStore.selectedServers.forEach(s => {
      serverStore.setServerPassword(s.id, serverPassword.value)
    })
  }

  showPasswordModal.value = false
  const userMessage = {
    role: 'user',
    content: prompt.value
  }
  messages.value.push(userMessage)
  scrollToBottom()

  const userPrompt = prompt.value
  prompt.value = ''
  loading.value = true

  try {
    const hostPayload = {
      id: currentServer.value.id,
      name: currentServer.value.name,
      host: currentServer.value.host,
      port: currentServer.value.port,
      username: currentServer.value.username,
      password: serverPassword.value,
      private_key: '',
      use_local: false
    }

    const hostsPayload = serverStore.isMultiMode
      ? serverStore.selectedServers.map(s => ({
          id: s.id, name: s.name, host: s.host, port: s.port,
          username: s.username,
          password: serverStore.serverPasswords[s.id] || serverPassword.value || '',
          private_key: '', use_local: false
        }))
      : null

    if (serverStore.isMultiMode) {
      initBatchTabs()
    }

    const response = await chatApi.sendMessage(userPrompt, selectedMode.value, hostPayload, activeConversationId.value, reactEnabled.value, hostsPayload)

    const taskId = response.data.task_id
    const status = response.data.status
    // 后端可能返回新的 conversation_id（首次发送时自动创建）
    if (response.data.conversation_id && !activeConversationId.value) {
      activeConversationId.value = response.data.conversation_id
    }
    // 刷新对话列表（新会话或 updated_at 变化）
    await loadConversations()

    if (status === 'pending_confirmation' || status === 'accepted') {
      await startSSE(taskId)
    } else if (status === 'chat_only') {
      const assistantMessage = {
        role: 'assistant',
        content: response.data.reply_message || '处理完成'
      }
      messages.value.push(assistantMessage)
    } else {
      await startSSE(taskId)
    }
  } catch (error) {
    console.error('发送消息失败:', error)
    let errorContent = '请求失败'
    if (error.response) {
      errorContent = `请求失败: ${error.response.data?.detail || error.response.data?.message || error.message}`
    } else if (error.request) {
      errorContent = '请求失败: 无法连接到服务器，请检查后端服务是否运行'
    } else {
      errorContent = `请求失败: ${error.message}`
    }
    const errorMessage = {
      role: 'assistant',
      content: errorContent
    }
    messages.value.push(errorMessage)
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

const startSSE = async (taskId) => {
  currentSSE.value = new EventSource(`/api/stream/${taskId}`)
  const assistantMessage = reactive({
    role: 'assistant',
    content: 'Shannon 正在处理中...',
    meta: { plan: null, events: [], thinking: null, currentTaskId: taskId, pendingConfirmation: false }
  })
  messages.value.push(assistantMessage)
  scrollToBottom()

  currentSSE.value.onmessage = (event) => {
    const payload = JSON.parse(event.data)

    if (payload.type === 'thinking') {
      assistantMessage.meta.thinking = payload.content
      assistantMessage.content = `### ${payload.stage === 'intent' ? '意图分析' : '计划生成'}中...\n\n**思考过程:**\n${payload.content}`
    } else if (payload.type === 'raw_content') {
      assistantMessage.meta.rawContent = payload.content
      if (!assistantMessage.meta.thinking) {
        assistantMessage.content = `### ${payload.stage === 'intent' ? '意图分析' : '计划生成'}中...\n\n\`\`\`\n${payload.content}\n\`\`\``
      }
    } else if (payload.type === 'plan') {
      assistantMessage.content = payload.reply_message || '已生成执行计划。'
      assistantMessage.meta.plan = payload
      if (assistantMessage.meta.thinking) {
        assistantMessage.content = `**分析过程:**\n${assistantMessage.meta.thinking}\n\n---\n\n${payload.reply_message || '已生成执行计划。'}`
      }
    } else if (payload.type === 'command_result') {
      terminalStore.addEvent(payload)
      if (payload.host_id) updateBatchTab(payload.host_id, payload.returncode === 0 ? 'success' : 'failed', null)
      let formattedOutput = `### 执行完成\n\`\`\`bash\n${payload.command}\n\`\`\``
      if (payload.stdout) {
        formattedOutput += `\n\n### 标准输出\n\`\`\`\n${payload.stdout}\n\`\`\``
      }
      if (payload.stderr) {
        formattedOutput += `\n\n### 错误输出\n\`\`\`\n${payload.stderr}\n\`\`\``
      }
      const resultMsg = reactive({
        role: 'assistant',
        content: payload.reply_message || formattedOutput,
        meta: { type: 'command_result', command: payload.command, returncode: payload.returncode, iteration: assistantMessage.meta.currentIteration || 1 }
      })
      messages.value.push(resultMsg)
    } else if (payload.type === 'command_start') {
      terminalStore.addEvent(payload)
      if (payload.host_id) updateBatchTab(payload.host_id, 'running', null)
      let cmdContent = `### 正在执行\n\`\`\`bash\n${payload.command}\n\`\`\``
      if (payload.reasoning) {
        cmdContent = `**思考:** ${payload.reasoning}\n\n${cmdContent}`
      }
      if (payload.purpose) {
        cmdContent += `\n\n**目的:** ${payload.purpose}`
      }
      const cmdMsg = reactive({
        role: 'assistant',
        content: cmdContent,
        meta: { type: 'command_start', command: payload.command, purpose: payload.purpose, reasoning: payload.reasoning, iteration: assistantMessage.meta.currentIteration || 1 }
      })
      messages.value.push(cmdMsg)
    } else if (payload.type === 'command_output') {
      // 实时流式输出：更新最后一条消息
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg && lastMsg.role === 'assistant' && lastMsg.meta.type === 'command_start') {
        const lines = (lastMsg.meta._streamLines || [])
        const line = payload.line.endsWith('\n') ? payload.line : payload.line + '\n'
        lines.push(line)
        if (lines.length > 20) lines.splice(0, lines.length - 20)
        lastMsg.meta._streamLines = lines
        lastMsg.content = `### 命令执行中\n\`\`\`bash\n${payload.command}\n\`\`\`\n\`\`\`\n${lines.join('')}\`\`\``
      }
    } else if (payload.type === 'self_heal_retry') {
      terminalStore.addEvent(payload)
      assistantMessage.meta.events.push(payload)
      assistantMessage.content = `### 正在重试\n\`\`\`bash\n${payload.new_command}\n\`\`\``
    } else if (payload.type === 'iteration_start') {
      assistantMessage.meta.currentIteration = payload.iteration
      assistantMessage.meta.maxIterations = payload.max_iterations
      assistantMessage.content = `### 第 ${payload.iteration}/${payload.max_iterations} 轮执行\n\n正在分析上一步结果...`
    } else if (payload.type === 'react_action') {
      let content = `**思考:** ${payload.reasoning || ''}`
      if (payload.command) {
        content += `\n\n**下一步:**\`\`\`bash\n${payload.command}\n\`\`\``
      }
      if (payload.purpose) {
        content += `\n\n**目的:** ${payload.purpose}`
      }
      assistantMessage.content = content
    } else if (payload.type === 'react_done') {
      const doneMsg = reactive({
        role: 'assistant',
        content: payload.message || '执行完成',
        meta: { _sse_done: true }
      })
      messages.value.push(doneMsg)
      currentSSE.value.close()
      loadConversations()
    } else if (payload.type === 'react_ask') {
      const askMsg = reactive({
        role: 'assistant',
        content: `**需要你的帮助:** ${payload.message}` + (payload.reasoning ? `\n\n**思考:** ${payload.reasoning}` : ''),
        meta: {}
      })
      messages.value.push(askMsg)
    } else if (payload.type === 'status' && payload.message === '正在执行命令...') {
      assistantMessage.content = '### 正在执行命令...\n\n请稍候，命令执行中...'
    } else if (payload.type === 'done') {
      let finalContent = payload.message || ''
      if (payload.stdout) {
        finalContent += `\n\n### 最终输出\n\`\`\`\n${payload.stdout}\n\`\`\``
      }
      if (payload.stderr) {
        finalContent += `\n\n### 错误信息\n\`\`\`\n${payload.stderr}\n\`\`\``
      }
      if (finalContent) {
        const doneMsg = reactive({
          role: 'assistant',
          content: finalContent,
          meta: { _sse_done: true }
        })
        messages.value.push(doneMsg)
      }
      currentSSE.value.close()
      loadConversations()
    } else if (payload.type === 'risk_hold') {
      assistantMessage.content = payload.reason || '请确认执行以下命令'
      assistantMessage.meta.plan = {
        risk_level: payload.risk_level,
        reasoning: payload.reason,
        commands_plan: payload.commands_plan || [],
        task_id: payload.task_id || taskId
      }
      assistantMessage.meta.pendingConfirmation = true
    } else if (payload.type === 'confirmation_accepted' || payload.type === 'confirmation_cancelled') {
      assistantMessage.meta.pendingConfirmation = false
      assistantMessage.meta.isExecuting = payload.type === 'confirmation_accepted'
    // ── 委托事件处理 ──
    } else if (payload.type === 'delegate_confirm_required') {
      // 预判器命中 或 LLM 建议委托 → 展示确认卡片，等待用户选择
      delegationState.visible = true
      delegationState.state = 'suggested'
      delegationState.agent = payload.agent || 'Claude Code'
      delegationState.reason = payload.reason || payload.message || ''
      delegationState.riskLevel = payload.risk_level || 'HIGH'
      delegationState.currentTaskId = payload.task_id || taskId
      delegationState.pendingConfirmTaskId = payload.task_id || taskId
      assistantMessage.content = ''
      assistantMessage.meta._delegationActive = true
      assistantMessage.meta._delegationState = 'suggested'
    } else if (payload.type === 'delegate_suggested') {
      // 兼容旧事件：仅作信息提示，不展示操作按钮
      delegationState.agent = payload.agent || 'Claude Code'
      delegationState.reason = payload.reason || payload.message || ''
    } else if (payload.type === 'delegate_started') {
      delegationState.state = 'running'
      delegationState.outputLines = []
      delegationState.waitingPermission = false
      delegationState.permissionPrompt = ''
      delegationState.permissionId = ''
      delegationState.visible = true
      assistantMessage.meta._delegationActive = true
      assistantMessage.meta._delegationState = 'running'
      assistantMessage.content = `### 委托执行中 - ${payload.agent || 'Claude Code'}\n\n正在远程服务器上执行...`
    } else if (payload.type === 'delegate_progress') {
      // 流式输出，追加到 outputLines
      delegationState.outputLines.push(payload.line || '')
      if (delegationState.outputLines.length > 200) {
        delegationState.outputLines = delegationState.outputLines.slice(-150)
      }
      // 聊天区直接累积 Claude Code 输出（后端已 strip ANSI），markdown 渲染
      if (!assistantMessage.meta._ccOutput) assistantMessage.meta._ccOutput = []
      assistantMessage.meta._ccOutput.push(payload.line || '')
      if (assistantMessage.meta._ccOutput.length > 500) {
        assistantMessage.meta._ccOutput = assistantMessage.meta._ccOutput.slice(-400)
      }
      assistantMessage.content = `### 委托执行中 - ${delegationState.agent}\n\n${assistantMessage.meta._ccOutput.join('\n')}`
    } else if (payload.type === 'delegate_permission_required') {
      delegationState.waitingPermission = true
      delegationState.permissionPrompt = payload.prompt_text || ''
      delegationState.permissionId = payload.permission_id || ''
      delegationState.autoApproved = payload.auto_approved || false
    } else if (payload.type === 'delegate_completed') {
      delegationState.waitingPermission = false
      delegationState.state = 'completed'
      delegationState.executionTime = payload.execution_time_sec || 0
      assistantMessage.meta._delegationState = 'completed'
    } else if (payload.type === 'delegate_review') {
      delegationState.goalAchieved = payload.goal_achieved || '⚠️ 部分达成'
      delegationState.goalReasoning = payload.goal_reasoning || ''
      delegationState.filesChanged = payload.files_changed || []
      delegationState.filesChangedCount = (payload.files_changed || []).length
      delegationState.riskWarnings = payload.risk_warnings || []
      delegationState.outputSummary = payload.output_summary || ''
      delegationState.stderr = payload.stderr || ''
      delegationState.exitCode = payload.exit_code
      let reviewContent = `### 委托执行完成\n\n**目标达成:** ${delegationState.goalAchieved}\n**耗时:** ${delegationState.executionTime}秒\n**退出码:** ${payload.exit_code ?? '未知'}\n**变更文件:** ${delegationState.filesChangedCount}个`
      if (delegationState.goalReasoning) {
        reviewContent += `\n\n**判断理由:** ${delegationState.goalReasoning}`
      }
      if (delegationState.riskWarnings.length > 0) {
        reviewContent += `\n\n⚠️ **风险警告:**\n${delegationState.riskWarnings.map(w => `- ${w}`).join('\n')}`
      }
      if (delegationState.stderr) {
        reviewContent += `\n\n### 错误输出\n\`\`\`\n${delegationState.stderr}\n\`\`\``
      }
      if (delegationState.outputSummary) {
        reviewContent += `\n\n### 执行摘要\n${delegationState.outputSummary}`
      }
      assistantMessage.content = reviewContent
      assistantMessage.meta._delegationDone = true
    } else if (payload.type === 'delegate_cancelled') {
      delegationState.state = 'cancelled'
      delegationState.message = payload.message || '委托已被取消'
      assistantMessage.content = `### 委托已取消\n\n${delegationState.message}`
      assistantMessage.meta._delegationDone = true
    } else if (payload.type === 'delegate_timeout') {
      delegationState.state = 'timeout'
      delegationState.message = payload.message || '委托执行超时'
      assistantMessage.content = `### 委托超时\n\n${delegationState.message}`
      assistantMessage.meta._delegationDone = true
    } else if (payload.type === 'delegate_fallback') {
      delegationState.state = 'fallback'
      delegationState.message = payload.message || '已退回 Agent 模式'
      assistantMessage.content = `### ${delegationState.message}`
      assistantMessage.meta._delegationDone = true
    } else if (payload.type === 'delegate_install_required') {
      delegationInstallModal.visible = true
      delegationInstallModal.hostName = payload.host_name || '目标服务器'
      delegationInstallModal.taskId = taskId
      assistantMessage.content = `### 需要安装 Claude Code CLI\n\n${payload.message}`
      assistantMessage.meta._delegationPendingInstall = true
    } else if (payload.type === 'delegation_conflict') {
      delegationConflictModal.visible = true
      delegationConflictModal.existingTaskId = payload.existing_task_id || ''
      delegationConflictModal.newTaskId = taskId
      assistantMessage.meta._delegationConflict = true
    } else if (payload.type === 'error') {
      assistantMessage.content = `错误: ${payload.message || '未知错误'}`
      assistantMessage.meta.pendingConfirmation = false
      assistantMessage.meta._sse_done = true
      currentSSE.value.close()
    } else {
      assistantMessage.meta.events.push(payload)
    }

    scrollToBottom()
  }

  currentSSE.value.onerror = (error) => {
    console.error('SSE连接错误:', error)
    if (assistantMessage.meta._sse_done) return // 正常完成，忽略 onerror
    assistantMessage.content = '连接已断开，请刷新页面重试'
    assistantMessage.meta.pendingConfirmation = false
    currentSSE.value.close()
    scrollToBottom()
  }
}

const confirmExecution = async (taskId, forceExecute) => {
  const msg = messages.value.find(m => m.meta && m.meta.plan && m.meta.plan.task_id === taskId)
  if (msg) {
    msg.meta.pendingConfirmation = false
  }

  try {
    await chatApi.confirmExecution(taskId, forceExecute, 'Shannon User')
  } catch (error) {
    console.error('确认执行失败:', error)
    if (msg) {
      msg.meta.pendingConfirmation = true
    }
    const errorMessage = {
      role: 'assistant',
      content: `确认执行失败：${error.message}`
    }
    messages.value.push(errorMessage)
    scrollToBottom()
  }
}

const cancelExecution = async (taskId) => {
  const msg = messages.value.find(m => m.meta && m.meta.plan && m.meta.plan.task_id === taskId)
  if (msg) {
    msg.meta.pendingConfirmation = false
  }

  try {
    await chatApi.confirmExecution(taskId, false, 'Shannon User')
  } catch (error) {
    console.error('取消执行失败:', error)
  }
}

// ── 委托操作方法 ──
const confirmDelegation = async (taskId) => {
  try {
    await chatApi.confirmExecution(taskId, true, 'Shannon User')
    delegationState.state = 'running'
  } catch (error) {
    console.error('确认委托失败:', error)
    delegationState.state = 'fallback'
  }
}

const rejectDelegation = async (taskId) => {
  try {
    await chatApi.confirmExecution(taskId, false, 'Shannon User')
    delegationState.state = 'fallback'
  } catch (error) {
    console.error('拒绝委托失败:', error)
  }
}

const cancelDelegation = async (taskId) => {
  try {
    await delegateApi.cancel(taskId)
    delegationState.state = 'cancelled'
  } catch (error) {
    console.error('取消委托失败:', error)
  }
}

const respondPermission = async (permissionId, approved) => {
  const taskId = delegationState.currentTaskId
  if (!taskId) return
  try {
    await delegateApi.respondPermission(taskId, permissionId, approved)
    delegationState.waitingPermission = false
    delegationState.permissionPrompt = ''
    delegationState.permissionId = ''
  } catch (error) {
    console.error('响应权限请求失败:', error)
  }
}

const confirmInstall = async () => {
  if (!delegationInstallModal.taskId) return
  try {
    await delegateApi.confirmInstall(delegationInstallModal.taskId, true)
    delegationInstallModal.visible = false
  } catch (error) {
    console.error('确认安装失败:', error)
  }
}

const rejectInstall = async () => {
  if (!delegationInstallModal.taskId) return
  try {
    await delegateApi.confirmInstall(delegationInstallModal.taskId, false)
    delegationInstallModal.visible = false
  } catch (error) {
    console.error('拒绝安装失败:', error)
  }
}

const resolveConflictCancelAndNew = async () => {
  try {
    await delegateApi.resolveConflict(delegationConflictModal.newTaskId, 'cancel_and_new')
    delegationConflictModal.visible = false
    // SSE 连接保持存活，后端会用同一 task_id 重新生成消息
    // 前端已连接在该 task_id 的 SSE 流上，会自动收到新事件
  } catch (error) {
    console.error('解决冲突失败:', error)
  }
}

const resolveConflictQueue = async () => {
  try {
    await delegateApi.resolveConflict(delegationConflictModal.newTaskId, 'queue')
    delegationConflictModal.visible = false
    // SSE 连接保持存活，等待当前委托完成后自动处理排队消息
  } catch (error) {
    console.error('排队失败:', error)
  }
}

const applyTemplate = async (template) => {
  showTemplates.value = false
  if (!currentServer.value) {
    alert('请先选择服务器')
    return
  }
  // 创建新对话并切换到新对话
  try {
    const convRes = await chatApi.createConversation(currentServer.value.id, template.name)
    const convId = convRes.data.id
    await switchConversation(convId)
    // 填充提示词后调用 sendMessage
    prompt.value = template.prompt
    await sendMessage()
  } catch (error) {
    console.error('应用模板失败:', error)
    alert('创建对话失败，请重试')
  }
}

const resetCustomTemplate = () => {
  customTemplate.name = ''
  customTemplate.category = '基础管理'
  customTemplate.prompt = ''
  customTemplate.description = ''
  aiError.value = ''
}

const saveCustomTemplate = () => {
  if (!customTemplate.name.trim() || !customTemplate.prompt.trim()) return
  templateStore.addTemplate({
    name: customTemplate.name.trim(),
    category: customTemplate.category,
    prompt: customTemplate.prompt.trim(),
    description: customTemplate.description.trim() || customTemplate.name.trim()
  })
  resetCustomTemplate()
  showCustomTemplateForm.value = false
}

const deleteUserTemplate = (templateId) => {
  templateStore.deleteTemplate(templateId)
}

const generateWithAI = async () => {
  if (!customTemplate.description.trim()) {
    aiError.value = '请先填写描述'
    return
  }
  aiGenerating.value = true
  aiError.value = ''
  try {
    const response = await settingsApi.generateTemplate(customTemplate.description.trim())
    const data = response.data
    if (data.ok && data.template) {
      customTemplate.name = data.template.name || ''
      customTemplate.category = data.template.category || '基础管理'
      customTemplate.prompt = data.template.prompt || ''
      customTemplate.description = data.template.description || customTemplate.description
    } else {
      aiError.value = data.message || '生成失败'
    }
  } catch (error) {
    aiError.value = error.response?.data?.detail || error.message || '请求失败'
  } finally {
    aiGenerating.value = false
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.dashboard-layout {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 1260px;
  margin: 0 auto;
}

.dashboard-container {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.chat-main-area {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.conversation-sidebar {
  width: 280px;
  flex-shrink: 0;
  background: var(--bg-surface);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 180px);
  position: sticky;
  top: 20px;
}

.sidebar-header {
  padding: 14px 16px;
  border-bottom: 1px solid var(--bg-border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.sidebar-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.sidebar-empty {
  padding: 32px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--text-tertiary);
}

.sidebar-empty-hint {
  font-size: 12px;
  margin-top: 6px;
}

.sidebar-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.sidebar-conv-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--transition-fast);
  margin-bottom: 2px;
}

.sidebar-conv-item:hover {
  background: var(--bg-hover);
}

.sidebar-conv-item.active {
  background: var(--primary-light);
}

.conv-item-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.conv-icon {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.conv-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.conv-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-meta {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.conv-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.sidebar-conv-item:hover .conv-actions {
  opacity: 1;
}

.conv-action-btn {
  width: 26px;
  height: 26px;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.conv-action-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.conv-action-delete:hover {
  background: var(--danger-light);
  color: var(--danger);
}

.conv-rename-form {
  width: 100%;
}

.conv-rename-input {
  width: 100%;
  padding: 4px 8px;
  font-size: 13px;
  border: 1px solid var(--primary);
  border-radius: var(--radius-sm);
  outline: none;
  background: var(--bg-surface);
  color: var(--text-primary);
}

.delete-confirm {
  padding: 12px 16px;
  border-top: 1px solid var(--bg-border-light);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.delete-confirm p {
  font-size: 13px;
  color: var(--text-primary);
}

.delete-confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}

.sidebar-slide-enter-active,
.sidebar-slide-leave-active {
  transition: all 0.25s ease;
}

.sidebar-slide-enter-from,
.sidebar-slide-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.server-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.server-label {
  font-size: 13px;
  color: var(--text-tertiary);
}

.server-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.alert {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 18px;
  border-radius: var(--radius-lg);
  border: 1px solid;
}

.alert-danger {
  background: var(--danger-light);
  border-color: #FECACA;
}

.alert-icon {
  color: var(--danger);
  flex-shrink: 0;
  margin-top: 1px;
}

.alert-content {
  flex: 1;
}

.alert-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--danger);
  margin-bottom: 4px;
}

.alert-desc {
  font-size: 13px;
  color: #991B1B;
  margin-bottom: 8px;
}

.chat-card {
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--bg-border);
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--bg-border-light);
}

.chat-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.chat-messages {
  padding: 16px 20px;
  height: 480px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-row {
  display: flex;
}

.message-user {
  justify-content: flex-end;
}

.message-assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 80%;
  padding: 14px 16px;
  border-radius: var(--radius-lg);
}

.bubble-user {
  background: var(--primary);
  color: var(--text-inverse);
  border-bottom-right-radius: 4px;
}

.bubble-assistant {
  background: var(--bg-page);
  border: 1px solid var(--bg-border);
  border-bottom-left-radius: 4px;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-user {
  background: rgba(255, 255, 255, 0.25);
  color: white;
}

.avatar-assistant {
  background: var(--primary);
  color: white;
}

.message-sender {
  font-size: 12px;
  font-weight: 500;
}

.bubble-user .message-sender {
  color: rgba(255, 255, 255, 0.85);
}

.bubble-assistant .message-sender {
  color: var(--text-secondary);
}

.message-content {
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.bubble-user .message-content {
  color: rgba(255, 255, 255, 0.95);
}

.bubble-assistant .message-content {
  color: var(--text-primary);
}

.plan-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.bubble-user .plan-section {
  border-top-color: rgba(255, 255, 255, 0.2);
}

.plan-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.plan-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.risk-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 1px 8px;
  border-radius: 9999px;
}

.risk-high {
  background: var(--danger-light);
  color: var(--danger);
}

.risk-low {
  background: var(--success-light);
  color: var(--success);
}

.plan-reasoning {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.commands-section {
  margin-bottom: 0;
}

.commands-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.commands-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.command-item {
  background: var(--bg-surface);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  padding: 8px 12px;
}

.command-purpose {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-bottom: 4px;
}

.command-code {
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  color: var(--success);
  background: var(--bg-page);
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  margin: 0;
  overflow-x: auto;
}

/* ReAct 步骤卡片 */
.react-step {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--bg-border);
}

.react-action-step {
  background: var(--bg-page);
  border-left: 3px solid var(--primary);
}

.react-result-step {
  background: var(--bg-page);
  border-left: 3px solid var(--success);
}

.step-header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 6px;
}

.step-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 9999px;
  white-space: nowrap;
  flex-shrink: 0;
}

.step-run { background: var(--info-light); color: var(--info); }
.step-ok { background: var(--success-light); color: var(--success); }
.step-fail { background: var(--danger-light); color: var(--danger); }

.step-reasoning {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.step-returncode {
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: 'SF Mono', monospace;
}

.step-command {
  margin-bottom: 4px;
}

.step-purpose {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 2px;
  display: block;
}

.step-message {
  font-size: 12px;
  color: var(--text-primary);
  line-height: 1.5;
}

.step-output {
  margin-top: 6px;
}

.step-output-label {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-tertiary);
  margin-bottom: 2px;
}

.step-output-label-error {
  color: var(--danger);
}

.step-output-text {
  font-size: 11px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  background: var(--bg-surface);
  border: 1px solid var(--bg-border-light);
  border-radius: var(--radius-sm);
  padding: 6px 8px;
  margin: 0;
  max-height: 120px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.4;
}

.step-output-text-error {
  color: var(--danger);
  border-color: var(--danger-light);
}

.events-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.events-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.events-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 160px;
  overflow-y: auto;
}

.event-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.event-icon {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}

.event-command_start { background: var(--info-light); color: var(--info); }
.event-command_result { background: var(--success-light); color: var(--success); }
.event-self_heal_retry { background: var(--warning-light); color: var(--warning); }
.event-error { background: var(--danger-light); color: var(--danger); }

.event-content {
  flex: 1;
  min-width: 0;
}

.event-message {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
}

.event-output {
  font-size: 11px;
  color: var(--text-tertiary);
  background: var(--bg-page);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  margin-top: 4px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.confirmation-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.confirmation-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.btn-danger {
  background: var(--danger);
  color: white;
}

.btn-danger:hover {
  background: #DC2626;
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 0;
}

.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-tertiary);
  animation: typingBounce 1.4s ease-in-out infinite;
}

.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingBounce {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}

.chat-input-area {
  padding: 16px 20px;
  border-top: 1px solid var(--bg-border-light);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mode-selector {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mode-label {
  font-size: 13px;
  color: var(--text-tertiary);
}

.mode-buttons {
  display: flex;
  gap: 4px;
}

.mode-btn {
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 9999px;
  border: 1px solid var(--bg-border);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.mode-btn:hover {
  background: var(--bg-hover);
}

.mode-btn.active {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}

.chat-textarea {
  width: 100%;
  min-height: 80px;
  padding: 10px 14px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-input);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  resize: vertical;
  outline: none;
  font-family: inherit;
  line-height: 1.6;
  transition: all var(--transition-base);
}

.chat-textarea:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(79, 110, 247, 0.12);
  background: var(--bg-surface);
}

.chat-textarea::placeholder {
  color: var(--text-tertiary);
}

.chat-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chat-actions-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.voice-btn-active {
  background: var(--danger-light) !important;
  border-color: var(--danger) !important;
  color: var(--danger) !important;
}

.voice-pulse {
  animation: voicePulse 1.2s ease-in-out infinite;
}

@keyframes voicePulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.voice-active {
  border-color: var(--danger) !important;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15) !important;
}

.voice-interim {
  padding: 6px 14px;
  font-size: 12px;
  color: var(--text-tertiary);
  font-style: italic;
  background: var(--bg-hover);
  border-radius: var(--radius-sm);
  margin-top: -4px;
}

.voice-error {
  padding: 6px 14px;
  font-size: 12px;
  color: var(--danger);
  background: var(--danger-light);
  border-radius: var(--radius-sm);
  margin-top: -4px;
}

.templates-card {
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--bg-border);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.templates-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.templates-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.templates-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

/* 自定义模板表单 */
.custom-template-form {
  background: var(--bg-page);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 16px;
}

.form-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.form-group {
  margin-bottom: 10px;
}

.form-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.form-textarea {
  resize: vertical;
  font-family: inherit;
  line-height: 1.5;
}

.form-actions {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-top: 4px;
}

.form-actions-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.form-actions-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ai-error {
  font-size: 12px;
  color: var(--danger);
}

.template-delete-btn {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: none;
  background: var(--bg-hover);
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: all var(--transition-fast);
}

.template-card {
  position: relative;
}

.close-btn {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.close-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}

.template-card {
  background: var(--bg-page);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  padding: 14px;
  cursor: pointer;
  transition: all var(--transition-base);
}

.template-card:hover {
  border-color: var(--primary);
  box-shadow: var(--shadow-md);
}

.template-card:hover .template-delete-btn {
  opacity: 1;
}

.template-delete-btn:hover {
  background: var(--danger-light);
  color: var(--danger);
}

.template-category {
  font-size: 11px;
  font-weight: 500;
  color: var(--primary);
  margin-bottom: 4px;
}

.template-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.template-desc {
  font-size: 12px;
  color: var(--text-tertiary);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal {
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
  padding: 24px;
  width: 100%;
  max-width: 400px;
  box-shadow: var(--shadow-xl);
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.modal-body {
  margin-bottom: 16px;
}

.modal-server {
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.modal-address {
  font-size: 13px;
  color: var(--text-tertiary);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.modal-input-group {
  margin-bottom: 16px;
}

.modal-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.modal-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.checkbox {
  width: 16px;
  height: 16px;
  accent-color: var(--primary);
}

.checkbox-label {
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
