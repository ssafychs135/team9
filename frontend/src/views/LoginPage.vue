<template>
  <div class="login-page">
    <div class="form-container card">
      <div class="page-header">
        <h1>로그인</h1>
        <p>ReviewSite에 오신 것을 환영합니다.</p>
      </div>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <input type="text" v-model="username" placeholder="유저명" required />
        </div>
        <div class="form-group">
          <input type="password" v-model="password" placeholder="비밀번호" required />
        </div>
        <button type="submit" class="submit-btn btn-primary">로그인</button>
      </form>

      <div class="form-footer">
        <p>아이디가 없으신가요? <RouterLink to="/signup">지금 만들기</RouterLink></p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/authStore';
import { useModalStore } from '@/stores/modalStore';

const router = useRouter();
const store = useAuthStore();
const modalStore = useModalStore();

const username = ref('');
const password = ref('');

function handleLogin() {
  const payload = {
    username: username.value,
    password: password.value,
  };

  store.login(payload)
    .then(() => {
      console.log('Login successful');
      router.push({ name: 'landing' });
    })
    .catch(error => {
      modalStore.alert('Login failed: ' + (error.response?.data?.detail || '로그인에 실패했습니다.'));
    });
}
</script>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 150px); /* 헤더/푸터 고려 */
  padding: 40px 20px;
}

.form-container {
  width: 100%;
  max-width: 400px;
  /* 카드 스타일은 base.css .card로 대체됨 */
}

.submit-btn {
  /* 기본 버튼 스타일은 base.css .btn-primary로 대체됨 */
  margin-top: 10px;
}

.form-footer {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
  color: var(--c-text-secondary);
}

.form-footer a {
  color: var(--c-accent);
  font-weight: 500;
  text-decoration: none;
}

.form-footer a:hover {
  text-decoration: underline;
}
</style>
