import request from './request'

export function getWeatherApi(city) {
  return request.get('/weather', { params: city ? { city } : {} })
}
