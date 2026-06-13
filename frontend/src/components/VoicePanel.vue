<template>
  <article class="voice-input-panel">
    <div class="section-head">
      <div>
        <p class="panel-kicker">Input</p>
        <h3>指令输入</h3>
      </div>
      <el-tag :type="speechSupported ? 'success' : 'warning'" effect="dark" round>
        {{ speechSupported ? '支持语音识别' : '请使用文本输入' }}
      </el-tag>
    </div>

    <button class="microphone-button" :class="{ listening }" :disabled="!speechSupported || busy" @click="toggleListening">
      <span></span>
      <strong>{{ listening ? '正在识别' : '点击说话' }}</strong>
    </button>

    <p v-if="!speechSupported" class="voice-fallback-tip">
      当前浏览器不支持 Web Speech API，请直接输入中文指令。
    </p>

    <el-input
      :model-value="modelValue"
      type="textarea"
      :rows="5"
      maxlength="200"
      show-word-limit
      placeholder="例如：打开客厅灯"
      @update:model-value="$emit('update:modelValue', $event)"
    />

    <div class="voice-actions">
      <el-button :disabled="!modelValue.trim() || busy" @click="$emit('parse')">解析预览</el-button>
      <el-button class="execute-button" type="primary" :loading="busy" @click="$emit('execute')">
        执行指令
      </el-button>
    </div>

    <div class="command-chip-list">
      <button v-for="item in examples" :key="item" @click="$emit('choose', item)">{{ item }}</button>
    </div>
  </article>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'

defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  busy: {
    type: Boolean,
    default: false
  },
  examples: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'parse', 'execute', 'choose'])
const listening = ref(false)
const recognition = ref(null)
const speechSupported = computed(() => Boolean(window.SpeechRecognition || window.webkitSpeechRecognition))

function createRecognition() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!Recognition) return null
  const instance = new Recognition()
  instance.lang = 'zh-CN'
  instance.interimResults = false
  instance.continuous = false
  instance.onresult = (event) => {
    const text = event.results?.[0]?.[0]?.transcript || ''
    emit('update:modelValue', text.trim())
    listening.value = false
  }
  instance.onerror = () => {
    listening.value = false
    ElMessage.warning('语音识别失败，请使用文本输入')
  }
  instance.onend = () => {
    listening.value = false
  }
  return instance
}

function toggleListening() {
  if (!speechSupported.value) {
    ElMessage.warning('当前浏览器不支持 Web Speech API')
    return
  }
  if (!recognition.value) recognition.value = createRecognition()
  if (!recognition.value) return

  if (listening.value) {
    recognition.value.stop()
    listening.value = false
    return
  }

  listening.value = true
  recognition.value.start()
}

onBeforeUnmount(() => {
  if (recognition.value && listening.value) recognition.value.stop()
})
</script>
