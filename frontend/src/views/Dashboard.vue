<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #409EFF">
              <el-icon :size="28"><VideoCamera /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.concertCount }}</div>
              <div class="stat-label">监控演出</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #67C23A">
              <el-icon :size="28"><Ticket /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.showCount }}</div>
              <div class="stat-label">监控场次</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #E6A23C">
              <el-icon :size="28"><Warning /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.alertCount }}</div>
              <div class="stat-label">状态变更</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #F56C6C">
              <el-icon :size="28"><Monitor /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.runningJobs }}</div>
              <div class="stat-label">活跃监控</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="14">
        <el-card>
          <template #header>
            <span>最近告警</span>
          </template>
          <el-table :data="recentHistory" size="small" max-height="300" stripe>
            <el-table-column prop="message" label="变更内容" min-width="250" />
            <el-table-column prop="change_type" label="类型" width="80">
              <template #default="{ row }">
                <el-tag :type="changeTagType(row.change_type)" size="small">
                  {{ changeLabel(row.change_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="170">
              <template #default="{ row }">
                {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '' }}
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="recentHistory.length === 0" description="暂无告警记录" />
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card>
          <template #header>
            <span>最近日志</span>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="log in recentLogs"
              :key="log.id"
              :timestamp="log.created_at ? new Date(log.created_at).toLocaleString('zh-CN') : ''"
              :type="logLevelType(log.level)"
              placement="top"
            >
              {{ log.message?.substring(0, 80) }}
            </el-timeline-item>
          </el-timeline>
          <el-empty v-if="recentLogs.length === 0" description="暂无监控日志" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { concertAPI, monitorAPI } from '@/api'

const stats = reactive({
  concertCount: 0,
  showCount: 0,
  alertCount: 0,
  runningJobs: 0,
})

const recentHistory = ref([])
const recentLogs = ref([])

function changeTagType(type) {
  const map = { stock: 'warning', price: 'danger', open: 'success', sold_out: 'info' }
  return map[type] || 'info'
}

function changeLabel(type) {
  const map = { stock: '库存', price: '价格', open: '开售', sold_out: '售罄' }
  return map[type] || type || ''
}

function logLevelType(level) {
  const map = { info: 'info', warning: 'warning', error: 'danger', success: 'success' }
  return map[level] || 'info'
}

async function loadDashboard() {
  try {
    // 加载演出统计
    const concertRes = await concertAPI.getList({ page: 1, page_size: 1 })
    stats.concertCount = concertRes.total || 0

    // 统计有票场次
    let showTotal = 0
    if (concertRes.items?.length > 0) {
      for (const c of concertRes.items ?? []) {
        try {
          const detail = await concertAPI.getDetail(c.id)
          showTotal += (detail.shows || []).length
        } catch (e) { /* skip */ }
      }
    }
    stats.showCount = showTotal

    // 监控状态
    try {
      const monitorStatus = await monitorAPI.getStatus()
      stats.runningJobs = monitorStatus?.active_jobs || 0
    } catch (e) {
      stats.runningJobs = 0
    }

    // 最近历史变更
    try {
      const historyRes = await monitorAPI.getHistory({ page: 1, page_size: 10 })
      recentHistory.value = historyRes?.items || []
      stats.alertCount = historyRes?.total || 0
    } catch (e) {
      recentHistory.value = []
    }

    // 最近日志
    try {
      const logRes = await monitorAPI.getLogs({ page: 1, page_size: 6 })
      recentLogs.value = logRes?.items || []
    } catch (e) {
      recentLogs.value = []
    }
  } catch (e) {
    // 静默处理
  }
}

onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
.stats-row {
  margin-bottom: 0;
}

.stat-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}
</style>
