<template>
  <div class="dashboard-page" v-loading="loading">
    <section class="dashboard-hero live-hero compact-hero">
      <div>
        <p class="panel-kicker">Control center</p>
        <h2>家庭运行概览</h2>
        <p>实时汇总设备、场景、天气和最近指令，适合课堂演示时一屏展示系统状态。</p>
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
              :reserve-keyword="false"
              :loading="weatherLoading"
              @change="loadWeather"
            >
              <el-option v-for="city in weatherCityOptions" :key="city" :label="city" :value="city" />
            </el-select>
          </div>
          <p>{{ weather.advice }}</p>
          <small class="weather-source-note">本地模拟天气数据</small>
        </div>
        <div class="weather-meter">
          <strong>{{ weather.temperature ?? '--' }}℃</strong>
          <span>湿度 {{ weather.humidity ?? '--' }}%</span>
        </div>
      </article>

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

      <article class="scene-shortcuts">
        <p class="panel-kicker">Scene shortcuts</p>
        <h3>快捷场景入口</h3>
        <p>直接执行后端场景联动，执行成功后自动刷新 Dashboard 统计。</p>
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
const selectedWeatherCity = ref('北京')
const weatherLoading = ref(false)
const weatherCityOptions = ['北京', '上海', '广州', '本地']

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
  return Array.from(typeMap.values()).sort((a, b) => b.count - a.count).slice(0, 5)
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
    recentLogs.value = logData.map(normalizeCommandLog).slice(0, 4)
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
</script>
