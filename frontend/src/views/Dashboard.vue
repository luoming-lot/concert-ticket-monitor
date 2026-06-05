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
              <div class="stat-value">{{ stats.availableTickets }}</div>
              <div class="stat-label">有票场次</div>
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
              <div class="stat-value">{{ stats.alerts }}</div>
              <div class="stat-label">告警次数</div>
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
              <div class="stat-value">{{ stats.activeMonitors }}</div>
              <div class="stat-label">活跃监控</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="16">
        <el-card>
          <template #header>
            <span>库存变化趋势</span>
          </template>
          <div class="chart-container" style="height: 350px">
            <v-chart :option="chartOption" autoresize />
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>最近告警</span>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="alert in recentAlerts"
              :key="alert.id"
              :timestamp="alert.time"
              :type="alert.type"
            >
              {{ alert.message }}
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components'

use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
])

// 统计数据（占位 - 后续接入API）
const stats = reactive({
  concertCount: 0,
  availableTickets: 0,
  alerts: 0,
  activeMonitors: 0,
})

// 图表配置（占位）
const chartOption = ref({
  tooltip: { trigger: 'axis' },
  legend: { data: ['库存数量'] },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: [] },
  yAxis: { type: 'value' },
  series: [{ name: '库存数量', type: 'line', data: [] }],
})

// 最近告警（占位）
const recentAlerts = ref([])
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

.chart-container {
  width: 100%;
}
</style>
