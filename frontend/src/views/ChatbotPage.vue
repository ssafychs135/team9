<template>
  <div class="chatbot-page">
    <!-- 멀티턴: 새 대화 버튼 (메시지가 있을 때만) -->
    <button v-if="messages.length > 0" class="new-conversation-btn" @click="newConversation"
      :disabled="isStreaming" title="새 대화 시작 (대화 기록 초기화)">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 5V19M5 12H19" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <span>새 대화</span>
    </button>

    <!-- 메인 채팅 영역 -->
    <div class="chat-content" ref="chatContentRef">
      <!-- 1. 웰컴 스크린 (메시지가 없을 때) -->
      <div v-if="messages.length === 0" class="welcome-screen">
        <h1 class="greeting">
          <span class="gradient-text">안녕하세요, {{ authStore.username }}님</span><br />
          <span class="sub-text">무엇을 도와드릴까요?</span>
        </h1>

        <div class="suggestion-grid">
          <button v-for="(chip, index) in suggestions" :key="index" class="suggestion-card"
            :disabled="isStreaming" @click="sendMessage(chip)">
            <p>{{ chip }}</p>
            <div class="icon-box">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 20V10M12 10L16 14M12 10L8 14" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </div>
          </button>
        </div>
      </div>

      <!-- 2. 대화 목록 -->
      <div v-else class="message-list">
        <div v-for="(msg, idx) in messages" :key="idx" :class="['message-row', msg.role]">

          <!-- Bot 아이콘 (ChatBot Sparkle) -->
          <div v-if="msg.role === 'bot'" class="bot-avatar">
            <img src="https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg"
              alt="ChatBot" />
          </div>

          <!-- 메시지 본문 -->
          <div class="message-bubble">
            <!-- role이 bot일 때만 markdown-body 클래스를 적용하여 마크다운 스타일을 입힙니다. -->
            <div 
              :class="['text-content', { 'markdown-body': msg.role === 'bot' }]" 
              v-html="msg.text"
            ></div>
          </div>
        </div>

        <!-- 로딩 인디케이터 -->
        <div v-if="isLoading" class="message-row bot">
          <div class="bot-avatar loading">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="11" width="18" height="10" rx="2"></rect>
              <circle cx="12" cy="5" r="2"></circle>
              <path d="M12 7v4"></path>
              <line x1="8" y1="16" x2="8" y2="16"></line>
              <line x1="16" y1="16" x2="16" y2="16"></line>
            </svg>
          </div>
          <div class="message-bubble">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. 하단 플로팅 입력창 -->
    <div class="input-container">
      <div class="input-wrapper">
        <button class="btn-icon add-file">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 5V19M5 12H19" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>

        <input v-model="userInput" @keyup.enter="handleSend" type="text"
          :placeholder="isStreaming ? '답변을 생성하는 중입니다…' : '질문을 입력하세요'"
          :disabled="isStreaming" class="chat-input" />

        <button class="btn-icon send-msg"
          :class="{ active: userInput.length > 0 && !isStreaming }"
          :disabled="isStreaming" @click="handleSend">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 2L11 13M22 2L15 22L11 13M11 13L2 9L22 2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
      </div>
      <p class="disclaimer">ChatBot은 부정확한 정보를 표시할 수 있습니다. 답변을 다시 확인하세요.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue';
import { marked } from 'marked';
import { useAuthStore } from '@/stores/authStore';

const authStore = useAuthStore();

const API_BASE = 'http://localhost:8000';

const userInput = ref('');
const isLoading = ref(false);          // SSE 첫 chunk 도착 전까지 typing-dot 표시
const isStreaming = ref(false);        // 스트림 진행 중 입력 비활성화
const chatContentRef = ref(null);

const suggestions = [
  "아이폰 15 프로 vs 맥스 비교해줘",
  "맥북 에어 M3 개발용으로 어때?",
  "애플워치 9 배터리 성능 요약해줘",
  "아이패드 에어 6세대 출시일 예측"
];

const messages = ref([]);

function scrollToBottom() {
  nextTick(() => {
    if (chatContentRef.value) {
      chatContentRef.value.scrollTop = chatContentRef.value.scrollHeight;
    }
  });
}

watch(messages, () => scrollToBottom(), { deep: true });
watch(isLoading, (v) => { if (v) scrollToBottom(); });

/**
 * SSE 스트리밍 + 멀티턴.
 * - credentials: 'include' 로 Django session cookie 동반 전송 (멀티턴의 전제).
 * - 매 SSE chunk 도착 시 누적 raw markdown 을 marked.parse 로 점진 렌더.
 * - 'data: [DONE]' 수신 시 종료.
 */
async function sendMessage(text) {
  messages.value.push({ role: 'user', text });
  // bot 슬롯 미리 push 해두고 점진 update (raw=markdown source, text=rendered HTML)
  const botIndex = messages.value.push({ role: 'bot', text: '', raw: '' }) - 1;
  isLoading.value = true;
  isStreaming.value = true;

  try {
    const res = await fetch(`${API_BASE}/ai/chatbot/stream/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ query: text }),
    });
    if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE event 는 빈 줄(\n\n) 로 구분
      let sepIdx;
      while ((sepIdx = buffer.indexOf('\n\n')) !== -1) {
        const raw = buffer.slice(0, sepIdx);
        buffer = buffer.slice(sepIdx + 2);
        if (!raw.startsWith('data: ')) continue;
        const payload = raw.slice(6);
        if (payload === '[DONE]') {
          isStreaming.value = false;
          return;
        }
        try {
          const obj = JSON.parse(payload);
          if (obj.chunk) {
            // 첫 chunk 도착 → typing-dot 사라지고 텍스트 시작
            if (isLoading.value) isLoading.value = false;
            messages.value[botIndex].raw += obj.chunk;
            messages.value[botIndex].text = marked.parse(messages.value[botIndex].raw);
          } else if (obj.error) {
            messages.value[botIndex].text = `오류가 발생했어요: ${obj.error}`;
            isStreaming.value = false;
            return;
          }
        } catch (e) {
          console.warn('SSE parse error:', payload, e);
        }
      }
    }
  } catch (e) {
    console.error('Stream error:', e);
    messages.value[botIndex].text = '죄송합니다. 답변을 가져오는 중 오류가 발생했습니다.';
  } finally {
    isLoading.value = false;
    isStreaming.value = false;
  }
}

function handleSend() {
  if (!userInput.value.trim() || isStreaming.value) return;
  const text = userInput.value;
  userInput.value = '';
  sendMessage(text);
}

/** 멀티턴 세션 초기화 — 새 대화 시작. */
async function newConversation() {
  if (isStreaming.value) return;
  try {
    await fetch(`${API_BASE}/ai/chatbot/reset/`, {
      method: 'POST',
      credentials: 'include',
    });
  } catch (e) {
    console.warn('Reset failed:', e);
  }
  messages.value = [];
}
</script>

<style scoped>
/* 전체 페이지 레이아웃
 * App.vue 의 <main> 이 명시 height 가 없어 height: 100% chain 이 깨짐. 따라서
 * viewport 에 직접 anchor (fixed) — global-nav(48px) 아래부터 viewport bottom 까지.
 * 다른 페이지 layout 에는 영향 없음. input-container 의 absolute 도 그대로 동작
 * (fixed 는 positioned ancestor 로 인정됨). */
.chatbot-page {
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 48px;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--c-background);
  overflow: hidden;
  width: 100%;
}

/* 멀티턴: 새 대화 버튼 (우상단 floating) */
.new-conversation-btn {
  position: absolute;
  top: 16px;
  right: 20px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--c-background-secondary);
  color: var(--c-text-primary);
  border: 1px solid transparent;
  border-radius: 999px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.new-conversation-btn:hover:not(:disabled) {
  background: var(--c-input-border);
  border-color: var(--c-accent);
}
.new-conversation-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 입력 비활성화 상태 */
.chat-input:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.btn-icon:disabled,
.suggestion-card:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.chat-content {
  flex: 1;
  overflow-y: auto;
  /* 하단 입력창(약 100px) 위로 넉넉한 여백(60px 이상)을 추가합니다. */
  padding: 40px 20px 160px;
  display: flex;
  flex-direction: column;
  align-items: center;
  
  /* 스크롤바를 숨기는 설정입니다. */
  -ms-overflow-style: none; /* 인터넷 익스플로러 및 엣지 */
  scrollbar-width: none;    /* 파이어폭스 */
}

/* 크롬, 사파리, 오페라에서 스크롤바를 숨깁니다. */
.chat-content::-webkit-scrollbar {
  display: none;
}

/* 1. 웰컴 스크린 */
.welcome-screen {
  width: 100%;
  max-width: 800px;
  margin-top: 60px;
}

.greeting {
  font-size: 56px;
  line-height: 1.2;
  margin-bottom: 60px;
  font-weight: 500;
  color: #c4c7c5;
  /* Default muted color */
}

.gradient-text {
  background: linear-gradient(74deg, #4285f4 0%, #9b72cb 19%, #d96570 40%, #131314 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
}

@media (prefers-color-scheme: dark) {
  .gradient-text {
    background: linear-gradient(74deg, #4285f4 0%, #9b72cb 19%, #d96570 40%, #ffffff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
}

.sub-text {
  color: var(--c-text-secondary);
  opacity: 0.5;
}

.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.suggestion-card {
  text-align: left;
  background: var(--c-background-secondary);
  border: none;
  border-radius: 12px;
  padding: 20px;
  height: 200px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  cursor: pointer;
  transition: background 0.2s;
  color: var(--c-text-primary);
  font-size: 16px;
}

.suggestion-card:hover {
  background: var(--c-input-border);
}

.icon-box {
  align-self: flex-end;
  background: var(--c-background);
  border-radius: 50%;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 2. 메시지 목록 */
.message-list {
  width: 100%;
  max-width: 800px;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.message-row {
  display: flex;
  gap: 20px;
  line-height: 1.6;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.bot {
  align-items: flex-start;
}

.bot-avatar img {
  width: 30px;
  height: 30px;
}

.bot-avatar.loading {
  animation: spin 2s linear infinite;
}

@keyframes spin {
  100% {
    transform: rotate(360deg);
  }
}

/* User Bubble: 배경 있음 */
.user .message-bubble {
  background-color: var(--c-background-secondary);
  padding: 12px 20px;
  border-radius: 20px;
  max-width: 80%;
}

/* Bot Bubble: 배경 없음 */
.bot .message-bubble {
  flex: 1;
  padding-top: 5px;
  /* 아이콘과 높이 맞춤 */
}

/* 로딩 애니메이션 */
.typing-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  background-color: var(--c-text-secondary);
  border-radius: 50%;
  margin: 0 2px;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-dot:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {

  0%,
  80%,
  100% {
    transform: scale(0);
  }

  40% {
    transform: scale(1);
  }
}

/* 3. 하단 입력창 */
.input-container {
  position: absolute;
  bottom: 0;
  width: 100%;
  background: var(--c-background);
  /* 뒤가 비치지 않게 */
  padding: 0 20px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.input-wrapper {
  width: 100%;
  max-width: 800px;
  background-color: var(--c-background-secondary);
  border-radius: 999px;
  /* Pill shape */
  padding: 10px 15px;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.input-wrapper:focus-within {
  background-color: var(--c-input-background);
  border-color: var(--c-accent);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.1);
}

.chat-input {
  flex: 1;
  border: none !important;
  background: transparent !important;
  font-size: 16px;
  padding: 10px;
  color: var(--c-input-text);
  box-shadow: none !important;
}

.chat-input:focus {
  outline: none;
}

.btn-icon {
  background: transparent;
  border: none;
  color: var(--c-text-secondary);
  padding: 8px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-icon:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: var(--c-text-primary);
}

.btn-icon.send-msg.active {
  color: var(--c-accent);
}

.disclaimer {
  font-size: 12px;
  color: var(--c-text-secondary);
  margin-top: 10px;
  text-align: center;
}
</style>
