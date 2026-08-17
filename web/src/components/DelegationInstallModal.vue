<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3>&#128679; 未检测到 Claude Code CLI</h3>
      </div>
      <div class="modal-body">
        <p>目标服务器 <strong>{{ hostName }}</strong> 上未安装 Claude Code CLI。</p>
        <p>是否自动安装？（将同时安装 Node.js 20.x 如需要）</p>
      </div>
      <div class="modal-footer">
        <button @click="$emit('install')" class="btn btn-primary">&#128640; 安装</button>
        <button @click="$emit('reject')" class="btn btn-outline">不使用，正常处理</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: false },
  hostName: { type: String, default: '' },
})
defineEmits(['install', 'reject', 'close'])
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal-content {
  background: #fff; border-radius: 12px; padding: 24px;
  max-width: 420px; width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
.modal-header h3 { margin: 0; font-size: 16px; }
.modal-body { margin: 16px 0; font-size: 14px; color: #374151; line-height: 1.6; }
.modal-footer { display: flex; gap: 8px; justify-content: flex-end; }
.btn { padding: 8px 20px; border-radius: 6px; border: none; font-size: 13px; cursor: pointer; font-weight: 500; }
.btn-primary { background: #4f46e5; color: #fff; }
.btn-primary:hover { background: #4338ca; }
.btn-outline { background: #fff; color: #374151; border: 1px solid #d1d5db; }
.btn-outline:hover { background: #f9fafb; }
</style>
