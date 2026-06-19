<template>
  <div class="dashboard-page" v-loading="loading">
    <section class="dashboard-hero live-hero compact-hero">
      <div>
        <p class="panel-kicker">Control center</p>
        <h2>家庭运行概览</h2>
      </div>
      <div class="dashboard-status-strip">
        <div>
          <span>在线率</span>
          <strong>{{ onlineRate }}%</strong>
        </div>
        <div>
          <span>已配置场景</span>
          <strong>{{ scenes.length }}</strong>
        </div>
        <div>
          <span>最近日志</span>
          <strong>{{ recentLogs.length }}</strong>
        </div>
      </div>
    </section>

    <section class="dashboard-stat-grid">
      <div class="stat-card" v-for="item in stats" :key="item.label">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.note }}</small>
      </div>
    </section>

    <section class="dashboard-lower-grid">
      <div class="dashboard-side-stack">
        <article class="weather-card">
          <div class="weather-card-main">
            <div class="weather-card-head">
              <div>
                <p class="panel-kicker">Weather</p>
                <h3>{{ weather.city }} · {{ weather.weather }}</h3>
              </div>
              <el-select
                v-model="selectedWeatherCity"
                class="weather-city-select"
                size="small"
                filterable
                allow-create
                default-first-option
                popper-class="weather-city-popper"
                :reserve-keyword="false"
                :loading="weatherLoading"
                @change="loadWeather"
              >
                <el-option v-for="city in weatherCityOptions" :key="city" :label="city" :value="city" />
              </el-select>
            </div>
            <p>{{ weather.advice }}</p>
            <small class="weather-source-note">{{ weather.sourceLabel }}</small>
          </div>
          <div class="weather-meter">
            <strong>{{ weather.temperature ?? '--' }}℃</strong>
            <span>湿度 {{ weather.humidity ?? '--' }}%</span>
            <span>风速 {{ weather.windSpeed ?? '--' }} km/h</span>
          </div>
        </article>

        <article class="scene-shortcuts">
          <p class="panel-kicker">Scene shortcuts</p>
          <h3>快捷场景入口</h3>
          <div class="scene-chip-list">
            <button
              v-for="scene in scenes"
              :key="scene.id"
              :disabled="runningSceneId === scene.id"
              @click="runDashboardScene(scene)"
            >
              {{ runningSceneId === scene.id ? '执行中...' : scene.name }}
            </button>
          </div>
        </article>
      </div>

      <article class="device-insight-card">
        <p class="panel-kicker">Device mix</p>
        <h3>设备类型分布</h3>
        <div class="device-type-list">
          <div v-for="item in deviceTypeStats" :key="item.type">
            <span>{{ item.label }}</span>
            <strong>{{ item.count }}</strong>
          </div>
          <el-empty v-if="!deviceTypeStats.length" description="暂无设备数据" />
        </div>
      </article>

      <article class="home-floor-card">
        <div class="home-floor-head">
          <div>
            <p class="panel-kicker">Home plan</p>
            <h3>家庭平面总览</h3>
          </div>
          <div class="floor-legend">
            <span><i class="on"></i>运行</span>
            <span><i></i>关闭</span>
          </div>
        </div>
        <div class="floor-plan-canvas" aria-label="家庭平面总览">
          <div
            v-for="room in floorPlanRooms"
            :key="room.key"
            class="floor-room"
            :class="{ active: getRoomStats(room.name).onCount, empty: !getRoomStats(room.name).total }"
            :style="room.style"
          >
            <div class="floor-room-info">
              <strong>{{ room.name }}</strong>
              <span>{{ getRoomStats(room.name).onCount }} / {{ getRoomStats(room.name).total }} 运行</span>
            </div>
          </div>
          <div
            v-for="device in floorPlanDevices"
            :key="device.id"
            class="floor-device-dot"
            :class="{ on: device.isOn, offline: !device.isOnline }"
            :style="{ left: `${device.x}%`, top: `${device.y}%` }"
            :title="`${device.roomName || ''}${device.name || device.typeLabel}`"
          >
            <span>{{ getDevicePlanLabel(device) }}</span>
          </div>
        </div>
      </article>
    </section>

    <section class="dashboard-bottom-grid">
      <article class="recent-log-card">
        <div class="section-head">
          <div>
            <p class="panel-kicker">Recent activity</p>
            <h3>最近指令日志</h3>
          </div>
        </div>
        <div v-if="recentLogs.length" class="recent-log-list dashboard-log-list">
          <article v-for="log in recentLogs" :key="log.id">
            <span :class="{ failed: !log.success }">{{ log.success ? '成功' : '失败' }}</span>
            <strong>{{ log.rawCommand || '空指令' }}</strong>
            <small>{{ summarizeCommandExecution(log.executionResult) }}</small>
          </article>
        </div>
        <el-empty v-else description="暂无指令日志" />
      </article>

      <article class="device-health-card">
        <p class="panel-kicker">Device health</p>
        <h3>设备健康摘要</h3>
        <div class="health-rows">
          <div>
            <span>离线设备</span>
            <strong>{{ dashboard.offlineDeviceCount }}</strong>
          </div>
          <div>
            <span>开启设备</span>
            <strong>{{ dashboard.onDeviceCount }}</strong>
          </div>
          <div>
            <span>关闭设备</span>
            <strong>{{ offDeviceCount }}</strong>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getCommandLogsApi } from '../api/command'
import { getDashboardApi } from '../api/dashboard'
import { getDevicesApi } from '../api/device'
import { getScenesApi, runSceneApi } from '../api/scene'
import { getWeatherApi } from '../api/weather'
import {
  normalizeCommandLog,
  normalizeDashboard,
  normalizeDevice,
  normalizeScene,
  normalizeWeather,
  summarizeCommandExecution
} from '../utils/normalizers'

const loading = ref(false)
const runningSceneId = ref(null)
const dashboard = reactive(normalizeDashboard())
const weather = reactive(normalizeWeather())
const scenes = ref([])
const recentLogs = ref([])
const devices = ref([])
const selectedWeatherCity = ref('广州')
const weatherLoading = ref(false)
const weatherCityOptions = ['北京', '上海', '广州', '深圳', '杭州', '南京', '成都', '重庆', '西安', '武汉', '本地']

const stats = computed(() => [
  { label: '房间数量', value: dashboard.roomCount, note: '当前家庭空间' },
  { label: '设备总数', value: dashboard.deviceCount, note: '已接入设备' },
  { label: '在线设备', value: dashboard.onlineDeviceCount, note: '可远程控制' },
  { label: '开启设备', value: dashboard.onDeviceCount, note: '正在运行' }
])

const onlineRate = computed(() => {
  if (!dashboard.deviceCount) return 0
  return Math.round((dashboard.onlineDeviceCount / dashboard.deviceCount) * 100)
})

const offDeviceCount = computed(() => Math.max(dashboard.deviceCount - dashboard.onDeviceCount, 0))

const deviceTypeStats = computed(() => {
  const typeMap = new Map()
  devices.value.forEach((device) => {
    const key = device.type || 'unknown'
    const current = typeMap.get(key) || { type: key, label: device.typeLabel || key, count: 0 }
    current.count += 1
    typeMap.set(key, current)
  })
  return Array.from(typeMap.values()).sort((a, b) => b.count - a.count)
})

async function loadDashboard() {
  loading.value = true
  try {
    const [dashboardData, weatherData, sceneData, logData, deviceData] = await Promise.all([
      getDashboardApi(),
      getWeatherApi(selectedWeatherCity.value),
      getScenesApi(),
      getCommandLogsApi(),
      getDevicesApi()
    ])
    Object.assign(dashboard, normalizeDashboard(dashboardData))
    Object.assign(weather, normalizeWeather(weatherData))
    scenes.value = sceneData.map(normalizeScene)
    recentLogs.value = logData.map(normalizeCommandLog).slice(0, 3)
    devices.value = deviceData.map(normalizeDevice)
  } finally {
    loading.value = false
  }
}

async function loadWeather(city = selectedWeatherCity.value) {
  selectedWeatherCity.value = city || '本地'
  weatherLoading.value = true
  try {
    const weatherData = await getWeatherApi(selectedWeatherCity.value)
    Object.assign(weather, normalizeWeather(weatherData))
  } finally {
    weatherLoading.value = false
  }
}

async function runDashboardScene(scene) {
  runningSceneId.value = scene.id
  try {
    await runSceneApi(scene.id)
    ElMessage.success(`${scene.name}执行成功`)
    await loadDashboard()
  } finally {
    runningSceneId.value = null
  }
}

onMounted(loadDashboard)

const floorPlanRooms = [
  { key: 'living', name: '客厅', style: { left: '4%', top: '8%', width: '50%', height: '46%' } },
  { key: 'bedroom', name: '卧室', style: { left: '58%', top: '8%', width: '38%', height: '38%' } },
  { key: 'kitchen', name: '厨房', style: { left: '4%', top: '58%', width: '32%', height: '34%' } },
  { key: 'study', name: '书房', style: { left: '40%', top: '55%', width: '56%', height: '37%' } }
]

const floorDeviceSlots = {
  '客厅:light': { x: 30, y: 23 },
  '客厅:air_conditioner': { x: 45, y: 23 },
  '客厅:tv': { x: 30, y: 38 },
  '客厅:curtain': { x: 45, y: 38 },
  '客厅:robot_vacuum': { x: 30, y: 50 },
  '客厅:speaker': { x: 45, y: 50 },
  '卧室:light': { x: 75, y: 22 },
  '卧室:air_conditioner': { x: 90, y: 22 },
  '卧室:curtain': { x: 90, y: 34 },
  '卧室:bedside_lamp': { x: 75, y: 39 },
  '卧室:humidifier': { x: 90, y: 43 },
  '厨房:light': { x: 22, y: 72 },
  '厨房:fan': { x: 31, y: 72 },
  '厨房:fridge': { x: 22, y: 86 },
  '厨房:smoke_sensor': { x: 31, y: 86 },
  '书房:light': { x: 59, y: 69 },
  '书房:air_conditioner': { x: 84, y: 69 },
  '书房:desk_lamp': { x: 59, y: 82 },
  '书房:air_purifier': { x: 84, y: 82 },
  '书房:smart_plug': { x: 72, y: 88 }
}

const roomStats = computed(() => {
  const statsMap = new Map()
  floorPlanRooms.forEach((room) => {
    statsMap.set(room.name, { total: 0, onCount: 0 })
  })
  devices.value.forEach((device) => {
    const roomName = device.roomName || '客厅'
    const current = statsMap.get(roomName) || { total: 0, onCount: 0 }
    current.total += 1
    if (device.isOn) current.onCount += 1
    statsMap.set(roomName, current)
  })
  return statsMap
})

const floorPlanDevices = computed(() =>
  devices.value.map((device, index) => {
    const slot = floorDeviceSlots[`${device.roomName}:${device.type}`] || getFallbackDeviceSlot(device, index)
    return {
      ...device,
      x: slot.x,
      y: slot.y
    }
  })
)

function getRoomStats(roomName) {
  return roomStats.value.get(roomName) || { total: 0, onCount: 0 }
}

function getFallbackDeviceSlot(device, index) {
  const room = floorPlanRooms.find((item) => item.name === device.roomName) || floorPlanRooms[0]
  const left = parseFloat(room.style.left)
  const top = parseFloat(room.style.top)
  const width = parseFloat(room.style.width)
  const height = parseFloat(room.style.height)
  return {
    x: left + width * (0.28 + (index % 3) * 0.2),
    y: top + height * (0.35 + (index % 2) * 0.22)
  }
}

function getDevicePlanLabel(device) {
  const labelMap = {
    desk_lamp: '台灯',
    bedside_lamp: '床头灯',
    light: '灯',
    air_conditioner: '空调',
    tv: '电视',
    curtain: '窗帘',
    fan: '排风扇',
    robot_vacuum: '扫地机',
    speaker: '音箱',
    humidifier: '加湿器',
    air_purifier: '净化器',
    smart_plug: '插座',
    fridge: '冰箱',
    smoke_sensor: '烟感'
  }
  if (labelMap[device.type]) return labelMap[device.type]
  return (device.name || device.typeLabel || '设备').replace(device.roomName || '', '')
}
</script>
