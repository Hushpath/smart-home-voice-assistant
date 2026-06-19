import request from './request'

export function parseCommandApi(command, options = {}) {
  return request.post('/commands/parse', { command, ...(options.dialect ? { dialect: options.dialect } : {}) }, {
    rawEnvelope: Boolean(options.rawEnvelope),
    suppressErrorMessage: Boolean(options.suppressErrorMessage)
  })
}

export function executeCommandApi(command, options = {}) {
  return request.post('/commands/execute', { command, ...(options.dialect ? { dialect: options.dialect } : {}) }, {
    rawEnvelope: Boolean(options.rawEnvelope),
    suppressErrorMessage: Boolean(options.suppressErrorMessage)
  })
}

export function getCommandLogsApi() {
  return request.get('/commands/logs')
}
