<template>
  <el-dialog
    :model-value="modelValue"
    title="设备别名管理"
    width="680px"
    class="device-alias-dialog"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="alias-dialog-body">
      <el-form label-position="top">
        <div class="alias-form-grid">
          <el-form-item label="选择设备">
            <el-select v-model="form.deviceId" filterable style="width: 100%">
              <el-option
                v-for="device in devices"
                :key="device.id"
                :label="`${device.roomName || '-'} · ${device.name || '设备'}`"
                :value="device.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="别名">
            <el-input v-model="form.alias" maxlength="20" show-word-limit placeholder="例如：小灯" />
          </el-form-item>
        </div>
        <el-button type="primary" :loading="saving" :disabled="!canSubmit" @click="submit">新增别名</el-button>
      </el-form>

      <div class="alias-list" v-loading="loading">
        <el-empty v-if="!loading && !aliases.length" description="暂无设备别名" />
        <article v-for="alias in aliases" :key="alias.id">
          <div>
            <strong>{{ alias.alias }}</strong>
            <span>{{ alias.roomName }} · {{ alias.deviceName }} · {{ alias.deviceTypeLabel }}</span>
          </div>
          <el-button text type="danger" :loading="deletingId === alias.id" @click="remove(alias)">删除</el-button>
        </article>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createDeviceAliasApi, deleteDeviceAliasApi } from '../api/personalization'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  devices: {
    type: Array,
    default: () => []
  },
  aliases: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  saving: {
    type: Boolean,
    default: false
  },
  deletingId: {
    type: Number,
    default: null
  },
  initialDeviceId: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'refresh', 'update:saving', 'update:deletingId'])

const form = reactive({
  deviceId: null,
  alias: ''
})

const canSubmit = computed(() => {
  const alias = form.alias.trim()
  return Boolean(form.deviceId && alias.length >= 2 && alias.length <= 20)
})

watch(
  () => props.devices,
  (devices) => {
    if (props.initialDeviceId) form.deviceId = props.initialDeviceId
    if (!form.deviceId && devices.length) form.deviceId = devices[0].id
  },
  { immediate: true }
)

watch(
  () => props.initialDeviceId,
  (deviceId) => {
    if (deviceId) form.deviceId = deviceId
  }
)

async function submit() {
  if (!canSubmit.value) {
    ElMessage.warning('请选择设备并输入 2-20 个字符的别名')
    return
  }
  emit('update:saving', true)
  try {
    const response = await createDeviceAliasApi(
      { device_id: form.deviceId, alias: form.alias.trim() },
      { rawEnvelope: true, suppressErrorMessage: true }
    )
    ElMessage.success(response.message || '设备别名已保存')
    form.alias = ''
    emit('refresh')
  } catch (error) {
    ElMessage.error(error.payload?.message || '设备别名保存失败')
  } finally {
    emit('update:saving', false)
  }
}

async function remove(alias) {
  emit('update:deletingId', alias.id)
  try {
    const response = await deleteDeviceAliasApi(alias.id, { rawEnvelope: true, suppressErrorMessage: true })
    ElMessage.success(response.message || '设备别名已删除')
    emit('refresh')
  } catch (error) {
    ElMessage.error(error.payload?.message || '设备别名删除失败')
  } finally {
    emit('update:deletingId', null)
  }
}
</script>
