<template>
  <div class="monitor-page">
    <!-- 控制栏 -->
    <el-card class="toolbar-card">
      <el-row justify="space-between" align="middle">
        <el-col :span="14">
          <el-space>
            <el-tag :type="monitorStatus.running ? 'success' : 'danger'" size="large">
              {{ monitorStatus.running ? '运行中' : '已停止' }}
            </el-tag>
            <span style="color: #606266">
              活跃任务: <b>{{ monitorStatus.active_jobs || 0 }}</b> 个
            </span>
            <span v-if="monitorStatus.start_time" style="color: #909399; font-size: 13px">
              已运行 {{ runningTime }}
            </span>
          </el-space>
        </el-col>
        <el-col :span="10" style="text-align: right">
          <el-button type="success" @click="handleStartAll" :loading="starting">
            <el-icon><VideoPlay /></el-icon>启动全部
          </el-button>
          <el-button type="danger" @click="handleStopAll" :loading="stopping">
            <el-icon><VideoPause /></el-icon>停止全部
          </el-button>
          <el-button @click="refreshAll">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 日志 + 历史 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>监控日志</span>
            <el-button size="small" style="float: right" @click="refreshLogs">
              刷新
            </el-button>
          </template>
          <div class="log-container" ref="logContainerRef">
            <div
              v-for="log in logs"
              :key="log.id"
              class="log-entry"
              :class="log.level || 'info'"
            >
              <span class="log-time">{{ formatTime(log.created_at) }}</span>
              <span class="log-level">{{ levelTag(log.level) }}</span>
              <span class="log-message">{{ log.message }}</span>
            </div>
            <el-empty v-if="logs.length === 0" description="暂无日志" />
          </div>
          <el-pagination
            v-if="logTotal > 20"
            v-model:current-page="logPage"
            :page-size="20"
            :total="logTotal"
            layout="prev, pager, next"
            size="small"
            style="margin-top: 8px; justify-content: center"
            @current-change="refreshLogs"
          />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>状态变更历史</span>
            <el-button size="small" style="float: right" @click="refreshHistory">
              刷新
            </el-button>
          </template>
          <el-table :data="history" size="small" max-height="420" stripe>
            <el-table-column prop="message" label="变更内容" min-width="180" show-overflow-tooltip />
            <el-table-column prop="change_type" label="类型" width="70">
              <template #default="{ row }">
                <el-tag :type="changeTagType(row.change_type)" size="small">
                  {{ changeLabel(row.change_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="150">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="history.length === 0" description="暂无变更记录" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { monitorAPI } from '@/api'

const monitorStatus = reactive({
  running: false,
  active_jobs: 0,
  start_time: null,
})

const logs = ref([])
const logTotal = ref(0)
const logPage = ref(1)
const history = ref([])
const logContainerRef = ref(null)

const starting = ref(false)
const stopping = ref(false)

let refreshTimer = null
let runningSeconds = 0

const runningTime = computed(() => {
  const h = Math.floor(runningSeconds / 3600)
  const m = Math.floor((runningSeconds % 3600) / 60)
  const s = runningSeconds % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleString('zh-CN')
}

function levelTag(level) {
  const map = { info: '[INFO]', warning: '[WARN]', error: '[ERROR]', success: '[OK]  ' }
  return map[level] || '[INFO]'
}

function changeTagType(type) {
  const map = { stock: 'warning', price: 'danger', open: 'success', sold_out: 'info' }
  return map[type] || 'info'
}

function changeLabel(type) {
  const map = { stock: '库存', price: '价格', open: '开售', sold_out: '售罄' }
  return map[type] || type || ''
}

async function fetchStatus() {
  try {
    const res = await monitorAPI.getStatus()
    monitorStatus.running = res.running
    monitorStatus.active_jobs = res.active_jobs
    monitorStatus.start_time = res.start_time
    if (res.running && res.start_time) {
      runningSeconds = Math.floor((Date.now() - new Date(res.start_time).getTime()) / 1000)
    }
  } catch (e) { /* ignore */ }
}

async function refreshLogs() {
  try {
    const res = await monitorAPI.getLogs({ page: logPage.value, page_size: 20 })
    logs.value = res?.items || []
    logTotal.value = res?.total || 0
  } catch (e) { /* ignore */ }
}

async function refreshHistory() {
  try {
    const res = await monitorAPI.getHistory({ page: 1, page_size: 20 })
    history.value = res?.items || []
  } catch (e) { /* ignore */ }
}

async function handleStartAll() {
  starting.value = true
  try {
    await monitorAPI.startAll()
    ElMessage.success('监控任务已启动')
    await refreshAll()
  } catch (e) {
    ElMessage.error('启动失败')
  } finally {
    starting.value = false
  }
}

async function handleStopAll() {
  stopping.value = true
  try {
    await monitorAPI.stopAll()
    ElMessage.success('所有监控任务已停止')
    await refreshAll()
  } catch (e) {
    ElMessage.error('停止失败')
  } finally {
    stopping.value = false
  }
}

async function refreshAll() {
  await Promise.all([fetchStatus(), refreshLogs(), refreshHistory()])
}

onMounted(() => {
  refreshAll()
  refreshTimer = setInterval(async () => {
    await fetchStatus()
    runningSeconds++
    // Auto-scroll log container
    if (logContainerRef.value) {
      logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
    }
  }, 10000) // Refresh status every 10s
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.log-container {
  max-height: 420px;
  overflow-y: auto;
  background: #1e1e1e;
  border-radius: 6px;
  padding: 12px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.8;
}

.log-entry {
  display: flex;
  gap: 8px;
  word-break: break-all;
}

.log-entry.info { color: #4fc3f7; }
.log-entry.warning { color: #ffa726; }
.log-entry.error { color: #ef5350; }
.log-entry.success { color: #66bb6a; }

.log-time {
  color: #888;
  min-width: 140px;
  flex-shrink: 0;
}

.log-level {
  min-width: 52px;
  font-weight: bold;
  flex-shrink: 0;
}
</style>
