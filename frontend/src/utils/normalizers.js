export function normalizeDevice(device = {}) {
  const properties = device.properties || {}
  return {
    id: device.id,
    name: device.name,
    type: device.device_type,
    typeLabel: getDeviceTypeLabel(device.device_type),
    roomId: device.room_id,
    roomName: device.room_name,
    isOn: device.is_on,
    isOnline: device.is_online,
    properties,
    propertyBadges: normalizeDeviceProperties(device.device_type, properties),
    createdAt: device.created_at,
    updatedAt: device.updated_at
  }
}

export function normalizeDeviceHistory(item = {}) {
  return {
    id: item.id,
    deviceId: item.device_id,
    beforeState: item.before_state,
    afterState: item.after_state,
    changeSource: item.change_source,
    createdAt: item.created_at
  }
}

export function normalizeRoom(room = {}) {
  return {
    id: room.id,
    name: room.name,
    homeId: room.home_id,
    deviceCount: room.device_count || 0,
    createdAt: room.created_at
  }
}

export function normalizeDashboard(dashboard = {}) {
  return {
    roomCount: dashboard.room_count || 0,
    deviceCount: dashboard.device_count || 0,
    onlineDeviceCount: dashboard.online_device_count || 0,
    onDeviceCount: dashboard.on_device_count || 0,
    offlineDeviceCount: dashboard.offline_device_count || 0
  }
}

export function normalizeCommandLog(log = {}) {
  const parsedResult = normalizeParsedCommand(log.parsed_result || {})
  const detail = normalizeLogDetail(log.detail || {}, parsedResult, log.execution_result || null)
  const confidence = typeof log.confidence === 'number' ? log.confidence : parsedResult.confidence
  const isBatch = Boolean(detail.batch?.is_batch || parsedResult.is_batch || log.execution_result?.is_batch)
  return {
    id: log.id,
    userId: log.user_id,
    traceId: log.trace_id || detail.asr.trace_id || '-',
    commandText: cleanText(log.command_text || log.raw_command),
    rawCommand: log.raw_command || '-',
    inputSource: log.input_source || detail.asr.input_source || 'text',
    inputSourceLabel: getInputSourceLabel(log.input_source || detail.asr.input_source || 'text'),
    asrProvider: cleanText(log.asr_provider || detail.asr.asr_provider),
    intent: cleanText(log.intent || parsedResult.intent),
    room: cleanText(log.room || parsedResult.room),
    deviceType: cleanText(log.device_type || parsedResult.device_type),
    confidence,
    confidenceLabel: getConfidenceLabel(confidence),
    parsedResult,
    executionResult: log.execution_result || null,
    success: Boolean(log.success),
    isBatch,
    commandCount: detail.batch?.command_count || parsedResult.command_count || log.execution_result?.command_count || null,
    message: cleanText(log.message || detail.execution.message),
    errorMessage: log.error_message || '',
    createdAt: log.created_at || null,
    detail
  }
}

export function normalizeLogDetail(detail = {}, parsedResult = {}, executionResult = null) {
  const parseDetail = parsedResult.parseDetail || parsedResult.parse_detail || {}
  const normalization = detail.normalization || parseDetail.dialect_normalization || {}
  const execution = detail.execution || executionResult || {}
  return {
    asr: detail.asr || {},
    normalization,
    parse: detail.parse || {
      intent: parsedResult.intent,
      room: parsedResult.room,
      device_type: parsedResult.deviceType || parsedResult.device_type,
      value: parsedResult.value,
      scene: parsedResult.scene,
      reminder_time: parsedResult.reminderTime || parsedResult.reminder_time,
      reminder_content: parsedResult.reminderContent || parsedResult.reminder_content,
      city: parsedResult.city,
      intent_scores: parseDetail.intent_scores,
      parser_confidence: parsedResult.confidence,
      matched_keywords: parsedResult.matchedKeywords || parsedResult.matched_keywords || [],
      match_type: parsedResult.matchType || parsedResult.match_type,
      message: parsedResult.message
    },
    execution,
    batch: detail.batch || {
      is_batch: Boolean(parsedResult.is_batch || execution?.is_batch),
      command_count: parsedResult.command_count || execution?.command_count,
      success_count: execution?.success_count,
      failed_count: execution?.failed_count,
      sub_commands: parsedResult.sub_commands || [],
      sub_results: execution?.sub_results || []
    },
    raw: detail.raw || {
      parsed_result: parsedResult,
      execution_result: executionResult
    }
  }
}

export function normalizeReminder(reminder = {}) {
  return {
    id: reminder.id,
    userId: reminder.user_id,
    title: reminder.title || '-',
    remindTime: reminder.remind_time || null,
    isDone: Boolean(reminder.is_done),
    createdAt: reminder.created_at || null,
    updatedAt: reminder.updated_at || null
  }
}

export function normalizeScene(scene = {}) {
  return {
    id: scene.id,
    name: scene.name || '-',
    description: scene.description || '',
    homeId: scene.home_id,
    actions: (scene.actions || []).map((action) => ({
      id: action.id,
      deviceId: action.device_id,
      deviceName: action.device_name || `设备 ${action.device_id ?? '-'}`,
      action: action.action || '-',
      targetState: action.target_state || {},
      sortOrder: action.sort_order ?? 0
    }))
  }
}

export function normalizeCommandResult(result = {}) {
  const data = result.data || result
  const isBatch = Boolean(data.is_batch)
  return {
    success: result.success,
    code: data.code || result.code,
    message: data.message || result.message,
    traceId: data.trace_id || null,
    isBatch,
    commandCount: data.command_count || 0,
    successCount: data.success_count || 0,
    failedCount: data.failed_count || 0,
    subCommands: data.sub_commands || [],
    subResults: normalizeSubResults(data.sub_results || []),
    parsed: data.parsed ? normalizeParsedCommand(data.parsed) : null,
    result: data.result || null,
    deviceBefore: data.device_before || data.result?.before_state || null,
    deviceAfter: data.device_after || data.result?.after_state || null,
    affectedDevices: data.affected_devices || [],
    reminder: data.reminder || data.result?.reminder || null,
    weather: data.weather || data.result?.weather || null,
    scene: data.scene || data.result?.scene || null
  }
}

export function normalizeSubResults(items = []) {
  if (!Array.isArray(items)) return []
  return items.map((item) => ({
    ...item,
    index: item.index,
    text: cleanText(item.text),
    success: Boolean(item.success),
    code: cleanText(item.code),
    message: cleanText(item.message),
    parsed: item.parsed ? normalizeParsedCommand(item.parsed) : null,
    affectedDevices: item.affected_devices || [],
    deviceBefore: item.device_before || null,
    deviceAfter: item.device_after || null,
    reminder: item.reminder || item.result?.reminder || null,
    weather: item.weather || item.result?.weather || null,
    scene: item.scene || item.result?.scene || null
  }))
}

export function normalizeVoiceExecuteResult(result = {}) {
  const data = result.data || result
  const execution = data.execution || {}
  const normalizedExecution = normalizeCommandResult({
    success: result.success,
    code: result.code,
    message: result.message,
    data: execution
  })
  return {
    ...normalizedExecution,
    traceId: data.trace_id || execution.trace_id || normalizedExecution.traceId,
    recognition: data.recognition || null
  }
}

export function normalizeVoiceProviderStatus(status = {}) {
  const cloudConfigured = Boolean(status.cloud_configured)
  const currentProvider = status.current_provider || 'cloud'
  const providerLabel = currentProvider === 'xunfei' || currentProvider === 'iflytek' ? '讯飞 ASR' : '云端 ASR'
  return {
    currentProvider,
    providerLabel,
    cloudConfigured,
    cloudStatus: cloudConfigured ? `${providerLabel} 可用` : '未配置',
    cloudStatusType: cloudConfigured ? 'success' : 'warning',
    availableProviders: status.available_providers || [],
    browserFallbackSupported: Boolean(status.browser_fallback_supported),
    browserSupported: typeof window !== 'undefined' && Boolean(window.SpeechRecognition || window.webkitSpeechRecognition),
    textFallbackSupported: status.text_fallback_supported !== false,
    notes: status.notes || (cloudConfigured ? '云端语音识别可用。' : '云端语音识别未配置，请使用浏览器识别或文本输入。')
  }
}

export function cleanText(value, fallback = '-') {
  if (value === null || value === undefined || value === '') return fallback
  if (typeof value === 'object') return formatJson(value)
  return String(value)
}

export function getInputSourceLabel(source) {
  const sourceMap = {
    cloud_asr: '云端 ASR',
    browser_speech: '浏览器识别',
    text: '文本输入',
    mock_asr: 'Mock ASR'
  }
  return sourceMap[source] || cleanText(source)
}

export function normalizeParsedCommand(parsed = {}) {
  const confidence = typeof parsed.confidence === 'number' ? parsed.confidence : null
  return {
    ...parsed,
    originalText: parsed.original_text || '',
    normalizedText: parsed.normalized_text || '',
    deviceType: parsed.device_type || null,
    reminderTime: parsed.reminder_time || null,
    reminderContent: parsed.reminder_content || null,
    confidence,
    confidencePercent: confidence === null ? null : Math.round(confidence * 100),
    confidenceLabel: getConfidenceLabel(confidence),
    matchedKeywords: parsed.matched_keywords || [],
    matchType: parsed.match_type || null,
    parseDetail: parsed.parse_detail || {}
  }
}

export function getConfidenceLabel(confidence) {
  if (confidence === null || confidence === undefined) return '-'
  if (confidence >= 0.8) return '高'
  if (confidence >= 0.6) return '中'
  return '低'
}

export function normalizeWeather(weather = {}) {
  const source = weather.source || 'mock'
  return {
    city: weather.city || '本地',
    weather: weather.weather || '--',
    temperature: weather.temperature,
    humidity: weather.humidity,
    windSpeed: weather.wind_speed,
    advice: weather.advice || '暂无建议',
    source,
    sourceLabel: source === 'open_meteo' ? 'Open-Meteo 实时天气' : '本地备用天气',
    updatedAt: weather.updated_at || null
  }
}

export function getDeviceTypeLabel(type) {
  const typeMap = {
    light: '灯光',
    air_conditioner: '空调',
    tv: '电视',
    curtain: '窗帘',
    fan: '排风扇'
  }
  return typeMap[type] || type || '未知设备'
}

export function normalizeDeviceProperties(type, properties = {}) {
  const badges = []
  if (properties.brightness !== undefined) badges.push({ label: '亮度', value: `${properties.brightness}%` })
  if (properties.temperature !== undefined) badges.push({ label: '温度', value: `${properties.temperature}℃` })
  if (properties.volume !== undefined) badges.push({ label: '音量', value: properties.volume })
  if (properties.open_percent !== undefined) badges.push({ label: '开合', value: `${properties.open_percent}%` })
  if (properties.speed !== undefined) badges.push({ label: '风速', value: properties.speed })
  if (properties.mode !== undefined) badges.push({ label: '模式', value: properties.mode })
  if (properties.fan_speed !== undefined) badges.push({ label: '风量', value: properties.fan_speed })
  if (properties.channel !== undefined) badges.push({ label: '频道', value: properties.channel })
  if (properties.color_temperature !== undefined) badges.push({ label: '色温', value: properties.color_temperature })

  if (!badges.length && type) {
    badges.push({ label: '类型', value: getDeviceTypeLabel(type) })
  }
  return badges
}

export function formatDeviceState(state = {}) {
  if (!state || typeof state !== 'object') return '无状态数据'
  const parts = []
  if (state.is_on !== undefined) parts.push(`开关：${state.is_on ? '开启' : '关闭'}`)
  if (state.is_online !== undefined) parts.push(`在线：${state.is_online ? '在线' : '离线'}`)
  const properties = state.properties || {}
  normalizeDeviceProperties(null, properties).forEach((item) => {
    parts.push(`${item.label}：${item.value}`)
  })
  return parts.length ? parts.join('，') : JSON.stringify(state)
}

export function formatDateTime(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export function summarizeCommandExecution(executionResult = {}) {
  if (!executionResult || typeof executionResult !== 'object') return '无执行结果'
  const data = executionResult.data || executionResult
  if (data.is_batch) {
    return `批量执行：成功 ${data.success_count ?? 0} 条，失败 ${data.failed_count ?? 0} 条`
  }
  const result = data.result || data

  if (result.device) {
    const device = normalizeDevice(result.device)
    return `${device.roomName || ''}${device.name || '设备'}：${device.isOn ? '开启' : '关闭'}`
  }
  if (result.before_state || result.after_state) {
    return `状态变化：${formatDeviceState(result.after_state || {})}`
  }
  if (result.devices) {
    return `查询到 ${result.devices.length} 台设备`
  }
  if (result.reminder) {
    return `提醒：${result.reminder.title || result.reminder.reminder_content || '已创建'}`
  }
  if (result.weather) {
    return `${result.weather.city || '本地'}天气：${result.weather.weather || '--'}`
  }
  if (result.scene) {
    return `${result.scene.name || '场景'}已执行，影响 ${(result.changes || []).length} 台设备`
  }
  if (result.changes) {
    return `影响 ${result.changes.length} 台设备`
  }
  return JSON.stringify(result)
}

export function formatJson(value) {
  if (value === null || value === undefined) return '无'
  if (typeof value === 'string') return value
  return JSON.stringify(value, null, 2)
}
