<template>
  <div class="scenes-page">
    <section class="table-toolbar">
      <div>
        <p class="panel-kicker">Scene automation</p>
        <h2>场景模式</h2>
      </div>
      <el-button class="refresh-button" :loading="loading" @click="loadScenes">刷新场景</el-button>
    </section>

    <section class="scene-grid" v-loading="loading">
      <SceneCard
        v-for="scene in scenes"
        :key="scene.id"
        :scene="scene"
        :busy="busySceneId === scene.id"
        @run="runScene(scene)"
      />
    </section>

    <section v-if="lastRun" class="scene-result-panel">
      <p class="panel-kicker">Last run</p>
      <h3>{{ lastRun.scene?.name || '场景' }}已执行，影响 {{ lastRunRows.length }} 台设备</h3>
      <div v-if="lastRunRows.length" class="scene-change-list">
        <article v-for="row in lastRunRows" :key="row.id || row.name">
          <strong>{{ row.name }}</strong>
          <span>{{ row.summary }}</span>
        </article>
      </div>
      <el-empty v-else description="本次场景没有设备变化" />
    </section>

    <section class="scene-result-panel">
      <div class="section-head">
        <div>
          <p class="panel-kicker">Device refresh</p>
          <h3>{{ lastRun ? '本次影响设备状态' : '执行后设备状态' }}</h3>
        </div>
        <el-button class="refresh-button" :loading="deviceLoading" @click="loadDevices">刷新设备</el-button>
      </div>
      <div v-if="visibleDevices.length" class="voice-device-list">
        <article v-for="device in visibleDevices" :key="device.id">
          <span>{{ device.roomName || '-' }} · {{ device.typeLabel }}</span>
          <strong>{{ device.name }}</strong>
          <small>{{ device.isOnline ? '在线' : '离线' }} / {{ device.isOn ? '开启' : '关闭' }}</small>
        </article>
      </div>
      <el-empty v-else :description="lastRun ? '暂无本次影响设备状态' : '执行场景后显示相关设备状态'" />
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getDevicesApi } from '../api/device'
import { getScenesApi, runSceneApi } from '../api/scene'
import SceneCard from '../components/SceneCard.vue'
import { normalizeDevice, normalizeScene } from '../utils/normalizers'

const loading = ref(false)
const deviceLoading = ref(false)
const busySceneId = ref(null)
const scenes = ref([])
const devices = ref([])
const lastRun = ref(null)

const lastRunRows = computed(() => (lastRun.value?.changes || []).map((change) => {
  const device = change.device || {}
  return {
    id: device.id,
    name: formatDeviceName(device),
    summary: formatSceneDeviceSummary(change.after_state || {}, device)
  }
}))

const affectedDeviceIds = computed(() => new Set(lastRunRows.value.map((row) => row.id).filter(Boolean)))
const visibleDevices = computed(() => {
  if (!lastRun.value) return []
  return devices.value.filter((device) => affectedDeviceIds.value.has(device.id))
})

async function loadScenes() {
  loading.value = true
  try {
    const data = await getScenesApi()
    scenes.value = data.map(normalizeScene)
  } finally {
    loading.value = false
  }
}

async function loadDevices() {
  deviceLoading.value = true
  try {
    const data = await getDevicesApi()
    devices.value = data.map(normalizeDevice)
  } finally {
    deviceLoading.value = false
  }
}

function formatDeviceName(device = {}) {
  const roomName = device.room_name || device.roomName || ''
  const name = device.name || '设备'
  if (roomName && !name.includes(roomName)) return `${roomName}${name}`
  return name
}

function formatSceneDeviceSummary(state = {}, device = {}) {
  const parts = []
  if (state.is_on !== undefined) parts.push(state.is_on ? '已开启' : '已关闭')
  const properties = state.properties || device.properties || {}
  if (properties.mode !== undefined) parts.push(properties.mode)
  if (properties.temperature !== undefined) parts.push(`${properties.temperature}℃`)
  if (properties.fan_speed !== undefined) parts.push(properties.fan_speed)
  if (properties.brightness !== undefined) parts.push(`亮度 ${properties.brightness}%`)
  if (properties.open_percent !== undefined) parts.push(`开合 ${properties.open_percent}%`)
  if (properties.volume !== undefined) parts.push(`音量 ${properties.volume}`)
  if (properties.channel !== undefined) parts.push(properties.channel)
  if (properties.speed !== undefined) parts.push(`风速 ${properties.speed}`)
  if (properties.color_temperature !== undefined) parts.push(properties.color_temperature)
  if (properties.humidity_target !== undefined) parts.push(`湿度 ${properties.humidity_target}%`)
  if (properties.battery !== undefined) parts.push(`电量 ${properties.battery}%`)
  if (properties.air_quality !== undefined) parts.push(`空气 ${properties.air_quality}`)
  if (properties.power_watt !== undefined) parts.push(`功率 ${properties.power_watt}W`)
  if (properties.status !== undefined) parts.push(properties.status)
  return parts.length ? parts.join(' · ') : '状态已更新'
}

async function runScene(scene) {
  busySceneId.value = scene.id
  try {
    lastRun.value = await runSceneApi(scene.id)
    await loadDevices()
    ElMessage.success(`${scene.name}执行成功`)
  } finally {
    busySceneId.value = null
  }
}

onMounted(() => {
  loadScenes()
  loadDevices()
})
</script>
