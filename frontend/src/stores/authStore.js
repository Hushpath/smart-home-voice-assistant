import { defineStore } from 'pinia'
import { clearAuthSession, getCurrentUserApi, loginApi, normalizeLoginResponse, saveAuthSession } from '../api/auth'
import { TOKEN_KEY, TOKEN_TYPE_KEY } from '../api/request'

function readStoredUser() {
  const value = localStorage.getItem('smart_home_user')
  if (!value) return null
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    tokenType: localStorage.getItem(TOKEN_TYPE_KEY) || 'bearer',
    user: readStoredUser(),
    authChecked: false,
    loading: false
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token),
    displayName: (state) => state.user?.nickname || state.user?.username || '演示用户'
  },
  actions: {
    async login(credentials) {
      this.loading = true
      try {
        const payload = await loginApi(credentials)
        const session = normalizeLoginResponse(payload)
        if (!session.token) {
          throw new Error('登录响应缺少 access_token')
        }
        saveAuthSession(session)
        this.token = session.token
        this.tokenType = session.tokenType
        this.user = session.user
        this.authChecked = true
        return session
      } finally {
        this.loading = false
      }
    },
    async fetchCurrentUser() {
      if (!this.token) return null
      this.loading = true
      try {
        const user = await getCurrentUserApi()
        this.user = user
        localStorage.setItem('smart_home_user', JSON.stringify(user))
        this.authChecked = true
        return user
      } catch (error) {
        this.logout()
        throw error
      } finally {
        this.loading = false
      }
    },
    logout() {
      clearAuthSession()
      this.token = ''
      this.tokenType = 'bearer'
      this.user = null
      this.authChecked = false
    }
  }
})
