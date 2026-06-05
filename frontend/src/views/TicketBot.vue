<template>
  <div class="bot-page">
    <el-row :gutter="20">
      <!-- 左侧：配置表单 -->
      <el-col :span="14">
        <el-card>
          <template #header>
            <span>抢票配置</span>
            <el-tag v-if="botStatus.running" type="danger" style="float: right">运行中</el-tag>
            <el-tag v-else type="info" style="float: right">待机</el-tag>
          </template>

          <el-form :model="form" label-width="110px">
            <el-form-item label="目标演出URL" required>
              <el-input v-model="form.target_url" placeholder="https://detail.damai.cn/item.htm?id=xxxxxx" />
            </el-form-item>

            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="演出城市">
                  <el-input v-model="form.city" placeholder="如：杭州" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="购票数量">
                  <el-tag>{{ form.users.length }} 张</el-tag>
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="观演人姓名" required>
              <el-select
                v-model="form.users"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="输入观演人姓名后回车添加"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="场次日期">
              <el-select
                v-model="form.dates"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="支持多种格式：2026-04-11 / 4月11日 / 2026.04.11"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="票价">
              <el-select
                v-model="form.prices"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="支持多种格式：680 / ¥680 / 680元"
                style="width: 100%"
              />
            </el-form-item>

            <el-divider>高级设置</el-divider>

            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="快速模式">
                  <el-switch v-model="form.fast_mode" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="监听缺货">
                  <el-switch v-model="form.if_listen" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="自动提交">
                  <el-switch v-model="form.if_commit_order" />
                  <el-tooltip content="首次使用建议关闭，先手动确认订单信息正确">
                    <el-icon style="margin-left: 4px; color: #909399"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="最大重试次数">
                  <el-input-number v-model="form.max_retries" :min="1" :max="100000" :step="100" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="页面加载等待(秒)">
                  <el-input-number v-model="form.page_load_delay" :min="0.5" :max="30" :step="0.5" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item>
              <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
              <el-button :loading="saving" @click="loadConfig">加载配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：控制面板 + 日志 -->
      <el-col :span="10">
        <!-- 控制面板 -->
        <el-card>
          <template #header>
            <span>控制面板</span>
          </template>

          <div class="control-center">
            <div class="stage-display">
              <el-steps :active="stageIndex" direction="vertical" :space="40">
                <el-step title="启动浏览器" :description="stageDesc('launch')" />
                <el-step title="扫码登录" :description="stageDesc('login')" />
                <el-step title="选择场次票价" :description="stageDesc('select')" />
                <el-step title="轮询预订" :description="stageDesc('polling')" />
                <el-step title="选择观演人" :description="stageDesc('select_users')" />
                <el-step title="提交订单" :description="stageDesc('submit')" />
              </el-steps>
            </div>

            <div class="control-buttons" style="margin-top: 20px; text-align: center">
              <el-checkbox v-model="headlessMode" :disabled="botStatus.running" style="margin-right: 12px">
                无头模式
              </el-checkbox>
              <el-button
                type="success"
                size="large"
                :loading="starting"
                :disabled="botStatus.running"
                @click="handleStart"
              >
                开始抢票
              </el-button>
              <el-button
                type="danger"
                size="large"
                :disabled="!botStatus.running"
                @click="handleStop"
              >
                停止
              </el-button>
            </div>

            <div v-if="botStatus.running" class="run-stats" style="margin-top: 16px; text-align: center">
              <el-descriptions :column="2" size="small" border>
                <el-descriptions-item label="当前阶段">
                  <el-tag>{{ stageLabel(botStatus.stage) }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="重试次数">
                  {{ botStatus.retry_count }} / {{ botStatus.max_retries }}
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </div>
        </el-card>

        <!-- 运行日志 -->
        <el-card style="margin-top: 16px">
          <template #header>
            <span>运行日志</span>
            <el-button size="small" style="float: right" @click="refreshStatus">刷新</el-button>
          </template>
          <div class="bot-log-container">
            <div
              v-for="(log, idx) in botStatus.recent_logs?.slice().reverse() || []"
              :key="idx"
              class="bot-log-entry"
              :class="log.level"
            >
              <span class="log-t">{{ formatLogTime(log.time) }}</span>
              <span class="log-m">{{ log.message }}</span>
            </div>
            <el-empty v-if="!botStatus.recent_logs?.length" description="暂无日志" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'
import { botAPI } from '@/api'

const saving = ref(false)
const starting = ref(false)
const headlessMode = ref(true)
let statusTimer = null

const form = reactive({
  target_url: '',
  users: [],
  index_url: 'https://www.damai.cn/',
  login_url: 'https://passport.damai.cn/login',
  city: '',
  dates: [],
  prices: [],
  fast_mode: true,
  if_listen: true,
  if_commit_order: false,
  max_retries: 1000,
  page_load_delay: 2.0,
})

const botStatus = reactive({
  running: false,
  stage: 'idle',
  start_time: null,
  retry_count: 0,
  max_retries: 0,
  recent_logs: [],
})

const stageMap = { launch: 0, login: 1, select: 2, polling: 3, select_users: 4, submit: 5, done: 6 }
const stageIndex = computed(() => stageMap[botStatus.stage] ?? 0)

function stageLabel(s) {
  const map = { idle: '待命', launch: '启动浏览器', login: '扫码登录', select: '选择场次票价',
    polling: '轮询预订中', select_users: '选择观演人', submit: '提交订单', done: '已完成' }
  return map[s] || s
}

function stageDesc(s) {
  const map = {
    launch: '打开Chrome浏览器',
    login: '等待手机扫码登录',
    select: '自动选择城市/场次/票价/数量',
    polling: '循环检测预订按钮',
    select_users: '按顺序勾选观演人',
    submit: '点击提交按钮',
  }
  return map[s] || ''
}

function formatLogTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleTimeString('zh-CN')
}

// Vue computed workaround for script setup
import { computed } from 'vue'

async function loadConfig() {
  try {
    const res = await botAPI.getConfig()
    Object.assign(form, res.config || {})
    ElMessage.success('配置已加载')
  } catch (e) {
    ElMessage.error('加载配置失败')
  }
}

async function saveConfig() {
  if (!form.target_url) {
    ElMessage.warning('请填写目标演出URL')
    return
  }
  if (!form.users.length) {
    ElMessage.warning('请添加至少一个观演人')
    return
  }
  saving.value = true
  try {
    await botAPI.updateConfig({
      target_url: form.target_url,
      users: form.users,
      city: form.city,
      dates: form.dates,
      prices: form.prices,
      fast_mode: form.fast_mode,
      if_listen: form.if_listen,
      if_commit_order: form.if_commit_order,
      max_retries: form.max_retries,
      page_load_delay: form.page_load_delay,
    })
    ElMessage.success('配置已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function handleStart() {
  await saveConfig()
  if (!form.target_url || !form.users.length) return

  if (form.if_commit_order) {
    await ElMessageBox.confirm(
      '已开启「自动提交订单」，确认后系统将自动完成下单。\n\n请确保：\n1. 观演人姓名与账号中完全一致\n2. 票款余额充足\n3. 已了解平台规则',
      '⚠️ 确认自动下单',
      { confirmButtonText: '我确认', cancelButtonText: '取消', type: 'warning' }
    )
  }

  starting.value = true
  try {
    await botAPI.start({ headless: headlessMode.value })
    ElMessage.success('抢票引擎已启动，请查看浏览器窗口')
    refreshStatus()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '启动失败')
  } finally {
    starting.value = false
  }
}

async function handleStop() {
  try {
    await ElMessageBox.confirm('确定要停止抢票吗？', '确认停止', { type: 'warning' })
    await botAPI.stop()
    ElMessage.success('已发送停止信号')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('停止失败')
  }
}

async function refreshStatus() {
  try {
    const res = await botAPI.getStatus()
    Object.assign(botStatus, res)
  } catch (e) { /* ignore */ }
}

onMounted(() => {
  loadConfig()
  refreshStatus()
  statusTimer = setInterval(refreshStatus, 3000)
})

onUnmounted(() => {
  if (statusTimer) clearInterval(statusTimer)
})
</script>

<style scoped>
.bot-log-container {
  max-height: 300px;
  overflow-y: auto;
  background: #1e1e1e;
  border-radius: 6px;
  padding: 10px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  line-height: 1.7;
}

.bot-log-entry {
  display: flex;
  gap: 6px;
}

.bot-log-entry.info { color: #4fc3f7; }
.bot-log-entry.warning { color: #ffa726; }
.bot-log-entry.error { color: #ef5350; }
.bot-log-entry.success { color: #66bb6a; }

.log-t {
  color: #888;
  min-width: 70px;
  flex-shrink: 0;
}

.control-center {
  min-height: 320px;
}
</style>
