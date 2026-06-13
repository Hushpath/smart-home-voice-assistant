import request from './request'

export function getDashboardApi() {
  return request.get('/dashboard')
}
