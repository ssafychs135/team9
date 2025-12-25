import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '../views/LandingPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'landing',
      component: LandingPage,
    },
    {
      path: '/reviews',
      name: 'reviews',
      component: () => import('../views/PostListPage.vue'),
    },
    {
      path: '/reviews/create',
      name: 'review-create',
      component: () => import('../views/PostCreatePage.vue'),
    },
    {
      // :id는 동적 세그먼트로, 리뷰의 ID(숫자 등)가 들어갈 자리입니다.
      path: '/reviews/:id',
      name: 'review-detail',
      component: () => import('../views/PostDetailPage.vue'),
    },
    {
      path: '/chatbot',
      name: 'chatbot',
      component: () => import('../views/ChatbotPage.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginPage.vue'),
    },
    {
      path: '/signup',
      name: 'signup',
      component: () => import('../views/SignupPage.vue'),
    },
  ],
})

export default router