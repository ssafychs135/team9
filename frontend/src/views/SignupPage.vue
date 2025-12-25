<template>
  <div class="signup-page">
    <div class="form-container">
      <div class="form-header">
        <h1>계정 생성</h1>
        <p>새로운 ReviewSite ID를 만드세요.</p>
      </div>

      <form @submit.prevent="handleSignup">
        <div class="form-group">
          <input type="text" v-model="username" placeholder="username" required />
        </div>
        <div class="form-group">
          <input type="email" v-model="email" placeholder="name@example.com" required />
        </div>
        <div class="form-group">
          <input type="password" v-model="password" placeholder="password" required />
        </div>
        <div class="form-group">
          <input type="password" v-model="password2" placeholder="password confirmation" required />
        </div>
        <button type="submit" class="submit-btn">Sign Up</button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/authStore';

const router = useRouter();
const store = useAuthStore();

const username = ref('');
const email = ref('');
const password = ref('');
const password2 = ref('');

function handleSignup() {
  const payload = {
    username: username.value,
    email: email.value,
    password1: password.value,
    password2: password2.value,
  };

  store.signup(payload)
    .then(() => {
      console.log('Signup successful');
      router.push({ name: 'landing' });
    })
    .catch(error => {
      // 에러 처리 (예: 사용자에게 에러 메시지 표시)
      window.alert('Signup failed: ' + JSON.stringify(error.response.data));
    });
}
</script>

<style scoped>
.signup-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 150px);
  padding: 40px 20px;
}

.form-container {
  width: 100%;
  max-width: 460px;
  /* 로그인보다 조금 더 넓게 */
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

.form-row {
  display: flex;
  gap: 12px;
}

.form-row .form-group {
  flex: 1;
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
</style>
