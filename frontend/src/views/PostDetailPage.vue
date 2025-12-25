<template>
  <div class="post-detail-page container">
    <div class="detail-wrapper">
      <header class="detail-header">
        <RouterLink to="/reviews" class="btn-back">← 목록으로 돌아가기</RouterLink>
        <h1 class="post-title">{{ title }}</h1>
        <div class="post-meta">
          <span v-if="author" class="author">작성자: {{ author }}</span>
          <span class="date">{{ formattedDate }}</span>
        </div>
      </header>

      <!-- 유튜브 영상 임베드 섹션 -->
      <div v-if="videoId" class="video-section">
        <div class="video-container">
          <iframe 
            :src="`https://www.youtube.com/embed/${videoId}`" 
            frameborder="0" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
            allowfullscreen>
          </iframe>
        </div>
      </div>

      <main class="review-content-wrapper">
        <!-- 마크다운 전용 클래스를 적용합니다. -->
        <div class="markdown-body" v-html="content"></div>
      </main>

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
import { useRoute } from 'vue-router';
import { RouterLink } from 'vue-router';

const route = useRoute();
const postId = route.params.id;

const title = ref('');
const content = ref('');
const videoId = ref('');
const author = ref('');
const createdAt = ref('');

// 날짜를 보기 좋게 포맷팅합니다.
const formattedDate = computed(() => {
  if (!createdAt.value) return '';
  const date = new Date(createdAt.value);
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
});

marked.setOptions({
  gfm: true,
  breaks: true,
});

onMounted(() => {
  console.log('Fetching details for post ID:', postId);
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
});
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

.btn-back {
  display: inline-block;
  color: var(--c-accent);
  text-decoration: none;
  font-weight: 500;
  margin-bottom: 20px;
  transition: opacity 0.2s;
}

.btn-back:hover {
  opacity: 0.7;
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
  box-shadow: 0 10px 30px rgba(0,0,0,0.1);
}

.video-container {
  position: relative;
  padding-bottom: 56.25%; /* 16:9 비율 */
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
  background: var(--c-card-background);
  padding: 40px;
  border-radius: 24px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04);
  margin-bottom: 40px;
}

.detail-footer {
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid var(--c-input-border);
}

.btn-secondary {
  background-color: var(--c-input-background);
  color: var(--c-text-primary);
  padding: 12px 24px;
  border-radius: 12px;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background-color: #e8e8ed;
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
