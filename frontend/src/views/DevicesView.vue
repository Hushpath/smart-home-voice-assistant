<template>
  <div class="devices-page">
    <section class="device-toolbar">
      <div>
        <p class="panel-kicker">Device matrix</p>
        <h2>按房间管理虚拟智能设备</h2>
      </div>
      <div class="toolbar-actions">
        <el-button class="refresh-button" @click="aliasVisible = true">设备别名管理</el-button>
        <el-button class="refresh-button" :loading="loading" @click="loadDevices">刷新设备</el-button>
      </div>
    </section>

    <section class="room-filter">
      <button :class="{ active: selectedRoomId === null }" @click="selectedRoomId = null">全部房间</button>
      <button
        v-for="room in rooms"
        :key="room.id"
        :class="{ active: selectedRoomId === room.id }"
        @click="selectedRoomId = room.id"
      >
        {{ room.name }}
        <small>{{ room.deviceCount }}</small>
      </button>
    </section>

    <el-empty v-if="!loading && !filteredGroups.length" description="暂无设备数据，请确认后端已初始化数据库" />

    <section v-for="group in filteredGroups" :key="group.room.id || group.room.name" class="room-section">
      <div class="room-heading">
        <div>
          <span>{{ group.room.name }}</span>
          <h3>{{ group.devices.length }} 台设备</h3>
        </div>
      </div>

      <div class="device-grid" v-loading="loading">
        <DeviceCard
          v-for="device in group.devices"
          :key="device.id"
          :device="device"
          :busy="busyDeviceId === device.id"
          @toggle="toggleDevice(device, $event)"
          @detail="openDetail(device)"
          @history="openHistory(device)"
          @adjust="openAdjust(device)"
          @alias="openAliasDialog(device)"
        />
      </div>
    </section>

    <section class="room-section alias-overview-section">
      <div class="room-heading">
        <div>
          <span>设备别名</span>
          <h3>{{ aliases.length }} 个别名</h3>
        </div>
      </div>
      <el-empty v-if="!aliasesLoading && !aliases.length" description="暂无设备别名" :image-size="56" />
      <div v-else class="alias-overview-list" v-loading="aliasesLoading">
        <article v-for="alias in aliases" :key="alias.id">
          <strong>{{ alias.alias }}</strong>
          <span>{{ alias.roomName }} · {{ alias.deviceName }}</span>
        </article>
      </div>
    </section>

    <el-drawer v-model="detailVisible" size="520px" direction="rtl" class="history-drawer">
      <template #header>
        <div class="history-header">
          <span>设备详情</span>
          <strong>{{ detailDevice?.roomName }} · {{ detailDevice?.name }}</strong>
        </div>
      </template>

      <div v-loading="detailLoading">
        <article v-if="detailDevice" class="device-detail-card">
          <div class="detail-row">
            <span>设备 ID</span>
            <strong>{{ detailDevice.id }}</strong>
          </div>
          <div class="detail-row">
            <span>设备类型</span>
            <strong>{{ detailDevice.typeLabel }}</strong>
          </div>
          <div class="detail-row">
            <span>所属房间</span>
            <strong>{{ detailDevice.roomName }}</strong>
          </div>
          <div class="detail-row">
            <span>在线状态</span>
            <strong>{{ detailDevice.isOnline ? '在线' : '离线' }}</strong>
          </div>
          <div class="detail-row">
            <span>开关状态</span>
            <strong>{{ detailDevice.isOn ? '开启' : '关闭' }}</strong>
          </div>
          <div class="detail-props">
            <label>关键属性</label>
            <div class="device-props">
              <span v-for="item in detailDevice.propertyBadges" :key="`${item.label}-${item.value}`">
                <small>{{ item.label }}</small>
                <b>{{ item.value }}</b>
              </span>
            </div>
          </div>
          <div class="detail-props">
            <label>原始 properties</label>
            <pre>{{ formatJson(detailDevice.properties) }}</pre>
          </div>
          <small>更新时间：{{ formatDateTime(detailDevice.updatedAt) }}</small>
        </article>
      </div>
    </el-drawer>

    <el-dialog v-model="adjustVisible" :title="`调节 ${adjustDevice?.roomName || ''}${adjustDevice?.name || ''}`" width="480px">
      <el-form v-if="adjustDevice" label-position="top">
        <el-form-item v-for="control in adjustControls" :key="control.field" :label="control.label">
          <el-slider
            v-if="control.inputType === 'slider'"
            v-model="adjustValues[control.field]"
            :min="control.min"
            :max="control.max"
            show-input
          />
          <el-select v-else v-model="adjustValues[control.field]" style="width: 100%">
            <el-option v-for="option in control.options" :key="option" :label="option" :value="option" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustVisible = false">取消</el-button>
        <el-button type="primary" :loading="adjustSaving" @click="saveAdjustment">保存调节</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="historyVisible" size="520px" direction="rtl" class="history-drawer">
      <template #header>
        <div class="history-header">
          <span>设备历史记录</span>
          <strong>{{ currentDevice?.roomName }} · {{ currentDevice?.name }}</strong>
        </div>
      </template>

      <div v-loading="historyLoading">
        <el-empty v-if="!historyLoading && !historyItems.length" description="暂无状态变更历史" />
        <el-timeline v-else>
          <el-timeline-item
            v-for="item in historyItems"
            :key="item.id"
            :timestamp="formatDateTime(item.createdAt)"
            placement="top"
          >
            <article class="history-card">
              <div class="history-meta">
                <span>{{ sourceLabel(item.changeSource) }}</span>
                <small>#{{ item.id }}</small>
              </div>
              <div class="history-state">
                <label>修改前</label>
                <p>{{ formatDeviceState(item.beforeState) }}</p>
              </div>
              <div class="history-state after">
                <label>修改后</label>
                <p>{{ formatDeviceState(item.afterState) }}</p>
              </div>
            </article>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-drawer>

    <DeviceAliasDialog
      v-model="aliasVisible"
      v-model:saving="aliasSaving"
      v-model:deleting-id="aliasDeletingId"
      :devices="devices"
      :aliases="aliases"
      :loading="aliasesLoading"
      :initial-device-id="selectedAliasDeviceId"
      @refresh="refreshAliases"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getDeviceApi, getDeviceHistoryApi, getDevicesApi, getRoomsApi, updateDeviceStateApi } from '../api/device'
import { getDeviceAliasesApi } from '../api/personalization'
import DeviceAliasDialog from '../components/DeviceAliasDialog.vue'
import DeviceCard from '../components/DeviceCard.vue'
import {
  formatDateTime,
  formatDeviceState,
  formatJson,
  normalizeDevice,
  normalizeDeviceAlias,
  normalizeDeviceHistory,
  normalizeRoom
} from '../utils/normalizers'

const loading = ref(false)
const historyLoading = ref(false)
const busyDeviceId = ref(null)
const selectedRoomId = ref(null)
const rooms = ref([])
const devices = ref([])
const historyVisible = ref(false)
const historyItems = ref([])
const currentDevice = ref(null)
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailDevice = ref(null)
const adjustVisible = ref(false)
const adjustSaving = ref(false)
const adjustDevice = ref(null)
const adjustControls = ref([])
const adjustValues = ref({})
const aliases = ref([])
const aliasesLoading = ref(false)
const aliasVisible = ref(false)
const aliasSaving = ref(false)
const aliasDeletingId = ref(null)
const selectedAliasDeviceId = ref(null)

const filteredDevices = computed(() => {
  if (selectedRoomId.value === null) return devices.value
  return devices.value.filter((device) => device.roomId === selectedRoomId.value)
})

const filteredGroups = computed(() => {
  const roomMap = new Map()
  rooms.value.forEach((room) => {
    if (selectedRoomId.value === null || selectedRoomId.value === room.id) {
      roomMap.set(room.id, { room, devices: [] })
    }
  })

  filteredDevices.value.forEach((device) => {
    const groupKey = device.roomId || `room-${device.roomName || 'unknown'}`
    if (!roomMap.has(groupKey)) {
      roomMap.set(groupKey, {
        room: { id: device.roomId, name: device.roomName || '未分配房间' },
        devices: []
      })
    }
    roomMap.get(groupKey).devices.push(device)
  })

  return Array.from(roomMap.values()).filter((group) => group.devices.length > 0)
})

async function loadDevices() {
  loading.value = true
  try {
    const [roomData, deviceData] = await Promise.all([
      getRoomsApi(),
      getDevicesApi(),
      loadAliases()
    ])
    rooms.value = roomData.map(normalizeRoom)
    devices.value = deviceData.map((device) => withAliases(normalizeDevice(device)))
  } finally {
    loading.value = false
  }
}

async function loadAliases() {
  aliasesLoading.value = true
  try {
    const data = await getDeviceAliasesApi()
    aliases.value = data.map(normalizeDeviceAlias)
    return aliases.value
  } finally {
    aliasesLoading.value = false
  }
}

async function refreshAliases() {
  await loadAliases()
  devices.value = devices.value.map(withAliases)
}

function withAliases(device) {
  return {
    ...device,
    aliases: aliases.value.filter((alias) => alias.deviceId === device.id).map((alias) => alias.alias)
  }
}

function openAliasDialog(device) {
  selectedAliasDeviceId.value = device?.id || null
  aliasVisible.value = true
}

async function toggleDevice(device, nextState) {
  busyDeviceId.value = device.id
  try {
    await updateDeviceStateApi(device.id, { is_on: nextState })
    ElMessage.success(`${device.roomName}${device.name}已${nextState ? '开启' : '关闭'}`)
    await loadDevices()
  } finally {
    busyDeviceId.value = null
  }
}

async function openHistory(device) {
  currentDevice.value = device
  historyVisible.value = true
  historyLoading.value = true
  try {
    const data = await getDeviceHistoryApi(device.id)
    historyItems.value = data.map(normalizeDeviceHistory)
  } finally {
    historyLoading.value = false
  }
}

async function openDetail(device) {
  detailVisible.value = true
  detailLoading.value = true
  detailDevice.value = null
  try {
    const data = await getDeviceApi(device.id)
    detailDevice.value = normalizeDevice(data)
  } finally {
    detailLoading.value = false
  }
}

function openAdjust(device) {
  const controls = getAdjustControls(device)
  if (!controls.length) {
    ElMessage.warning('该设备暂无可调节属性')
    return
  }

  adjustDevice.value = device
  adjustControls.value = controls
  adjustValues.value = controls.reduce((values, control) => {
    values[control.field] = control.value
    return values
  }, {})
  adjustVisible.value = true
}

function getAdjustControls(device) {
  const properties = device.properties || {}
  const map = {
    light: [
      {
        field: 'brightness',
        label: '灯光亮度',
        value: Number(properties.brightness ?? 60),
        min: 0,
        max: 100,
        inputType: 'slider'
      },
      {
        field: 'color_temperature',
        label: '灯光色温',
        value: properties.color_temperature || '暖白',
        inputType: 'select',
        options: ['暖黄', '暖白', '自然光', '冷白']
      }
    ],
    desk_lamp: [
      {
        field: 'brightness',
        label: '台灯亮度',
        value: Number(properties.brightness ?? 65),
        min: 0,
        max: 100,
        inputType: 'slider'
      },
      {
        field: 'color_temperature',
        label: '台灯色温',
        value: properties.color_temperature || '冷白',
        inputType: 'select',
        options: ['暖黄', '暖白', '自然光', '冷白']
      }
    ],
    bedside_lamp: [
      {
        field: 'brightness',
        label: '床头灯亮度',
        value: Number(properties.brightness ?? 35),
        min: 0,
        max: 100,
        inputType: 'slider'
      },
      {
        field: 'color_temperature',
        label: '床头灯色温',
        value: properties.color_temperature || '暖黄',
        inputType: 'select',
        options: ['暖黄', '暖白', '自然光', '冷白']
      }
    ],
    air_conditioner: [
      {
        field: 'temperature',
        label: '空调温度',
        value: Number(properties.temperature ?? 26),
        min: 16,
        max: 30,
        inputType: 'slider'
      },
      {
        field: 'mode',
        label: '空调模式',
        value: properties.mode || '制冷',
        inputType: 'select',
        options: ['制冷', '制热', '除湿', '送风', '睡眠']
      },
      {
        field: 'fan_speed',
        label: '空调风量',
        value: properties.fan_speed || '自动',
        inputType: 'select',
        options: ['低速', '中速', '高速', '自动']
      }
    ],
    tv: [
      {
        field: 'volume',
        label: '电视音量',
        value: Number(properties.volume ?? 20),
        min: 0,
        max: 100,
        inputType: 'slider'
      },
      {
        field: 'channel',
        label: '电视频道',
        value: properties.channel || 'CCTV-1',
        inputType: 'select',
        options: ['CCTV-1', 'CCTV-5', 'CCTV-13', '湖南卫视', '浙江卫视']
      }
    ],
    curtain: [
      {
        field: 'open_percent',
        label: '窗帘开合比例',
        value: Number(properties.open_percent ?? 0),
        min: 0,
        max: 100,
        inputType: 'slider'
      }
    ],
    fan: [
      {
        field: 'speed',
        label: '排风扇风速',
        value: properties.speed || '中速',
        inputType: 'select',
        options: ['低速', '中速', '高速']
      }
    ],
    speaker: [
      {
        field: 'volume',
        label: '音箱音量',
        value: Number(properties.volume ?? 35),
        min: 0,
        max: 100,
        inputType: 'slider'
      },
      {
        field: 'mode',
        label: '音箱模式',
        value: properties.mode || '待机',
        inputType: 'select',
        options: ['待机', '播放', '静音']
      }
    ],
    humidifier: [
      {
        field: 'humidity_target',
        label: '目标湿度',
        value: Number(properties.humidity_target ?? 55),
        min: 30,
        max: 80,
        inputType: 'slider'
      },
      {
        field: 'mode',
        label: '加湿模式',
        value: properties.mode || '自动',
        inputType: 'select',
        options: ['低档', '自动', '睡眠']
      }
    ],
    air_purifier: [
      {
        field: 'mode',
        label: '净化模式',
        value: properties.mode || '自动',
        inputType: 'select',
        options: ['低速', '自动', '强力']
      }
    ],
    smart_plug: [
      {
        field: 'power_watt',
        label: '当前功率',
        value: Number(properties.power_watt ?? 0),
        min: 0,
        max: 2400,
        inputType: 'slider'
      }
    ],
    fridge: [
      {
        field: 'temperature',
        label: '冷藏温度',
        value: Number(properties.temperature ?? 4),
        min: 2,
        max: 8,
        inputType: 'slider'
      },
      {
        field: 'mode',
        label: '冰箱模式',
        value: properties.mode || '保鲜',
        inputType: 'select',
        options: ['保鲜', '节能', '速冷']
      }
    ]
  }
  return map[device.type] || []
}

async function saveAdjustment() {
  if (!adjustDevice.value || !adjustControls.value.length) return

  adjustSaving.value = true
  try {
    await updateDeviceStateApi(adjustDevice.value.id, {
      properties: { ...adjustValues.value }
    })
    ElMessage.success(`${adjustDevice.value.roomName}${adjustDevice.value.name}调节成功`)
    adjustVisible.value = false
    await loadDevices()
  } finally {
    adjustSaving.value = false
  }
}

function sourceLabel(source) {
  const map = {
    manual: '手动控制',
    command: '语音指令',
    scene: '场景联动',
    system: '系统'
  }
  return map[source] || source || '未知来源'
}

onMounted(loadDevices)
</script>
