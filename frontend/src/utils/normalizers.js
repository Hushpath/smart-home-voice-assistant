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
  const parsedResult = log.parsed_result || {}
  return {
    id: log.id,
    userId: log.user_id,
    rawCommand: log.raw_command || '-',
    intent: parsedResult.intent || '-',
    parsedResult,
    executionResult: log.execution_result || null,
    success: Boolean(log.success),
    errorMessage: log.error_message || '',
    createdAt: log.created_at || null
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
  return {
    success: result.success,
    code: result.code,
    message: result.message,
    parsed: data.parsed || null,
    result: data.result || null
  }
}

export function normalizeWeather(weather = {}) {
  return {
    city: weather.city || '本地',
    weather: weather.weather || '--',
    temperature: weather.temperature,
    humidity: weather.humidity,
    advice: weather.advice || '暂无建议'
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
