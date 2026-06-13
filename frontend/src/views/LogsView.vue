<template>
  <div class="logs-page">
    <section class="table-toolbar">
      <div>
        <p class="panel-kicker">Command audit</p>
        <h2>操作日志</h2>
        <p>展示后端 command_logs 表中当前用户的指令执行记录。</p>
      </div>
      <div class="toolbar-actions">
        <el-input v-model="keyword" clearable placeholder="搜索指令或错误信息" />
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
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="log-expand">
              <div>
                <label>解析结果</label>
                <pre>{{ formatJson(row.parsedResult) }}</pre>
              </div>
              <div>
                <label>执行结果</label>
                <pre>{{ formatJson(row.executionResult) }}</pre>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="rawCommand" label="指令文本" min-width="180" />
        <el-table-column label="意图" width="150">
          <template #default="{ row }">
            <el-tag effect="plain" round>{{ row.intent || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="130">
          <template #default="{ row }">
            <span v-if="row.confidence !== null && row.confidence !== undefined">
              {{ row.confidenceLabel }} {{ Math.round(row.confidence * 100) }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="执行摘要" min-width="220">
          <template #default="{ row }">{{ summarizeCommandExecution(row.executionResult) }}</template>
        </el-table-column>
        <el-table-column label="结果" width="110">
          <template #default="{ row }">
            <el-tag :type="row.success ? 'success' : 'danger'" effect="dark" round>
              {{ row.success ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="errorMessage" label="错误信息" min-width="160" show-overflow-tooltip />
        <el-table-column label="时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
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

    <el-dialog v-model="detailVisible" title="解析详情" width="760px" destroy-on-close>
      <div v-if="selectedLog" class="log-detail-dialog">
        <div class="result-tags">
          <span>原始文本：{{ selectedLog.parsedResult.originalText || selectedLog.rawCommand || '-' }}</span>
          <span>标准化：{{ selectedLog.parsedResult.normalizedText || '-' }}</span>
          <span>意图：{{ selectedLog.intent || '-' }}</span>
          <span>置信度：{{ selectedLog.confidenceLabel }} {{ selectedLog.confidence !== null ? Math.round(selectedLog.confidence * 100) + '%' : '' }}</span>
          <span>匹配方式：{{ selectedLog.parsedResult.matchType || '-' }}</span>
        </div>
        <div class="log-detail-grid">
          <div>
            <label>意图打分</label>
            <pre>{{ formatJson(selectedLog.parsedResult.parseDetail?.intent_scores) }}</pre>
          </div>
          <div>
            <label>关键词</label>
            <pre>{{ formatJson(selectedLog.parsedResult.matchedKeywords) }}</pre>
          </div>
          <div>
            <label>房间匹配</label>
            <pre>{{ formatJson(selectedLog.parsedResult.parseDetail?.room_match) }}</pre>
          </div>
          <div>
            <label>设备匹配</label>
            <pre>{{ formatJson(selectedLog.parsedResult.parseDetail?.device_match) }}</pre>
          </div>
          <div>
            <label>参数抽取</label>
            <pre>{{ formatJson(selectedLog.parsedResult.parseDetail?.value_extract) }}</pre>
          </div>
          <div>
            <label>执行结果</label>
            <pre>{{ formatJson(selectedLog.executionResult) }}</pre>
          </div>
        </div>
        <el-collapse>
          <el-collapse-item title="Raw JSON" name="raw">
            <pre>{{ formatJson(selectedLog) }}</pre>
          </el-collapse-item>
        </el-collapse>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { getCommandLogsApi } from '../api/command'
import { formatDateTime, formatJson, normalizeCommandLog, summarizeCommandExecution } from '../utils/normalizers'

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
      log.rawCommand,
      log.errorMessage,
      summarizeCommandExecution(log.executionResult),
      formatJson(log.parsedResult),
      formatJson(log.executionResult)
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
  const headers = ['ID', '指令文本', '意图', '执行摘要', '结果', '错误信息', '创建时间']
  const rows = filteredLogs.value.map((log) => [
    log.id,
    log.rawCommand,
    log.intent || '-',
    summarizeCommandExecution(log.executionResult),
    log.success ? '成功' : '失败',
    log.errorMessage || '',
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

watch([keyword, statusFilter], () => {
  currentPage.value = 1
})

onMounted(loadLogs)
</script>
