import request from './request'

export function parseCommandApi(command, options = {}) {
  return request.post('/commands/parse', { command }, { rawEnvelope: Boolean(options.rawEnvelope) })
}

export function executeCommandApi(command, options = {}) {
  return request.post('/commands/execute', { command }, { rawEnvelope: Boolean(options.rawEnvelope) })
}

export function getCommandLogsApi() {
  return request.get('/commands/logs')
}
