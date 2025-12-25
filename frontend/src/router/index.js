import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '../views/LandingPage.vue'
import { useAuthStore } from '../stores/authStore'

const requireGuest = (to, from, next) => {
  const authStore = useAuthStore()
  if (authStore.isAuthenticated) {
    window.alert('이미 로그인된 상태입니다.')
    if (from.name) {
      next(false)
    } else {
      next('/')
    }
  } else {
    next()
  }
}

const requireAuth = (to, from, next) => {
  const authStore = useAuthStore()
  if (!authStore.isAuthenticated) {
    window.alert('로그인이 필요한 서비스입니다.')
    next('/login')
  } else {
    next()
  }
}

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
      beforeEnter: requireAuth,
    },
    {
      // :id는 동적 세그먼트로, 리뷰의 ID(숫자 등)가 들어갈 자리입니다.
      path: '/reviews/:id',
      name: 'review-detail',
      component: () => import('../views/PostDetailPage.vue'),
    },
    {
      path: '/reviews/:id/edit',
      name: 'review-edit',
      component: () => import('../views/PostUpdatePage.vue'),
      beforeEnter: requireAuth,
    },
    {
      path: '/chatbot',
      name: 'chatbot',
      component: () => import('../views/ChatbotPage.vue'),
      beforeEnter: requireAuth,
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginPage.vue'),
      beforeEnter: requireGuest,
    },
    {
      path: '/signup',
      name: 'signup',
      component: () => import('../views/SignupPage.vue'),
      beforeEnter: requireGuest,
    },
  ],
})

export default router
