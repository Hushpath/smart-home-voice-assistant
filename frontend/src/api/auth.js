import request, { TOKEN_KEY, TOKEN_TYPE_KEY } from './request'

export function normalizeLoginResponse(payload) {
  const data = payload?.success === true ? payload.data : payload
  const token = data?.access_token || data?.token || data?.accessToken || ''
  const tokenType = data?.token_type || data?.tokenType || 'bearer'
  const user = data?.user || null

  return {
    token,
    tokenType,
    user
  }
}

export function loginApi(credentials) {
  return request.post('/auth/login', {
    username: credentials.username,
    password: credentials.password
  })
}

export function getCurrentUserApi() {
  return request.get('/auth/me')
}

export function saveAuthSession({ token, tokenType, user }) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(TOKEN_TYPE_KEY, tokenType || 'bearer')
  if (user) {
    localStorage.setItem('smart_home_user', JSON.stringify(user))
  }
}

export function clearAuthSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(TOKEN_TYPE_KEY)
  localStorage.removeItem('smart_home_user')
}
