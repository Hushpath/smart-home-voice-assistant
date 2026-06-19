<template>
  <article class="voice-capability-card personalization-card" v-loading="loading">
    <div class="section-head">
      <div>
        <p class="panel-kicker">Personal voice</p>
        <h3>个性化设置</h3>
      </div>
      <el-button class="refresh-button" type="primary" :loading="saving" @click="save">保存</el-button>
    </div>

    <div class="preference-form-grid">
      <label>
        <span>默认方言模式</span>
        <el-select v-model="form.preferredDialect" style="width: 100%">
          <el-option v-for="option in dialectOptions" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
      </label>

      <label>
        <span>默认输入方式</span>
        <el-select v-model="form.preferredInputMode" style="width: 100%">
          <el-option v-for="option in inputModeOptions" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
      </label>
    </div>

    <div class="preference-summary">
      <span>语音习惯：{{ dialectLabel(form.preferredDialect) }}</span>
      <span>输入方式：{{ inputModeLabel(form.preferredInputMode) }}</span>
    </div>

    <div class="preference-learning" v-loading="suggestionsLoading">
      <div class="learning-head">
        <span>自动学习建议</span>
        <el-button link type="primary" :loading="suggestionsLoading" @click="loadSuggestions">刷新</el-button>
      </div>
      <div class="learning-list">
        <div v-for="item in suggestionRows" :key="item.key" class="learning-row">
          <div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.reason }}</p>
          </div>
          <el-button
            v-if="item.canApply"
            size="small"
            type="primary"
            :loading="saving"
            @click="applySuggestion(item.payload)"
          >
            应用
          </el-button>
          <span v-else class="learning-status">无需调整</span>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getPreferenceSuggestionsApi, updateUserPreferencesApi } from '../api/personalization'
import { normalizePreferenceSuggestions } from '../utils/normalizers'

const props = defineProps({
  preference: {
    type: Object,
    default: () => ({})
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['saved'])

const saving = ref(false)
const suggestionsLoading = ref(false)
const suggestions = ref(normalizePreferenceSuggestions({}))

const form = reactive({
  preferredDialect: 'auto',
  preferredInputMode: 'browser_speech'
})

const dialectOptions = [
  { label: '自动', value: 'auto' },
  { label: '普通话', value: 'mandarin' },
  { label: '粤语', value: 'cantonese' },
  { label: '西南口音', value: 'southwest' },
  { label: '东北口语', value: 'northeast' }
]
const inputModeOptions = [
  { label: '浏览器识别', value: 'browser_speech' },
  { label: '云端 ASR', value: 'cloud_asr' },
  { label: '文本输入', value: 'text' }
]

const suggestionRows = computed(() => [
  {
    key: 'dialect',
    title: '默认方言',
    reason: suggestions.value.dialect.reason,
    canApply: suggestions.value.dialect.canApply,
    payload: suggestions.value.dialect.applyPayload
  },
  {
    key: 'inputMode',
    title: '默认输入方式',
    reason: suggestions.value.inputMode.reason,
    canApply: suggestions.value.inputMode.canApply,
    payload: suggestions.value.inputMode.applyPayload
  }
])

watch(
  () => props.preference,
  (preference) => {
    form.preferredDialect = preference.preferredDialect || 'auto'
    form.preferredInputMode = preference.preferredInputMode || 'browser_speech'
  },
  { immediate: true, deep: true }
)

async function save() {
  saving.value = true
  try {
    const response = await updateUserPreferencesApi(
      {
        preferred_dialect: form.preferredDialect,
        preferred_input_mode: form.preferredInputMode
      },
      { rawEnvelope: true, suppressErrorMessage: true }
    )
    ElMessage.success(response.message || '个性化设置已保存')
    emit('saved', response.data)
    await loadSuggestions()
  } catch (error) {
    ElMessage.error(error.payload?.message || '保存个性化设置失败')
  } finally {
    saving.value = false
  }
}

async function applySuggestion(payload) {
  if (payload.preferred_dialect) form.preferredDialect = payload.preferred_dialect
  if (payload.preferred_input_mode) form.preferredInputMode = payload.preferred_input_mode
  await save()
}

async function loadSuggestions() {
  suggestionsLoading.value = true
  try {
    const data = await getPreferenceSuggestionsApi({ limit: 20 })
    suggestions.value = normalizePreferenceSuggestions(data)
  } finally {
    suggestionsLoading.value = false
  }
}

function dialectLabel(value) {
  return dialectOptions.find((item) => item.value === value)?.label || '自动'
}

function inputModeLabel(value) {
  return inputModeOptions.find((item) => item.value === value)?.label || '浏览器识别'
}

onMounted(loadSuggestions)
</script>
