<template>
  <div class="concerts-page">
    <!-- 操作栏 -->
    <el-card class="toolbar-card">
      <el-row justify="space-between" align="middle">
        <el-col :span="12">
          <el-space>
            <el-input
              v-model="searchKeyword"
              placeholder="搜索演出名称"
              clearable
              style="width: 240px"
              :prefix-icon="Search"
            />
            <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 140px">
              <el-option label="全部" value="" />
              <el-option label="监控中" value="monitoring" />
              <el-option label="已暂停" value="paused" />
              <el-option label="已结束" value="ended" />
            </el-select>
          </el-space>
        </el-col>
        <el-col :span="12" style="text-align: right">
          <el-button type="primary" :icon="Plus" @click="showAddDialog = true">
            添加演出
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 演出列表 -->
    <el-card style="margin-top: 16px">
      <el-table :data="concertList" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="演出名称" min-width="180" />
        <el-table-column prop="venue" label="场馆" width="150" />
        <el-table-column prop="url" label="链接" min-width="200">
          <template #default="{ row }">
            <el-link :href="row.url" target="_blank" type="primary" :underline="false">
              {{ row.url }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_check" label="最后检测" width="160" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleScrape(row)">采集</el-button>
            <el-button size="small" type="warning" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        style="margin-top: 16px; justify-content: center"
      />
    </el-card>

    <!-- 添加/编辑对话框（占位 - 后续完善） -->
    <el-dialog
      v-model="showAddDialog"
      title="添加演出"
      width="600px"
      @close="resetForm"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="演出名称" required>
          <el-input v-model="form.name" placeholder="请输入演出名称" />
        </el-form-item>
        <el-form-item label="演出链接" required>
          <el-input v-model="form.url" placeholder="请输入票务平台链接" />
        </el-form-item>
        <el-form-item label="演出场馆">
          <el-input v-model="form.venue" placeholder="请输入场馆名称" />
        </el-form-item>
        <el-form-item label="监控频率(秒)">
          <el-input-number v-model="form.interval" :min="10" :max="3600" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const searchKeyword = ref('')
const statusFilter = ref('')
const loading = ref(false)
const showAddDialog = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const concertList = ref([])

const form = reactive({
  name: '',
  url: '',
  venue: '',
  interval: 60,
})

function statusTagType(status) {
  const map = { monitoring: 'success', paused: 'warning', ended: 'info' }
  return map[status] || 'info'
}

function resetForm() {
  form.name = ''
  form.url = ''
  form.venue = ''
  form.interval = 60
}

async function handleAdd() {
  // 后续接入API
  ElMessage.success('添加成功（功能开发中）')
  showAddDialog.value = false
  resetForm()
}

function handleEdit(row) {
  ElMessage.info('编辑功能开发中')
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定要删除该演出吗？', '确认删除', { type: 'warning' })
  ElMessage.success('删除成功（功能开发中）')
}

async function handleScrape(row) {
  ElMessage.info('数据采集功能开发中')
}

function loadConcerts() {
  // 后续接入API
  loading.value = false
}
</script>
