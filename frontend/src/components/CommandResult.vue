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
        <span v-if="parsed.confidence !== null && parsed.confidence !== undefined">
          置信度：{{ parsed.confidenceLabel }} {{ parsed.confidencePercent }}%
        </span>
      </div>
      <el-progress
        v-if="parsed.confidencePercent !== null && parsed.confidencePercent !== undefined"
        :percentage="parsed.confidencePercent"
        :status="parsed.confidence < LOW_CONFIDENCE_THRESHOLD ? 'exception' : 'success'"
      />
      <p v-if="parsed.confidence !== null && parsed.confidence < LOW_CONFIDENCE_THRESHOLD" class="result-warning">
        系统不太确定你的指令含义，请换一种说法，或使用文本输入。
      </p>
    </div>

    <div v-if="result" class="result-section">
      <label>执行结果</label>
      <p>{{ summarizeCommandExecution(result) }}</p>
    </div>

    <div v-if="deviceBefore || deviceAfter" class="result-section">
      <label>状态变化</label>
      <div class="state-diff">
        <span>执行前：{{ formatDeviceState(deviceBefore || {}) }}</span>
        <span>执行后：{{ formatDeviceState(deviceAfter || {}) }}</span>
      </div>
    </div>

    <el-collapse v-if="parsed || result" class="result-detail-collapse">
      <el-collapse-item title="查看解析详情" name="detail">
        <pre>{{ formatJson({ parsed, result }) }}</pre>
      </el-collapse-item>
    </el-collapse>

    <div v-else class="result-section">
      <label>返回内容</label>
      <pre>{{ formatJson(payload) }}</pre>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { LOW_CONFIDENCE_THRESHOLD, formatDeviceState, formatJson, normalizeParsedCommand, summarizeCommandExecution } from '../utils/normalizers'

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

const parsed = computed(() => {
  const raw = props.payload?.parsed || props.payload?.data?.parsed || null
  return raw ? normalizeParsedCommand(raw) : null
})
const result = computed(() => props.payload?.result || props.payload?.data?.result || null)
const deviceBefore = computed(() => props.payload?.deviceBefore || props.payload?.device_before || result.value?.before_state || null)
const deviceAfter = computed(() => props.payload?.deviceAfter || props.payload?.device_after || result.value?.after_state || null)
const message = computed(() => props.payload?.message || '')
const title = computed(() => {
  if (!props.success) return props.payload?.message || '后端返回错误'
  return summarizeCommandExecution(result.value || props.payload)
})
</script>
