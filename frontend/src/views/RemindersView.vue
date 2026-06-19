<template>
  <div class="reminders-page">
    <section class="table-toolbar">
      <div>
        <p class="panel-kicker">Reminder center</p>
        <h2>提醒管理</h2>
      </div>
      <el-button class="execute-button" type="primary" @click="openCreateDialog">新建提醒</el-button>
    </section>

    <section class="reminder-grid" v-loading="loading">
      <el-empty v-if="!loading && !reminders.length" description="暂无提醒，可通过页面或语音指令创建" />
      <article v-for="item in reminders" :key="item.id" class="reminder-card" :class="{ done: item.isDone }">
        <div class="reminder-card-head">
          <span>{{ item.isDone ? '已完成' : '待提醒' }}</span>
          <el-switch :model-value="item.isDone" @change="updateDone(item, $event)" />
        </div>
        <h3>{{ item.title }}</h3>
        <p>提醒时间：{{ formatDateTime(item.remindTime) }}</p>
        <small>创建时间：{{ formatDateTime(item.createdAt) }}</small>
        <div class="reminder-actions">
          <el-button class="ghost-action" text @click="openEditDialog(item)">编辑</el-button>
          <el-popconfirm title="确认删除这条提醒？" @confirm="removeReminder(item)">
            <template #reference>
              <el-button class="ghost-action" text>删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </article>
    </section>

    <el-dialog v-model="dialogVisible" :title="editingReminderId ? '编辑提醒' : '新建提醒'" width="460px">
      <el-form :model="form" label-position="top">
        <el-form-item label="提醒内容">
          <el-input v-model="form.title" maxlength="200" placeholder="例如：吃药" />
        </el-form-item>
        <el-form-item label="提醒时间">
          <el-date-picker
            v-model="form.remind_time"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="选择提醒时间"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveReminder">
          {{ editingReminderId ? '保存修改' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createReminderApi, deleteReminderApi, getRemindersApi, updateReminderApi } from '../api/reminder'
import { formatDateTime, normalizeReminder } from '../utils/normalizers'

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingReminderId = ref(null)
const reminders = ref([])
const form = reactive({
  title: '',
  remind_time: ''
})

async function loadReminders() {
  loading.value = true
  try {
    const data = await getRemindersApi()
    reminders.value = data.map(normalizeReminder)
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  editingReminderId.value = null
  form.title = ''
  form.remind_time = ''
  dialogVisible.value = true
}

function openEditDialog(item) {
  editingReminderId.value = item.id
  form.title = item.title
  form.remind_time = item.remindTime ? item.remindTime.slice(0, 19) : ''
  dialogVisible.value = true
}

async function saveReminder() {
  if (!form.title.trim()) {
    ElMessage.warning('请输入提醒内容')
    return
  }
  saving.value = true
  try {
    const payload = {
      title: form.title.trim(),
      remind_time: form.remind_time || null
    }
    if (editingReminderId.value) {
      await updateReminderApi(editingReminderId.value, payload)
      ElMessage.success('提醒修改成功')
    } else {
      await createReminderApi(payload)
      ElMessage.success('提醒创建成功')
    }
    dialogVisible.value = false
    editingReminderId.value = null
    form.title = ''
    form.remind_time = ''
    await loadReminders()
  } finally {
    saving.value = false
  }
}

async function updateDone(item, isDone) {
  await updateReminderApi(item.id, { is_done: isDone })
  ElMessage.success(isDone ? '提醒已标记完成' : '提醒已恢复待办')
  await loadReminders()
}

async function removeReminder(item) {
  await deleteReminderApi(item.id)
  ElMessage.success('提醒已删除')
  await loadReminders()
}

onMounted(loadReminders)
</script>
