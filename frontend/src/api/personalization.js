import request from './request'

export function getUserPreferencesApi() {
  return request.get('/user/preferences')
}

export function updateUserPreferencesApi(payload, options = {}) {
  return request.patch('/user/preferences', payload, {
    rawEnvelope: Boolean(options.rawEnvelope),
    suppressErrorMessage: Boolean(options.suppressErrorMessage)
  })
}

export function getPreferenceSuggestionsApi(params = {}) {
  return request.get('/user/preference-suggestions', { params })
}

export function getDeviceAliasesApi() {
  return request.get('/user/device-aliases')
}

export function createDeviceAliasApi(payload, options = {}) {
  return request.post('/user/device-aliases', payload, {
    rawEnvelope: Boolean(options.rawEnvelope),
    suppressErrorMessage: Boolean(options.suppressErrorMessage)
  })
}

export function deleteDeviceAliasApi(aliasId, options = {}) {
  return request.delete(`/user/device-aliases/${aliasId}`, {
    rawEnvelope: Boolean(options.rawEnvelope),
    suppressErrorMessage: Boolean(options.suppressErrorMessage)
  })
}

export function getFrequentCommandsApi(params = {}) {
  return request.get('/user/frequent-commands', { params })
}
