<template>
  <div class="monitor-page">
    <!-- 控制栏 -->
    <el-card class="toolbar-card">
      <el-row justify="space-between" align="middle">
        <el-col :span="12">
          <el-space>
            <el-tag :type="monitorRunning ? 'success' : 'danger'" size="large">
              {{ monitorRunning ? '监控运行中' : '监控已停止' }}
            </el-tag>
            <span style="color: #909399; font-size: 13px">
              已运行 {{ runningTime }}
            </span>
          </el-space>
        </el-col>
        <el-col :span="12" style="text-align: right">
          <el-button
            :type="monitorRunning ? 'danger' : 'success'"
            @click="toggleMonitor"
          >
            {{ monitorRunning ? '停止监控' : '启动监控' }}
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 监控日志 -->
    <el-card style="margin-top: 16px">
      <template #header>
        <span>监控日志</span>
        <el-button size="small" style="float: right" @click="clearLogs">
          清空日志
        </el-button>
      </template>
      <div class="log-container" ref="logContainer">
        <div
          v-for="(log, index) in logEntries"
          :key="index"
          class="log-entry"
          :class="log.level"
        >
          <span class="log-time">{{ log.time }}</span>
          <span class="log-level">[{{ log.level.toUpperCase() }}]</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
        <el-empty v-if="logEntries.length === 0" description="暂无日志" />
      </div>
    </el-card>

    <!-- 状态历史 -->
    <el-card style="margin-top: 16px">
      <template #header>
        <span>状态变更历史</span>
      </template>
      <el-table :data="historyList" stripe size="small">
        <el-table-column prop="time" label="时间" width="180" />
        <el-table-column prop="concert" label="演出" min-width="150" />
        <el-table-column prop="show" label="场次" width="120" />
        <el-table-column prop="tier" label="票档" width="100" />
        <el-table-column prop="change" label="变更内容" min-width="200" />
        <el-table-column prop="type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="changeTagType(row.type)" size="small">
              {{ row.type }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'

const monitorRunning = ref(false)
const runningTime = ref('00:00:00')
const logEntries = ref([])
const historyList = ref([])
const logContainer = ref(null)

let timerInterval = null

function toggleMonitor() {
  monitorRunning.value = !monitorRunning.value
  // 后续接入监控服务
}

function clearLogs() {
  logEntries.value = []
}

function changeTagType(type) {
  const map = { stock: 'warning', price: 'danger', open: 'success' }
  return map[type] || 'info'
}

onUnmounted(() => {
  if (timerInterval) clearInterval(timerInterval)
})
</script>

<style scoped>
.log-container {
  max-height: 400px;
  overflow-y: auto;
  background: #1e1e1e;
  border-radius: 4px;
  padding: 12px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.8;
}

.log-entry {
  display: flex;
  gap: 8px;
}

.log-entry.info { color: #4fc3f7; }
.log-entry.warning { color: #ffa726; }
.log-entry.error { color: #ef5350; }
.log-entry.success { color: #66bb6a; }

.log-time {
  color: #888;
  min-width: 80px;
}

.log-level {
  min-width: 60px;
  font-weight: bold;
}
</style>
