<template>
  <div class="login-page">
    <div class="form-container">
      <div class="form-header">
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
        <button type="submit" class="submit-btn">로그인</button>
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

const router = useRouter();
const store = useAuthStore();

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
      window.alert('Login failed: ' + (error.response?.data?.detail || '로그인에 실패했습니다.'));
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
  background: var(--c-card-background);
  padding: 48px;
  border-radius: 24px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

.form-header {
  text-align: center;
  margin-bottom: 32px;
}

.form-header h1 {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
}

.form-header p {
  font-size: 15px;
  color: #86868b;
}

.form-group {
  margin-bottom: 20px;
}

input {
  width: 100%;
  padding: 16px;
  border: 1px solid var(--c-input-border);
  border-radius: 12px;
  font-size: 17px;
  color: var(--c-input-text);
  transition: all 0.2s ease;
  background-color: var(--c-input-background);
}

input:focus {
  outline: none;
  border-color: #0071e3;
  background-color: var(--c-input-background);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.15);
}

.submit-btn {
  width: 100%;
  padding: 16px;
  font-size: 17px;
  font-weight: 600;
  margin-top: 10px;
}

.form-footer {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
  color: #86868b;
}

.form-footer a {
  color: #0071e3;
  font-weight: 500;
  text-decoration: none;
}

.form-footer a:hover {
  text-decoration: underline;
}
</style>
