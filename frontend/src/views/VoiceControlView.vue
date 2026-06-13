<template>
  <div class="voice-page">
    <section class="voice-console">
      <div class="voice-copy">
        <p class="panel-kicker">Voice command console</p>
        <h2>让中文指令直接驱动虚拟家居。</h2>
        <p>语音识别由浏览器完成，后端只接收识别后的中文文本并执行设备、场景、提醒或天气查询。</p>
      </div>

      <div class="voice-radar" :class="{ listening: executing }">
        <span></span>
        <strong>{{ executing ? '执行中' : '待命' }}</strong>
      </div>
    </section>

    <section class="voice-command-grid">
      <VoicePanel
        v-model="commandText"
        :busy="executing || parsing"
        :examples="examples"
        @parse="parseCommand"
        @execute="executeCommand"
        @choose="chooseExample"
      />

      <div class="voice-result-stack">
        <article v-if="parsePreview" class="parse-preview-card">
          <p class="panel-kicker">Parse preview</p>
          <div class="result-tags">
            <span>意图：{{ parsePreview.intent || '--' }}</span>
            <span v-if="parsePreview.room">房间：{{ parsePreview.room }}</span>
            <span v-if="parsePreview.device_type">设备：{{ parsePreview.device_type }}</span>
            <span v-if="parsePreview.value !== null && parsePreview.value !== undefined">数值：{{ parsePreview.value }}</span>
            <span v-if="parsePreview.scene">场景：{{ parsePreview.scene }}</span>
            <span v-if="parsePreview.reminder_time">时间：{{ parsePreview.reminder_time }}</span>
            <span v-if="parsePreview.reminder_content">提醒：{{ parsePreview.reminder_content }}</span>
            <span v-if="parsePreview.city">城市：{{ parsePreview.city }}</span>
          </div>
        </article>

        <CommandResult v-if="lastResult" :payload="lastResult" />
        <CommandResult v-else-if="lastError" :payload="lastError" :success="false" />
        <article v-else class="command-result-card empty-result">
          <div class="command-result-head">
            <span>Result</span>
            <strong>等待指令执行</strong>
          </div>
          <p>执行后会显示后端 message、解析结果、设备前后状态、提醒、天气或场景联动结果。</p>
        </article>
      </div>
    </section>

    <section class="voice-monitor-grid">
      <article class="voice-monitor-card">
        <div class="section-head">
          <div>
            <p class="panel-kicker">Device refresh</p>
            <h3>设备状态快照</h3>
          </div>
          <el-button class="refresh-button" :loading="devicesLoading" @click="loadDevices">刷新</el-button>
        </div>
        <div class="voice-device-list">
          <article v-for="device in devices" :key="device.id">
            <span>{{ device.roomName }} · {{ device.name }}</span>
            <strong>{{ device.isOn ? '开启' : '关闭' }}</strong>
            <small>{{ device.propertyBadges.map((item) => `${item.label}:${item.value}`).join(' / ') }}</small>
          </article>
        </div>
      </article>

      <article class="voice-monitor-card">
        <div class="section-head">
          <div>
            <p class="panel-kicker">Recent logs</p>
            <h3>最近执行记录</h3>
          </div>
          <el-button class="refresh-button" :loading="logsLoading" @click="loadLogs">刷新</el-button>
        </div>
        <div class="recent-log-list compact">
          <article v-for="log in recentLogs" :key="log.id">
            <span :class="{ failed: !log.success }">{{ log.success ? '成功' : '失败' }}</span>
            <strong>{{ log.rawCommand || '空指令' }}</strong>
            <small>{{ summarizeCommandExecution(log.executionResult) }}</small>
          </article>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getCommandLogsApi, parseCommandApi, executeCommandApi } from '../api/command'
import { getDevicesApi } from '../api/device'
import CommandResult from '../components/CommandResult.vue'
import VoicePanel from '../components/VoicePanel.vue'
import {
  normalizeCommandLog,
  normalizeCommandResult,
  normalizeDevice,
  summarizeCommandExecution
} from '../utils/normalizers'

const commandText = ref('')
const parsing = ref(false)
const executing = ref(false)
const devicesLoading = ref(false)
const logsLoading = ref(false)
const parsePreview = ref(null)
const lastResult = ref(null)
const lastError = ref(null)
const devices = ref([])
const recentLogs = ref([])

const examples = [
  '打开客厅灯',
  '关闭卧室空调',
  '把卧室空调调到26度',
  '将客厅灯亮度调到80',
  '把电视音量调到30',
  '开启睡眠模式',
  '提醒我晚上八点吃药',
  '查询北京天气'
]

function chooseExample(command) {
  commandText.value = command
}

async function parseCommand() {
  const command = commandText.value.trim()
  if (!command) {
    ElMessage.warning('请输入或识别一条中文指令')
    return null
  }

  parsing.value = true
  try {
    const response = await parseCommandApi(command, { rawEnvelope: true })
    parsePreview.value = response.data
    ElMessage.success(response.message || '解析成功')
    return response.data
  } finally {
    parsing.value = false
  }
}

async function executeCommand() {
  const command = commandText.value.trim()
  if (!command) {
    ElMessage.warning('请输入或识别一条中文指令')
    return
  }

  executing.value = true
  lastError.value = null
  try {
    const response = await executeCommandApi(command, { rawEnvelope: true })
    lastResult.value = normalizeCommandResult(response)
    parsePreview.value = response.data?.parsed || parsePreview.value
    ElMessage.success(response.message || '指令执行成功')
    speak(response.message || '指令执行成功')
    await Promise.all([loadDevices(), loadLogs()])
  } catch (error) {
    lastResult.value = null
    lastError.value = error.payload || { message: error.message }
  } finally {
    executing.value = false
  }
}

async function loadDevices() {
  devicesLoading.value = true
  try {
    const data = await getDevicesApi()
    devices.value = data.map(normalizeDevice)
  } finally {
    devicesLoading.value = false
  }
}

async function loadLogs() {
  logsLoading.value = true
  try {
    const data = await getCommandLogsApi()
    recentLogs.value = data.map(normalizeCommandLog).slice(0, 5)
  } finally {
    logsLoading.value = false
  }
}

function speak(text) {
  if (!window.speechSynthesis) return
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'zh-CN'
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(utterance)
}

onMounted(() => {
  loadDevices()
  loadLogs()
})

onBeforeUnmount(() => {
  if (window.speechSynthesis) window.speechSynthesis.cancel()
})
</script>
