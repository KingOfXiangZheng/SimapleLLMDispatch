<template>
  <Teleport to="body">
    <Transition name="toast">
      <div 
        v-if="toast.show" 
        class="toast" 
        :class="toast.type === 'error' ? 'toast-error' : 'toast-success'"
      >
        {{ toast.msg }}
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { reactive, defineExpose } from 'vue'

const toast = reactive({
  show: false,
  msg: '',
  type: 'success'
})

function showToast(msg, type = 'success') {
  toast.msg = msg
  toast.type = type
  toast.show = true
  setTimeout(() => {
    toast.show = false
  }, 2500)
}

defineExpose({ showToast })
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.25s ease-out;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(12px);
}
</style>
