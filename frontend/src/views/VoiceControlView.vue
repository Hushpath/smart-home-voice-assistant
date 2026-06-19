<template>
  <div class="voice-page">
    <section class="voice-console">
      <div class="voice-copy">
        <p class="panel-kicker">Direct voice control</p>
        <h2>直接说出你要控制的家居动作。</h2>
      </div>

      <div class="voice-radar" :class="{ listening: activeStep === 'listening' || recording || browserListening }">
        <span></span>
        <strong>{{ currentStepLabel }}</strong>
      </div>
    </section>

    <section class="voice-capability-card">
      <div class="section-head">
        <div>
          <p class="panel-kicker">Voice capability</p>
          <h3>语音能力状态</h3>
        </div>
        <div class="capability-actions">
          <el-button class="refresh-button" @click="asrConfigDialogVisible = true">配置讯飞</el-button>
          <el-button class="refresh-button" @click="personalizationDialogVisible = true">个性化设置</el-button>
          <el-button class="refresh-button" :loading="providerLoading" @click="loadVoiceProviders">刷新状态</el-button>
        </div>
      </div>
      <div class="capability-grid">
        <span>
          <label>云端 ASR</label>
          <el-tag :type="providerStatus.cloudStatusType" effect="dark" round>{{ providerStatus.cloudStatus }}</el-tag>
        </span>
        <span>
          <label>浏览器识别</label>
          <el-tag :type="providerStatus.browserSupported ? 'success' : 'warning'" effect="dark" round>
            {{ providerStatus.browserSupported ? '支持' : '不支持' }}
          </el-tag>
        </span>
        <span>
          <label>文本输入</label>
          <el-tag type="success" effect="dark" round>可用</el-tag>
        </span>
      </div>
      <p v-if="providerStatus.notes" class="voice-fallback-tip">{{ providerStatus.notes }}</p>
    </section>

    <section class="voice-command-grid">
      <article class="voice-input-panel direct-control-panel">
        <div class="section-head">
          <div>
            <p class="panel-kicker">Assistant</p>
            <h3>选择输入方式</h3>
          </div>
          <el-switch v-model="speechEnabled" active-text="播报" inactive-text="静音" />
        </div>

        <div class="voice-mode-selector" role="radiogroup" aria-label="选择语音输入方式">
          <button
            v-for="mode in inputModes"
            :key="mode.key"
            class="voice-mode-option"
            :class="{ active: inputMode === mode.key, disabled: mode.disabled }"
            :aria-checked="inputMode === mode.key"
            :disabled="busy || recording || mode.disabled"
            role="radio"
            type="button"
            @click="selectInputMode(mode.key)"
          >
            <span class="mode-icon">{{ mode.icon }}</span>
            <span class="mode-copy">
              <strong>{{ mode.title }}</strong>
              <small>{{ mode.description }}</small>
            </span>
            <em>{{ mode.status }}</em>
          </button>
        </div>

        <div class="voice-mode-workspace">
          <template v-if="inputMode === 'cloud'">
            <button
              class="microphone-button cloud-mic"
              :class="{ listening: recording }"
              :disabled="busy"
              @click="toggleCloudRecording"
            >
              <span></span>
              <strong>{{ recording ? '停止录音并执行' : '按下开始说话' }}</strong>
            </button>
            <p class="mode-help">
              {{ cloudModeHelp }}
            </p>
          </template>

          <template v-else-if="inputMode === 'browser'">
            <button
              class="browser-speech-button"
              :class="{ listening: browserListening }"
              :disabled="(busy && !browserListening) || !providerStatus.browserSupported"
              type="button"
              @click="startBrowserSpeech"
            >
              <span>{{ browserListening ? '结束识别并执行' : '开始浏览器识别' }}</span>
              <strong>{{ providerStatus.browserSupported ? '点一下开始，再点一下结束' : '当前浏览器不支持' }}</strong>
            </button>
            <p class="mode-help">浏览器识别结束后，会把文本提交后端方言容错、解析和执行。</p>
          </template>

          <template v-else>
            <div class="text-fallback-box">
              <el-input
                v-model="commandText"
                type="textarea"
                :rows="4"
                maxlength="200"
                show-word-limit
                placeholder="输入中文指令，例如：打开客厅灯"
                @keyup.ctrl.enter="executeTextFallback"
              />
              <div class="voice-actions text-submit-row">
                <el-button :disabled="busy || recording || !commandText.trim()" type="primary" @click="executeTextFallback">
                  执行文本指令
                </el-button>
                <span>Ctrl + Enter 快速执行</span>
              </div>
            </div>
          </template>
        </div>

        <div class="example-groups">
          <div class="example-group">
            <label>你的常用指令</label>
            <el-empty v-if="!frequentCommandsLoading && !frequentCommands.length" description="暂无常用指令" :image-size="48" />
            <div v-else class="frequent-command-list" v-loading="frequentCommandsLoading">
              <button
                v-for="item in frequentCommands"
                :key="`${item.command}-${item.count}`"
                :disabled="busy || recording"
                @click="runFrequentCommand(item.command)"
              >
                <strong>{{ item.command }}</strong>
                <small>{{ item.count }} 次 · {{ formatDateTime(item.lastUsedAt) }}</small>
              </button>
            </div>
          </div>
        </div>
      </article>

      <div class="voice-result-stack">
        <article class="voice-stage-card">
          <p class="panel-kicker">Execution chain</p>
          <div class="direct-flow-list">
            <span v-for="step in flowSteps" :key="step.key" :class="{ active: step.key === activeStep, done: step.done }">
              {{ step.label }}
            </span>
          </div>
        </article>

        <article v-if="lastResult" class="command-result-card direct-summary-card">
          <div class="command-result-head">
            <span>{{ lastResult.success ? '控制完成' : '控制失败' }}</span>
            <strong>{{ safe(resultDisplay.title) }}</strong>
          </div>

          <div v-if="resultDisplay.details.length" class="result-detail-grid">
            <div v-for="item in resultDisplay.details" :key="item.label" :class="{ danger: item.tone === 'danger' }">
              <label>{{ item.label }}</label>
              <strong>{{ safe(item.value) }}</strong>
            </div>
          </div>

          <div v-if="resultDisplay.batchItems.length" class="batch-result-list">
            <article v-for="item in resultDisplay.batchItems" :key="item.index" :class="{ failed: !item.success }">
              <span>{{ item.index }}</span>
              <strong>{{ safe(item.title) }}</strong>
              <small>{{ safe(item.detail || item.sourceText || item.message) }}</small>
            </article>
          </div>

          <div v-if="resultDisplay.meta.length" class="result-tags result-meta-tags">
            <span v-for="item in resultDisplay.meta" :key="item.label">{{ item.label }}：{{ safe(item.value) }}</span>
          </div>

          <p v-if="lastResult.parsed?.confidence !== null && lastResult.parsed?.confidence < LOW_CONFIDENCE_THRESHOLD" class="result-warning">
            系统不太确定你的指令含义，请换一种更明确的说法。
          </p>

          <div v-if="resultDisplay.changes.length" class="state-change-list">
            <article v-for="item in resultDisplay.changes" :key="item.label">
              <label>{{ item.label }}</label>
              <span>{{ safe(item.before) }}</span>
              <strong>{{ safe(item.after) }}</strong>
            </article>
          </div>
          <p v-else-if="resultDisplay.noChangeText" class="state-no-change">{{ resultDisplay.noChangeText }}</p>

          <div class="summary-actions">
            <el-button link type="primary" :disabled="!lastTraceId" @click="openLogDetail">查看日志详情</el-button>
          </div>
        </article>

        <article v-else-if="lastError" class="command-result-card failed direct-summary-card">
          <div class="command-result-head">
            <span>控制失败</span>
            <strong>{{ safe(lastError.message) }}</strong>
          </div>
          <p>{{ safe(lastError.suggestion || '请换用浏览器识别或文本输入再试。') }}</p>
        </article>

        <article v-else class="command-result-card empty-result">
          <div class="command-result-head">
            <span>待命</span>
            <strong>等待家居指令</strong>
          </div>
          <p>可以使用云端录音、浏览器识别或文本输入，执行细节会记录到操作日志。</p>
        </article>

        <article class="voice-monitor-card recent-log-embed">
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
              <strong>{{ log.commandText || log.rawCommand || '空指令' }}</strong>
              <small>{{ log.traceId }} · {{ log.intent }}</small>
            </article>
          </div>
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
    </section>

    <el-dialog v-model="asrConfigDialogVisible" title="讯飞云端 ASR 配置" width="620px" class="asr-config-dialog">
      <div class="asr-config-form">
        <p>配置会保存到后端本地文件，不进入前端代码或浏览器存储。前端仍不会直接调用讯飞。</p>
        <div v-if="asrConfigStatus.config_file_exists" class="asr-config-status">
          <span>当前 AppID：{{ safe(asrConfigStatus.app_id_masked) }}</span>
          <span>当前 APIKey：{{ safe(asrConfigStatus.api_key_masked) }}</span>
          <span>APISecret：{{ asrConfigStatus.secret_key_configured ? '已配置' : '未配置' }}</span>
        </div>
        <el-input v-model="asrConfig.appId" placeholder="讯飞 AppID" />
        <el-input v-model="asrConfig.apiKey" placeholder="讯飞 APIKey" show-password />
        <el-input v-model="asrConfig.secretKey" placeholder="讯飞 APISecret" show-password />
        <p class="mode-help">保存后立即生效；再次保存时可保留密钥字段为空，后端会沿用已有密钥。</p>
      </div>
      <template #footer>
        <el-button @click="asrConfigDialogVisible = false">关闭</el-button>
        <el-button :loading="asrConfigSaving" @click="clearAsrConfig">清除配置</el-button>
        <el-button type="primary" :loading="asrConfigSaving" @click="saveAsrConfig">保存到后端</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="personalizationDialogVisible" title="个性化语音设置" width="640px" class="personalization-dialog">
      <PersonalizationCard
        :preference="preference"
        :loading="preferenceLoading"
        @saved="handlePreferenceSaved"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getCommandLogsApi, executeCommandApi } from '../api/command'
import { getDevicesApi } from '../api/device'
import { getFrequentCommandsApi, getUserPreferencesApi } from '../api/personalization'
import { clearAsrConfigApi, executeVoiceAudioApi, getAsrConfigApi, getVoiceProvidersApi, saveAsrConfigApi } from '../api/voice'
import PersonalizationCard from '../components/PersonalizationCard.vue'
import {
  buildAssistantSpeech,
  buildCommandResultDisplay,
  cleanText,
  formatDateTime,
  LOW_CONFIDENCE_THRESHOLD,
  normalizeCommandLog,
  normalizeCommandResult,
  normalizeDevice,
  normalizeFrequentCommand,
  normalizeUserPreference,
  normalizeVoiceExecuteResult,
  normalizeVoiceProviderStatus,
} from '../utils/normalizers'

const router = useRouter()
const commandText = ref('')
const activeStep = ref('idle')
const recording = ref(false)
const browserListening = ref(false)
const busy = ref(false)
const providerLoading = ref(false)
const devicesLoading = ref(false)
const logsLoading = ref(false)
const preferenceLoading = ref(false)
const frequentCommandsLoading = ref(false)
const speechEnabled = ref(true)
const asrConfigDialogVisible = ref(false)
const personalizationDialogVisible = ref(false)
const asrConfigSaving = ref(false)
const inputMode = ref('browser')
const userSelectedInputMode = ref(false)
const currentInputSource = ref('text')
const lastResult = ref(null)
const lastError = ref(null)
const devices = ref([])
const recentLogs = ref([])
const frequentCommands = ref([])
const preference = ref(normalizeUserPreference({}))
const providerStatus = ref(normalizeVoiceProviderStatus({}))

const mediaRecorder = ref(null)
const mediaStream = ref(null)
const recordingChunks = ref([])
const recordingStartedAt = ref(0)
const audioContext = ref(null)
const audioSource = ref(null)
const audioProcessor = ref(null)
const xunfeiAudioChunks = ref([])
const xunfeiSampleRate = ref(16000)
const recognition = ref(null)
const browserTranscript = ref('')
const browserStopRequested = ref(false)
const browserStopTimer = ref(null)
const browserFinalized = ref(false)
const asrConfig = ref({
  appId: '',
  apiKey: '',
  secretKey: ''
})
const asrConfigStatus = ref({})

const currentStepLabel = computed(() => {
  const labels = {
    idle: '待命',
    listening: '听取指令',
    understanding: '理解语音',
    executing: '执行控制',
    done: '控制完成',
    error: '需要重试'
  }
  return labels[activeStep.value] || '待命'
})

const flowSteps = computed(() => {
  const order = ['listening', 'understanding', 'executing', 'done']
  const labels = {
    listening: '听取指令',
    understanding: '理解语音',
    executing: '执行控制',
    done: '完成反馈'
  }
  const activeIndex = order.indexOf(activeStep.value)
  return order.map((key, index) => ({
    key,
    label: labels[key],
    done: activeIndex > index || activeStep.value === 'done'
  }))
})

const lastTraceId = computed(() => lastResult.value?.traceId || recentLogs.value[0]?.traceId || '')
const resultDisplay = computed(() => buildCommandResultDisplay(lastResult.value || {}))

const cloudModeHelp = computed(() => {
  if (!providerStatus.value.cloudConfigured) return '云端语音识别未配置，请切换到浏览器识别或文本输入。'
  if (isXunfeiProvider()) return '讯飞云端 ASR 会在浏览器中采集语音并编码为 wav，再上传后端识别和执行。'
  return '录音会上传后端云端 ASR，再进入指令理解和执行。'
})

const inputModes = computed(() => [
  {
    key: 'cloud',
    icon: 'ASR',
    title: providerStatus.value.providerLabel || '云端 ASR',
    description: '录音上传后端识别并执行',
    status: providerStatus.value.cloudConfigured ? '可用' : '未配置',
    disabled: false
  },
  {
    key: 'browser',
    icon: 'WEB',
    title: '浏览器识别',
    description: '本机识别后交给后端执行',
    status: providerStatus.value.browserSupported ? '支持' : '不支持',
    disabled: !providerStatus.value.browserSupported
  },
  {
    key: 'text',
    icon: 'TXT',
    title: '文本输入',
    description: '手动输入，适合演示兜底',
    status: '可用',
    disabled: false
  }
])

function selectInputMode(mode) {
  if (mode === 'browser' && !providerStatus.value.browserSupported) {
    showFriendlyError('当前浏览器不支持 Web Speech API，请使用文本输入。')
    return
  }
  userSelectedInputMode.value = true
  inputMode.value = mode
}

function syncPreferredInputMode() {
  if (userSelectedInputMode.value) return
  if (providerStatus.value.cloudConfigured) {
    inputMode.value = 'cloud'
  } else if (providerStatus.value.browserSupported) {
    inputMode.value = 'browser'
  } else {
    inputMode.value = 'text'
  }
}

async function loadVoiceProviders() {
  providerLoading.value = true
  try {
    const data = await getVoiceProvidersApi()
    providerStatus.value = normalizeVoiceProviderStatus(data)
    syncPreferredInputMode()
  } catch (error) {
    providerStatus.value = {
      ...normalizeVoiceProviderStatus({}),
      cloudStatus: '调用失败',
      cloudStatusType: 'danger',
      notes: '语音能力状态获取失败，请使用浏览器识别或文本输入。'
    }
    syncPreferredInputMode()
  } finally {
    providerLoading.value = false
  }
}

async function loadPreferences() {
  preferenceLoading.value = true
  try {
    const data = await getUserPreferencesApi()
    preference.value = normalizeUserPreference(data)
    applyPreferredInputMode()
  } finally {
    preferenceLoading.value = false
  }
}

function handlePreferenceSaved(data) {
  preference.value = normalizeUserPreference(data)
  applyPreferredInputMode()
}

function applyPreferredInputMode() {
  if (userSelectedInputMode.value) return
  const modeMap = {
    cloud_asr: 'cloud',
    browser_speech: 'browser',
    text: 'text'
  }
  const preferredMode = modeMap[preference.value.preferredInputMode] || 'browser'
  if (preferredMode === 'cloud' && !providerStatus.value.cloudConfigured) return syncPreferredInputMode()
  if (preferredMode === 'browser' && !providerStatus.value.browserSupported) return syncPreferredInputMode()
  inputMode.value = preferredMode
}

async function loadAsrConfig() {
  try {
    const data = await getAsrConfigApi()
    asrConfigStatus.value = data.config || {}
  } catch (error) {
    asrConfigStatus.value = {}
  }
}

async function saveAsrConfig() {
  asrConfigSaving.value = true
  try {
    const response = await saveAsrConfigApi(
      {
        provider: 'xunfei',
        app_id: asrConfig.value.appId,
        api_key: asrConfig.value.apiKey,
        secret_key: asrConfig.value.secretKey,
        enable_cloud: true
      },
      { rawEnvelope: true, suppressErrorMessage: true }
    )
    asrConfigStatus.value = response.data?.config || {}
    asrConfig.value.apiKey = ''
    asrConfig.value.secretKey = ''
    asrConfigDialogVisible.value = false
    ElMessage.success(response.message || 'ASR 配置已保存')
    await loadVoiceProviders()
  } catch (error) {
    ElMessage.error(error.payload?.message || 'ASR 配置保存失败，请检查必填项。')
  } finally {
    asrConfigSaving.value = false
  }
}

async function clearAsrConfig() {
  asrConfigSaving.value = true
  try {
    await clearAsrConfigApi({ rawEnvelope: true, suppressErrorMessage: true })
    asrConfig.value = { appId: '', apiKey: '', secretKey: '' }
    asrConfigStatus.value = {}
    ElMessage.success('ASR 本地配置已清除')
    await loadVoiceProviders()
  } catch (error) {
    ElMessage.error(error.payload?.message || 'ASR 配置清除失败')
  } finally {
    asrConfigSaving.value = false
  }
}

async function toggleCloudRecording() {
  if (recording.value) {
    stopCloudRecording()
    return
  }
  await startCloudRecording()
}

async function startCloudRecording() {
  if (!providerStatus.value.cloudConfigured) {
    showFriendlyError('云端语音识别未配置，请使用浏览器识别或文本输入。')
    return
  }
  if (isXunfeiProvider()) {
    await startXunfeiRecording()
    return
  }
  if (!window.MediaRecorder) {
    showFriendlyError('当前浏览器不支持录音上传，请使用浏览器识别或文本输入。')
    return
  }
  const mimeType = pickAudioMimeType()
  try {
    mediaStream.value = await navigator.mediaDevices.getUserMedia({ audio: true })
    recordingChunks.value = []
    mediaRecorder.value = new MediaRecorder(mediaStream.value, mimeType ? { mimeType } : undefined)
    mediaRecorder.value.ondataavailable = (event) => {
      if (event.data?.size > 0) recordingChunks.value.push(event.data)
    }
    mediaRecorder.value.onerror = () => {
      showFriendlyError('录音过程中出现问题，请检查麦克风后重试。')
      cleanupRecording()
    }
    mediaRecorder.value.onstop = handleRecordingStop
    recordingStartedAt.value = Date.now()
    recording.value = true
    activeStep.value = 'listening'
    mediaRecorder.value.start()
  } catch (error) {
    showFriendlyError('无法访问麦克风，请允许浏览器麦克风权限后重试。')
    cleanupRecording()
  }
}

function stopCloudRecording() {
  if (isXunfeiProvider() && audioProcessor.value) {
    handleXunfeiRecordingStop()
    return
  }
  if (mediaRecorder.value?.state === 'recording') {
    mediaRecorder.value.stop()
  }
}

async function startXunfeiRecording() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext
  if (!AudioContextClass) {
    showFriendlyError('当前浏览器不支持云端录音采集，请使用浏览器识别或文本输入。')
    return
  }
  try {
    mediaStream.value = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioContext.value = new AudioContextClass()
    xunfeiSampleRate.value = audioContext.value.sampleRate
    xunfeiAudioChunks.value = []
    audioSource.value = audioContext.value.createMediaStreamSource(mediaStream.value)
    audioProcessor.value = audioContext.value.createScriptProcessor(4096, 1, 1)
    audioProcessor.value.onaudioprocess = (event) => {
      const channel = event.inputBuffer.getChannelData(0)
      xunfeiAudioChunks.value.push(new Float32Array(channel))
    }
    audioSource.value.connect(audioProcessor.value)
    audioProcessor.value.connect(audioContext.value.destination)
    recordingStartedAt.value = Date.now()
    recording.value = true
    activeStep.value = 'listening'
  } catch (error) {
    showFriendlyError('无法访问麦克风，请允许浏览器麦克风权限后重试。')
    cleanupRecording()
  }
}

async function handleXunfeiRecordingStop() {
  const durationMs = Date.now() - recordingStartedAt.value
  const chunks = [...xunfeiAudioChunks.value]
  const sourceRate = xunfeiSampleRate.value
  cleanupRecording()
  if (durationMs < 700 || !chunks.length) {
    showFriendlyError('录音时间太短，请按住稍久一点再说完整指令。')
    return
  }
  const wavBytes = encodeWav(resampleTo16k(mergeFloat32Chunks(chunks), sourceRate), 16000)
  await executeCloudAudio(new Blob([wavBytes], { type: 'audio/wav' }))
}

async function handleRecordingStop() {
  const durationMs = Date.now() - recordingStartedAt.value
  const mimeType = mediaRecorder.value?.mimeType || 'audio/webm'
  const chunks = [...recordingChunks.value]
  cleanupRecording()
  if (durationMs < 700 || !chunks.length) {
    showFriendlyError('录音时间太短，请按住稍久一点再说完整指令。')
    return
  }
  const blob = new Blob(chunks, { type: mimeType })
  await executeCloudAudio(blob)
}

async function executeCloudAudio(blob) {
  startRun('cloud')
  activeStep.value = 'understanding'
  const stepTimer = window.setTimeout(() => {
    if (busy.value) activeStep.value = 'executing'
  }, 900)
  try {
    const response = await executeVoiceAudioApi(blob, {
      rawEnvelope: true,
      filename: audioFilename(blob.type),
      suppressErrorMessage: true
    })
    lastResult.value = normalizeVoiceExecuteResult(response)
    finishRun(speechSummary(lastResult.value, response.message), lastResult.value.success)
  } catch (error) {
    failRun(friendlyError(error, 'cloud'), 'cloud')
  } finally {
    window.clearTimeout(stepTimer)
    busy.value = false
  }
}

function startBrowserSpeech() {
  if (browserListening.value) {
    stopBrowserSpeech()
    return
  }
  if (!providerStatus.value.browserSupported) {
    showFriendlyError('当前浏览器不支持 Web Speech API，请使用文本输入。')
    return
  }
  if (!recognition.value) recognition.value = createRecognition()
  if (!recognition.value) return
  startRun('browser')
  activeStep.value = 'listening'
  browserTranscript.value = ''
  browserStopRequested.value = false
  browserFinalized.value = false
  clearBrowserStopTimer()
  browserListening.value = true
  try {
    recognition.value.start()
  } catch (error) {
    failRun('浏览器语音识别启动失败，请刷新页面或使用文本输入。')
  }
}

function stopBrowserSpeech() {
  browserStopRequested.value = true
  activeStep.value = 'understanding'
  clearBrowserStopTimer()
  browserStopTimer.value = window.setTimeout(() => {
    finalizeBrowserSpeech()
  }, browserTranscript.value.trim() ? 300 : 1200)
  try {
    recognition.value?.stop()
  } catch (error) {
    browserListening.value = false
    clearBrowserStopTimer()
    failRun('浏览器语音识别停止失败，请使用文本输入。')
  }
}

function createRecognition() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!Recognition) return null
  const instance = new Recognition()
  instance.lang = 'zh-CN'
  instance.interimResults = true
  instance.continuous = false
  instance.onresult = (event) => {
    const text = Array.from(event.results || [])
      .map((result) => result?.[0]?.transcript || '')
      .join('')
      .trim()
    if (text) browserTranscript.value = text
  }
  instance.onerror = (event) => {
    if (browserFinalized.value) return
    if (browserStopRequested.value && event?.error === 'aborted') return
    browserFinalized.value = true
    browserStopRequested.value = false
    browserListening.value = false
    clearBrowserStopTimer()
    failRun('浏览器语音识别失败，请使用文本输入。')
  }
  instance.onend = () => {
    if (!browserListening.value && !browserStopRequested.value) return
    finalizeBrowserSpeech()
  }
  return instance
}

async function finalizeBrowserSpeech() {
  if (browserFinalized.value) return
  browserFinalized.value = true
  clearBrowserStopTimer()
  try {
    if (browserListening.value) recognition.value?.abort?.()
  } catch (error) {
    // Browser speech engines can reject abort after stop; the captured text is still usable.
  }
  browserStopRequested.value = false
  browserListening.value = false
  const text = browserTranscript.value.trim()
  if (!text) {
    browserListening.value = false
    failRun('没有听清指令，请再说一次或使用文本输入。')
    return
  }
  commandText.value = text
  await executeTextCommand(text, 'browser')
}

function clearBrowserStopTimer() {
  if (!browserStopTimer.value) return
  window.clearTimeout(browserStopTimer.value)
  browserStopTimer.value = null
}

async function executeTextFallback() {
  const command = commandText.value.trim()
  if (!command) {
    ElMessage.warning('请输入一条中文指令')
    return
  }
  await executeTextCommand(command, 'text')
}

async function runFrequentCommand(command) {
  commandText.value = command
  await executeTextCommand(command, 'text')
}

async function executeTextCommand(command, source) {
  startRun(source)
  activeStep.value = 'understanding'
  await nextFrame()
  activeStep.value = 'executing'
  try {
    const response = await executeCommandApi(command, {
      rawEnvelope: true,
      suppressErrorMessage: true
    })
    lastResult.value = normalizeCommandResult(response)
    finishRun(speechSummary(lastResult.value, response.message), lastResult.value.success)
  } catch (error) {
    failRun(friendlyError(error, source), source)
  } finally {
    busy.value = false
  }
}

function startRun(source = 'text') {
  currentInputSource.value = source
  busy.value = true
  lastError.value = null
  lastResult.value = null
}

async function finishRun(message, success = true) {
  activeStep.value = 'done'
  if (success) {
    ElMessage.success(message)
  } else {
    ElMessage.warning(message)
  }
  speak(message)
  await Promise.all([loadDevices(), loadLogs(), loadFrequentCommands()])
}

function failRun(message, source = currentInputSource.value) {
  const displayMessage = normalizeInputErrorMessage(message, source)
  activeStep.value = 'error'
  lastResult.value = null
  lastError.value = { message: displayMessage, suggestion: fallbackSuggestion(displayMessage, source) }
  ElMessage.warning(displayMessage)
  speak(displayMessage)
  busy.value = false
}

function showFriendlyError(message, source = currentInputSource.value) {
  const displayMessage = normalizeInputErrorMessage(message, source)
  activeStep.value = 'error'
  lastError.value = { message: displayMessage, suggestion: fallbackSuggestion(displayMessage, source) }
  ElMessage.warning(displayMessage)
  speak(displayMessage)
}

function speechSummary(result, fallback = '') {
  return buildAssistantSpeech(result) || fallback || result?.message || '控制完成'
}

function friendlyError(error, source = currentInputSource.value) {
  const code = error.payload?.code
  if (code === 'ASR_PROVIDER_NOT_CONFIGURED' || code === 'ASR_NOT_CONFIGURED') return '云端语音识别未配置，请使用浏览器识别或文本输入。'
  if (code === 'ASR_TIMEOUT') return '云端语音识别请求超时，请使用浏览器识别或文本输入。'
  if (code === 'ASR_AUTH_FAILED') return '云端语音识别认证失败，请检查后端配置或使用文本输入。'
  if (code === 'ASR_EMPTY_TRANSCRIPT') return '云端语音识别没有返回有效文本，请使用浏览器识别或文本输入。'
  if (code === 'ASR_INVALID_RESPONSE' || code === 'ASR_REQUEST_FAILED') return '云端语音识别失败，请使用文本输入。'
  if (code === 'ASR_UNSUPPORTED_AUDIO_FORMAT') return '当前录音格式暂不支持，请使用浏览器识别或文本输入。'
  if (code === 'ASR_EMPTY_AUDIO') return '录音内容为空，请重新录制。'
  if (code === 'UNAUTHORIZED') return '登录已失效，请重新登录。'
  if (!error.response && !error.payload) return '后端服务不可用，请确认 FastAPI 正在运行。'
  return normalizeInputErrorMessage(error.payload?.message || error.message || '指令执行失败，请稍后重试。', source)
}

function normalizeInputErrorMessage(message, source) {
  if (source !== 'text') return message
  return String(message || '')
    .replace(/，?或使用文本输入。?/g, '。')
    .replace(/请换一种说法，。/g, '请换一种说法。')
    .replace(/请换一种说法或使用文本输入。?/g, '请换一种说法。')
}

function fallbackSuggestion(message, source = currentInputSource.value) {
  if (message.includes('云端') || message.includes('录音') || message.includes('麦克风')) {
    return '可以改用浏览器识别或文本输入。'
  }
  if (source === 'text') return '请换一种更明确的说法，或使用完整房间和设备名称。'
  return '请换一种说法，或使用文本输入。'
}

function mergeFloat32Chunks(chunks) {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0)
  const merged = new Float32Array(totalLength)
  let offset = 0
  chunks.forEach((chunk) => {
    merged.set(chunk, offset)
    offset += chunk.length
  })
  return merged
}

function resampleTo16k(samples, sourceRate) {
  const targetRate = 16000
  if (!sourceRate || sourceRate === targetRate) return samples
  const ratio = sourceRate / targetRate
  const newLength = Math.max(1, Math.round(samples.length / ratio))
  const result = new Float32Array(newLength)
  for (let index = 0; index < newLength; index += 1) {
    const sourceIndex = index * ratio
    const before = Math.floor(sourceIndex)
    const after = Math.min(before + 1, samples.length - 1)
    const weight = sourceIndex - before
    result[index] = samples[before] * (1 - weight) + samples[after] * weight
  }
  return result
}

function encodeWav(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)
  writeAscii(view, 0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  writeAscii(view, 8, 'WAVE')
  writeAscii(view, 12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeAscii(view, 36, 'data')
  view.setUint32(40, samples.length * 2, true)
  let offset = 44
  samples.forEach((sample) => {
    const value = Math.max(-1, Math.min(1, sample))
    view.setInt16(offset, value < 0 ? value * 0x8000 : value * 0x7fff, true)
    offset += 2
  })
  return buffer
}

function writeAscii(view, offset, text) {
  for (let index = 0; index < text.length; index += 1) {
    view.setUint8(offset + index, text.charCodeAt(index))
  }
}

function pickAudioMimeType() {
  const candidates = isXunfeiProvider()
    ? ['audio/mpeg', 'audio/wav']
    : ['audio/webm;codecs=opus', 'audio/webm', 'audio/wav', 'audio/mpeg']
  return candidates.find((item) => window.MediaRecorder?.isTypeSupported?.(item)) || ''
}

function isXunfeiProvider() {
  return ['xunfei', 'iflytek'].includes(providerStatus.value.currentProvider)
}

function audioFilename(type) {
  if (type.includes('wav')) return 'voice-command.wav'
  if (type.includes('mpeg')) return 'voice-command.mp3'
  return 'voice-command.webm'
}

function cleanupRecording() {
  recording.value = false
  recordingChunks.value = []
  xunfeiAudioChunks.value = []
  audioProcessor.value?.disconnect?.()
  audioSource.value?.disconnect?.()
  audioContext.value?.close?.()
  audioProcessor.value = null
  audioSource.value = null
  audioContext.value = null
  mediaStream.value?.getTracks?.().forEach((track) => track.stop())
  mediaStream.value = null
  mediaRecorder.value = null
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

async function loadFrequentCommands() {
  frequentCommandsLoading.value = true
  try {
    const data = await getFrequentCommandsApi({ limit: 5 })
    frequentCommands.value = data.map(normalizeFrequentCommand).filter((item) => item.command)
  } finally {
    frequentCommandsLoading.value = false
  }
}

function openLogDetail() {
  router.push({ name: 'logs', query: lastTraceId.value ? { trace_id: lastTraceId.value } : {} })
}

function speak(text) {
  if (!speechEnabled.value || !window.speechSynthesis || !text) return
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'zh-CN'
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(utterance)
}

function safe(value) {
  return cleanText(value)
}

function nextFrame() {
  return new Promise((resolve) => window.requestAnimationFrame(resolve))
}

onMounted(() => {
  loadVoiceProviders()
  loadAsrConfig()
  loadPreferences()
  loadDevices()
  loadLogs()
  loadFrequentCommands()
})

onBeforeUnmount(() => {
  if (window.speechSynthesis) window.speechSynthesis.cancel()
  clearBrowserStopTimer()
  if (recognition.value && browserListening.value) {
    browserListening.value = false
    browserStopRequested.value = false
    recognition.value.stop()
  }
  cleanupRecording()
})
</script>
