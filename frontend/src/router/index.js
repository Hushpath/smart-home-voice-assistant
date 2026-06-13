import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import AppLayout from '../components/AppLayout.vue'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import DevicesView from '../views/DevicesView.vue'
import VoiceControlView from '../views/VoiceControlView.vue'
import LogsView from '../views/LogsView.vue'
import RemindersView from '../views/RemindersView.vue'
import ScenesView from '../views/ScenesView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { public: true }
    },
    {
      path: '/',
      component: AppLayout,
      meta: { requiresAuth: true },
      redirect: '/dashboard',
      children: [
        { path: 'dashboard', name: 'dashboard', component: DashboardView, meta: { title: 'Dashboard' } },
        { path: 'devices', name: 'devices', component: DevicesView, meta: { title: '设备管理' } },
        { path: 'voice', name: 'voice', component: VoiceControlView, meta: { title: '语音控制' } },
        { path: 'logs', name: 'logs', component: LogsView, meta: { title: '操作日志' } },
        { path: 'reminders', name: 'reminders', component: RemindersView, meta: { title: '提醒管理' } },
        { path: 'scenes', name: 'scenes', component: ScenesView, meta: { title: '场景模式' } }
      ]
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/dashboard'
    }
  ]
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  if (to.meta.public && authStore.isAuthenticated) {
    return to.query.redirect || '/dashboard'
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (to.meta.requiresAuth && authStore.isAuthenticated && !authStore.user && !authStore.authChecked) {
    try {
      await authStore.fetchCurrentUser()
    } catch {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }

  return true
})

export default router
