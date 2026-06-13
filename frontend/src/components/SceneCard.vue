<template>
  <article class="scene-card">
    <div class="scene-card-head">
      <div class="scene-icon">{{ shortName }}</div>
      <div>
        <span>Scene mode</span>
        <h3>{{ scene.name }}</h3>
      </div>
    </div>
    <p>{{ scene.description || '暂无场景描述' }}</p>
    <div class="scene-actions-list">
      <span v-for="action in scene.actions" :key="action.id">
        {{ action.deviceName || `设备 ${action.deviceId}` }}
      </span>
    </div>
    <el-button class="scene-run-button" :loading="busy" @click="$emit('run')">执行场景</el-button>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  scene: {
    type: Object,
    required: true
  },
  busy: {
    type: Boolean,
    default: false
  }
})

defineEmits(['run'])

const shortName = computed(() => props.scene.name?.slice(0, 1) || '景')
</script>
