import axios from 'axios'
import { ElMessage } from 'element-plus'
import { API_BASE_URL } from '../config/api'

const TOKEN_KEY = 'smart_home_token'
const TOKEN_TYPE_KEY = 'smart_home_token_type'

function getErrorPayload(error) {
  const body = error.response?.data
  if (body?.success === false) return body
  if (body?.detail?.success === false) return body.detail
  return null
}

function normalizeTokenType(type) {
  if (!type) return 'Bearer'
  return type.toLowerCase() === 'bearer' ? 'Bearer' : type
}

const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  const tokenType = normalizeTokenType(localStorage.getItem(TOKEN_TYPE_KEY))
  if (token) {
    config.headers.Authorization = `${tokenType} ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => {
    const body = response.data
    if (body && typeof body.success === 'boolean') {
      if (response.config.rawEnvelope) return body
      if (body.success) return body.data
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(Object.assign(new Error(body.message || '请求失败'), { payload: body }))
    }
    return body
  },
  (error) => {
    const payload = getErrorPayload(error)
    const status = error.response?.status

    if (!error.response) {
      ElMessage.error('后端服务未启动或网络不可达，请确认 FastAPI 正在运行')
      return Promise.reject(error)
    }

    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(TOKEN_TYPE_KEY)
      localStorage.removeItem('smart_home_user')
      ElMessage.error(payload?.message || '登录已失效，请重新登录')
      if (window.location.pathname !== '/login') {
        const redirect = encodeURIComponent(`${window.location.pathname}${window.location.search}`)
        window.location.href = `/login?redirect=${redirect}`
      }
      return Promise.reject(Object.assign(error, { payload }))
    }

    ElMessage.error(payload?.message || error.message || '请求失败')
    return Promise.reject(Object.assign(error, { payload }))
  }
)

export { TOKEN_KEY, TOKEN_TYPE_KEY }
export default request
