<template>
  <div class="post-update-page container">
    <div class="form-wrapper">
      <div class="page-header">
        <h1>리뷰 수정</h1>
        <p>기존 리뷰 내용을 수정합니다.</p>
      </div>

      <form @submit.prevent="submitReview" class="review-form">
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
          <button type="button" class="btn-cancel" @click="$router.back()">취소</button>
          <button type="submit" class="btn-submit">수정 완료</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();
const postId = route.params.id;
const authStore = useAuthStore();

// 입력 데이터들을 관리하기 위한 반응형 변수(Ref)들입니다.
const title = ref('');
const youtubeUrl = ref('');
const content = ref('');
const isSummarizing = ref(false);
let videoId = "";

/**
 * 유튜브 URL에서 11자리 비디오 ID를 추출합니다.
 */
function extractYoutubeId(url) {
    const regex = /(?:youtube\.com\/(?:[^/]+\/.+\/|(?:v|e(?:mbed)|shorts|live)\/|.*[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
    const match = url.match(regex);
    return match ? match[1] : null;
}

// 기존 리뷰 데이터를 불러옵니다.
onMounted(async () => {
  try {
    const response = await axios.get(`http://localhost:8000/api/reviews/${postId}/`);
    title.value = response.data.title;
    content.value = response.data.content;
    videoId = response.data.video_id;
    if (videoId) {
      youtubeUrl.value = `https://www.youtube.com/watch?v=${videoId}`;
    }
    
    // 권한 확인 (선택 사항: 백엔드에서도 막지만 UX 차원에서)
    if (authStore.username !== response.data.user.username) {
      alert("수정 권한이 없습니다.");
      router.push('/reviews');
    }
  } catch (error) {
    console.error('Error fetching review data:', error);
    alert('리뷰 정보를 불러오는 데 실패했습니다.');
    router.push('/reviews');
  }
});

/**
 * 입력된 유튜브 링크를 바탕으로 AI 요약을 요청합니다.
 */
async function requestSummary() {
  videoId = extractYoutubeId(youtubeUrl.value);
  
  if (!videoId) {
    alert('올바른 유튜브 링크를 입력해 주세요.');
    return;
  }

  isSummarizing.value = true;
  content.value = 'AI가 영상을 분석하고 요약하는 중입니다... 잠시만 기다려 주세요.';

  try {
    const response = await axios.get('http://127.0.0.1:3000', {
      params: {
        videoId: videoId,
        langCode: 'ko'
      }
    });

    content.value = response.data; 
    alert('요약이 완료되었습니다!');
    
  } catch (error) {
    console.error('요약 요청 중 오류 발생:', error);
    content.value = '요약 중 오류가 발생했습니다. 서버가 켜져 있는지 확인해 주세요.';
    alert('서버 연결에 실패했습니다.');
  } finally {
    isSummarizing.value = false;
  }
}

// 글 수정 완료 로직입니다.
function submitReview() {
  if (!title.value || !content.value) {
    alert('제목과 내용을 모두 입력해 주세요.');
    return;
  }

  // 유튜브 URL이 변경되었을 수 있으므로 videoId 다시 추출
  const newVideoId = extractYoutubeId(youtubeUrl.value);
  if (newVideoId) {
    videoId = newVideoId;
  }
  
  axios.put(`http://localhost:8000/api/reviews/${postId}/`, 
    {
      title: title.value,
      video_id: videoId, 
      lang_code: 'ko',
      content: content.value,
    },
    {
      headers: {
        'Authorization': `Token ${authStore.token}`
      }
    }
  ).then(() => {
    alert('리뷰가 성공적으로 수정되었습니다!');
    router.push({ name: 'review-detail', params: { id: postId } });
  }).catch(error => {
    console.error('리뷰 수정 중 오류 발생:', error);
    alert('리뷰 수정에 실패했습니다. 다시 시도해 주세요.');
  });
}
</script>

<style scoped>
.post-update-page {
  padding: 60px 20px;
}

.form-wrapper {
  max-width: 720px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 40px;
}

.page-header h1 {
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 10px;
}

.review-form {
  background: var(--c-card-background);
  padding: 40px;
  border-radius: 24px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

.form-group {
  margin-bottom: 24px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text-primary);
  margin-bottom: 8px;
  margin-left: 4px;
}

/* 통합형 입력창 래퍼 스타일 */
.input-integrated-wrapper {
  display: flex;
  align-items: center;
  background-color: var(--c-input-background);
  border: 1px solid var(--c-input-border);
  border-radius: 12px;
  padding: 0;
  overflow: hidden;
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
  background: transparent !important;
  padding: 16px;
  font-size: 16px;
  outline: none;
  color: var(--c-input-text);
}

.btn-summarize-integrated {
  align-self: stretch;
  padding: 0 24px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 0;
  background-color: var(--c-accent);
  color: white;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.2s ease;
}

.btn-summarize-integrated:hover:not(:disabled) {
  background-color: #0077ed;
}

.btn-summarize-integrated:disabled {
  background-color: var(--c-input-border);
  color: white;
  cursor: not-allowed;
}

input,
textarea {
  width: 100%;
  padding: 16px;
  border: 1px solid var(--c-input-border);
  border-radius: 12px;
  font-size: 16px;
  font-family: inherit;
  resize: vertical;
  background-color: var(--c-input-background);
  color: var(--c-input-text);
  transition: all 0.2s ease;
}

input:focus,
textarea:focus {
  outline: none;
  border-color: #0071e3;
  background-color: var(--c-input-background);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.15);
}

.textarea-wrapper {
  position: relative;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 40px;
}

.btn-submit {
  padding: 12px 30px;
  font-size: 16px;
  font-weight: 600;
}

.btn-cancel {
  background-color: transparent;
  color: #86868b;
  padding: 12px 20px;
  font-size: 16px;
}

.btn-cancel:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: #1d1d1f;
  transform: none;
}
</style>
