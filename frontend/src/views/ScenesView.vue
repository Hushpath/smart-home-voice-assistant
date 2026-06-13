<template>
  <div class="scenes-page">
    <section class="table-toolbar">
      <div>
        <p class="panel-kicker">Scene automation</p>
        <h2>场景模式</h2>
        <p>场景动作由后端 scene_actions 读取，执行后会批量修改设备状态并写入历史。</p>
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
      <h3>{{ lastRun.scene?.name || '场景' }} 执行结果</h3>
      <div class="scene-change-list">
        <article v-for="(change, index) in lastRun.changes || []" :key="index">
          <strong>{{ change.device?.room_name }}{{ change.device?.name }}</strong>
          <span>{{ formatDeviceState(change.after_state) }}</span>
        </article>
      </div>
    </section>

    <section class="scene-result-panel">
      <div class="section-head">
        <div>
          <p class="panel-kicker">Device refresh</p>
          <h3>执行后设备状态</h3>
        </div>
        <el-button class="refresh-button" :loading="deviceLoading" @click="loadDevices">刷新设备</el-button>
      </div>
      <div v-if="devices.length" class="voice-device-list">
        <article v-for="device in devices" :key="device.id">
          <span>{{ device.roomName || '-' }} · {{ device.typeLabel }}</span>
          <strong>{{ device.name }}</strong>
          <small>{{ device.isOnline ? '在线' : '离线' }} / {{ device.isOn ? '开启' : '关闭' }}</small>
        </article>
      </div>
      <el-empty v-else description="暂无设备状态" />
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getDevicesApi } from '../api/device'
import { getScenesApi, runSceneApi } from '../api/scene'
import SceneCard from '../components/SceneCard.vue'
import { formatDeviceState, normalizeDevice, normalizeScene } from '../utils/normalizers'

const loading = ref(false)
const deviceLoading = ref(false)
const busySceneId = ref(null)
const scenes = ref([])
const devices = ref([])
const lastRun = ref(null)

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
