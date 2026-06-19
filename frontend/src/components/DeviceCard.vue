<template>
  <article class="device-card" :class="{ 'is-offline': !device.isOnline, 'is-on': device.isOn }">
    <div class="device-card-top">
      <div class="device-icon" :data-type="device.type">{{ iconText }}</div>
      <div class="device-title">
        <span>{{ device.roomName || '未分配房间' }}</span>
        <h3>{{ device.name }}</h3>
      </div>
      <el-tag :type="device.isOnline ? 'success' : 'danger'" effect="dark" round>
        {{ device.isOnline ? '在线' : '离线' }}
      </el-tag>
    </div>

    <div class="device-state-row">
      <div>
        <small>设备类型</small>
        <strong>{{ device.typeLabel }}</strong>
      </div>
      <div>
        <small>当前状态</small>
        <strong>{{ device.isOn ? '开启' : '关闭' }}</strong>
      </div>
    </div>

    <div class="device-props">
      <span v-for="item in device.propertyBadges" :key="`${item.label}-${item.value}`">
        <small>{{ item.label }}</small>
        <b>{{ item.value }}</b>
      </span>
    </div>

    <div class="device-actions">
      <el-switch
        :model-value="device.isOn"
        :disabled="!device.isOnline || busy"
        :loading="busy"
        active-text="开启"
        inactive-text="关闭"
        @change="$emit('toggle', $event)"
      />
      <div class="device-action-buttons">
        <el-button class="ghost-action" text @click="$emit('detail')">详情</el-button>
        <el-button v-if="canAdjust" class="ghost-action" text @click="$emit('adjust')">调节</el-button>
        <el-button class="ghost-action" text @click="$emit('history')">历史记录</el-button>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  device: {
    type: Object,
    required: true
  },
  busy: {
    type: Boolean,
    default: false
  }
})

defineEmits(['toggle', 'history', 'adjust', 'detail'])

const iconText = computed(() => {
  const map = {
    desk_lamp: '台',
    bedside_lamp: '床',
    light: '灯',
    air_conditioner: '空',
    tv: '视',
    curtain: '帘',
    fan: '风',
    robot_vacuum: '扫',
    speaker: '音',
    humidifier: '湿',
    air_purifier: '净',
    smart_plug: '插',
    fridge: '冰',
    smoke_sensor: '烟'
  }
  return map[props.device.type] || '控'
})

const canAdjust = computed(() => {
  return [
    'light',
    'desk_lamp',
    'bedside_lamp',
    'air_conditioner',
    'tv',
    'curtain',
    'fan',
    'speaker',
    'humidifier',
    'air_purifier',
    'smart_plug',
    'fridge'
  ].includes(props.device.type)
})
</script>
