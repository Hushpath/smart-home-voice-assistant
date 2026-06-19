export const LOW_CONFIDENCE_THRESHOLD = 0.6

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
      confidence_breakdown: parseDetail.confidence_breakdown,
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
  if (confidence >= LOW_CONFIDENCE_THRESHOLD) return '中'
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
    desk_lamp: '台灯',
    bedside_lamp: '床头灯',
    light: '灯光',
    air_conditioner: '空调',
    tv: '电视',
    curtain: '窗帘',
    fan: '排风扇',
    robot_vacuum: '扫地机器人',
    speaker: '音箱',
    humidifier: '加湿器',
    air_purifier: '空气净化器',
    smart_plug: '智能插座',
    fridge: '冰箱',
    smoke_sensor: '烟雾传感器'
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
  if (properties.humidity_target !== undefined) badges.push({ label: '目标湿度', value: `${properties.humidity_target}%` })
  if (properties.battery !== undefined) badges.push({ label: '电量', value: `${properties.battery}%` })
  if (properties.air_quality !== undefined) badges.push({ label: '空气质量', value: properties.air_quality })
  if (properties.power_watt !== undefined) badges.push({ label: '功率', value: `${properties.power_watt}W` })
  if (properties.status !== undefined) badges.push({ label: '状态', value: properties.status })

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

export function buildAssistantSpeech(commandResult = {}) {
  if (!commandResult || typeof commandResult !== 'object') return ''
  const data = commandResult.data || commandResult
  if (data.is_batch || data.isBatch) {
    const subResults = data.sub_results || data.subResults || []
    const sentences = subResults
      .map((item) => buildAssistantSpeechForSingle(item))
      .filter(Boolean)
    if (sentences.length) return joinSpeechSentences(sentences)
    return `已为你处理 ${data.command_count ?? data.commandCount ?? 0} 条指令`
  }
  return buildAssistantSpeechForSingle(data)
}

function buildAssistantSpeechForSingle(item = {}) {
  if (!item || typeof item !== 'object') return ''
  if (item.success === false) return buildFailureSpeech(item)

  const result = item.result || item
  const parsed = item.parsed || {}
  const intent = parsed.intent
  const deviceName = getAssistantDeviceName(item, result, parsed)
  const deviceAfter = item.device_after || item.deviceAfter || result.after_state || result.afterState || {}
  const properties = deviceAfter.properties || result.device?.properties || {}

  if (intent === 'turn_on') return `已为你打开${deviceName}`
  if (intent === 'turn_off') return `已为你关闭${deviceName}`
  if (intent === 'set_temperature') {
    const value = parsed.value ?? properties.temperature
    return `已将${deviceName}调到${value}度`
  }
  if (intent === 'set_brightness') {
    const value = parsed.value ?? properties.brightness
    return `已将${deviceName}亮度调到${value}%`
  }
  if (intent === 'set_volume') {
    const value = parsed.value ?? properties.volume
    return `已将${deviceName}音量调到${value}`
  }
  if (intent === 'run_scene') {
    const scene = item.scene || result.scene || {}
    return `已为你开启${scene.name || parsed.scene || '场景'}`
  }
  if (intent === 'create_reminder') {
    const reminder = item.reminder || result.reminder || {}
    const content = parsed.reminderContent || parsed.reminder_content || reminder.title || reminder.reminder_content || '这件事'
    const timeText = getReminderSpeechTime(parsed, reminder)
    return timeText ? `${timeText}会提醒你${content}` : `会提醒你${content}`
  }
  if (intent === 'query_weather') {
    const weather = item.weather || result.weather || {}
    const temperature = weather.temperature !== undefined ? `，${weather.temperature}度` : ''
    return `${weather.city || parsed.city || '本地'}今天${weather.weather || '天气信息已更新'}${temperature}`
  }
  if (intent === 'query_status' && result.devices) {
    return `查询到${result.devices.length}台设备`
  }

  const summary = summarizeCommandExecution(item)
  return summary === '无执行结果' ? item.message || '' : summary
}

function buildFailureSpeech(item = {}) {
  const text = cleanText(item.text || item.parsed?.originalText || item.parsed?.normalizedText || '这条指令', '')
  const code = item.code || item.error_code
  const message = cleanText(item.message || item.error_message, '')
  if (['ROOM_NOT_FOUND', 'DEVICE_NOT_FOUND', 'AMBIGUOUS_SUB_COMMAND'].includes(code)) {
    return `${text}没有执行成功，请检查房间或设备名称`
  }
  return message ? `${text}没有执行成功，${message}` : `${text}没有执行成功`
}

function getAssistantDeviceName(item = {}, result = {}, parsed = {}) {
  const device = result.device || item.affectedDevices?.[0] || item.affected_devices?.[0] || {}
  const name = cleanText(device.name, '')
  const roomName = cleanText(device.room_name || device.roomName || parsed.room, '')
  if (name && roomName && !name.includes(roomName)) return `${roomName}${name}`
  if (name) return name
  return `${roomName}${getAssistantDeviceTypeLabel(parsed.deviceType || parsed.device_type)}`
}

function getAssistantDeviceTypeLabel(type) {
  const typeMap = {
    desk_lamp: '台灯',
    bedside_lamp: '床头灯',
    light: '灯',
    air_conditioner: '空调',
    tv: '电视',
    curtain: '窗帘',
    fan: '排风扇',
    robot_vacuum: '扫地机器人',
    speaker: '音箱',
    humidifier: '加湿器',
    air_purifier: '空气净化器',
    smart_plug: '智能插座',
    fridge: '冰箱',
    smoke_sensor: '烟雾传感器'
  }
  return typeMap[type] || getDeviceTypeLabel(type)
}

function getReminderSpeechTime(parsed = {}, reminder = {}) {
  const extracted = extractReminderTimeText(parsed)
  if (extracted) return extracted
  const value = parsed.reminderTime || parsed.reminder_time || reminder.remind_time
  if (!value) return ''
  const timeMatch = String(value).match(/(\d{1,2}):(\d{2})/)
  if (!timeMatch) return String(value)
  return formatSpeechClock(Number(timeMatch[1]), Number(timeMatch[2]))
}

function extractReminderTimeText(parsed = {}) {
  const content = parsed.reminderContent || parsed.reminder_content
  const source = cleanText(parsed.originalText || parsed.original_text || parsed.normalizedText || parsed.normalized_text, '')
  if (!content || !source || !source.includes(content)) return ''
  const beforeContent = source.split(content)[0]
    .replace(/.*?提醒我/, '')
    .replace(/^(请|帮我|麻烦|到时候|在)/, '')
    .trim()
  return beforeContent || ''
}

function formatSpeechClock(hour, minute) {
  const period =
    hour >= 18 ? '晚上' :
      hour >= 12 ? '下午' :
        hour >= 6 ? '早上' : '凌晨'
  const displayHour = hour > 12 ? hour - 12 : hour
  const minuteText = minute ? `${numberToChinese(minute)}分` : ''
  return `${period}${numberToChinese(displayHour)}点${minuteText}`
}

function numberToChinese(value) {
  const digits = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']
  if (value <= 10) return value === 10 ? '十' : digits[value]
  if (value < 20) return `十${digits[value - 10]}`
  const ten = Math.floor(value / 10)
  const one = value % 10
  return `${digits[ten]}十${one ? digits[one] : ''}`
}

function joinSpeechSentences(sentences = []) {
  return sentences
    .map((sentence) => String(sentence).replace(/[。.!！]+$/g, ''))
    .filter(Boolean)
    .join('。')
}

export function buildCommandResultDisplay(commandResult = {}) {
  if (!commandResult || typeof commandResult !== 'object') return emptyCommandDisplay()
  const data = commandResult.data || commandResult
  if (data.is_batch || data.isBatch) return buildBatchDisplay(data)
  return buildSingleDisplay(data)
}

function buildBatchDisplay(data = {}) {
  const subResults = data.sub_results || data.subResults || []
  const successCount = data.success_count ?? data.successCount ?? subResults.filter((item) => item.success).length
  const failedCount = data.failed_count ?? data.failedCount ?? subResults.filter((item) => item.success === false).length
  const commandCount = data.command_count ?? data.commandCount ?? subResults.length
  const items = subResults.map((item) => {
    const display = buildSingleDisplay(item)
    return {
      index: item.index,
      success: item.success !== false,
      sourceText: cleanText(item.text || item.parsed?.originalText || item.parsed?.normalizedText, ''),
      title: display.title,
      detail: display.details.map((detail) => `${detail.label} ${detail.value}`).join(' · ') || cleanText(item.message, ''),
      message: cleanText(item.message, '')
    }
  })
  const title = failedCount
    ? `已完成 ${successCount} 条，${failedCount} 条未完成`
    : `已完成 ${commandCount} 条指令`
  return {
    title,
    details: [
      { label: '指令总数', value: `${commandCount} 条` },
      { label: '成功', value: `${successCount} 条` },
      { label: '未完成', value: `${failedCount} 条`, tone: failedCount ? 'danger' : '' }
    ],
    meta: [{ label: '识别类型', value: '批量指令' }],
    changes: [],
    noChangeText: '',
    batchItems: items
  }
}

function buildSingleDisplay(item = {}) {
  if (!item || typeof item !== 'object') return emptyCommandDisplay()
  if (item.success === false) return buildFailedDisplay(item)

  const result = item.result || item
  const parsed = item.parsed || {}
  const intent = parsed.intent
  const details = []
  const deviceName = getAssistantDeviceName(item, result, parsed)
  const deviceBefore = item.device_before || item.deviceBefore || result.before_state || result.beforeState || null
  const deviceAfter = item.device_after || item.deviceAfter || result.after_state || result.afterState || null
  const changes = buildStateChangeRows(deviceBefore, deviceAfter)
  const title = buildDisplayTitle(item, result, parsed, deviceName)

  if (['turn_on', 'turn_off', 'set_temperature', 'set_brightness', 'set_volume'].includes(intent)) {
    addDetail(details, '设备', deviceName)
    addDeviceStateDetails(details, intent, deviceAfter, result.device?.properties || {})
  } else if (intent === 'query_status') {
    const devices = result.devices || []
    addDetail(details, '范围', parsed.room || '全部房间')
    addDetail(details, '设备数量', `${devices.length} 台`)
    addDetail(details, '设备', compactDeviceNames(devices))
  } else if (intent === 'run_scene') {
    const scene = item.scene || result.scene || {}
    const changesCount = (result.changes || []).length
    addDetail(details, '场景', scene.name || parsed.scene)
    addDetail(details, '影响设备', `${changesCount} 台`)
    addDetail(details, '设备', compactDeviceNames((result.changes || []).map((change) => change.device).filter(Boolean)))
  } else if (intent === 'create_reminder') {
    const reminder = item.reminder || result.reminder || {}
    addDetail(details, '内容', parsed.reminderContent || parsed.reminder_content || reminder.title || reminder.reminder_content)
    addDetail(details, '时间', formatReminderDisplayTime(parsed, reminder))
  } else if (intent === 'query_weather') {
    const weather = item.weather || result.weather || {}
    addDetail(details, '城市', weather.city || parsed.city || '本地')
    addDetail(details, '天气', weather.weather)
    addDetail(details, '温度', weather.temperature !== undefined ? `${weather.temperature} 度` : '')
    addDetail(details, '湿度', weather.humidity !== undefined ? `${weather.humidity}%` : '')
    addDetail(details, '建议', weather.advice)
  } else {
    addDetail(details, '结果', summarizeCommandExecution(item))
  }

  return {
    title,
    details,
    meta: buildResultMeta(parsed),
    changes,
    noChangeText: !changes.length && (deviceBefore || deviceAfter) ? '设备原本已是目标状态' : '',
    batchItems: []
  }
}

function buildFailedDisplay(item = {}) {
  const parsed = item.parsed || {}
  const text = cleanText(item.text || parsed.originalText || parsed.normalizedText || '这条指令', '')
  return {
    title: text ? `${text}没有执行成功` : '指令没有执行成功',
    details: [{ label: '原因', value: cleanText(item.message || item.error_message || '请检查指令内容', '') }],
    meta: buildResultMeta(parsed),
    changes: [],
    noChangeText: '',
    batchItems: []
  }
}

function buildDisplayTitle(item = {}, result = {}, parsed = {}, deviceName = '') {
  const intent = parsed.intent
  const deviceAfter = item.device_after || item.deviceAfter || result.after_state || result.afterState || {}
  const properties = deviceAfter.properties || result.device?.properties || {}
  if (intent === 'turn_on') return `已打开${deviceName}`
  if (intent === 'turn_off') return `已关闭${deviceName}`
  if (intent === 'set_temperature') return `已将${deviceName}调到 ${parsed.value ?? properties.temperature} 度`
  if (intent === 'set_brightness') return `已将${deviceName}亮度调到 ${parsed.value ?? properties.brightness}%`
  if (intent === 'set_volume') return `已将${deviceName}音量调到 ${parsed.value ?? properties.volume}`
  if (intent === 'query_status') return `${parsed.room || '全部房间'}设备状态已查询`
  if (intent === 'run_scene') {
    const scene = item.scene || result.scene || {}
    return `${scene.name || parsed.scene || '场景'}已执行，影响 ${(result.changes || []).length} 台设备`
  }
  if (intent === 'create_reminder') {
    const reminder = item.reminder || result.reminder || {}
    const content = parsed.reminderContent || parsed.reminder_content || reminder.title || reminder.reminder_content || '提醒'
    return `已设置提醒：${content}`
  }
  if (intent === 'query_weather') {
    const weather = item.weather || result.weather || {}
    const temperature = weather.temperature !== undefined ? `，${weather.temperature} 度` : ''
    return `${weather.city || parsed.city || '本地'}今天${weather.weather || '天气已更新'}${temperature}`
  }
  return summarizeCommandExecution(item)
}

function buildResultMeta(parsed = {}) {
  const meta = []
  addDetail(meta, '识别类型', getIntentLabel(parsed.intent))
  addDetail(meta, '位置', parsed.room)
  const deviceType = parsed.deviceType || parsed.device_type
  if (deviceType) addDetail(meta, '设备', getAssistantDeviceTypeLabel(deviceType))
  if (parsed.confidence !== null && parsed.confidence !== undefined) {
    addDetail(meta, '置信度', `${parsed.confidenceLabel || getConfidenceLabel(parsed.confidence)} ${Math.round(parsed.confidence * 100)}%`)
  }
  return meta
}

function addDeviceStateDetails(details, intent, state = {}, fallbackProperties = {}) {
  const properties = state?.properties || fallbackProperties || {}
  if (state?.is_on !== undefined) addDetail(details, '开关', state.is_on ? '开启' : '关闭')
  if (intent === 'set_temperature' || properties.temperature !== undefined) addDetail(details, '温度', formatPropertyValue('temperature', properties.temperature))
  if (intent === 'set_brightness' || properties.brightness !== undefined) addDetail(details, '亮度', formatPropertyValue('brightness', properties.brightness))
  if (intent === 'set_volume' || properties.volume !== undefined) addDetail(details, '音量', formatPropertyValue('volume', properties.volume))
  addDetail(details, '模式', properties.mode)
  addDetail(details, '风量', properties.fan_speed)
  addDetail(details, '频道', properties.channel)
  addDetail(details, '开合', formatPropertyValue('open_percent', properties.open_percent))
  addDetail(details, '风速', properties.speed)
  addDetail(details, '色温', properties.color_temperature)
}

function buildStateChangeRows(before = null, after = null) {
  if (!before || !after) return []
  const rows = []
  addChange(rows, '开关', before.is_on, after.is_on, (value) => value ? '开启' : '关闭')
  addChange(rows, '在线', before.is_online, after.is_online, (value) => value ? '在线' : '离线')
  const beforeProperties = before.properties || {}
  const afterProperties = after.properties || {}
  const keys = Array.from(new Set([...Object.keys(beforeProperties), ...Object.keys(afterProperties)]))
  keys.forEach((key) => {
    addChange(rows, getPropertyLabel(key), beforeProperties[key], afterProperties[key], (value) => formatPropertyValue(key, value))
  })
  return rows
}

function addChange(rows, label, before, after, formatter = (value) => value) {
  if (before === after || before === undefined && after === undefined) return
  rows.push({
    label,
    before: before === undefined ? '未设置' : formatter(before),
    after: after === undefined ? '未设置' : formatter(after)
  })
}

function addDetail(list, label, value, tone = '') {
  if (value === null || value === undefined || value === '' || value === '-') return
  list.push({ label, value, tone })
}

function compactDeviceNames(devices = []) {
  const names = devices
    .map((device) => {
      const roomName = cleanText(device.room_name || device.roomName, '')
      const name = cleanText(device.name, '')
      if (roomName && name && !name.includes(roomName)) return `${roomName}${name}`
      return name
    })
    .filter(Boolean)
  if (!names.length) return ''
  if (names.length <= 3) return names.join('、')
  return `${names.slice(0, 3).join('、')} 等 ${names.length} 台`
}

function formatReminderDisplayTime(parsed = {}, reminder = {}) {
  const extracted = extractReminderTimeText(parsed)
  if (extracted) return extracted
  const value = parsed.reminderTime || parsed.reminder_time || reminder.remind_time
  return value ? formatDateTime(value) : ''
}

function formatPropertyValue(key, value) {
  if (value === null || value === undefined || value === '') return ''
  if (key === 'temperature') return `${value}℃`
  if (key === 'brightness' || key === 'open_percent') return `${value}%`
  return value
}

function getPropertyLabel(key) {
  const labels = {
    temperature: '温度',
    brightness: '亮度',
    volume: '音量',
    open_percent: '开合',
    speed: '风速',
    mode: '模式',
    fan_speed: '风量',
    channel: '频道',
    color_temperature: '色温'
  }
  return labels[key] || key
}

function getIntentLabel(intent) {
  const labels = {
    turn_on: '打开设备',
    turn_off: '关闭设备',
    set_temperature: '调节温度',
    set_brightness: '调节亮度',
    set_volume: '调节音量',
    query_status: '查询状态',
    run_scene: '执行场景',
    create_reminder: '创建提醒',
    query_weather: '查询天气'
  }
  return labels[intent] || intent
}

function emptyCommandDisplay() {
  return {
    title: '暂无执行结果',
    details: [],
    meta: [],
    changes: [],
    noChangeText: '',
    batchItems: []
  }
}

export function summarizeCommandExecution(executionResult = {}) {
  if (!executionResult || typeof executionResult !== 'object') return '无执行结果'
  const data = executionResult.data || executionResult
  if (data.is_batch || data.isBatch) {
    return `批量执行：成功 ${data.success_count ?? data.successCount ?? 0} 条，失败 ${data.failed_count ?? data.failedCount ?? 0} 条`
  }
  const result = data.result || data
  const deviceBefore = data.device_before || data.deviceBefore || result.before_state || result.beforeState
  const deviceAfter = data.device_after || data.deviceAfter || result.after_state || result.afterState
  const reminder = data.reminder || result.reminder
  const weather = data.weather || result.weather
  const scene = data.scene || result.scene
  const changes = data.changes || result.changes || []

  if (result.device) {
    const device = normalizeDevice(result.device)
    const deviceName = device.roomName && !String(device.name || '').includes(device.roomName)
      ? `${device.roomName}${device.name || '设备'}`
      : device.name || '设备'
    return `${deviceName}：${formatDeviceState(deviceAfter || {
      is_on: result.device.is_on,
      properties: result.device.properties || {}
    })}`
  }
  if (deviceBefore || deviceAfter) {
    return `状态变化：${formatDeviceState(deviceAfter || {})}`
  }
  if (result.devices) {
    return `查询到 ${result.devices.length} 台设备`
  }
  if (reminder) {
    const title = reminder.title || reminder.reminder_content || '已创建'
    return reminder.remind_time ? `提醒：${title}，时间 ${formatDateTime(reminder.remind_time)}` : `提醒：${title}`
  }
  if (weather) {
    const temperature = weather.temperature !== undefined ? `，${weather.temperature}℃` : ''
    return `${weather.city || '本地'}天气：${weather.weather || '--'}${temperature}`
  }
  if (scene) {
    return `${scene.name || '场景'}已执行，影响 ${changes.length} 台设备`
  }
  if (changes.length) {
    return `影响 ${changes.length} 台设备`
  }
  if (result !== data && Object.keys(result).length) return JSON.stringify(result)
  return data.message || '无执行结果'
}

export function formatJson(value) {
  if (value === null || value === undefined) return '无'
  if (typeof value === 'string') return value
  return JSON.stringify(value, null, 2)
}
