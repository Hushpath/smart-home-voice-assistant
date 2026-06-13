<template>
  <main class="login-page">
    <section class="login-hero">
      <div class="voice-orbit">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <p class="login-eyebrow">Smart home voice interaction</p>
      <h1>用一句中文指令，控制整套虚拟家居。</h1>
      <p class="login-summary">
        前端接入 FastAPI 后端，完成 JWT 登录后进入统一控制台。当前阶段只实现认证、路由、布局和页面骨架。
      </p>
      <div class="demo-commands">
        <span>打开客厅灯</span>
        <span>开启睡眠模式</span>
        <span>查询北京天气</span>
      </div>
    </section>

    <section class="login-card">
      <div class="card-heading">
        <span>Console access</span>
        <h2>登录系统</h2>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" size="large" autocomplete="username" placeholder="testuser" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            size="large"
            type="password"
            autocomplete="current-password"
            placeholder="test123456"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-button class="login-button" size="large" type="primary" :loading="authStore.loading" @click="handleLogin">
          登录并进入 Dashboard
        </el-button>
      </el-form>

      <div class="default-account">
        默认账号：<strong>testuser</strong> / <strong>test123456</strong>
      </div>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const formRef = ref()

const form = reactive({
  username: 'testuser',
  password: 'test123456'
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleLogin() {
  await formRef.value?.validate()
  await authStore.login(form)
  ElMessage.success('登录成功')
  router.replace(route.query.redirect || '/dashboard')
}
</script>
