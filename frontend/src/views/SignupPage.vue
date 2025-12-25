<template>
  <div class="signup-page">
    <div class="form-container card">
      <div class="page-header">
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
        <button type="submit" class="submit-btn btn-primary">Sign Up</button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/authStore';
import { useModalStore } from '@/stores/modalStore';

const router = useRouter();
const store = useAuthStore();
const modalStore = useModalStore();

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
      modalStore.alert('Signup failed: ' + JSON.stringify(error.response.data));
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
  /* 카드 스타일은 base.css .card로 대체됨 */
}

.submit-btn {
  /* 기본 버튼 스타일은 base.css .btn-primary로 대체됨 */
  margin-top: 10px;
}
</style>
