import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 - 添加 Token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 统一错误处理
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      if (status === 401) {
        localStorage.removeItem('token')
        window.location.href = '/login'
        ElMessage.error('登录已过期，请重新登录')
      } else if (status === 403) {
        ElMessage.error('没有权限执行此操作')
      } else {
        ElMessage.error(data?.detail || '请求失败')
      }
    } else {
      ElMessage.error('网络连接异常')
    }
    return Promise.reject(error)
  }
)

// ============ API 接口 ============

// --- 认证 ---
export const authAPI = {
  login: (data) => api.post('/auth/login', data),
  logout: () => api.post('/auth/logout'),
  getInfo: () => api.get('/auth/me'),
}

// --- 演出管理 ---
export const concertAPI = {
  getList: (params) => api.get('/concerts', { params }),
  getDetail: (id) => api.get(`/concerts/${id}`),
  create: (data) => api.post('/concerts', data),
  update: (id, data) => api.put(`/concerts/${id}`, data),
  delete: (id) => api.delete(`/concerts/${id}`),
  scrape: (id) => api.post(`/concerts/${id}/scrape`),
}

// --- 监控管理 ---
export const monitorAPI = {
  getStatus: () => api.get('/monitor/status'),
  start: (data) => api.post('/monitor/start', data),
  startAll: () => api.post('/monitor/start-all'),
  stop: (id) => api.post(`/monitor/stop/${id}`),
  stopAll: () => api.post('/monitor/stop-all'),
  getLogs: (params) => api.get('/monitor/logs', { params }),
  getHistory: (params) => api.get('/monitor/history', { params }),
}

// --- 系统配置 ---
export const settingsAPI = {
  get: () => api.get('/settings'),
  update: (data) => api.put('/settings', data),
  testEmail: (data) => api.post('/settings/test-email', data),
  testWecom: (data) => api.post('/settings/test-wecom', data),
  testDingtalk: (data) => api.post('/settings/test-dingtalk', data),
}

export default api
