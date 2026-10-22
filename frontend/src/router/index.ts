import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { requiresGuest: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { requiresGuest: true },
    },
    {
      path: '/',
      component: () => import('../layouts/DashboardLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'overview',
          component: () => import('../views/OverviewView.vue'),
        },
        {
          path: 'finance',
          name: 'finance',
          component: () => import('../views/FinanceView.vue'),
        },
        {
          path: 'portfolio',
          name: 'portfolio',
          component: () => import('../views/PortfolioView.vue'),
        },
        {
          path: 'portfolio/asset/:ticker',
          name: 'portfolio-asset-detail',
          component: () => import('../views/StockDetailView.vue'),
        },
        {
          path: 'portfolio/news/:id',
          name: 'portfolio-news-detail',
          component: () => import('../views/NewsDetailView.vue'),
        },
        {
          path: 'workspace',
          name: 'workspace',
          component: () => import('../views/WorkspaceView.vue'),
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('../views/SettingsView.vue'),
        },
      ],
    },
  ],
})

router.beforeEach(async (to, _from) => {
  const authStore = useAuthStore()

  // ถ้าเพิ่งเปิดเว็บ ให้ลองตรวจหา Session ผ่าน Cookie ดูก่อน
  if (authStore.isLoading) {
    await authStore.fetchMe()
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: 'login' }
  }
  if (to.meta.requiresGuest && authStore.isAuthenticated) {
    return { name: 'overview' }
  }
})

export default router
