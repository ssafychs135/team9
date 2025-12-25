<template>
  <div class="landing-page">
    <section class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title">Review.</h1>
        <h2 class="hero-subtitle">가장 똑똑하게 제품을 고르는 방법.</h2>
        <p class="hero-desc">AI가 분석한 유튜브 리뷰 요약부터<br />나에게 딱 맞는 제품 추천까지.</p>
        <div class="hero-links">
          <RouterLink to="/reviews" class="btn">리뷰 살펴보기</RouterLink>
          <RouterLink to="/chatbot" class="text-link">AI 상담하기 ></RouterLink>
        </div>
      </div>
      <!-- Placeholder for a sleek product image -->
      <div class="hero-image-placeholder">
        <img src="@/assets/landing.jpeg" alt="Device Mockup" class="device-mockup" />
      </div>
    </section>

    <section class="feature-section">
      <div class="feature-card">
        <h3>AI Summary</h3>
        <p>수십 분짜리 영상을 3줄로 요약해 드립니다.</p>
      </div>
      <div class="feature-card">
        <h3>Smart Choice</h3>
        <p>빅데이터 기반으로 최저가와 장단점을 분석합니다.</p>
      </div>
      <div class="feature-card">
        <h3>Genius Chat</h3>
        <p>무엇이든 물어보세요. 전문가처럼 답변해 드립니다.</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router';
</script>

<style scoped>
.landing-page {
  width: 100%;
}

.hero-section {
  text-align: center;
  padding: 100px 20px 60px;
  background-color: var(--c-background);
}

.hero-title {
  font-size: 56px;
  font-weight: 700;
  margin-bottom: 0;
  color: var(--c-text-primary);
}

.hero-subtitle {
  font-size: 56px;
  font-weight: 700;
  margin-top: 0;
  margin-bottom: 20px;
  background: linear-gradient(90deg, #1d1d1f 0%, #434344 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-desc {
  font-size: 21px;
  line-height: 1.4;
  font-weight: 400;
  margin-bottom: 30px;
  color: var(--c-text-secondary);
}

.hero-links {
  display: flex;
  gap: 20px;
  justify-content: center;
  align-items: center;
  margin-bottom: 50px;
}

.text-link {
  color: var(--c-accent);
  font-size: 19px;
  font-weight: 400;
  text-decoration: none;
}

.text-link:hover {
  text-decoration: underline;
}

.hero-image-placeholder {
  height: 300px;
  display: flex;
  justify-content: center;
  align-items: flex-end;
}

.device-mockup {
  width: 600px;
  height: 300px;
  background: linear-gradient(135deg, #e0e0e0 0%, #f5f5f7 100%);
  border-radius: 20px 20px 0 0;
  box-shadow: 0 -20px 40px rgba(0,0,0,0.1);
  border: 1px solid #d2d2d7;
  border-bottom: none;
}

.feature-section {
  display: flex;
  justify-content: center;
  gap: 20px;
  padding: 60px 20px;
  background-color: var(--c-background-secondary);
}

.feature-card {
  background: var(--c-card-background);
  padding: 30px;
  border-radius: 18px;
  width: 300px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0,0,0,0.04);
  transition: transform 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-5px);
}

.feature-card h3 {
  font-size: 24px;
  margin-bottom: 10px;
}

.feature-card p {
  font-size: 15px;
  line-height: 1.5;
}
</style>