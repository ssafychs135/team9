<template>
  <div class="post-detail-page container">
    <div class="detail-wrapper">
      <header class="detail-header">
        <div class="header-top">
          <RouterLink to="/reviews" class="btn-back">← 목록으로 돌아가기</RouterLink>
          <div v-if="isAuthor" class="post-actions">
            <button @click="editReview" class="btn-action">수정</button>
            <button @click="deleteReview" class="btn-action delete">삭제</button>
          </div>
        </div>
        <h1 class="post-title">{{ title }}</h1>
        <div class="post-meta">
          <span v-if="author" class="author">작성자: {{ author }}</span>
          <span class="date">{{ formattedDate }}</span>
        </div>
      </header>

      <!-- 유튜브 영상 임베드 섹션 -->
      <div v-if="videoId" class="video-section">
        <div class="video-container">
          <iframe :src="`https://www.youtube.com/embed/${videoId}`" frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen>
          </iframe>
        </div>
      </div>

      <main class="review-content-wrapper card">
        <!-- 마크다운 전용 클래스를 적용합니다. -->
        <div class="markdown-body" v-html="content"></div>
      </main>

      <!-- 댓글 섹션 -->
      <section class="comments-section">
        <h2 class="section-title">댓글 {{ comments.length }}</h2>

        <!-- 댓글 작성 폼 -->
        <div class="comment-form-wrapper card">
          <div v-if="authStore.isAuthenticated" class="comment-form">
            <textarea v-model="newCommentContent" placeholder="댓글을 작성해 주세요..." rows="3"></textarea>
            <div class="form-actions">
              <button @click="submitComment" :disabled="!newCommentContent.trim()" class="btn-primary">등록</button>
            </div>
          </div>
          <div v-else class="login-plz">
            <p>
              <RouterLink to="/login">로그인</RouterLink> 후 댓글을 작성할 수 있습니다.
            </p>
          </div>
        </div>

        <!-- 댓글 목록 -->
        <div class="comments-list">
          <div v-for="comment in comments" :key="comment.id" class="comment-item">
            <div class="comment-header">
              <span class="comment-author">{{ comment.user.username }}</span>
              <span class="comment-date">{{ formatDate(comment.created_at) }}</span>
            </div>
            <div class="comment-content">{{ comment.content }}</div>
          </div>
          <div v-if="comments.length === 0" class="no-comments">
            <p>아직 작성된 댓글이 없습니다.</p>
          </div>
        </div>
      </section>

      <footer class="detail-footer">
        <button class="btn-secondary" @click="$router.back()">뒤로 가기</button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import axios from 'axios';
import { marked } from 'marked';
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { RouterLink } from 'vue-router';
import { useAuthStore } from '@/stores/authStore';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const postId = route.params.id;

const title = ref('');
const content = ref('');
const videoId = ref('');
const author = ref('');
const createdAt = ref('');
const comments = ref([]);
const newCommentContent = ref('');

// 날짜를 보기 좋게 포맷팅합니다.
const formattedDate = computed(() => {
  if (!createdAt.value) return '';
  return formatDate(createdAt.value);
});

// 작성자 여부 확인
const isAuthor = computed(() => {
  return authStore.isAuthenticated && authStore.username === author.value;
});

function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
}

marked.setOptions({
  gfm: true,
  breaks: true,
});

onMounted(() => {
  window.scrollTo(0, 0);
  console.log('Fetching details for post ID:', postId);
  fetchReviewDetail();
  fetchComments();
});

function fetchReviewDetail() {
  axios.get(`http://localhost:8000/api/reviews/${postId}/`)
    .then(response => {
      title.value = response.data.title;
      content.value = marked(response.data.content);
      videoId.value = response.data.video_id;
      author.value = response.data.user.username;
      createdAt.value = response.data.created_at;
    })
    .catch(error => {
      console.error('Error fetching review data:', error);
    });
}

function fetchComments() {
  axios.get(`http://localhost:8000/api/reviews/${postId}/comments/`)
    .then(response => {
      comments.value = response.data;
    })
    .catch(error => {
      console.error('Error fetching comments:', error);
    });
}

function submitComment() {
  if (!newCommentContent.value.trim()) return;

  axios.post(`http://localhost:8000/api/reviews/${postId}/comments/`,
    { content: newCommentContent.value },
    {
      headers: {
        Authorization: `Token ${authStore.token}`
      }
    }
  )
    .then(response => {
      // 성공 시 댓글 목록 갱신 및 입력창 초기화
      newCommentContent.value = '';
      fetchComments(); // 전체 목록 다시 불러오기 (또는 response.data를 comments에 push)
    })
    .catch(error => {
      console.error('Error posting comment:', error);
      alert('댓글 작성에 실패했습니다.');
    });
}

function deleteReview() {
  if (!confirm('정말로 이 리뷰를 삭제하시겠습니까?')) return;

  axios.delete(`http://localhost:8000/api/reviews/${postId}/`, {
    headers: {
      Authorization: `Token ${authStore.token}`
    }
  })
    .then(() => {
      alert('리뷰가 삭제되었습니다.');
      router.push('/reviews');
    })
    .catch(error => {
      console.error('Error deleting review:', error);
      alert('리뷰 삭제에 실패했습니다.');
    });
}

function editReview() {
  router.push({ name: 'review-edit', params: { id: postId } });
}
</script>

<style scoped>
.post-detail-page {
  padding: 60px 20px;
  background-color: var(--c-background);
  min-height: 100vh;
}

.detail-wrapper {
  max-width: 800px;
  margin: 0 auto;
}

.detail-header {
  margin-bottom: 40px;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.btn-back {
  display: inline-block;
  color: var(--c-accent);
  text-decoration: none;
  font-weight: 500;
  transition: opacity 0.2s;
}

.btn-back:hover {
  opacity: 0.7;
}

.post-actions {
  display: flex;
  gap: 12px;
}

.btn-action {
  background: none;
  border: none;
  font-size: 14px;
  color: var(--c-text-secondary);
  cursor: pointer;
  transition: color 0.2s;
  padding: 0;
}

.btn-action:hover {
  color: var(--c-text-primary);
  text-decoration: underline;
}

.btn-action.delete:hover {
  color: #ff3b30;
  /* Red color for delete action */
}

.post-title {
  font-size: 40px;
  font-weight: 700;
  color: var(--c-text-primary);
  line-height: 1.2;
  margin-bottom: 16px;
}

.post-meta {
  color: var(--c-text-secondary);
  font-size: 15px;
  display: flex;
  gap: 16px;
}

/* 영상 섹션 스타일 */
.video-section {
  margin-bottom: 40px;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.video-container {
  position: relative;
  padding-bottom: 56.25%;
  /* 16:9 비율 */
  height: 0;
}

.video-container iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

/* 본문 영역 스타일 */
.review-content-wrapper {
  /* 카드 스타일은 base.css .card로 대체됨 */
  margin-bottom: 40px;
}

.detail-footer {
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid var(--c-input-border);
}

/* .btn-secondary 스타일은 base.css로 대체됨 */

/* 댓글 섹션 스타일 */
.comments-section {
  margin-bottom: 60px;
}

.section-title {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 20px;
  color: var(--c-text-primary);
}

.comment-form-wrapper {
  /* 카드 스타일은 base.css .card로 대체됨 */
  padding: 24px; /* 댓글 폼은 기본 카드 패딩(40px)보다 좁게 설정하고 싶으면 여기서 재정의 */
  margin-bottom: 30px;
}

.comment-form textarea {
  /* 기본 textarea 스타일은 base.css로 대체됨 */
  font-size: 15px;
  min-height: 80px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}

/* .btn-submit 스타일은 base.css .btn-primary로 대체됨 */
.btn-primary {
  width: auto; /* 댓글 등록 버튼은 full width가 아님 */
  padding: 8px 20px; /* 크기 조정 */
  border-radius: 20px; /* 둥근 모양 유지 */
  font-size: 14px;
}

.login-plz {
  text-align: center;
  color: var(--c-text-secondary);
  font-size: 15px;
  padding: 20px 0;
}

.login-plz a {
  color: var(--c-accent);
  font-weight: 600;
}

/* 댓글 목록 스타일 */
.comment-item {
  background: var(--c-card-background);
  padding: 20px;
  border-radius: 16px;
  margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.02);
  border: 1px solid var(--c-border);
}

.comment-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}

.comment-author {
  font-weight: 600;
  color: var(--c-text-primary);
}

.comment-date {
  color: var(--c-text-secondary);
}

.comment-content {
  color: var(--c-text-primary);
  line-height: 1.5;
  font-size: 15px;
  white-space: pre-wrap;
  /* 줄바꿈 유지 */
}

.no-comments {
  text-align: center;
  color: var(--c-text-secondary);
  padding: 40px 0;
}

@media (max-width: 768px) {
  .post-title {
    font-size: 32px;
  }

  .review-content-wrapper {
    padding: 24px;
  }
}
</style>
