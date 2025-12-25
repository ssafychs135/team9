<template>
  <div class="post-list-page container">
    <div class="header-section">
      <div class="title-group">
        <h1>Latest Reviews</h1>
        <RouterLink to="/reviews/create" class="btn-text"> + 새 리뷰 작성</RouterLink>
      </div>
      
      <div class="search-wrapper">
        <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
        <!-- @input 이벤트로 디바운스된 검색 실행 -->
        <input 
          :value="searchQuery" 
          @input="onSearchInput"
          type="text" 
          placeholder="리뷰 검색..." 
          class="search-input"
        />
      </div>
    </div>
    
    <!-- 로딩 중일 때 -->
    <div v-if="isLoading" class="loading-state">
      <div class="spinner"></div>
      <p>리뷰를 불러오는 중...</p>
    </div>

    <!-- 데이터가 있을 때 -->
    <div v-else-if="posts.length > 0">
      <div class="review-grid ">
        <div v-for="post in posts" :key="post.id" class="review-card">
          <div class="card-image">
            <img :src="`https://img.youtube.com/vi/${post.video_id}/mqdefault.jpg`" alt="">
            <!-- <div class="placeholder-img"></div> -->
          </div>
          <div class="card-content">
            <span v-if="post.isNew" class="card-tag">NEW</span>
            <h3>{{ post.title }}</h3>
            <p class="card-summary">{{ removeMd(post.content.substring(0, 40)) }}...</p>
            <RouterLink :to="`/reviews/${post.id}`" class="card-link">더 보기</RouterLink>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div class="pagination" v-if="totalPages > 1">
        <button 
          class="page-btn nav-btn" 
          :disabled="currentPage === 1" 
          @click="changePage(currentPage - 1)"
        >
          &lt;
        </button>
        
        <button 
          v-for="page in totalPages" 
          :key="page" 
          class="page-btn"
          :class="{ active: currentPage === page }"
          @click="changePage(page)"
        >
          {{ page }}
        </button>
        
        <button 
          class="page-btn nav-btn" 
          :disabled="currentPage === totalPages" 
          @click="changePage(currentPage + 1)"
        >
          &gt;
        </button>
      </div>
    </div>

    <!-- 검색 결과가 없을 때 -->
    <div v-else class="no-results">
      <p>검색 결과가 없습니다.</p>
    </div>
  </div>
</template>

<script setup>
import axios from 'axios';
import removeMd from 'remove-markdown';
import { ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router';

// 상태 관리
const posts = ref([]); // 현재 페이지에 보여줄 데이터만 담음
const searchQuery = ref('');
const currentPage = ref(1);
const totalPages = ref(1);
const isLoading = ref(false);

const itemsPerPage = 6;
let debounceTimeout = null;


async function fetchPosts(page, query) {
  isLoading.value = true;

  axios({
  method: 'get',
  url: 'http://localhost:8000/api/reviews/',
    }).then((response) => {
      console.log('API 응답 데이터:', response.data);
      const filtered = response.data.filter(p => 
        p.title.toLowerCase().includes(query.toLowerCase()) || 
        p.content.toLowerCase().includes(query.toLowerCase())
  );
    // 2. 전체 페이지 수 계산
  totalPages.value = Math.ceil(filtered.length / itemsPerPage);

  // 3. 현재 페이지에 해당하는 데이터만 자르기 (백엔드 역할)
  const start = (page - 1) * itemsPerPage;
  posts.value = filtered.slice(start, start + itemsPerPage);

  isLoading.value = false;
}).catch((error) => {
  console.error('API 호출 오류:', error);
});
  

}

// 검색어 입력 핸들러 (Debounce 적용)
function onSearchInput(event) {
  const value = event.target.value;
  searchQuery.value = value;
  
  if (debounceTimeout) clearTimeout(debounceTimeout);
  
  // 사용자가 입력을 멈추고 0.3초 뒤에 검색 시작
  debounceTimeout = setTimeout(() => {
    currentPage.value = 1; // 검색 시 1페이지로 초기화
    fetchPosts(1, value);
  }, 300);
}

// 페이지 변경 핸들러
function changePage(page) {
  if (page < 1 || page > totalPages.value) return;
  currentPage.value = page;
  fetchPosts(page, searchQuery.value);
  // 스크롤 상단 이동
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// 초기 로드
onMounted(() => {
  fetchPosts(1, '');
});
</script>

<style scoped>
.post-list-page {
  padding-top: 60px;
  padding-bottom: 60px;
}

.loading-state {
  text-align: center;
  padding: 60px 0;
  color: var(--c-text-secondary);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(0,0,0,0.1);
  border-left-color: var(--c-accent);
  border-radius: 50%;
  margin: 0 auto 20px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center; 
  margin-bottom: 40px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--c-divider);
  flex-wrap: wrap; 
  gap: 20px;
}

.title-group h1 {
  margin-bottom: 5px;
}

.btn-text {
  color: var(--c-accent);
  font-size: 17px;
}

/* 검색창 스타일 */
.search-wrapper {
  position: relative;
  width: 300px;
}

.search-input {
  width: 100%;
  padding: 10px 10px 10px 36px;
  border-radius: 10px;
  border: 1px solid var(--c-input-border);
  background-color: var(--c-input-background);
  color: var(--c-input-text);
  font-size: 15px;
  transition: all 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: var(--c-accent);
  background-color: var(--c-card-background);
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.15);
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #86868b;
  pointer-events: none;
}

/* 그리드 및 카드 스타일 (기존 유지) */
.review-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 30px;
  margin-bottom: 60px;
}

.review-card {
  background: var(--c-card-background);
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  display: flex;
  flex-direction: column;
}

.review-card:hover {
  transform: scale(1.02);
  box-shadow: 0 12px 30px rgba(0,0,0,0.1);
}

.card-image img {
    width: 100%;
    height: 100%;
    object-fit: cover; /* 이미지가 비율을 유지하며 영역을 꽉 채우고 중앙을 맞춤 */
  }

.card-image {
  height: 200px;
  background-color: #f5f5f7;
}

.placeholder-img {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #e1e1e1 0%, #f5f5f7 100%);
}

.card-content {
  padding: 24px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.card-tag {
  font-size: 10px;
  font-weight: 700;
  color: #bf4800;
  margin-bottom: 8px;
  text-transform: uppercase;
}

.card-content h3 {
  font-size: 21px;
  margin-bottom: 10px;
  line-height: 1.2;
}

.card-summary {
  font-size: 15px;
  color: var(--c-text-secondary);
  line-height: 1.5;
  flex: 1;
}

.card-link {
  margin-top: 15px;
  font-size: 15px;
  font-weight: 600;
}

/* 페이지네이션 스타일 */
.pagination {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 40px;
}

.page-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background-color: transparent;
  border: none;
  font-size: 15px;
  color: var(--c-text-primary);
  cursor: pointer;
  transition: background 0.2s;
}

.page-btn:hover:not(:disabled) {
  background-color: var(--c-input-background);
}

.page-btn.active {
  background-color: var(--c-accent);
  color: white;
  font-weight: 600;
}

.page-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.nav-btn {
  font-weight: bold;
}

.no-results {
  text-align: center;
  padding: 60px 0;
  color: var(--c-text-secondary);
  font-size: 17px;
}
</style>
