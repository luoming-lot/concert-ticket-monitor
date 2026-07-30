<template>
  <div class="settings-page">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 基本设置 -->
      <el-tab-pane label="基本设置" name="basic">
        <el-form :model="basicForm" label-width="150px">
          <el-form-item label="默认监控间隔(秒)">
            <el-input-number v-model="basicForm.monitor_interval" :min="10" :max="3600" />
            <span class="form-tip">建议值：30-120秒</span>
          </el-form-item>
          <el-form-item label="浏览器超时(毫秒)">
            <el-input-number v-model="basicForm.browser_timeout" :min="5000" :max="120000" :step="1000" />
          </el-form-item>
          <el-form-item label="无头模式">
            <el-switch v-model="basicForm.headless" />
            <span class="form-tip">关闭可在采集时看到浏览器窗口</span>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="saveBasic">保存设置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 邮件通知 -->
      <el-tab-pane label="邮件通知" name="email">
        <el-form :model="emailForm" label-width="120px">
          <el-form-item label="SMTP服务器">
            <el-input v-model="emailForm.smtp_host" placeholder="smtp.qq.com" />
          </el-form-item>
          <el-form-item label="SMTP端口">
            <el-input-number v-model="emailForm.smtp_port" :min="1" :max="65535" />
          </el-form-item>
          <el-form-item label="发件邮箱">
            <el-input v-model="emailForm.smtp_user" placeholder="your-email@qq.com" />
          </el-form-item>
          <el-form-item label="授权码/密码">
            <el-input v-model="emailForm.smtp_password" type="password" show-password />
          </el-form-item>
          <el-form-item>
            <el-input v-model="emailForm.test_email" placeholder="测试接收邮箱" style="width: 240px" />
            <el-button style="margin-left: 8px" :loading="testing.email" @click="testEmail">测试发送</el-button>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="saveEmail">保存设置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 企业微信 -->
      <el-tab-pane label="企业微信" name="wecom">
        <el-form :model="wecomForm" label-width="140px">
          <el-form-item label="Webhook URL">
            <el-input v-model="wecomForm.wecom_webhook" placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..." />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="saveWecom">保存设置</el-button>
            <el-button :loading="testing.wecom" @click="testWecom">测试发送</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 钉钉 -->
      <el-tab-pane label="钉钉机器人" name="dingtalk">
        <el-form :model="dingtalkForm" label-width="140px">
          <el-form-item label="Webhook URL">
            <el-input v-model="dingtalkForm.dingtalk_webhook" placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
          </el-form-item>
          <el-form-item label="加签密钥">
            <el-input v-model="dingtalkForm.dingtalk_secret" placeholder="SEC..." />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="saveDingtalk">保存设置</el-button>
            <el-button :loading="testing.dingtalk" @click="testDingtalk">测试发送</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { settingsAPI } from '@/api'

const activeTab = ref('basic')
const saving = ref(false)
const testing = reactive({ email: false, wecom: false, dingtalk: false })

const basicForm = reactive({
  monitor_interval: 60,
  browser_timeout: 30000,
  headless: true,
})

const emailForm = reactive({
  smtp_host: '',
  smtp_port: 587,
  smtp_user: '',
  smtp_password: '',
  test_email: '',
})

const wecomForm = reactive({
  wecom_webhook: '',
})

const dingtalkForm = reactive({
  dingtalk_webhook: '',
  dingtalk_secret: '',
})

async function loadSettings() {
  try {
    const res = await settingsAPI.get()
    basicForm.monitor_interval = parseInt(res.monitor_interval) || 60
    basicForm.browser_timeout = parseInt(res.browser_timeout) || 30000
    basicForm.headless = res.headless === 'true' || res.headless === true
    emailForm.smtp_host = res.smtp_host || ''
    emailForm.smtp_port = parseInt(res.smtp_port) || 587
    emailForm.smtp_user = res.smtp_user || ''
    emailForm.smtp_password = res.smtp_password || ''
    wecomForm.wecom_webhook = res.wecom_webhook || ''
    dingtalkForm.dingtalk_webhook = res.dingtalk_webhook || ''
    dingtalkForm.dingtalk_secret = res.dingtalk_secret || ''
  } catch (e) {
    // 首次加载可能为空，使用默认值
  }
}

async function saveSettings(data) {
  saving.value = true
  try {
    await settingsAPI.update(data)
    ElMessage.success('设置已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

function saveBasic() {
  saveSettings({
    monitor_interval: basicForm.monitor_interval,
    browser_timeout: basicForm.browser_timeout,
    headless: basicForm.headless,
  })
}

function saveEmail() {
  saveSettings({
    smtp_host: emailForm.smtp_host,
    smtp_port: emailForm.smtp_port,
    smtp_user: emailForm.smtp_user,
    smtp_password: emailForm.smtp_password,
  })
}

function saveWecom() {
  saveSettings({ wecom_webhook: wecomForm.wecom_webhook })
}

function saveDingtalk() {
  saveSettings({
    dingtalk_webhook: dingtalkForm.dingtalk_webhook,
    dingtalk_secret: dingtalkForm.dingtalk_secret,
  })
}

async function testEmail() {
  if (!emailForm.test_email) {
    ElMessage.warning('请先输入测试接收邮箱')
    return
  }
  testing.email = true
  try {
    await settingsAPI.testEmail({
      to: emailForm.test_email,
      subject: '演唱会票务监控系统 - 测试邮件',
      body: '如果您收到此邮件，说明邮件通知配置成功！'
    })
    ElMessage.success('测试邮件已发送')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '发送失败')
  } finally {
    testing.email = false
  }
}

async function testWecom() {
  testing.wecom = true
  try {
    await settingsAPI.testWecom({ message: '🎫 演唱会票务监控系统 - 测试消息' })
    ElMessage.success('企业微信通知已发送')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '发送失败')
  } finally {
    testing.wecom = false
  }
}

async function testDingtalk() {
  testing.dingtalk = true
  try {
    await settingsAPI.testDingtalk({ message: '🎫 演唱会票务监控系统 - 测试消息' })
    ElMessage.success('钉钉通知已发送')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '发送失败')
  } finally {
    testing.dingtalk = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.form-tip {
  margin-left: 8px;
  color: #909399;
  font-size: 13px;
}
</style>
