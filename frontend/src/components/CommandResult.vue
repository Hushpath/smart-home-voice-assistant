<template>
  <article class="command-result-card" :class="{ failed: !success }">
    <div class="command-result-head">
      <span>{{ success ? '执行成功' : '执行失败' }}</span>
      <strong>{{ title }}</strong>
    </div>

    <p v-if="message" class="result-message">{{ message }}</p>

    <div v-if="parsed" class="result-section">
      <label>解析结果</label>
      <div class="result-tags">
        <span>意图：{{ parsed.intent || '--' }}</span>
        <span v-if="parsed.room">房间：{{ parsed.room }}</span>
        <span v-if="parsed.device_type">设备：{{ parsed.device_type }}</span>
        <span v-if="parsed.value !== null && parsed.value !== undefined">数值：{{ parsed.value }}</span>
        <span v-if="parsed.scene">场景：{{ parsed.scene }}</span>
        <span v-if="parsed.city">城市：{{ parsed.city }}</span>
      </div>
    </div>

    <div class="result-section">
      <label>执行结果</label>
      <pre>{{ formatJson(result || payload) }}</pre>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { formatJson, summarizeCommandExecution } from '../utils/normalizers'

const props = defineProps({
  payload: {
    type: Object,
    default: null
  },
  success: {
    type: Boolean,
    default: true
  }
})

const parsed = computed(() => props.payload?.parsed || props.payload?.data?.parsed || null)
const result = computed(() => props.payload?.result || props.payload?.data?.result || null)
const message = computed(() => props.payload?.message || '')
const title = computed(() => {
  if (!props.success) return props.payload?.message || '后端返回错误'
  return summarizeCommandExecution(result.value || props.payload)
})
</script>
