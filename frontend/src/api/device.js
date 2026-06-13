import request from './request'

export function getRoomsApi() {
  return request.get('/rooms')
}

export function getDevicesApi(params = {}) {
  return request.get('/devices', { params })
}

export function getDeviceApi(deviceId) {
  return request.get(`/devices/${deviceId}`)
}

export function updateDeviceStateApi(deviceId, payload) {
  return request.patch(`/devices/${deviceId}/state`, payload)
}

export function getDeviceHistoryApi(deviceId) {
  return request.get(`/devices/${deviceId}/history`)
}
