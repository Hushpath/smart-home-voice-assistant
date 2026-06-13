import request from './request'

export function getScenesApi() {
  return request.get('/scenes')
}

export function runSceneApi(sceneId) {
  return request.post(`/scenes/${sceneId}/run`)
}
