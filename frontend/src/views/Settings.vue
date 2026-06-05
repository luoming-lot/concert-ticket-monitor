<template>
  <div class="settings-page">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 基本设置 -->
      <el-tab-pane label="基本设置" name="basic">
        <el-form :model="basicForm" label-width="140px">
          <el-form-item label="默认监控间隔(秒)">
            <el-input-number v-model="basicForm.interval" :min="10" :max="3600" />
            <span class="form-tip">建议值：30-120秒</span>
          </el-form-item>
          <el-form-item label="浏览器超时(毫秒)">
            <el-input-number v-model="basicForm.timeout" :min="5000" :max="120000" :step="1000" />
          </el-form-item>
          <el-form-item label="无头模式">
            <el-switch v-model="basicForm.headless" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveBasic">保存设置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 邮件通知 -->
      <el-tab-pane label="邮件通知" name="email">
        <el-form :model="emailForm" label-width="120px">
          <el-form-item label="SMTP服务器">
            <el-input v-model="emailForm.host" placeholder="smtp.qq.com" />
          </el-form-item>
          <el-form-item label="SMTP端口">
            <el-input-number v-model="emailForm.port" :min="1" :max="65535" />
          </el-form-item>
          <el-form-item label="发件邮箱">
            <el-input v-model="emailForm.user" placeholder="your-email@qq.com" />
          </el-form-item>
          <el-form-item label="授权码/密码">
            <el-input v-model="emailForm.password" type="password" show-password />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveEmail">保存设置</el-button>
            <el-button @click="testEmail">测试发送</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 企业微信 -->
      <el-tab-pane label="企业微信" name="wecom">
        <el-form :model="wecomForm" label-width="140px">
          <el-form-item label="Webhook URL">
            <el-input v-model="wecomForm.webhook" placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..." />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveWecom">保存设置</el-button>
            <el-button @click="testWecom">测试发送</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 钉钉 -->
      <el-tab-pane label="钉钉机器人" name="dingtalk">
        <el-form :model="dingtalkForm" label-width="140px">
          <el-form-item label="Webhook URL">
            <el-input v-model="dingtalkForm.webhook" placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
          </el-form-item>
          <el-form-item label="加签密钥">
            <el-input v-model="dingtalkForm.secret" placeholder="SEC..." />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveDingtalk">保存设置</el-button>
            <el-button @click="testDingtalk">测试发送</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'

const activeTab = ref('basic')

const basicForm = reactive({
  interval: 60,
  timeout: 30000,
  headless: true,
})

const emailForm = reactive({
  host: 'smtp.qq.com',
  port: 587,
  user: '',
  password: '',
})

const wecomForm = reactive({
  webhook: '',
})

const dingtalkForm = reactive({
  webhook: '',
  secret: '',
})

function saveBasic() {
  ElMessage.success('基本设置已保存（功能开发中）')
}

function saveEmail() {
  ElMessage.success('邮件设置已保存（功能开发中）')
}

function saveWecom() {
  ElMessage.success('企业微信设置已保存（功能开发中）')
}

function saveDingtalk() {
  ElMessage.success('钉钉设置已保存（功能开发中）')
}

function testEmail() {
  ElMessage.info('测试邮件功能开发中')
}

function testWecom() {
  ElMessage.info('测试企业微信功能开发中')
}

function testDingtalk() {
  ElMessage.info('测试钉钉功能开发中')
}
</script>

<style scoped>
.form-tip {
  margin-left: 8px;
  color: #909399;
  font-size: 13px;
}
</style>
