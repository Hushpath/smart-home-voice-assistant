<template>
  <el-drawer
    :model-value="modelValue"
    size="680px"
    direction="rtl"
    class="log-detail-drawer history-drawer"
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <template #header>
      <div class="history-header">
        <strong>日志详情</strong>
        <span>{{ value(log?.traceId) }} · {{ value(log?.commandText || log?.rawCommand) }}</span>
      </div>
    </template>

    <div v-if="log" class="log-detail-body">
      <section class="log-detail-section">
        <div class="section-title">
          <span>链路概览</span>
          <el-tag :type="log.success ? 'success' : 'danger'" effect="dark" round>
            {{ log.success ? '成功' : '失败' }}
          </el-tag>
        </div>
        <div class="detail-kv-grid">
          <div><label>trace_id</label><strong>{{ value(log.traceId) }}</strong></div>
          <div><label>输入来源</label><strong>{{ value(log.inputSourceLabel) }}</strong></div>
          <div><label>原始指令</label><strong>{{ value(log.commandText || log.rawCommand) }}</strong></div>
          <div><label>结果消息</label><strong>{{ value(log.message || log.errorMessage) }}</strong></div>
        </div>
      </section>

      <section class="log-detail-section">
        <div class="section-title"><span>语音识别信息</span></div>
        <div class="detail-kv-grid">
          <div><label>ASR provider</label><strong>{{ value(asr.asr_provider) }}</strong></div>
          <div><label>transcript</label><strong>{{ value(asr.transcript) }}</strong></div>
          <div><label>音频时长</label><strong>{{ seconds(asr.audio_duration) }}</strong></div>
          <div><label>ASR 耗时</label><strong>{{ milliseconds(asr.asr_latency_ms) }}</strong></div>
        </div>
        <JsonBlock title="raw_asr_result" :value="asr.raw_asr_result" />
      </section>

      <section class="log-detail-section">
        <div class="section-title"><span>方言容错信息</span></div>
        <div class="detail-kv-grid">
          <div><label>detected_dialect</label><strong>{{ value(normalization.detected_dialect) }}</strong></div>
          <div><label>normalized_text</label><strong>{{ value(normalization.normalized_text) }}</strong></div>
          <div><label>dialect_matches</label><strong>{{ list(normalization.dialect_matches) }}</strong></div>
          <div><label>识别文本纠错</label><strong>{{ list(normalization.asr_corrections) }}</strong></div>
          <div><label>number_conversions</label><strong>{{ list(normalization.number_conversions) }}</strong></div>
          <div><label>removed_fillers</label><strong>{{ list(normalization.removed_fillers) }}</strong></div>
        </div>
        <JsonBlock title="normalization_steps" :value="normalization.normalization_steps" />
      </section>

      <section class="log-detail-section">
        <div class="section-title"><span>指令解析信息</span></div>
        <div class="detail-kv-grid">
          <div><label>intent</label><strong>{{ value(parse.intent) }}</strong></div>
          <div><label>room</label><strong>{{ value(parse.room) }}</strong></div>
          <div><label>device_type</label><strong>{{ value(parse.device_type) }}</strong></div>
          <div><label>value</label><strong>{{ value(parse.value) }}</strong></div>
          <div><label>scene</label><strong>{{ value(parse.scene) }}</strong></div>
          <div><label>reminder_time</label><strong>{{ value(parse.reminder_time) }}</strong></div>
          <div><label>reminder_content</label><strong>{{ value(parse.reminder_content) }}</strong></div>
          <div><label>city</label><strong>{{ value(parse.city) }}</strong></div>
          <div><label>parser_confidence</label><strong>{{ percent(parse.parser_confidence) }}</strong></div>
          <div><label>match_type</label><strong>{{ value(parse.match_type) }}</strong></div>
          <div><label>matched_keywords</label><strong>{{ list(parse.matched_keywords) }}</strong></div>
        </div>
        <div v-if="hasConfidenceBreakdown" class="detail-kv-grid">
          <div><label>基础分</label><strong>{{ percent(confidenceBreakdown.base_score) }}</strong></div>
          <div><label>房间加分</label><strong>{{ signedPercent(confidenceBreakdown.room_bonus) }}</strong></div>
          <div><label>设备加分</label><strong>{{ signedPercent(confidenceBreakdown.device_bonus) }}</strong></div>
          <div><label>参数加分</label><strong>{{ signedPercent(confidenceBreakdown.value_bonus) }}</strong></div>
          <div><label>模糊匹配扣分</label><strong>{{ penaltyPercent(confidenceBreakdown.fuzzy_penalty) }}</strong></div>
          <div><label>识别文本纠错扣分</label><strong>{{ penaltyPercent(confidenceBreakdown.asr_correction_penalty) }}</strong></div>
          <div><label>多处模糊扣分</label><strong>{{ penaltyPercent(confidenceBreakdown.multi_fuzzy_penalty) }}</strong></div>
          <div v-if="confidenceBreakdown.ambiguity_guard_cap !== undefined">
            <label>歧义保护上限</label><strong>{{ percent(confidenceBreakdown.ambiguity_guard_cap) }}</strong>
          </div>
          <div><label>最终置信度</label><strong>{{ percent(confidenceBreakdown.final_confidence) }}</strong></div>
        </div>
        <JsonBlock title="intent_scores" :value="parse.intent_scores" />
      </section>

      <section v-if="batch.is_batch" class="log-detail-section">
        <div class="section-title"><span>批量执行信息</span></div>
        <div class="detail-kv-grid">
          <div><label>command_count</label><strong>{{ value(batch.command_count) }}</strong></div>
          <div><label>success_count</label><strong>{{ value(batch.success_count) }}</strong></div>
          <div><label>failed_count</label><strong>{{ value(batch.failed_count) }}</strong></div>
          <div><label>split_strategy</label><strong>{{ value(batch.split_detail?.strategy) }}</strong></div>
        </div>
        <JsonBlock title="sub_commands" :value="batch.sub_commands" />
        <JsonBlock title="sub_results" :value="batch.sub_results" />
      </section>

      <section class="log-detail-section">
        <div class="section-title"><span>执行信息</span></div>
        <div class="detail-kv-grid">
          <div><label>code</label><strong>{{ value(execution.code) }}</strong></div>
          <div><label>message</label><strong>{{ value(execution.message) }}</strong></div>
          <div><label>execution_latency_ms</label><strong>{{ milliseconds(execution.execution_latency_ms) }}</strong></div>
          <div><label>error_code</label><strong>{{ value(execution.error_code) }}</strong></div>
          <div><label>error_message</label><strong>{{ value(execution.error_message) }}</strong></div>
        </div>
        <JsonBlock title="device_before" :value="execution.device_before" />
        <JsonBlock title="device_after" :value="execution.device_after" />
        <JsonBlock title="affected_devices" :value="execution.affected_devices" />
      </section>

      <section class="log-detail-section">
        <div class="section-title"><span>原始 JSON</span></div>
        <pre>{{ formatJson(log.detail?.raw || log) }}</pre>
      </section>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed } from 'vue'
import { formatJson } from '../utils/normalizers'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  log: {
    type: Object,
    default: null
  }
})

defineEmits(['update:modelValue'])

const asr = computed(() => props.log?.detail?.asr || {})
const normalization = computed(() => props.log?.detail?.normalization || {})
const parse = computed(() => props.log?.detail?.parse || {})
const confidenceBreakdown = computed(() => parse.value?.confidence_breakdown || {})
const hasConfidenceBreakdown = computed(() => Object.keys(confidenceBreakdown.value).length > 0)
const execution = computed(() => props.log?.detail?.execution || {})
const batch = computed(() => props.log?.detail?.batch || {})
const JsonBlock = {
  props: {
    title: {
      type: String,
      required: true
    },
    value: {
      type: [Object, Array, String, Number, Boolean],
      default: null
    }
  },
  setup() {
    return { formatJson }
  },
  template: `
    <div class="detail-json-block">
      <label>{{ title }}</label>
      <pre>{{ formatJson(value) }}</pre>
    </div>
  `
}

function value(item) {
  if (item === null || item === undefined || item === '') return '-'
  if (typeof item === 'object') return formatJson(item)
  return String(item)
}

function list(items) {
  if (!Array.isArray(items) || !items.length) return '-'
  return items.join('；')
}

function percent(item) {
  return typeof item === 'number' ? `${Math.round(item * 100)}%` : '-'
}

function signedPercent(item) {
  if (typeof item !== 'number') return '-'
  if (item === 0) return '0%'
  return `+${Math.round(item * 100)}%`
}

function penaltyPercent(item) {
  if (typeof item !== 'number') return '-'
  if (item === 0) return '0%'
  return `-${Math.round(item * 100)}%`
}

function seconds(item) {
  return typeof item === 'number' ? `${item}s` : '-'
}

function milliseconds(item) {
  return typeof item === 'number' ? `${item}ms` : '-'
}
</script>
