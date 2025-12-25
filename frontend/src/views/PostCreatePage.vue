<template>
  <div class="post-create-page container">
    <div class="form-wrapper">
      <div class="page-header">
        <h1>새로운 리뷰 작성</h1>
        <p>AI가 영상을 분석하여 요약본을 만들어 드립니다.</p>
      </div>

      <form @submit.prevent="submitReview" class="review-form card">
        <div class="form-group">
          <label for="title">리뷰 제목</label>
          <input type="text" id="title" v-model="title" placeholder="예: 아이폰 15 프로 사용기" />
        </div>

        <div class="form-group">
          <label for="youtube-url">YouTube 링크</label>
          <div class="input-integrated-wrapper">
            <input type="text" id="youtube-url" v-model="youtubeUrl" placeholder="https://youtube.com/watch?v=..."
              class="integrated-input" />
            <button type="button" class="btn-summarize-integrated" @click="requestSummary" :disabled="isSummarizing">
              {{ isSummarizing ? '요약 중...' : '요약 요청' }}
            </button>
          </div>
        </div>

        <div class="form-group">
          <label for="content">내용 (AI 요약)</label>
          <div class="textarea-wrapper">
            <textarea id="content" v-model="content" rows="10" placeholder="영상을 분석하는 동안 잠시만 기다려주세요..."></textarea>
          </div>
        </div>

        <div class="form-actions">
          <button type="button" class="btn-text" @click="$router.back()">취소</button>
          <button type="submit" class="btn-primary">작성 완료</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios'; // HTTP 요청을 위해 axios를 불러옵니다.
import { useAuthStore } from '@/stores/authStore';
import { useModalStore } from '@/stores/modalStore';

// 입력 데이터들을 관리하기 위한 반응형 변수(Ref)들입니다.
const title = ref('');
const youtubeUrl = ref('');
const content = ref('');
const isSummarizing = ref(false); // 요약 진행 중 상태를 나타냅니다.
const userToken = useAuthStore().token; // 인증 토큰을 스토어에서 가져옵니다.
const modalStore = useModalStore();
let videoId =""; // 유튜브 비디오 ID를 저장할 변수입니다.
/**
 * 유튜브 URL에서 11자리 비디오 ID를 추출합니다.
 */
function extractYoutubeId(url) {
    const regex = /(?:youtube\.com\/(?:[^/]+\/.+\/|(?:v|e(?:mbed)|shorts|live)\/|.*[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
    const match = url.match(regex);
    return match ? match[1] : null;
}

/**
 * 입력된 유튜브 링크를 바탕으로 AI 요약을 요청합니다.
 */
async function requestSummary() {
  videoId = extractYoutubeId(youtubeUrl.value);
  console.log("Extracted Video ID:", videoId);

  if (!videoId) {
    modalStore.alert('올바른 유튜브 링크를 입력해 주세요.');
    return;
  }

  isSummarizing.value = true;
  content.value = 'AI가 영상을 분석하고 요약하는 중입니다... 잠시만 기다려 주세요.';

  try {
    // 1. axios를 사용하여 로컬 서버(3000번 포트)에 GET 요청을 보냅니다.
    // 2. params 객체에 videoid와 langcode를 담아 보냅니다.
    const response = await axios.get('http://127.0.0.1:3000', {
      params: {
        videoId: videoId,
        langCode: 'ko'
      }
    });

    // 서버에서 보내준 응답 데이터(요약본)를 화면의 내용(content)란에 넣어줍니다.
    // 서버 응답 구조에 따라 response.data 또는 response.data.summary 등으로 수정될 수 있습니다.
    content.value = response.data; 
    modalStore.alert('요약이 완료되었습니다!');
    
  } catch (error) {
    console.error('요약 요청 중 오류 발생:', error);
    // 에러 발생 시 사용자에게 알림을 줍니다.
    content.value = '요약 중 오류가 발생했습니다. 서버가 켜져 있는지 확인해 주세요.';
    modalStore.alert('서버 연결에 실패했습니다.');
  } finally {
    isSummarizing.value = false;
  }
}

// 글 작성 완료 로직입니다.
function submitReview() {
  if (!title.value || !content.value) {
    modalStore.alert('제목과 내용을 모두 입력해 주세요.');
    return;
  }
  
  // axios.post(url, data, config) 순서로 인자를 전달해야 합니다.
  axios.post('http://localhost:8000/api/reviews/', 
    {
      // 1. 서버로 보낼 데이터 (Body)
      title: title.value,
      // 백엔드(Django) 필드명에 맞춰 스네이크 케이스(snake_case)로 변경합니다.
      video_id: videoId, 
      lang_code: 'ko',
      content: content.value,
    },
    {
      // 2. 요청 설정 (Headers)
      headers: {
        'Authorization': `Token ${userToken}`
      }
    }
  ).then(async () => {
    await modalStore.alert('리뷰가 성공적으로 작성되었습니다!');
    // 작성 완료 후 리뷰 목록 페이지로 이동합니다.
    window.location.href = '/reviews';
  }).catch(error => {
    console.error('리뷰 작성 중 오류 발생:', error);
    modalStore.alert('리뷰 작성에 실패했습니다. 다시 시도해 주세요.');
  });
}
</script>

<style scoped>
.post-create-page {
  padding: 60px 20px;
}

.form-wrapper {
  max-width: 720px;
  margin: 0 auto;
}

.review-form {
  /* 카드 스타일은 base.css .card로 대체됨 */
}

/* 통합형 입력창 래퍼 스타일 */
.input-integrated-wrapper {
  display: flex;
  align-items: center;
  background-color: var(--c-input-background);
  border: 1px solid var(--c-input-border);
  border-radius: 12px;
  padding: 0;
  /* 패딩 제거하여 버튼이 꽉 차도록 함 */
  overflow: hidden;
  /* 버튼이 둥근 모서리를 넘지 않도록 처리 */
  transition: all 0.2s ease;
}

.input-integrated-wrapper:focus-within {
  border-color: #0071e3;
  background-color: var(--c-input-background);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.15);
}

.integrated-input {
  flex: 1;
  border: none !important;
  /* 외부 래퍼가 보더를 가지므로 제거 */
  background: transparent !important;
  padding: 16px;
  /* 텍스트 입력 영역 패딩 */
  font-size: 16px;
  outline: none;
  color: var(--c-input-text);
}

/* 통합형 요약 버튼 스타일 */
.btn-summarize-integrated {
  align-self: stretch;
  /* 높이를 부모 요소(래퍼)에 맞춰 꽉 채움 */
  padding: 0 24px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 0;
  /* 라운드 제거 (래퍼의 overflow:hidden으로 처리) */
  background-color: var(--c-accent);
  color: white;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.2s ease;
}

.btn-summarize-integrated:hover:not(:disabled) {
  background-color: #0077ed;
  /* 꽉 찬 형태이므로 크기 확대(scale) 효과는 제거 */
}

.btn-summarize-integrated:disabled {
  background-color: var(--c-input-border);
  color: white;
  cursor: not-allowed;
}

.textarea-wrapper {
  position: relative;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 40px;
  align-items: center;
}

/* .btn-submit, .btn-cancel 스타일은 base.css로 대체됨 */
.btn-primary {
  width: auto; /* 폼 버튼 너비 조정 */
}
</style>
