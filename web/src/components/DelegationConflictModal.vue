<template>
  <div v-if="visible" class="modal-overlay">
    <div class="modal-content">
      <div class="modal-header">
        <h3>&#128260; 委托冲突</h3>
      </div>
      <div class="modal-body">
        <p>当前有一个委托任务正在执行中。</p>
        <p>您希望如何处理新消息？</p>
      </div>
      <div class="modal-footer">
        <button @click="$emit('cancel-and-new')" class="btn btn-danger">
          &#10060; 取消当前委托，执行新任务
        </button>
        <button @click="$emit('queue')" class="btn btn-outline">
          &#128337; 排队等待
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: false },
})
defineEmits(['cancel-and-new', 'queue'])
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal-content {
  background: #fff; border-radius: 12px; padding: 24px;
  max-width: 440px; width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
.modal-header h3 { margin: 0; font-size: 16px; }
.modal-body { margin: 16px 0; font-size: 14px; color: #374151; line-height: 1.6; }
.modal-footer { display: flex; flex-direction: column; gap: 8px; }
.btn { padding: 10px 20px; border-radius: 6px; border: none; font-size: 13px; cursor: pointer; font-weight: 500; width: 100%; }
.btn-danger { background: #ef4444; color: #fff; }
.btn-danger:hover { background: #dc2626; }
.btn-outline { background: #fff; color: #374151; border: 1px solid #d1d5db; }
.btn-outline:hover { background: #f9fafb; }
</style>
