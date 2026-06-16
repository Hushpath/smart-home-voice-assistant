import request from './request'

export function getVoiceProvidersApi() {
  return request.get('/voice/providers')
}

export function executeVoiceAudioApi(audioBlob, options = {}) {
  const form = new FormData()
  const filename = options.filename || 'voice-command.webm'
  form.append('audio', audioBlob, filename)
  if (options.dialect) form.append('dialect', options.dialect)
  return request.post('/voice/execute', form, {
    rawEnvelope: Boolean(options.rawEnvelope),
    suppressErrorMessage: Boolean(options.suppressErrorMessage),
    timeout: options.timeout || 30000
  })
}
