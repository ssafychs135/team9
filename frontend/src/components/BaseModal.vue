<template>
  <Transition name="modal-fade">
    <div v-if="store.isVisible" class="modal-backdrop" @click.self="handleOverlayClick">
      <div class="modal-container" role="dialog" aria-modal="true">
        <header class="modal-header">
          <h3>{{ store.title }}</h3>
        </header>
        
        <div class="modal-body">
          <p>{{ store.message }}</p>
        </div>
        
        <footer class="modal-footer">
          <button 
            v-if="store.type === 'confirm'" 
            class="btn-text cancel-btn" 
            @click="cancel"
          >
            취소
          </button>
          <button 
            class="btn-primary confirm-btn" 
            @click="confirm"
            ref="confirmBtn"
          >
            확인
          </button>
        </footer>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { useModalStore } from '@/stores/modalStore'
import { onMounted, onUnmounted, ref, nextTick, watch } from 'vue'

const store = useModalStore()
const confirmBtn = ref(null)

function confirm() {
  store.close(true)
}

function cancel() {
  store.close(false)
}

function handleOverlayClick() {
  // 배경 클릭 시 닫히게 하려면 아래 주석 해제 (alert은 보통 강제성이 있어 막아두기도 함)
  // if (store.type === 'alert') store.close(true)
}

// 모달이 열릴 때 포커스 이동 (접근성)
watch(() => store.isVisible, async (newVal) => {
  if (newVal) {
    await nextTick()
    confirmBtn.value?.focus()
  }
})

function onKeydown(e) {
  if (!store.isVisible) return
  if (e.key === 'Escape') {
    cancel()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 10000;
  backdrop-filter: blur(4px);
}

.modal-container {
  background: var(--c-card-background);
  width: 90%;
  max-width: 320px;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  gap: 16px;
  transform: scale(1);
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.modal-header h3 {
  margin: 0;
  font-size: 19px;
  font-weight: 600;
  text-align: center;
  color: var(--c-text-primary);
}

.modal-body {
  text-align: center;
}

.modal-body p {
  margin: 0;
  font-size: 15px;
  color: var(--c-text-primary);
  line-height: 1.5;
  white-space: pre-wrap; /* 줄바꿈 지원 */
}

.modal-footer {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.modal-footer button {
  flex: 1;
  padding: 12px 0;
  font-size: 16px;
  border-radius: 12px;
}

.cancel-btn {
  color: var(--c-text-secondary);
}

.cancel-btn:hover {
  background-color: rgba(0,0,0,0.05);
}

/* 트랜지션 효과 */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-from .modal-container,
.modal-fade-leave-to .modal-container {
  transform: scale(0.9);
  opacity: 0;
}
</style>
