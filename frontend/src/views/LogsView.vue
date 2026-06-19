<template>
  <div class="logs-page">
    <section class="table-toolbar">
      <div>
        <p class="panel-kicker">Command audit</p>
        <h2>操作日志</h2>
      </div>
      <div class="toolbar-actions">
        <el-input v-model="keyword" clearable placeholder="搜索指令、trace_id 或错误信息" />
        <el-select v-model="statusFilter" style="width: 130px">
          <el-option label="全部结果" value="all" />
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failed" />
        </el-select>
        <el-button class="refresh-button" :disabled="!filteredLogs.length" @click="exportLogs">导出 CSV</el-button>
        <el-button class="refresh-button" :loading="loading" @click="loadLogs">刷新日志</el-button>
      </div>
    </section>

    <section class="glass-table-card">
      <el-table :data="pagedLogs" v-loading="loading" row-key="id" empty-text="暂无指令日志">
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="trace_id" min-width="190" show-overflow-tooltip>
          <template #default="{ row }">{{ safe(row.traceId) }}</template>
        </el-table-column>
        <el-table-column label="原始指令" min-width="190" show-overflow-tooltip>
          <template #default="{ row }">{{ safe(row.commandText || row.rawCommand) }}</template>
        </el-table-column>
        <el-table-column label="输入来源" width="120">
          <template #default="{ row }">{{ safe(row.inputSourceLabel) }}</template>
        </el-table-column>
        <el-table-column label="ASR" width="110">
          <template #default="{ row }">{{ safe(row.asrProvider) }}</template>
        </el-table-column>
        <el-table-column label="意图" width="130">
          <template #default="{ row }">
            <el-tag effect="plain" round>{{ safe(row.intent) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="房间" width="100">
          <template #default="{ row }">{{ safe(row.room) }}</template>
        </el-table-column>
        <el-table-column label="设备" width="110">
          <template #default="{ row }">{{ safe(row.deviceType) }}</template>
        </el-table-column>
        <el-table-column label="置信度" width="120">
          <template #default="{ row }">
            <span v-if="row.confidence !== null && row.confidence !== undefined">
              {{ row.confidenceLabel }} {{ Math.round(row.confidence * 100) }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="100">
          <template #default="{ row }">
            <el-tag :type="row.success ? 'success' : 'danger'" effect="dark" round>
              {{ row.success ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="消息" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ safe(row.message || row.errorMessage) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="table-pagination">
        <span>共 {{ filteredLogs.length }} 条记录</span>
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          layout="prev, pager, next"
          :total="filteredLogs.length"
        />
      </div>
    </section>

    <LogDetailDrawer v-model="detailVisible" :log="selectedLog" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getCommandLogsApi } from '../api/command'
import LogDetailDrawer from '../components/LogDetailDrawer.vue'
import { cleanText, formatDateTime, formatJson, normalizeCommandLog, summarizeCommandExecution } from '../utils/normalizers'

const route = useRoute()
const loading = ref(false)
const logs = ref([])
const keyword = ref('')
const statusFilter = ref('all')
const currentPage = ref(1)
const detailVisible = ref(false)
const selectedLog = ref(null)
const pageSize = 8

const filteredLogs = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return logs.value.filter((log) => {
    const matchStatus =
      statusFilter.value === 'all' ||
      (statusFilter.value === 'success' && log.success) ||
      (statusFilter.value === 'failed' && !log.success)
    const haystack = [
      log.traceId,
      log.commandText,
      log.rawCommand,
      log.inputSourceLabel,
      log.asrProvider,
      log.intent,
      log.room,
      log.deviceType,
      log.message,
      log.errorMessage,
      summarizeCommandExecution(log.executionResult),
      formatJson(log.detail)
    ].join(' ').toLowerCase()
    return matchStatus && (!text || haystack.includes(text))
  })
})

const pagedLogs = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredLogs.value.slice(start, start + pageSize)
})

async function loadLogs() {
  loading.value = true
  try {
    const data = await getCommandLogsApi()
    logs.value = data.map(normalizeCommandLog)
    currentPage.value = 1
  } finally {
    loading.value = false
  }
}

function exportLogs() {
  const headers = ['ID', 'trace_id', '指令文本', '输入来源', 'ASR', '意图', '房间', '设备', '置信度', '结果', '消息', '创建时间']
  const rows = filteredLogs.value.map((log) => [
    log.id,
    log.traceId,
    log.commandText,
    log.inputSourceLabel,
    log.asrProvider,
    log.intent,
    log.room,
    log.deviceType,
    log.confidence === null || log.confidence === undefined ? '' : `${Math.round(log.confidence * 100)}%`,
    log.success ? '成功' : '失败',
    log.message || log.errorMessage,
    formatDateTime(log.createdAt)
  ])
  const csv = [headers, ...rows]
    .map((row) => row.map((cell) => `"${String(cell ?? '').replaceAll('"', '""')}"`).join(','))
    .join('\r\n')
  const blob = new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `command-logs-${Date.now()}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

function openDetail(log) {
  selectedLog.value = log
  detailVisible.value = true
}

function safe(value) {
  return cleanText(value)
}

watch([keyword, statusFilter], () => {
  currentPage.value = 1
})

onMounted(() => {
  if (route.query.trace_id) keyword.value = String(route.query.trace_id)
  loadLogs()
})
</script>
