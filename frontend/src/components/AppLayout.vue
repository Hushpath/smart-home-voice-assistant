<template>
  <el-container class="app-layout">
    <el-aside class="layout-aside" width="252px">
      <div class="brand">
        <div class="brand-mark">AI</div>
        <div>
          <div class="brand-title">智能家居助手</div>
          <div class="brand-subtitle">Voice Home Console</div>
        </div>
      </div>

      <el-menu
        class="side-menu"
        :default-active="$route.path"
        router
        background-color="transparent"
        text-color="#9fb4cc"
        active-text-color="#e9fbff"
      >
        <el-menu-item index="/dashboard">Dashboard</el-menu-item>
        <el-menu-item index="/devices">设备管理</el-menu-item>
        <el-menu-item index="/voice">语音控制</el-menu-item>
        <el-menu-item index="/logs">操作日志</el-menu-item>
        <el-menu-item index="/reminders">提醒管理</el-menu-item>
        <el-menu-item index="/scenes">场景模式</el-menu-item>
      </el-menu>

      <div class="aside-footer">
        <span class="signal-dot"></span>
        后端 API：/api
      </div>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <div>
          <div class="route-eyebrow">Smart home voice interaction</div>
          <h1>{{ $route.meta.title || 'Dashboard' }}</h1>
        </div>
        <div class="user-panel">
          <div class="user-avatar">{{ avatarText }}</div>
          <div class="user-meta">
            <span>{{ authStore.displayName }}</span>
            <small>JWT 已连接</small>
          </div>
          <el-button class="logout-button" plain @click="handleLogout">退出</el-button>
        </div>
      </el-header>

      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const router = useRouter()
const authStore = useAuthStore()

const avatarText = computed(() => authStore.displayName.slice(0, 1).toUpperCase())

function handleLogout() {
  authStore.logout()
  router.replace('/login')
}
</script>
