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
              @keyup.enter="loadConcerts"
            />
            <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 140px"
              @change="loadConcerts">
              <el-option label="全部" value="" />
              <el-option label="监控中" value="monitoring" />
              <el-option label="已暂停" value="paused" />
              <el-option label="已结束" value="ended" />
            </el-select>
          </el-space>
        </el-col>
        <el-col :span="12" style="text-align: right">
          <el-button type="primary" :icon="Plus" @click="openAddDialog">
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
        <el-table-column prop="venue" label="场馆" width="140" />
        <el-table-column prop="url" label="链接" min-width="200">
          <template #default="{ row }">
            <el-link :href="row.url" target="_blank" type="primary" :underline="false" style="max-width: 250px">
              {{ row.url?.substring(0, 50) }}...
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="monitor_interval" label="监控间隔" width="100">
          <template #default="{ row }">{{ row.monitor_interval }}s</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_check" label="最后检测" width="160">
          <template #default="{ row }">
            {{ row.last_check ? new Date(row.last_check).toLocaleString('zh-CN') : '未检测' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button size="small" :loading="scrapingId === row.id" @click="handleScrape(row)">采集</el-button>
            <el-button size="small" type="warning" @click="openEditDialog(row)">编辑</el-button>
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
        @current-change="loadConcerts"
      />
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="showDialog"
      :title="isEdit ? '编辑演出' : '添加演出'"
      width="600px"
      @close="resetForm"
    >
      <el-form :model="form" label-width="110px">
        <el-form-item label="演出名称" required>
          <el-input v-model="form.name" placeholder="请输入演出名称" />
        </el-form-item>
        <el-form-item label="演出链接" required>
          <el-input v-model="form.url" placeholder="请输入票务平台链接" />
        </el-form-item>
        <el-form-item label="演出场馆">
          <el-input v-model="form.venue" placeholder="请输入场馆名称" />
        </el-form-item>
        <el-form-item label="平台标识">
          <el-input v-model="form.platform" placeholder="如: damai, maoyan" />
        </el-form-item>
        <el-form-item label="监控频率(秒)">
          <el-input-number v-model="form.monitor_interval" :min="10" :max="3600" />
        </el-form-item>
        <el-form-item v-if="isEdit" label="状态">
          <el-select v-model="form.status" style="width: 160px">
            <el-option label="监控中" value="monitoring" />
            <el-option label="已暂停" value="paused" />
            <el-option label="已结束" value="ended" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { concertAPI } from '@/api'

const searchKeyword = ref('')
const statusFilter = ref('')
const loading = ref(false)
const saving = ref(false)
const scrapingId = ref(null)
const showDialog = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const concertList = ref([])

const form = reactive({
  name: '',
  url: '',
  venue: '',
  platform: '',
  monitor_interval: 60,
  status: 'monitoring',
})

function statusTagType(status) {
  const map = { monitoring: 'success', paused: 'warning', ended: 'info' }
  return map[status] || 'info'
}

function statusLabel(status) {
  const map = { monitoring: '监控中', paused: '已暂停', ended: '已结束' }
  return map[status] || status
}

function resetForm() {
  Object.assign(form, {
    name: '', url: '', venue: '', platform: '', monitor_interval: 60, status: 'monitoring'
  })
  isEdit.value = false
  editId.value = null
}

function openAddDialog() {
  resetForm()
  showDialog.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    name: row.name,
    url: row.url,
    venue: row.venue || '',
    platform: row.platform || '',
    monitor_interval: row.monitor_interval || 60,
    status: row.status || 'monitoring',
  })
  showDialog.value = true
}

async function handleSave() {
  if (!form.name || !form.url) {
    ElMessage.warning('请填写演出名称和链接')
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await concertAPI.update(editId.value, form)
      ElMessage.success('更新成功')
    } else {
      await concertAPI.create({
        name: form.name,
        url: form.url,
        venue: form.venue,
        platform: form.platform,
        monitor_interval: form.monitor_interval,
      })
      ElMessage.success('添加成功')
    }
    showDialog.value = false
    await loadConcerts()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定要删除「${row.name}」吗？`, '确认删除', { type: 'warning' })
  try {
    await concertAPI.delete(row.id)
    ElMessage.success('已删除')
    await loadConcerts()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

async function handleScrape(row) {
  scrapingId.value = row.id
  try {
    await concertAPI.scrape(row.id)
    ElMessage.success('数据采集完成')
    await loadConcerts()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '采集失败')
  } finally {
    scrapingId.value = null
  }
}

async function loadConcerts() {
  loading.value = true
  try {
    const res = await concertAPI.getList({
      page: page.value,
      page_size: pageSize.value,
      keyword: searchKeyword.value,
      status: statusFilter.value,
    })
    concertList.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadConcerts()
})
</script>
