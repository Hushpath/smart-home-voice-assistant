<template>
  <section class="placeholder-panel">
    <div class="panel-copy">
      <p class="panel-kicker">{{ kicker }}</p>
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>
    </div>
    <div class="panel-terminal">
      <span v-for="item in items" :key="item">{{ item }}</span>
    </div>
  </section>
</template>

<script setup>
defineProps({
  kicker: {
    type: String,
    default: 'Module standby'
  },
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    required: true
  },
  items: {
    type: Array,
    default: () => ['API 已封装', '页面待接入', '适合后续阶段扩展']
  }
})
</script>
