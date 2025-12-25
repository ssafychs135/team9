import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useModalStore = defineStore('modal', () => {
  const isVisible = ref(false)
  const type = ref('alert') // 'alert' or 'confirm'
  const title = ref('')
  const message = ref('')
  const resolvePromise = ref(null)

  function show(options) {
    title.value = options.title || '알림'
    message.value = options.message || ''
    type.value = options.type || 'alert'
    isVisible.value = true

    return new Promise((resolve) => {
      resolvePromise.value = resolve
    })
  }

  function confirm(msg, ttl = '확인') {
    return show({ type: 'confirm', message: msg, title: ttl })
  }

  function alert(msg, ttl = '알림') {
    return show({ type: 'alert', message: msg, title: ttl })
  }

  function close(result) {
    isVisible.value = false
    if (resolvePromise.value) {
      resolvePromise.value(result)
      resolvePromise.value = null
    }
  }

  return { isVisible, type, title, message, show, confirm, alert, close }
})
