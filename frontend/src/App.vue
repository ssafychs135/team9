<script setup>
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'

const store = useAuthStore()
const router = useRouter()

const handleLogout = () => {
  store.logout()
  window.alert('성공적으로 로그아웃되었습니다.')
  router.push({ name: 'landing' })
}
</script>

<template>
  <header class="global-nav">
    <div class="nav-content">
      <RouterLink to="/" class="nav-logo"> ReviewSite</RouterLink>
      <nav>
        <RouterLink to="/reviews">Reviews</RouterLink>
        <RouterLink to="/chatbot">AI Genius</RouterLink>
        
        <!-- 로그인 상태에 따른 조건부 렌더링 -->
        <template v-if="store.isAuthenticated">
          <span class="user-info">{{ store.username }}님</span>
          <a href="#" @click.prevent="handleLogout" class="logout-btn">Logout</a>
        </template>
        <template v-else>
          <RouterLink to="/login">Login</RouterLink>
        </template>
      </nav>
    </div>
  </header>

  <main>
    <RouterView />
  </main>

  <footer class="global-footer">
    <div class="footer-content">
      <p>Copyright © 2025 ReviewSite Inc. 모든 권리 보유.</p>
    </div>
  </footer>
</template>

<style scoped>
/* 기존 스타일 유지하면서 추가 스타일 작성 */
.user-info {
  color: var(--c-text-primary);
  font-weight: 500;
  opacity: 0.9;
}

.logout-btn {
  cursor: pointer;
}
/* Apple-style Global Navigation */
.global-nav {
  position: sticky;
  top: 0;
  width: 100%;
  height: 48px; /* Slightly taller than standard 44px */
  background-color: var(--c-nav-background); /* Translucent background */
  backdrop-filter: saturate(180%) blur(20px); /* Blur effect */
  border-bottom: 1px solid var(--c-divider);
  z-index: 9999;
  display: flex;
  justify-content: center;
}

.nav-content {
  max-width: 980px;
  width: 100%;
  padding: 0 22px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.nav-logo {
  font-size: 18px;
  font-weight: 600;
  color: var(--c-text-primary);
  text-decoration: none !important;
  letter-spacing: -0.5px;
}

nav {
  display: flex;
  gap: 30px;
}

nav a {
  color: var(--c-text-primary);
  opacity: 0.8;
  text-decoration: none !important;
  font-size: 12px;
  font-weight: 400;
  transition: opacity 0.2s ease;
}

nav a:hover {
  opacity: 1;
  color: var(--c-accent);
}

nav a.router-link-active {
  color: var(--c-accent);
  opacity: 1;
}

main {
  flex: 1;
  width: 100%;
  overflow-y: auto; /* 내부 컨텐츠 스크롤 허용 */
  -webkit-overflow-scrolling: touch; /* 모바일 부드러운 스크롤 */
  
  /* 스크롤바 숨김 처리 */
  -ms-overflow-style: none; /* IE, Edge */
  scrollbar-width: none;    /* Firefox */
}

/* Chrome, Safari, Opera 등 */
main::-webkit-scrollbar {
  display: none;
}

.global-footer {
  background-color: var(--c-background-secondary);
  padding: 30px 0;
  font-size: 12px;
  color: var(--c-text-secondary);
  border-top: 1px solid var(--c-divider);
}

.footer-content {
  max-width: 980px;
  margin: 0 auto;
  padding: 0 22px;
}
</style>
